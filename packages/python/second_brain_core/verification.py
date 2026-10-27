"""Ordered committed transitions establish the disposable verification frontier."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from uuid import UUID

from jsonschema.exceptions import SchemaError, ValidationError

from .boundary import GENERATION, VERSION, CoreError, digest
from .codec import decode
from .commitment import SCHEME, ContentCommitment, covered
from .history import HISTORY
from .history_index import HistoryIndex, HistoryIndexError

IMMUTABLE = (
    "control/receipts/",
    "control/requests/",
    "knowledge/node_revision/",
    "knowledge/relation_revision/",
    "knowledge/node_revision_snapshot/",
)


class PreviousFiles:
    """Pin changed-path prestates; other paths remain unchanged in this transition."""

    def __init__(self, connection: sqlite3.Connection, changed: dict) -> None:
        self.connection = connection
        self.values: dict[str, str | None] = {}
        for path in changed:
            self.get(path)

    def get(self, path: str) -> str | None:
        if path not in self.values:
            row = self.connection.execute("SELECT oid FROM files WHERE path=?", (path,)).fetchone()
            self.values[path] = row[0] if row else None
        return self.values[path]

    def __contains__(self, path: str) -> bool:
        return self.get(path) is not None

    def __getitem__(self, path: str) -> str:
        result = self.get(path)
        if result is None:
            raise KeyError(path)
        return result


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
        if kind == "node_revision_snapshot":
            attrs["revision_id"] = record["revision_ref"]["revision_id"]
        if kind == "relation":
            self.connection.execute("DELETE FROM endpoints WHERE relation=?", (identifier,))
            for node in {record["source"]["id"], record["target"]["id"]}:
                self.connection.execute("INSERT INTO endpoints VALUES(?,?)", (node, identifier))
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
        if generation.get("commitment_scheme") == SCHEME:
            content_digest = ContentCommitment(
                self.connection, self.boundary.context.instance_id
            ).update({})
        elif content_digest is None:
            values = dict(
                self.connection.execute(
                    "SELECT path,sha FROM files WHERE path GLOB 'knowledge/*' OR path='control/metadata.json'"
                )
            )
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
        cached = self.index.blob_cache
        self.index.blob_cache = cached if cached is not None else {}
        self.index.blob_cache.update(self.store.blobs(list(oids - self.index.blob_cache.keys())))
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
        previous = PreviousFiles(self.connection, delta)
        for path, oid in delta.items():
            obligation = self.connection.execute(
                "SELECT oid FROM immutable WHERE path=?", (path,)
            ).fetchone()
            if obligation and obligation[0] != oid:
                self.fail(
                    "INVALID_RECEIPT"
                    if path.startswith("control/")
                    else ("MISSING_REVISION" if oid is None else "REVISION_DIGEST_MISMATCH")
                )
        prior_nodes = {}
        for path in delta:
            if path.startswith("knowledge/node/") and path.endswith(".yaml") and path in previous:
                identifier = path.rsplit("/", 1)[1][:-5]
                prior_nodes[identifier] = self.index.record("node", identifier)
        self.prior_nodes = prior_nodes
        # Registered interpretation is append-only in the supported M2 profile.
        for path, oid in delta.items():
            if (
                path in previous
                and path.startswith(
                    ("knowledge/node_type_definition/", "knowledge/relation_type_definition/")
                )
                and oid != previous[path]
            ):
                self.fail("CANONICAL_STATE_CORRUPT")
        metadata_path = "control/metadata.json"
        if parent and metadata_path in delta:
            old_metadata = decode(self._raw(metadata_path))
            new_oid = delta[metadata_path]
            if not new_oid:
                self.fail("CANONICAL_STATE_CORRUPT")
            cache = self.index.blob_cache or {}
            new_raw = cache.get(new_oid)
            if new_raw is None:
                new_raw = self.store.blobs([new_oid])[new_oid]
            new_metadata = decode(new_raw)
            if any(
                key not in new_metadata or new_metadata[key] != value
                for key, value in old_metadata.items()
            ):
                self.fail("CANONICAL_STATE_CORRUPT")
        required = {oid for oid in delta.values() if oid}
        blobs = self.index.blob_cache or self.store.blobs(list(required))
        changed = {}
        affected = []
        commitment_changes = {}
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
                if covered(path):
                    commitment_changes[path] = None
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
                sha = hashlib.sha256(raw).hexdigest()
                if covered(path):
                    commitment_changes[path] = sha
                self.connection.execute(
                    "INSERT OR REPLACE INTO files VALUES(?,?,?)",
                    (path, oid, sha),
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
        ContentCommitment(self.connection, self.boundary.context.instance_id).update(
            commitment_changes, apply=True
        )
        next_generation = decode(self._raw(GENERATION))
        old_scheme = old_generation.get("commitment_scheme") if old_generation else None
        next_scheme = next_generation.get("commitment_scheme")
        if old_scheme and old_scheme != next_scheme:
            self.fail()
        if old_generation and not old_scheme and next_scheme and set(delta) != {GENERATION}:
            self.fail()
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
        for identifier, prior in self.prior_nodes.items():
            current = changed.get(f"knowledge/node/{identifier}.yaml")
            if current and current["content"]["node_type"] != prior["content"]["node_type"]:
                affected.extend(
                    ("relation", relation)
                    for (relation,) in self.connection.execute(
                        "SELECT relation FROM endpoints WHERE node=?", (identifier,)
                    )
                )
        records = self.index.closure(affected)
        self.repository.domain.validate(records, metadata, bounded=True)
        explained = set()
        for path in delta:
            if path.startswith("control/receipts/") and delta[path]:
                if path in previous or parent is None:
                    self.fail("INVALID_RECEIPT")
                effects = self._receipt(path, commit, generation, old_generation, previous)
                if explained & effects:
                    self.fail("INVALID_RECEIPT")
                explained.update(effects)
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
                and parent is not None
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

    def _expectations(self, operation, previous, overlay, originals):
        if operation["instance_id"] != self.boundary.context.instance_id:
            self.fail("INVALID_RECEIPT")
        for expectation in operation["expectations"]:
            resource = expectation["resource"]
            kind, identifier = resource["resource_kind"], resource["id"]
            if resource["instance_id"] != self.boundary.context.instance_id or kind not in {
                "cluster",
                "node",
                "relation",
            }:
                self.fail("INVALID_RECEIPT")
            key = kind, identifier
            if key in overlay:
                record = overlay[key]
            else:
                if key not in originals:
                    path = f"knowledge/{kind}/{identifier}.yaml"
                    oid = previous.get(path)
                    body = (
                        previous.get(f"knowledge/node/{identifier}.md") if kind == "node" else None
                    )
                    if not oid or (kind == "node" and not body):
                        self.fail("INVALID_RECEIPT")
                    cache = self.index.blob_cache
                    if cache is None:
                        cache = self.index.blob_cache = {}
                    required = {oid} | ({body} if body else set())
                    cache.update(self.store.blobs(list(required - cache.keys())))
                    record = decode(cache[oid])
                    if body:
                        record["content"]["body"] = cache[body].decode()
                    self.boundary.contracts.parse("knowledge", record)
                    if (record["kind"], record["id"]) != key:
                        self.fail("INVALID_RECEIPT")
                    originals[key] = record
                record = originals[key]
            if record["revision"] != expectation["expected_revision"] or (
                "expected_digest" in expectation
                and digest(record) != expectation["expected_digest"]
            ):
                self.fail("INVALID_RECEIPT")

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
        if len({o["request_id"] for o in request["operations"]}) != len(
            request["operations"]
        ) or any("proposal_id" in o or "approval_id" in o for o in request["operations"]):
            self.fail("INVALID_RECEIPT")
        principal = receipt["actor"]["principal_id"]
        self.connection.execute(
            "INSERT INTO receipts VALUES(?,?,?,?,?)",
            (path, principal, receipt["idempotency_key"], receipt["transaction_id"], commit),
        )
        explained = set()
        changed_nodes = set()
        overlay = {}
        originals = {
            ("node", identifier): record for identifier, record in self.prior_nodes.items()
        }
        for position, (operation, result) in enumerate(
            zip(request["operations"], receipt["results"], strict=True)
        ):
            self._expectations(operation, previous, overlay, originals)
            if operation["operation"] in {"node.create", "node.update"}:
                identifier = operation["payload"].get("node_id", operation["request_id"])
                if identifier in changed_nodes:
                    self.fail("INVALID_RECEIPT")
                changed_nodes.add(identifier)
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
            for resource in result["resources"]:
                key = resource["resource_kind"], resource["id"]
                overlay[key] = records[key]
            resource = result["resources"][0]
            self.connection.execute(
                "INSERT INTO replay_scopes VALUES(?,?,?,?,?)",
                (path, position, operation["operation"], resource["resource_kind"], resource["id"]),
            )
            if operation["operation"] == "node.update":
                identifier = operation["payload"]["node_id"]
                prior = self.prior_nodes.get(identifier)
                current = records["node", identifier]
                revision = records["node_revision", current["revision_ref"]["revision_id"]]
                if (
                    not prior
                    or revision.get("previous") != prior["revision_ref"]
                    or current["created_at"] != prior["created_at"]
                    or current["lifecycle"] != prior["lifecycle"]
                    or current["revision"] != prior["revision"] + 1
                ):
                    self.fail("INVALID_RECEIPT")
                for expectation in operation["expectations"]:
                    if expectation["resource"] == self.boundary.resource("node", identifier) and (
                        expectation["expected_revision"] != prior["revision"]
                        or (
                            "expected_digest" in expectation
                            and expectation["expected_digest"] != digest(prior)
                        )
                    ):
                        self.fail("INVALID_RECEIPT")
                if not self.connection.execute(
                    "SELECT 1 FROM files WHERE path=?", (HISTORY,)
                ).fetchone():
                    self.fail("MISSING_REVISION")
            for kind, identifier in targets:
                target = f"knowledge/{kind}/{identifier}.yaml"
                if target in previous and not (
                    operation["operation"] == "node.update"
                    and kind == "node"
                    and identifier == operation["payload"]["node_id"]
                ):
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
            node = operation["operation"] in {"node.create", "node.update"}
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
        if self.index.blob_cache is not None:
            self.index.blob_cache.update(blobs)
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
