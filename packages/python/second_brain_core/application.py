"""Instance composition and one atomic transaction boundary for M1 operations."""

import hashlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from generated.v1.operations_schema import (
    NodeCreate,
    NodeRead,
    NodeRevisionRead,
    NodeUpdate,
    RelationCreate,
    RelationRead,
)
from generated.v1.transaction_schema import BatchRequest, CommittedReceipt, ReadResult
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel
from second_brain_contracts import ContractValidator

from .access import AccessControl
from .bootstrap import BootstrapInitializer
from .boundary import GENERATION, VERSION, ContractBoundary, CoreError, InstanceContext, digest, uid
from .codec import decode, encode
from .domain import DomainRules
from .git_store import PublicationConflict, StorageError
from .history import HistoricalEffects
from .history_index import HistoryIndex
from .operations import (
    NodeCreateStrategy,
    NodeReadStrategy,
    NodeRevisionReadStrategy,
    NodeUpdateStrategy,
    RelationCreateStrategy,
    RelationReadStrategy,
)
from .ports import CommitStore
from .receipts import ReceiptStore
from .repository import KnowledgeRepository


class Core:
    def __init__(
        self,
        context: InstanceContext,
        store: CommitStore,
        contracts: ContractValidator | None = None,
    ) -> None:
        self.context = context
        self.store = store
        self.contracts = contracts or ContractValidator(version=context.contract_version)
        self.boundary = ContractBoundary(context, self.contracts)
        if context.contract_version != VERSION:
            self.boundary.fail("UNSUPPORTED_VERSION")
        if (
            Path(context.repository).resolve() != store.repository
            or context.managed_ref != store.ref
        ):
            raise ValueError("Instance context and storage boundary disagree")
        self.contracts.validators["common"].evolve(
            schema=self.contracts.schemas["common"]["$defs"]["PrincipalRef"]
        ).validate({"principal_id": context.principal.principal_id})
        self.boundary.resource("cluster", context.instance_id)
        self.access = AccessControl(self.boundary)
        self.domain = DomainRules(self.boundary)
        self.mutations = {
            "node.create": NodeCreateStrategy(self.boundary, self.access, self.domain),
            "node.update": NodeUpdateStrategy(self.boundary, self.access, self.domain),
            "relation.create": RelationCreateStrategy(self.boundary, self.access, self.domain),
        }
        self.readers = {
            "node.read": NodeReadStrategy(self.boundary, self.access),
            "node.revision.read": NodeRevisionReadStrategy(self.boundary, self.access),
            "relation.read": RelationReadStrategy(self.access),
        }
        self.receipts = ReceiptStore(self.boundary, self.mutations)
        self.repository = KnowledgeRepository(self.boundary, store, self.domain, self.receipts)
        self.receipts.history = HistoricalEffects(self.repository)
        self.history_index = HistoryIndex(self.repository)
        self.repository.index = self.history_index
        self.initializer = BootstrapInitializer(self.boundary, store, self.repository, self.domain)

    def bootstrap(
        self, records: Iterable[BaseModel | dict[str, object]], metadata_schemas: dict[str, object]
    ) -> dict[str, object]:
        if not self.context.principal.bootstrap:
            self.boundary.fail("FORBIDDEN")
        if self.history_index.directory.exists():
            # Lost enrollment cannot be bypassed by deleting the managed ref.
            self.history_index.anchor()
            self.boundary.fail("REVISION_CONFLICT")
        result = self.initializer.initialize(records, metadata_schemas)
        with self.store.writer():
            self.history_index.rebuild()
        return result

    def generation(self) -> dict[str, object]:
        try:
            self.history_index.ensure()
            return self._generation()
        except CoreError:
            raise
        except (
            StorageError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            sqlite3.Error,
            ValidationError,
        ) as exc:
            raise CoreError(self.contracts, "REPAIR_REQUIRED") from exc
        except Exception as exc:
            raise CoreError(self.contracts, "INTERNAL") from exc

    def _generation(self):
        if self.history_index.frontier is None:
            raise CoreError(self.contracts, "REPAIR_REQUIRED")
        actual_oid = self.store.locate(self.history_index.frontier, GENERATION)
        stored_oid = self.history_index.query("SELECT oid FROM files WHERE path=?", (GENERATION,))[
            0
        ][0]
        if actual_oid != stored_oid:
            self.boundary.fail("REPAIR_REQUIRED")
        generation = decode(self.history_index.raw(GENERATION))
        schema = self.contracts.schemas["common"]["$defs"]["GenerationRef"]
        self.contracts.validators["common"].evolve(schema=schema).validate(generation)
        if generation != self.history_index.generation:
            self.boundary.fail("REPAIR_REQUIRED")
        return generation

    def submit(self, payload: BatchRequest | dict[str, object] | str | bytes) -> CommittedReceipt:
        try:
            batch = self.boundary.ingest("transaction", payload)
            if not isinstance(batch, BatchRequest):
                self.boundary.fail("VALIDATION_FAILED")
            request = self.boundary.dump("transaction", batch)
            self._check_batch(request)
            with self.store.writer(), self.history_index.request_blobs():
                return self._commit(request)
        except PublicationConflict as exc:
            raise CoreError(self.contracts, "REVISION_CONFLICT") from exc
        except (StorageError, OSError, sqlite3.Error) as exc:
            # Lock-file failures can occur before a Git subprocess is started.
            raise CoreError(self.contracts, "REPAIR_REQUIRED") from exc
        except ValidationError as exc:
            raise CoreError(self.contracts, "VALIDATION_FAILED") from exc
        except CoreError:
            raise
        except Exception as exc:
            raise CoreError(self.contracts, "INTERNAL") from exc

    def _check_batch(self, request):
        if request["instance_id"] != self.context.instance_id:
            self.boundary.fail("NOT_FOUND")
        for operation in request["operations"]:
            if operation["instance_id"] != self.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            if operation["operation"] not in self.mutations:
                self.boundary.fail("VALIDATION_FAILED")
            if "proposal_id" in operation or "approval_id" in operation:
                self.boundary.fail("VALIDATION_FAILED")

    def _commit(self, request) -> CommittedReceipt:
        self.history_index.ensure(locked=True)
        self.history_index.coherent()
        parent, generation = self.history_index.frontier, self._generation()
        if parent is None or self.history_index.connection is None:
            raise CoreError(self.contracts, "REPAIR_REQUIRED")
        replay = self._replay(request)
        if replay is not None:
            return replay
        if not self.history_index.query(
            "SELECT 1 FROM files WHERE path='control/history.json'"
        ) and any(o["operation"] == "node.update" for o in request["operations"]):
            self.boundary.fail("REPAIR_REQUIRED")
        changed_nodes = set()
        for operation in request["operations"]:
            if operation["operation"] in {"node.create", "node.update"}:
                identifier = operation["payload"].get("node_id", operation["request_id"])
                if identifier in changed_nodes:
                    self.boundary.fail("VALIDATION_FAILED")
                changed_nodes.add(identifier)
        pending = {}
        for operation in request["operations"]:
            self.mutations[operation["operation"]].screen(operation, self.history_index, pending)
        if request["expected_generation"] != generation:
            self.boundary.fail("REVISION_CONFLICT")
        self._check_unused(request)
        records, metadata = self._mutation_context(request)
        files = {}
        seen, results = set(), []
        for operation in request["operations"]:
            if operation["request_id"] in seen:
                self.boundary.fail("VALIDATION_FAILED")
            seen.add(operation["request_id"])
            results.append(self._create(operation, records, files, metadata))
        self.domain.validate(records, metadata, bounded=True)
        generation = self._next_generation(files)
        files[GENERATION] = encode(generation)
        receipt = self.receipts.record(request, generation, results, files)
        candidate = self.store.prepare_delta(files, parent)
        with self.history_index.candidate(candidate) as (projection, verified_generation):
            self.store.publish(candidate, parent)
            self.history_index.publish(projection, candidate, verified_generation)
        return receipt

    def _replay(self, request) -> CommittedReceipt | None:
        if self.history_index.connection is None:
            raise CoreError(self.contracts, "REPAIR_REQUIRED")
        path = self.receipts.for_request(request)
        existing = self.history_index.query("SELECT 1 FROM receipts WHERE path=?", (path,))
        if not existing:
            return None
        scopes = self.history_index.query(
            "SELECT operation,kind,resource FROM replay_scopes WHERE receipt=? ORDER BY position",
            (path,),
        )
        if not scopes:
            raise CoreError(self.contracts, "REPAIR_REQUIRED")
        for action, kind, identifier in scopes:
            if kind == "node":
                actions = (
                    ("node.update",)
                    if action == "node.update"
                    else ("node.create", "membership.admit")
                )
                self.access.screen_node(
                    self.history_index, identifier, actions=actions, active=action == "node.update"
                )
            else:
                self.access.screen_relation(
                    self.history_index, identifier, action="relation.create"
                )
        files = {path: self.history_index.raw(path)}
        request_path = self.receipts.request_path(path)
        files[request_path] = self.history_index.raw(request_path)
        self.receipts.validate_pair(path, files)
        receipt = decode(files[path])
        origin = self.history_index.query("SELECT origin FROM receipts WHERE path=?", (path,))[0][0]
        generation_oid = self.store.locate(origin, GENERATION)
        cache = self.history_index.blob_cache
        if cache is not None and generation_oid in cache:
            original_generation = cache[generation_oid]
        else:
            original_generation = self.store.blobs([generation_oid])[generation_oid]
            if cache is not None:
                cache[generation_oid] = original_generation
        if decode(original_generation) != receipt["generation"]:
            self.boundary.fail("REPAIR_REQUIRED")
        targets = [
            (r["resource_kind"], r["id"])
            for result in receipt["results"]
            for r in result["resources"]
        ]
        records = self.history_index.closure(targets)
        replay = self.receipts.replay(request, files, records)
        if replay is None:
            raise CoreError(self.contracts, "REPAIR_REQUIRED")
        from .verification import TransitionVerifier

        verifier = TransitionVerifier(self.repository, self.history_index.connection)
        verifier.index.blob_cache = self.history_index.blob_cache
        original = verifier.original_records(path)
        original_request = decode(files[request_path])
        for operation, result in zip(
            original_request["operations"], receipt["results"], strict=True
        ):
            self.mutations[operation["operation"]].verify_result(
                operation, result, receipt, original
            )
        return replay

    def _mutation_context(self, request):
        targets = []
        for operation in request["operations"]:
            targets.extend(
                self.mutations[operation["operation"]].dependencies(operation, self.history_index)
            )
            targets.extend(
                (e["resource"]["resource_kind"], e["resource"]["id"])
                for e in operation["expectations"]
            )
        records = self.history_index.closure(targets)
        metadata = decode(self.history_index.raw("control/metadata.json"))
        return records, metadata

    def _check_unused(self, request):
        keys = self.receipts.operation_keys(request)
        principal = self.context.principal.principal_id
        if len(set(keys)) != len(keys) or self.history_index.query(
            "SELECT 1 FROM receipts WHERE principal=? AND tx=?",
            (principal, request["transaction_id"]),
        ):
            self.boundary.fail("IDEMPOTENCY_CONFLICT")
        for operation, version, key in keys:
            if self.history_index.query(
                "SELECT 1 FROM operation_keys WHERE principal=? AND operation=? AND version=? AND key=?",
                (principal, operation, version, key),
            ):
                self.boundary.fail("IDEMPOTENCY_CONFLICT")

    def _next_generation(self, files):
        hashes = dict(
            self.history_index.query(
                "SELECT path,sha FROM files WHERE path GLOB 'knowledge/*' OR path='control/metadata.json'"
            )
        )
        hashes.update(
            {
                path: hashlib.sha256(raw).hexdigest()
                for path, raw in files.items()
                if path.startswith("knowledge/") or path == "control/metadata.json"
            }
        )
        return dict(
            instance_id=self.context.instance_id, generation_id=uid(), digest=digest(hashes)
        )

    def _create(self, operation, records, files, metadata):
        additions, revisions = self.mutations[operation["operation"]].prepare(
            operation, records, metadata
        )
        self.access.check_expectations(operation, records)
        for record in additions:
            key = record["kind"], record["id"]
            if key in records and not (
                operation["operation"] == "node.update"
                and key == ("node", operation["payload"]["node_id"])
            ):
                selector = {"node": self.access.node, "relation": self.access.relation}.get(
                    record["kind"]
                )
                if selector is not None:
                    selector(records, record["id"])
                self.boundary.fail("REVISION_CONFLICT")
            records[key] = record
            self.repository.pack(record, files)
        return dict(
            kind="operation_result",
            schema_version=VERSION,
            request_id=operation["request_id"],
            operation=operation["operation"],
            resources=[
                self.boundary.resource(r["kind"], r["id"])
                for r in additions
                if r["kind"] in {"node", "relation", "membership"}
            ],
            revisions=revisions,
        )

    def execute(
        self,
        payload: NodeCreate | NodeUpdate | RelationCreate | dict[str, object] | str | bytes,
        expected_generation: dict[str, object],
    ) -> CommittedReceipt:
        """Canonically revalidate typed inputs; keep the original generation on retry."""
        try:
            operation = self.boundary.ingest("operations", payload)
            if not isinstance(operation, NodeCreate | NodeUpdate | RelationCreate):
                self.boundary.fail("VALIDATION_FAILED")
            wire = self.boundary.dump("operations", operation)
            key = digest([wire["operation"], wire["operation_version"], wire["idempotency_key"]])[
                "value"
            ]
            return self.submit(
                dict(
                    kind="batch_request",
                    schema_version=VERSION,
                    instance_id=wire["instance_id"],
                    transaction_id=wire["request_id"],
                    idempotency_key=key,
                    expected_generation=expected_generation,
                    operations=[wire],
                )
            )
        except CoreError:
            raise
        except Exception as exc:
            raise CoreError(self.contracts, "INTERNAL") from exc

    def read(
        self, payload: NodeRead | NodeRevisionRead | RelationRead | dict[str, object] | str | bytes
    ) -> ReadResult:
        try:
            operation = self.boundary.ingest("operations", payload)
            wire = self.boundary.dump("operations", operation)
            if wire["instance_id"] != self.context.instance_id:
                self.boundary.fail("NOT_FOUND")
            strategy = self.readers.get(wire["operation"])
            if strategy is None:
                self.boundary.fail("VALIDATION_FAILED")
            with self.history_index.request_blobs():
                self.history_index.ensure()
                generation = self._generation()
                historical = wire["operation"] == "node.revision.read"
                kind = (
                    "node"
                    if wire["operation"] in {"node.read", "node.revision.read"}
                    else "relation"
                )
                reference = wire["payload"]["revision"] if historical else {}
                identifier = (
                    reference["resource"]["id"] if historical else wire["payload"][kind + "_id"]
                )
                if historical and reference["resource"]["instance_id"] != self.context.instance_id:
                    self.boundary.fail("NOT_FOUND")
                screens = {"node": self.access.screen_node, "relation": self.access.screen_relation}
                if historical:
                    self.access.screen_node(
                        self.history_index, identifier, actions=("node.read", "node.history.read")
                    )
                else:
                    screens[kind](
                        self.history_index, identifier, wire["payload"].get("selected_cluster_id")
                    )
                targets = [(kind, identifier)]
                if historical:
                    rows = self.history_index.query(
                        "SELECT resource,logical FROM revisions WHERE id=? AND kind='node_revision'",
                        (reference["revision_id"],),
                    )
                    if rows != [(identifier, reference["revision"])]:
                        self.boundary.fail("NOT_FOUND")
                    targets.append(("node_revision", reference["revision_id"]))
                    targets.extend(
                        ("node_revision_snapshot", i)
                        for (i,) in self.history_index.query(
                            "SELECT id FROM resources WHERE kind='node_revision_snapshot' AND json_extract(attrs,'$.revision_id')=?",
                            (reference["revision_id"],),
                        )
                    )
                records = self.history_index.closure(targets)
                metadata = decode(self.history_index.raw("control/metadata.json"))
                self.domain.validate(records, metadata, bounded=True)
                record = strategy.read(wire["payload"], records)
                result = dict(
                    kind="read_result",
                    schema_version=VERSION,
                    request_id=wire["request_id"],
                    generation=generation,
                    records=[record],
                )
                model = self.contracts.parse_as("transaction", result, ReadResult)
                self.boundary.dump("transaction", model)
                return model
        except CoreError:
            raise
        except (
            StorageError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            sqlite3.Error,
            ValidationError,
        ) as exc:
            raise CoreError(self.contracts, "REPAIR_REQUIRED") from exc
        except Exception as exc:
            raise CoreError(self.contracts, "INTERNAL") from exc
