"""Ordered committed transitions establish the disposable verification frontier."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from uuid import UUID

from jsonschema.exceptions import SchemaError, ValidationError

from .boundary import GENERATION, VERSION, CoreError, digest
from .codec import decode
from .history import HISTORY
from .history_index import HistoryIndex, HistoryIndexError

IMMUTABLE = (
    "control/receipts/",
    "control/requests/",
    "knowledge/node_revision/",
    "knowledge/relation_revision/",
    "knowledge/node_revision_snapshot/",
)


class TransitionVerifier:
    def __init__(self, repository, connection: sqlite3.Connection) -> None:
        self.repository = repository
        self.index = HistoryIndex(repository)
        self.index.connection = connection
        self.connection = connection
        self.boundary = repository.boundary
        self.store = repository.store

    def fail(self, category="CANONICAL_STATE_CORRUPT"):
        self.index.fail(category)

    def _raw(self, path):
        return self.index.raw(path)

    def _insert(self, record, path):
        kind, identifier = record["kind"], record["id"]
        attrs = {
            key: record[key]
            for key in (
                "node_id",
                "cluster_id",
                "owner_cluster_id",
                "source",
                "target",
                "lifecycle",
                "publication_mode",
            )
            if key in record
        }
        self.connection.execute("DELETE FROM resources WHERE path=?", (path,))
        self.connection.execute(
            "INSERT INTO resources VALUES(?,?,?,?)", (kind, identifier, path, json.dumps(attrs))
        )
        for table in ("memberships", "definitions", "revisions"):
            self.connection.execute(f"DELETE FROM {table} WHERE path=?", (path,))
        if kind == "membership":
            self.connection.execute(
                "INSERT INTO memberships VALUES(?,?)", (record["node_id"], path)
            )
        elif kind in {"node_type_definition", "relation_type_definition"}:
            self.connection.execute(
                "INSERT INTO definitions VALUES(?,?,?,?)",
                (
                    kind,
                    record.get("type_key", record.get("predicate")),
                    record["type_version"],
                    path,
                ),
            )
        elif kind in {"node_revision", "relation_revision"}:
            self.connection.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?)",
                (
                    identifier,
                    kind,
                    record.get("node_id", record.get("relation_id")),
                    record["logical_revision"],
                    path,
                ),
            )

    def _generation(self, content_digest=None):
        generation = decode(self._raw(GENERATION))
        schema = self.boundary.contracts.schemas["common"]["$defs"]["GenerationRef"]
        self.boundary.contracts.validators["common"].evolve(schema=schema).validate(generation)
        if content_digest is None:
            values = {
                path: sha
                for path, sha in self.connection.execute("SELECT path,sha FROM files")
                if path.startswith("knowledge/") or path == "control/metadata.json"
            }
            content_digest = digest(values)
        if (
            generation["instance_id"] != self.boundary.context.instance_id
            or generation["digest"] != content_digest
        ):
            self.fail()
        return generation

    def verify(self, changes) -> dict:
        # Explicit verification owns this bounded-lifetime unique-blob cache;
        # ordinary lookups never prefetch canonical history.
        oids = {oid for _, _, delta in changes for oid in delta.values() if oid}
        self.index.blob_cache = self.store.blobs(list(oids))
        generation = None
        for commit, parent, delta in changes:
            try:
                generation = self.transition(commit, parent, delta)
            except HistoryIndexError:
                raise
            except (CoreError, SchemaError, ValidationError) as exc:
                raise HistoryIndexError(self.boundary.contracts, "CANONICAL_STATE_CORRUPT") from exc
        if generation is None:
            self.fail("VERIFICATION_FAILED")
        return generation

    def transition(self, commit, parent, delta):
        old_generation = None
        if parent:
            rows = self.connection.execute(
                "SELECT generation FROM commits WHERE oid=?", (parent,)
            ).fetchall()
            if not rows:
                self.fail("MISSING_ANCESTOR")
            old_generation = json.loads(rows[0][0])
        previous = {
            path: oid for path, oid in self.connection.execute("SELECT path,oid FROM files")
        }
        obligations = dict(self.connection.execute("SELECT path,oid FROM immutable"))
        for path, oid in delta.items():
            if path in obligations and obligations[path] != oid:
                self.fail(
                    "INVALID_RECEIPT"
                    if path.startswith("control/")
                    else ("MISSING_REVISION" if oid is None else "REVISION_DIGEST_MISMATCH")
                )
        required = {oid for oid in delta.values() if oid}
        blobs = self.index.blob_cache or self.store.blobs(list(required))
        changed = {}
        affected = []
        for path, oid in delta.items():
            if path.startswith("knowledge/"):
                parts = path.split("/")
                if len(parts) != 3 or not (
                    path.endswith(".yaml") or (parts[1] == "node" and path.endswith(".md"))
                ):
                    self.fail()
            elif path not in {GENERATION, HISTORY, "control/metadata.json"} and not (
                path.startswith(("control/receipts/", "control/requests/"))
                and path.endswith(".json")
                and len(path.split("/")) == 3
            ):
                self.fail()
            if oid is None:
                if path.startswith("knowledge/node/") and path.endswith(".md"):
                    self.fail()
                rows = self.connection.execute(
                    "SELECT kind,id,attrs FROM resources WHERE path=?", (path,)
                ).fetchall()
                for kind, identifier, attrs in rows:
                    affected.append((kind, identifier))
                    if kind in {"node", "relation"}:
                        affected.extend(
                            self.connection.execute(
                                "SELECT kind,id FROM revisions WHERE resource=?", (identifier,)
                            ).fetchall()
                        )
                    data = json.loads(attrs)
                    if data.get("node_id"):
                        affected.append(("node", data["node_id"]))
                self.connection.execute("DELETE FROM files WHERE path=?", (path,))
                for table in ("resources", "memberships", "definitions", "revisions"):
                    self.connection.execute(f"DELETE FROM {table} WHERE path=?", (path,))
            else:
                raw = blobs[oid]
                self.connection.execute(
                    "INSERT OR REPLACE INTO files VALUES(?,?,?)",
                    (path, oid, hashlib.sha256(raw).hexdigest()),
                )
                if path.startswith("knowledge/") and path.endswith(".yaml"):
                    changed[path] = decode(raw)
                elif path.startswith("knowledge/node/") and path.endswith(".md"):
                    target = path[:-3] + ".yaml"
                    changed.setdefault(target, None)
        for path, record in list(changed.items()):
            record = record or decode(self._raw(path))
            kind, identifier = record["kind"], record["id"]
            if path != f"knowledge/{kind}/{identifier}.yaml":
                self.fail()
            if kind == "node":
                record["content"]["body"] = self._raw(f"knowledge/node/{identifier}.md").decode()
            self.boundary.contracts.parse("knowledge", record)
            if (
                kind in {"node_revision", "relation_revision", "node_revision_snapshot"}
                and "snapshot" in record
                and record["digest"] != digest(record["snapshot"])
            ):
                self.fail("REVISION_DIGEST_MISMATCH")
            if kind == "membership":
                old = self.connection.execute(
                    "SELECT attrs FROM resources WHERE path=?", (path,)
                ).fetchone()
                if old:
                    affected.append(("node", json.loads(old[0])["node_id"]))
            self._insert(record, path)
            affected.append((kind, identifier))
            changed[path] = record
        unchanged = old_generation is not None and not any(
            path.startswith("knowledge/") or path == "control/metadata.json" for path in delta
        )
        content_digest = (
            old_generation["digest"] if old_generation is not None and unchanged else None
        )
        generation = self._generation(content_digest)
        try:
            self.connection.execute(
                "INSERT INTO commits VALUES(?,?,?)", (commit, parent, json.dumps(generation))
            )
        except sqlite3.IntegrityError as exc:
            raise HistoryIndexError(self.boundary.contracts, "AMBIGUOUS_ORIGIN") from exc
        metadata = decode(self._raw("control/metadata.json"))
        self.repository.domain.metadata(metadata)
        if "control/metadata.json" in delta or any(
            "/node_type_definition/" in p or "/relation_type_definition/" in p or "/cluster/" in p
            for p in delta
        ):
            affected.extend(self.connection.execute("SELECT kind,id FROM resources").fetchall())
        records = self.index.closure(affected)
        self.repository.domain.validate(records, metadata)
        explained = set()
        for path in delta:
            if path.startswith("control/receipts/") and delta[path]:
                if path in previous or parent is None:
                    self.fail("INVALID_RECEIPT")
                explained.update(self._receipt(path, commit, generation, old_generation, previous))
        marked = bool(
            self.connection.execute("SELECT 1 FROM files WHERE path=?", (HISTORY,)).fetchone()
        )
        if delta.get(HISTORY):
            marker = decode(self._raw(HISTORY))
            self.boundary.contracts.parse("transaction", marker)
            if (
                marker["kind"] != "history_baseline"
                or marker["instance_id"] != self.boundary.context.instance_id
                or marker["generation"] != generation
            ):
                self.fail("MIGRATION_CONFLICT")
            if marker["mode"] == "fresh":
                if parent or marker["additions"] or marker["effects_digest"] != digest({}):
                    self.fail("MIGRATION_CONFLICT")
            else:
                additions = self._recovered()
                additions = {
                    path: record for path, record in additions.items() if path not in previous
                }
                if (
                    marker["source_commit"] != parent
                    or marker["source_generation"] != old_generation
                    or marker["additions"] != sorted(additions)
                    or marker["effects_digest"] != digest(additions)
                    or marker["plan_digest"]
                    != digest(
                        dict(
                            source_commit=parent,
                            source_generation=old_generation,
                            additions=additions,
                        )
                    )
                ):
                    self.fail("MIGRATION_CONFLICT")
                if any(
                    path != GENERATION and path != HISTORY and path not in additions
                    for path in delta
                ):
                    self.fail("MIGRATION_CONFLICT")
                if any(changed.get(path) != record for path, record in additions.items()):
                    self.fail("MIGRATION_CONFLICT")
                explained.update(additions)
        for path, record in changed.items():
            if (
                record["kind"] in {"node_revision", "relation_revision", "node_revision_snapshot"}
                and path not in previous
                and path not in explained
            ):
                self.fail("MISSING_REVISION")
            if (
                record["kind"] in {"node", "relation", "membership"}
                and path not in previous
                and path not in explained
            ):
                self.fail("INVALID_RECEIPT")
        for path, oid in delta.items():
            if oid and (path.startswith(IMMUTABLE) or path == HISTORY):
                self.connection.execute("INSERT INTO immutable VALUES(?,?)", (path, oid))
        # Requests cannot be introduced without their exact receipt pair.
        for path, oid in delta.items():
            if oid and path.startswith("control/requests/"):
                receipt = path.replace("/requests/", "/receipts/")
                if receipt not in delta or not delta[receipt]:
                    self.fail("INVALID_RECEIPT")
        if (
            marked
            and self.connection.execute(
                "SELECT 1 FROM legacy WHERE revision NOT IN (SELECT id FROM revisions) AND kind='relation_revision'"
            ).fetchone()
        ):
            self.fail("MISSING_REVISION")
        return generation

    def _receipt(self, path, commit, generation, parent_generation, previous):
        files = {path: self._raw(path)}
        request_path = self.repository.receipts.request_path(path)
        files[request_path] = self._raw(request_path)
        self.repository.receipts.validate_pair(path, files)
        receipt, request = decode(files[path]), decode(files[request_path])
        if (
            receipt["generation"] != generation
            or request["expected_generation"] != parent_generation
        ):
            self.fail("INVALID_RECEIPT")
        principal = receipt["actor"]["principal_id"]
        self.connection.execute(
            "INSERT INTO receipts VALUES(?,?,?,?,?)",
            (path, principal, receipt["idempotency_key"], receipt["transaction_id"], commit),
        )
        explained = set()
        for position, (operation, result) in enumerate(
            zip(request["operations"], receipt["results"], strict=True)
        ):
            self.connection.execute(
                "INSERT INTO operation_keys VALUES(?,?,?,?,?)",
                (
                    principal,
                    operation["operation"],
                    operation["operation_version"],
                    operation["idempotency_key"],
                    path,
                ),
            )
            targets = [(r["resource_kind"], r["id"]) for r in result["resources"]]
            targets.extend(
                (
                    "node_revision"
                    if r["resource"]["resource_kind"] == "node"
                    else "relation_revision",
                    r["revision_id"],
                )
                for r in result["revisions"]
            )
            records = self.index.closure(targets)
            strategy = self.repository.receipts.strategies.get(operation["operation"])
            if strategy is None:
                self.fail("INVALID_RECEIPT")
            strategy.verify_result(operation, result, receipt, records)
            for kind, identifier in targets:
                target = f"knowledge/{kind}/{identifier}.yaml"
                if target in previous:
                    self.fail("INVALID_RECEIPT")
                row = self.connection.execute(
                    "SELECT oid FROM files WHERE path=?", (target,)
                ).fetchone()
                if row:
                    body = None
                    if kind == "node":
                        body = self.connection.execute(
                            "SELECT oid FROM files WHERE path=?",
                            (f"knowledge/node/{identifier}.md",),
                        ).fetchone()[0]
                    self.connection.execute(
                        "INSERT INTO effects VALUES(?,?,?,?,?,?)",
                        (path, kind, identifier, target, row[0], body),
                    )
                    explained.add(target)
            ref = result["revisions"][0]
            node = operation["operation"] == "node.create"
            kind = "node_revision" if node else "relation_revision"
            revision = records.get((kind, ref["revision_id"]))
            if revision is None or (node and "snapshot" not in revision):
                if self.connection.execute(
                    "SELECT 1 FROM files WHERE path=?", (HISTORY,)
                ).fetchone():
                    self.fail("MISSING_REVISION")
                self.connection.execute(
                    "INSERT INTO legacy VALUES(?,?,?,?)", (ref["revision_id"], path, position, kind)
                )
        return explained

    def original_records(self, path):
        rows = self.connection.execute(
            "SELECT kind,id,oid,body FROM effects WHERE receipt=?", (path,)
        ).fetchall()
        oids = [oid for _, _, oid, _ in rows] + [body for _, _, _, body in rows if body]
        blobs = dict(self.index.blob_cache or {})
        missing = list(set(oids) - blobs.keys())
        blobs.update(self.store.blobs(missing))
        records = {}
        for kind, identifier, oid, body in rows:
            record = decode(blobs[oid])
            if body:
                record["content"]["body"] = blobs[body].decode()
            self.boundary.contracts.parse("knowledge", record)
            records[kind, identifier] = record
        return records

    def _recovered(self):
        additions = {}
        for revision, path, position, kind in self.connection.execute(
            "SELECT revision,receipt,position,kind FROM legacy"
        ).fetchall():
            receipt = decode(self._raw(path))
            original = self.original_records(path)
            result = receipt["results"][position]
            ref = result["revisions"][0]
            if kind == "node_revision":
                node = original["node", ref["resource"]["id"]]
                history = original[kind, revision]
                record = dict(
                    kind="node_revision_snapshot",
                    id=str(
                        UUID(
                            hex=digest(
                                [
                                    "node-revision-snapshot",
                                    self.boundary.context.instance_id,
                                    revision,
                                ]
                            )["value"][:32],
                            version=4,
                        )
                    ),
                    schema_version=VERSION,
                    revision_ref=ref,
                    snapshot=node["content"],
                    digest=history["digest"],
                    source_generation=receipt["generation"],
                )
            else:
                relation = original["relation", ref["resource"]["id"]]
                record = dict(
                    kind=kind,
                    id=revision,
                    schema_version=VERSION,
                    relation_id=relation["id"],
                    logical_revision=1,
                    snapshot=relation,
                    digest=digest(relation),
                    recorded_by=receipt["actor"],
                    recorded_at=receipt["committed_at"],
                )
            additions[f"knowledge/{record['kind']}/{record['id']}.yaml"] = record
        return additions
