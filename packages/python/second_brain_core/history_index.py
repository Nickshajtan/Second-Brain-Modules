"""Authenticated, disposable SQLite locators; Git alone owns canonical records."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from .boundary import GENERATION, CoreError, digest
from .codec import decode
from .projection import ProjectionConnection, checked_write, memory_connection

MAX_DELTAS = 1024
MAX_DELTA_BYTES = 16 * 1024 * 1024

SCHEMA = """
PRAGMA user_version=2;
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
CREATE TABLE replay_scopes(receipt TEXT, position INTEGER, operation TEXT, kind TEXT, resource TEXT,
 PRIMARY KEY(receipt,position));
CREATE TABLE endpoints(node TEXT, relation TEXT, PRIMARY KEY(node,relation));
CREATE INDEX endpoint_relation ON endpoints(relation);
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
        self.accepted: dict | None = None
        self.pending: tuple[bytes, dict] | None = None
        self.in_candidate = False
        self.binding = dict(
            instance=self.boundary.context.instance_id,
            repository=str(self.store.repository),
            common=str(self.store.common),
            ref=self.store.ref,
            format=3,
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

    def enrollment_state(self, *, rebuilding: bool = False) -> dict:
        try:
            key = self.key_path.read_bytes()
            envelope = json.loads(self.enrollment.read_bytes())
            payload = envelope["payload"]
            if len(key) != 32 or not hmac.compare_digest(
                envelope["mac"], hmac.digest(key, _json(payload), "sha256").hex()
            ):
                self.fail("VERIFICATION_FAILED")
            if not self._binding(payload["binding"], rebuilding):
                self.fail("INDEX_IDENTITY_MISMATCH")
            return payload
        except HistoryIndexError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            self.fail("VERIFICATION_FAILED")

    def _binding(self, binding, rebuilding):
        if binding == self.binding:
            return True
        if dict(binding, format=3) == self.binding and binding.get("format") in (1, 2):
            if rebuilding:
                return True
            self.fail("INDEX_STALE")
        return False

    def anchor(self, *, rebuilding: bool = False) -> dict | None:
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
            if payload["binding"].get("format") == 3 and raw != _json(
                dict(payload=payload, mac=envelope["mac"])
            ):
                self.fail("VERIFICATION_FAILED")
            if not self._binding(payload["binding"], rebuilding) or not self._binding(
                self.enrollment_state(rebuilding=rebuilding)["binding"], rebuilding
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
            self._base_path(payload)
            raw = self.database.read_bytes()
            if hashlib.sha256(raw).hexdigest() != payload["database_sha256"]:
                self.fail("INDEX_CORRUPT")
            connection = memory_connection()
            connection.deserialize(raw)
            if connection.execute("PRAGMA user_version").fetchone() != (2,):
                self.fail("INDEX_IDENTITY_MISMATCH")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                self.fail("INDEX_CORRUPT")
            self._replay_deltas(connection, payload)
            connection.commit()
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
            self.accepted = {k: v for k, v in payload.items() if not k.startswith("_")}
        except HistoryIndexError:
            raise
        except FileNotFoundError:
            self.fail("INDEX_MISSING")
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, IndexError):
            self.fail("INDEX_CORRUPT")

    def coherent(self) -> None:
        """Disk metadata cannot become a signing oracle during publication."""
        payload = self.anchor()
        if (
            payload is None
            or payload["_raw"] != self.checkpoint_raw
            or payload["_key"] != self.key
            or payload["commit"] != self.frontier
        ):
            self.fail("INDEX_STALE")
        if not self.database.exists():
            self.fail("INDEX_MISSING")
        if payload["sequence"] > payload["base_sequence"]:
            raw = self._delta_bytes(payload["sequence"])
            if hashlib.sha256(raw).hexdigest() != payload["tail_hash"]:
                self.fail("INDEX_CORRUPT")

    @staticmethod
    def empty() -> sqlite3.Connection:
        connection = memory_connection()
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
        if self.pending is not None and connection is self.connection:
            self._publish_delta(connection, commit, generation)
            return
        connection.commit()
        raw = connection.serialize()
        previous = self.anchor(rebuilding=True) if self.checkpoint.exists() else None
        sequence = previous.get("sequence", 0) if previous else 0
        filename = f"history-{uuid4().hex}.sqlite3"
        database = self.directory / filename
        base_digest = hashlib.sha256(raw).hexdigest()
        previous_state = hashlib.sha256(previous["_raw"]).hexdigest() if previous else None
        base_state = self._base_state(filename, base_digest, commit, generation, sequence)
        payload = dict(
            binding=self.binding,
            commit=commit,
            generation=generation,
            database_sha256=base_digest,
            base_filename=filename,
            base_commit=commit,
            base_generation=generation,
            base_sequence=sequence,
            sequence=sequence,
            tail_hash=base_state,
            tail_bytes=0,
            base_previous_state=previous_state,
            previous_state=previous_state,
        )
        _atomic(database, raw)
        checkpoint_raw = _json(
            dict(payload=payload, mac=hmac.digest(key, _json(payload), "sha256").hex())
        )
        _atomic(self.checkpoint, checkpoint_raw)
        enrollment = self.enrollment_state(rebuilding=True)
        if not enrollment["complete"] or enrollment["binding"] != self.binding:
            self._enrollment(enrollment["initial"], True)
        connection.execute("PRAGMA query_only=ON")
        self.connection, self.frontier, self.generation = connection, commit, generation
        self.key, self.checkpoint_raw = key, checkpoint_raw
        self.database, self.accepted = database, payload

    def _signed(self, payload: dict) -> bytes:
        if self.key is None:
            self.fail("VERIFICATION_FAILED")
        return _json(
            dict(payload=payload, mac=hmac.digest(self.key, _json(payload), "sha256").hex())
        )

    @staticmethod
    def _base_state(filename, digest_value, commit, generation, sequence):
        return hashlib.sha256(
            _json([filename, digest_value, commit, generation, sequence])
        ).hexdigest()

    def _base_path(self, payload):
        name = payload["base_filename"]
        if not isinstance(name, str) or not re.fullmatch(r"history-[0-9a-f]{32}\.sqlite3", name):
            self.fail("INDEX_CORRUPT")
        self.database = self.directory / name

    def _delta_path(self, sequence: int) -> Path:
        return self.directory / f"delta-{sequence:020d}.json"

    def _delta_bytes(self, sequence: int) -> bytes:
        try:
            path = self._delta_path(sequence)
            if path.stat().st_size > MAX_DELTA_BYTES:
                self.fail("INDEX_CORRUPT")
            with path.open("rb") as handle:
                raw = handle.read(MAX_DELTA_BYTES + 1)
            if len(raw) > MAX_DELTA_BYTES:
                self.fail("INDEX_CORRUPT")
            return raw
        except OSError:
            self.fail("INDEX_CORRUPT")

    def _replay_deltas(self, connection, payload, previous=None):
        start, end, size = payload["base_sequence"], payload["sequence"], payload["tail_bytes"]
        if (
            type(start) is not int
            or type(end) is not int
            or type(size) is not int
            or start < 0
            or not 0 <= end - start <= MAX_DELTAS
            or not 0 <= size <= MAX_DELTA_BYTES
        ):
            self.fail("INDEX_CORRUPT")
        key = payload["_key"]
        state = {k: v for k, v in payload.items() if not k.startswith("_")}
        if previous is None:
            state.update(
                commit=payload["base_commit"],
                generation=payload["base_generation"],
                sequence=start,
                tail_bytes=0,
                previous_state=payload["base_previous_state"],
                tail_hash=self._base_state(
                    payload["base_filename"],
                    payload["database_sha256"],
                    payload["base_commit"],
                    payload["base_generation"],
                    start,
                ),
            )
        else:
            state = dict(previous)
            if not start <= state["sequence"] <= end:
                self.fail("INDEX_STALE")
        for sequence in range(state["sequence"] + 1, end + 1):
            previous_raw = _json(
                dict(payload=state, mac=hmac.digest(key, _json(state), "sha256").hex())
            )
            raw = self._delta_bytes(sequence)
            if state["tail_bytes"] + len(raw) > size:
                self.fail("INDEX_CORRUPT")
            envelope = json.loads(raw)
            delta = envelope["payload"]
            if (
                not hmac.compare_digest(
                    envelope["mac"], hmac.digest(key, _json(delta), "sha256").hex()
                )
                or delta["binding"] != self.binding
                or delta["sequence"] != sequence
                or delta["previous"] != state["tail_hash"]
                or delta["previous_state"] != hashlib.sha256(previous_raw).hexdigest()
                or not isinstance(delta["writes"], list)
                or raw != _json(dict(payload=delta, mac=envelope["mac"]))
            ):
                self.fail("INDEX_CORRUPT")
            for item in delta["writes"]:
                if not isinstance(item, list) or len(item) != 2:
                    self.fail("INDEX_CORRUPT")
                sql, parameters = checked_write(*item)
                connection.execute(sql, parameters)
            state.update(
                commit=delta["commit"],
                generation=delta["generation"],
                sequence=sequence,
                tail_hash=hashlib.sha256(raw).hexdigest(),
                tail_bytes=state["tail_bytes"] + len(raw),
                previous_state=hashlib.sha256(previous_raw).hexdigest(),
            )
        if state != {k: v for k, v in payload.items() if not k.startswith("_")}:
            self.fail("INDEX_CORRUPT")

    def refresh(self) -> None:
        """Refresh another trusted writer's bounded same-base tail without copying SQLite."""
        payload = self.anchor()
        if payload is None:
            self.fail("INDEX_MISSING")
        previous = self.accepted
        base_keys = (
            "binding",
            "base_filename",
            "database_sha256",
            "base_commit",
            "base_generation",
            "base_sequence",
            "base_previous_state",
        )
        if previous is None or any(payload[key] != previous[key] for key in base_keys):
            # A new immutable base is an explicit maintenance boundary, not an
            # ordinary writer advancement. Authenticate its complete bytes once.
            self.load()
            return
        if payload["_key"] != self.key or not isinstance(self.connection, ProjectionConnection):
            self.fail("VERIFICATION_FAILED")
        connection = self.connection
        self.in_candidate = True
        accepted = False
        try:
            connection.execute("PRAGMA query_only=OFF")
            connection.execute("SAVEPOINT projection_refresh")
            self._replay_deltas(connection, payload, previous)
            oid = self.store.locate(payload["commit"], GENERATION)
            if decode(self.store.blobs([oid])[oid]) != payload["generation"]:
                self.fail("CANONICAL_STATE_CORRUPT")
            connection.execute("RELEASE projection_refresh")
            self.accepted = {k: v for k, v in payload.items() if not k.startswith("_")}
            self.frontier, self.generation = payload["commit"], payload["generation"]
            self.checkpoint_raw = payload["_raw"]
            accepted = True
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, IndexError) as exc:
            raise HistoryIndexError(self.boundary.contracts, "INDEX_CORRUPT") from exc
        finally:
            if not accepted:
                connection.close()
                self.connection = None
            else:
                connection.execute("PRAGMA query_only=ON")
            self.in_candidate = False

    def _prepare_delta(self, commit, generation, writes):
        if self.accepted is None or self.checkpoint_raw is None:
            self.fail("INDEX_MISSING")
        old = self.accepted
        delta = dict(
            binding=self.binding,
            sequence=old["sequence"] + 1,
            previous=old["tail_hash"],
            previous_state=hashlib.sha256(self.checkpoint_raw).hexdigest(),
            commit=commit,
            generation=generation,
            writes=writes,
        )
        raw = self._signed(delta)
        if (
            old["sequence"] - old["base_sequence"] >= MAX_DELTAS
            or old["tail_bytes"] + len(raw) > MAX_DELTA_BYTES
        ):
            self.fail("INDEX_COMPACTION_REQUIRED")
        payload = dict(
            old,
            commit=commit,
            generation=generation,
            sequence=delta["sequence"],
            tail_hash=hashlib.sha256(raw).hexdigest(),
            tail_bytes=old["tail_bytes"] + len(raw),
            previous_state=delta["previous_state"],
        )
        return raw, payload

    def _publish_delta(self, connection, commit, generation):
        self.coherent()
        pending = self.pending
        if pending is None:
            self.fail("INDEX_STALE")
        raw, payload = pending
        if payload["commit"] != commit or payload["generation"] != generation:
            self.fail("INDEX_STALE")
        _atomic(self._delta_path(payload["sequence"]), raw)
        checkpoint_raw = self._signed(payload)
        _atomic(self.checkpoint, checkpoint_raw)
        connection.writes = None
        connection.execute("RELEASE projection_candidate")
        connection.execute("PRAGMA query_only=ON")
        self.accepted, self.frontier, self.generation = payload, commit, generation
        self.checkpoint_raw, self.pending = checkpoint_raw, None

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

    @contextmanager
    def request_blobs(self) -> Iterator[None]:
        previous = self.blob_cache
        self.blob_cache = {}
        try:
            yield
        finally:
            self.blob_cache = previous

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
                snapshot = record.get("snapshot")
                if snapshot and kind == "node_revision":
                    for (path,) in self.query(
                        "SELECT path FROM definitions WHERE kind='node_type_definition' AND key=? AND version=?",
                        (snapshot["node_type"], snapshot["node_type_version"]),
                    ):
                        pending.append(("node_type_definition", path.rsplit("/", 1)[1][:-5]))
                pending.append(
                    (
                        "node" if kind == "node_revision" else "relation",
                        record["node_id"] if kind == "node_revision" else record["relation_id"],
                    )
                )
            elif kind == "node_revision_snapshot":
                pending.append(("node_revision", record["revision_ref"]["revision_id"]))
                snapshot = record["snapshot"]
                pending.extend(
                    ("node_type_definition", path.rsplit("/", 1)[1][:-5])
                    for (path,) in self.query(
                        "SELECT path FROM definitions WHERE kind='node_type_definition' AND key=? AND version=?",
                        (snapshot["node_type"], snapshot["node_type_version"]),
                    )
                )
        return records

    def ensure(self, *, locked: bool = False) -> None:
        """Healthy lookup never traverses ancestry; only a changed ref catches up."""
        if self.in_candidate:
            self.fail("INDEX_STALE")
        if self.connection is not None:
            # Compact trust material is checked even when checkpoint bytes match.
            self.enrollment_state()
            try:
                if self.key_path.read_bytes() != self.key:
                    self.fail("VERIFICATION_FAILED")
            except OSError:
                self.fail("VERIFICATION_FAILED")
        self.store.require_complete()
        commit = self.store.resolve()
        if commit is None:
            self.fail("CANONICAL_STATE_CORRUPT")
        if self.connection is None:
            self.load()
        elif not self.checkpoint.exists() or self.checkpoint.read_bytes() != self.checkpoint_raw:
            self.refresh()
        if commit == self.frontier:
            return
        if not locked:
            with self.store.writer():
                self.ensure(locked=True)
            return
        with self.candidate(commit) as (connection, generation):
            self.publish(connection, commit, generation)

    @contextmanager
    def candidate(self, commit: str):
        from .verification import TransitionVerifier

        self.coherent()
        if self.in_candidate or not isinstance(self.connection, ProjectionConnection):
            self.fail("INDEX_STALE")
        if (
            self.accepted is None
            or self.accepted["sequence"] - self.accepted["base_sequence"] >= MAX_DELTAS
        ):
            self.fail("INDEX_COMPACTION_REQUIRED")
        connection = self.connection
        self.in_candidate = True
        accepted = False
        try:
            connection.execute("PRAGMA query_only=OFF")
            connection.execute("SAVEPOINT projection_candidate")
            connection.writes = []
            verifier = TransitionVerifier(self.repository, connection)
            verifier.index.blob_cache = self.blob_cache
            generation = verifier.verify(self.store.changes(self.frontier, commit))
            self.pending = self._prepare_delta(commit, generation, connection.writes)
            yield connection, generation
            if self.pending is not None:
                self.fail("INDEX_STALE")
            accepted = True
        finally:
            connection.writes = None
            if not accepted:
                try:
                    connection.execute("ROLLBACK TO projection_candidate")
                    connection.execute("RELEASE projection_candidate")
                except sqlite3.Error:
                    pass
                # Even an atomic replace that succeeds then raises must reload its
                # exact accepted bytes; never reuse a tentative or uncertain view.
                connection.close()
                self.connection = None
            else:
                connection.execute("PRAGMA query_only=ON")
            self.pending, self.in_candidate = None, False

    def compact(self) -> dict[str, object]:
        """Explicit trusted maintenance; never called by an ordinary mutation."""
        self.ensure(locked=True)
        self.coherent()
        if self.connection is None or self.frontier is None or self.generation is None:
            self.fail("INDEX_MISSING")
        commit, generation = self.frontier, self.generation
        self.publish(self.connection, commit, generation)
        return dict(
            status="compacted",
            source_commit=commit,
            generation=generation,
            database_bytes=self.database.stat().st_size,
        )

    def rebuild(self) -> dict[str, object]:
        """Explicit trusted caller owns writer lock; existing rollback anchor survives."""
        from .verification import TransitionVerifier

        self.store.require_complete()
        commit = self.store.resolve()
        if commit is None:
            self.fail("CANONICAL_STATE_CORRUPT")
        initial = None
        if self.checkpoint.exists():
            payload = self.anchor(rebuilding=True)
            if payload is None:
                self.fail("INDEX_MISSING")
            initial = payload["commit"]
        elif self.directory.exists():
            enrollment = self.enrollment_state(rebuilding=True)
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
                    "replay_scopes",
                    "endpoints",
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
