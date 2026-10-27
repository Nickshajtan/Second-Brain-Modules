"""Authenticated, disposable SQLite locators; Git alone owns canonical records."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path
from typing import NoReturn

from .boundary import GENERATION, CoreError, digest
from .codec import decode

SCHEMA = """
PRAGMA user_version=1;
CREATE TABLE files(path TEXT PRIMARY KEY, oid TEXT NOT NULL, sha TEXT NOT NULL);
CREATE TABLE resources(kind TEXT, id TEXT, path TEXT UNIQUE, attrs TEXT NOT NULL,
 PRIMARY KEY(kind,id));
CREATE TABLE revisions(id TEXT PRIMARY KEY, kind TEXT, resource TEXT, logical INTEGER,
 path TEXT UNIQUE, UNIQUE(kind,resource,logical));
CREATE TABLE definitions(kind TEXT, key TEXT, version TEXT, path TEXT UNIQUE,
 UNIQUE(kind,key,version));
CREATE TABLE memberships(node TEXT, path TEXT PRIMARY KEY);
CREATE INDEX membership_node ON memberships(node);
CREATE TABLE receipts(path TEXT PRIMARY KEY, principal TEXT, key TEXT, tx TEXT, origin TEXT,
 UNIQUE(principal,key), UNIQUE(principal,tx));
CREATE TABLE operation_keys(principal TEXT, operation TEXT, version TEXT, key TEXT, receipt TEXT,
 PRIMARY KEY(principal,operation,version,key));
CREATE TABLE effects(receipt TEXT, kind TEXT, id TEXT, path TEXT, oid TEXT, body TEXT,
 PRIMARY KEY(receipt,kind,id));
CREATE TABLE legacy(revision TEXT PRIMARY KEY, receipt TEXT, position INTEGER, kind TEXT);
CREATE TABLE immutable(path TEXT PRIMARY KEY, oid TEXT NOT NULL);
CREATE TABLE commits(oid TEXT PRIMARY KEY, parent TEXT, generation TEXT NOT NULL);
CREATE UNIQUE INDEX generation_identity ON commits(json_extract(generation,'$.generation_id'));
"""


class HistoryIndexError(CoreError):
    def __init__(self, contracts, category: str) -> None:
        self.category = category
        super().__init__(contracts, "REPAIR_REQUIRED")


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _atomic(path: Path, raw: bytes) -> None:
    temporary = path.with_name(path.name + ".prepared")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(temporary, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class HistoryIndex:
    """Only authenticated bytes are deserialized; no mutable disk SQL connection."""

    def __init__(self, repository) -> None:
        self.repository = repository
        self.boundary = repository.boundary
        self.store = repository.store
        suffix = hashlib.sha256(self.store.ref.encode()).hexdigest()[:20]
        self.directory = self.store.common / f"second-brain-history-{suffix}"
        self.database = self.directory / "history.sqlite3"
        self.checkpoint = self.directory / "checkpoint.json"
        self.key_path = self.directory / "checkpoint.key"
        self.enrollment = self.directory / "enrollment.json"
        self.connection: sqlite3.Connection | None = None
        self.frontier: str | None = None
        self.generation: dict[str, object] | None = None
        self.checkpoint_raw: bytes | None = None
        self.key: bytes | None = None
        self.blob_cache: dict[str, bytes] | None = None
        self.binding = dict(
            instance=self.boundary.context.instance_id,
            repository=str(self.store.repository),
            common=str(self.store.common),
            ref=self.store.ref,
            format=1,
            contracts=digest(self.boundary.contracts.schemas)["value"],
        )

    def fail(self, category: str) -> NoReturn:
        raise HistoryIndexError(self.boundary.contracts, category)

    def begin(self, commit: str) -> None:
        """Trusted first enrollment; an interrupted/lost anchor is never reset here."""
        if self.directory.exists():
            self.fail("VERIFICATION_FAILED")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        descriptor = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(os.urandom(32))
            handle.flush()
            os.fsync(handle.fileno())
        self.key = self.key_path.read_bytes()
        self._enrollment(commit, False)

    def _enrollment(self, commit: str, complete: bool) -> None:
        key = self.key_path.read_bytes()
        payload = dict(binding=self.binding, initial=commit, complete=complete)
        _atomic(
            self.enrollment,
            _json(dict(payload=payload, mac=hmac.digest(key, _json(payload), "sha256").hex())),
        )

    def enrollment_state(self) -> dict:
        try:
            key = self.key_path.read_bytes()
            envelope = json.loads(self.enrollment.read_bytes())
            payload = envelope["payload"]
            if len(key) != 32 or not hmac.compare_digest(
                envelope["mac"], hmac.digest(key, _json(payload), "sha256").hex()
            ):
                self.fail("VERIFICATION_FAILED")
            if payload["binding"] != self.binding:
                self.fail("INDEX_IDENTITY_MISMATCH")
            return payload
        except HistoryIndexError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            self.fail("VERIFICATION_FAILED")

    def anchor(self) -> dict | None:
        if not self.checkpoint.exists():
            if self.directory.exists():
                self.fail("VERIFICATION_FAILED")
            return None
        try:
            key = self.key_path.read_bytes()
            raw = self.checkpoint.read_bytes()
            envelope = json.loads(raw)
            payload = envelope["payload"]
            if len(key) != 32 or not hmac.compare_digest(
                envelope["mac"], hmac.digest(key, _json(payload), "sha256").hex()
            ):
                self.fail("VERIFICATION_FAILED")
            if (
                payload["binding"] != self.binding
                or self.enrollment_state()["binding"] != self.binding
            ):
                self.fail("INDEX_IDENTITY_MISMATCH")
            return {**payload, "_raw": raw, "_key": key}
        except HistoryIndexError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            self.fail("VERIFICATION_FAILED")

    def load(self) -> None:
        payload = self.anchor()
        if payload is None:
            self.fail("INDEX_MISSING")
        try:
            raw = self.database.read_bytes()
            if hashlib.sha256(raw).hexdigest() != payload["database_sha256"]:
                self.fail("INDEX_CORRUPT")
            connection = sqlite3.connect(":memory:")
            connection.deserialize(raw)
            if connection.execute("PRAGMA user_version").fetchone() != (1,):
                self.fail("INDEX_IDENTITY_MISMATCH")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                self.fail("INDEX_CORRUPT")
            generation = json.loads(
                connection.execute(
                    "SELECT generation FROM commits WHERE oid=?", (payload["commit"],)
                ).fetchone()[0]
            )
            if generation != payload["generation"]:
                self.fail("INDEX_CORRUPT")
            # Canonical source fence, not a SQLite verified boolean.
            generation_oid = self.store.locate(payload["commit"], GENERATION)
            actual = decode(self.store.blobs([generation_oid])[generation_oid])
            if actual != generation:
                self.fail("CANONICAL_STATE_CORRUPT")
            connection.execute("PRAGMA query_only=ON")
            self.connection, self.frontier, self.generation = (
                connection,
                payload["commit"],
                generation,
            )
            self.key, self.checkpoint_raw = payload["_key"], payload["_raw"]
        except HistoryIndexError:
            raise
        except FileNotFoundError:
            self.fail("INDEX_MISSING")
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, IndexError):
            self.fail("INDEX_CORRUPT")

    def coherent(self) -> None:
        """Disk metadata cannot become a signing oracle during publication."""
        payload = self.anchor()
        if payload is None or payload["commit"] != self.frontier:
            self.fail("INDEX_STALE")
        try:
            if hashlib.sha256(self.database.read_bytes()).hexdigest() != payload["database_sha256"]:
                self.fail("INDEX_CORRUPT")
        except OSError:
            self.fail("INDEX_MISSING")

    @staticmethod
    def empty() -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        connection.executescript(SCHEMA)
        return connection

    def fork(self) -> sqlite3.Connection:
        if self.connection is None:
            self.fail("INDEX_MISSING")
        connection = sqlite3.connect(":memory:")
        connection.deserialize(self.connection.serialize())
        return connection

    def publish(self, connection: sqlite3.Connection, commit: str, generation: dict) -> None:
        """Caller owns writer lock and already verified canonical source fence."""
        if self.store.resolve() != commit:
            self.fail("INDEX_STALE")
        key = self.key_path.read_bytes()
        if len(key) != 32:
            self.fail("INDEX_CORRUPT")
        connection.commit()
        raw = connection.serialize()
        payload = dict(
            binding=self.binding,
            commit=commit,
            generation=generation,
            database_sha256=hashlib.sha256(raw).hexdigest(),
        )
        _atomic(self.database, raw)
        checkpoint_raw = _json(
            dict(payload=payload, mac=hmac.digest(key, _json(payload), "sha256").hex())
        )
        _atomic(self.checkpoint, checkpoint_raw)
        enrollment = self.enrollment_state()
        if not enrollment["complete"]:
            self._enrollment(enrollment["initial"], True)
        connection.execute("PRAGMA query_only=ON")
        self.connection, self.frontier, self.generation = connection, commit, generation
        self.key, self.checkpoint_raw = key, checkpoint_raw

    def query(self, sql: str, parameters=()):
        if self.connection is None:
            self.fail("INDEX_MISSING")
        return self.connection.execute(sql, parameters).fetchall()

    def files(self) -> dict[str, tuple[str, str]]:
        return {path: (oid, sha) for path, oid, sha in self.query("SELECT path,oid,sha FROM files")}

    def resource_metadata(self, kind: str, identifier: str) -> dict | None:
        rows = self.query("SELECT attrs FROM resources WHERE kind=? AND id=?", (kind, identifier))
        return json.loads(rows[0][0]) if rows else None

    def membership_metadata(self, node: str) -> list[dict]:
        return [
            json.loads(attrs)
            for (attrs,) in self.query(
                "SELECT r.attrs FROM memberships m JOIN resources r ON r.path=m.path WHERE m.node=?",
                (node,),
            )
        ]

    def raw(self, path: str) -> bytes:
        rows = self.query("SELECT oid FROM files WHERE path=?", (path,))
        if not rows:
            self.fail("CANONICAL_STATE_CORRUPT")
        oid = rows[0][0]
        if self.blob_cache is not None and oid in self.blob_cache:
            return self.blob_cache[oid]
        raw = self.store.blobs([oid])[oid]
        if self.blob_cache is not None:
            self.blob_cache[oid] = raw
        return raw

    def record(self, kind: str, identifier: str) -> dict | None:
        rows = self.query("SELECT path FROM resources WHERE kind=? AND id=?", (kind, identifier))
        if not rows:
            return None
        record = decode(self.raw(rows[0][0]))
        if kind == "node":
            record["content"]["body"] = self.raw(f"knowledge/node/{identifier}.md").decode()
        self.boundary.contracts.parse("knowledge", record)
        if record["kind"] != kind or record["id"] != identifier:
            self.fail("CANONICAL_STATE_CORRUPT")
        return record

    def closure(self, targets: list[tuple[str, str]]) -> dict:
        records, pending = {}, list(targets)
        while pending:
            kind, identifier = pending.pop()
            if (kind, identifier) in records:
                continue
            record = self.record(kind, identifier)
            if record is None:
                continue
            records[kind, identifier] = record
            if kind == "node":
                pending.append(("node_revision", record["revision_ref"]["revision_id"]))
                for (path,) in self.query(
                    "SELECT path FROM memberships WHERE node=?", (identifier,)
                ):
                    pending.append(("membership", path.rsplit("/", 1)[1][:-5]))
                key = (
                    "node_type_definition",
                    record["content"]["node_type"],
                    record["content"]["node_type_version"],
                )
                for (path,) in self.query(
                    "SELECT path FROM definitions WHERE kind=? AND key=? AND version=?", key
                ):
                    pending.append((key[0], path.rsplit("/", 1)[1][:-5]))
            elif kind == "membership":
                pending.extend([("cluster", record["cluster_id"]), ("node", record["node_id"])])
            elif kind == "relation":
                pending.extend(
                    [
                        ("cluster", record["owner_cluster_id"]),
                        ("node", record["source"]["id"]),
                        ("node", record["target"]["id"]),
                    ]
                )
                for (path,) in self.query(
                    "SELECT path FROM revisions WHERE kind='relation_revision' AND resource=? AND logical=?",
                    (identifier, record["revision"]),
                ):
                    pending.append(("relation_revision", path.rsplit("/", 1)[1][:-5]))
                for (path,) in self.query(
                    "SELECT path FROM definitions WHERE kind='relation_type_definition' AND key=? AND version=?",
                    (record["predicate"], record["predicate_version"]),
                ):
                    pending.append(("relation_type_definition", path.rsplit("/", 1)[1][:-5]))
            elif kind in {"node_revision", "relation_revision"}:
                pending.append(
                    (
                        "node" if kind == "node_revision" else "relation",
                        record["node_id"] if kind == "node_revision" else record["relation_id"],
                    )
                )
            elif kind == "node_revision_snapshot":
                pending.append(("node_revision", record["revision_ref"]["revision_id"]))
        return records

    def ensure(self, *, locked: bool = False) -> None:
        """Healthy lookup never traverses ancestry; only a changed ref catches up."""
        self.store.require_complete()
        commit = self.store.resolve()
        if commit is None:
            self.fail("CANONICAL_STATE_CORRUPT")
        if (
            self.connection is None
            or not self.checkpoint.exists()
            or self.checkpoint.read_bytes() != self.checkpoint_raw
        ):
            self.load()
        if commit == self.frontier:
            return
        if not locked:
            with self.store.writer():
                self.ensure(locked=True)
            return
        self.coherent()
        from .verification import TransitionVerifier

        changes = self.store.changes(self.frontier, commit)
        connection = self.fork()
        generation = TransitionVerifier(self.repository, connection).verify(changes)
        self.publish(connection, commit, generation)

    def candidate(self, commit: str):
        from .verification import TransitionVerifier

        self.coherent()
        connection = self.fork()
        generation = TransitionVerifier(self.repository, connection).verify(
            self.store.changes(self.frontier, commit)
        )
        return connection, generation

    def rebuild(self) -> dict[str, object]:
        """Explicit trusted caller owns writer lock; existing rollback anchor survives."""
        from .verification import TransitionVerifier

        self.store.require_complete()
        commit = self.store.resolve()
        if commit is None:
            self.fail("CANONICAL_STATE_CORRUPT")
        initial = None
        if self.checkpoint.exists():
            payload = self.anchor()
            if payload is None:
                self.fail("INDEX_MISSING")
            initial = payload["commit"]
        elif self.directory.exists():
            enrollment = self.enrollment_state()
            if enrollment["complete"]:
                self.fail("VERIFICATION_FAILED")
            initial = enrollment["initial"]
        if initial is not None:
            self.store.changes(initial, commit)
        connection = self.empty()
        changes = self.store.changes(None, commit)
        generation = TransitionVerifier(self.repository, connection).verify(changes)
        if self.store.resolve() != commit:
            self.fail("INDEX_STALE")
        if not self.key_path.exists():
            self.begin(commit)
        self.publish(connection, commit, generation)
        return dict(
            status="rebuilt",
            source_commit=commit,
            generation=generation,
            commits_verified=len(changes),
            database_bytes=self.database.stat().st_size,
        )

    def audit(self) -> dict[str, object]:
        from .verification import TransitionVerifier

        commit = self.store.resolve()
        if commit is None:
            self.fail("CANONICAL_STATE_CORRUPT")
        anchor = self.anchor()
        if anchor is not None:
            self.store.changes(anchor["commit"], commit)
        connection = self.empty()
        changes = self.store.changes(None, commit)
        generation = TransitionVerifier(self.repository, connection).verify(changes)
        diagnostic = "INDEX_MISSING"
        if self.database.exists():
            try:
                self.load()
                if self.connection is None:
                    self.fail("INDEX_MISSING")
                diagnostic = "INDEX_STALE" if self.frontier != commit else "OK"
                if self.frontier == commit:
                    for table in (
                        "files",
                        "resources",
                        "revisions",
                        "definitions",
                        "memberships",
                        "receipts",
                        "operation_keys",
                        "effects",
                        "legacy",
                        "immutable",
                        "commits",
                    ):
                        expected = sorted(
                            connection.execute(f"SELECT * FROM {table}").fetchall(), key=repr
                        )
                        actual = sorted(
                            self.connection.execute(f"SELECT * FROM {table}").fetchall(), key=repr
                        )
                        if actual != expected:
                            diagnostic = "INDEX_CORRUPT"
                            break
            except HistoryIndexError as exc:
                diagnostic = exc.category
        return dict(
            status="verified",
            source_commit=commit,
            generation=generation,
            commits_verified=len(changes),
            index_status=diagnostic,
            rebuild_recommended=diagnostic != "OK",
        )
