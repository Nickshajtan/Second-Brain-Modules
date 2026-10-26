"""Instance composition and one atomic transaction boundary for M1 operations."""

from collections.abc import Iterable
from pathlib import Path

from generated.v1.operations_schema import NodeCreate, NodeRead, RelationCreate, RelationRead
from generated.v1.transaction_schema import BatchRequest, CommittedReceipt, ReadResult
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel
from second_brain_contracts import ContractValidator

from .access import AccessControl
from .bootstrap import BootstrapInitializer
from .boundary import GENERATION, VERSION, ContractBoundary, CoreError, InstanceContext, digest
from .codec import encode
from .domain import DomainRules
from .git_store import PublicationConflict, StorageError
from .history import HistoricalEffects
from .operations import (
    NodeCreateStrategy,
    NodeReadStrategy,
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
            "relation.create": RelationCreateStrategy(self.boundary, self.access, self.domain),
        }
        self.readers = {
            "node.read": NodeReadStrategy(self.boundary, self.access),
            "relation.read": RelationReadStrategy(self.access),
        }
        self.receipts = ReceiptStore(self.boundary, self.mutations)
        self.repository = KnowledgeRepository(self.boundary, store, self.domain, self.receipts)
        self.receipts.history = HistoricalEffects(self.repository)
        self.initializer = BootstrapInitializer(self.boundary, store, self.repository, self.domain)

    def bootstrap(
        self, records: Iterable[BaseModel | dict[str, object]], metadata_schemas: dict[str, object]
    ) -> dict[str, object]:
        return self.initializer.initialize(records, metadata_schemas)

    def generation(self) -> dict[str, object]:
        return self.repository.snapshot()[2]

    def submit(self, payload: BatchRequest | dict[str, object] | str | bytes) -> CommittedReceipt:
        batch = self.boundary.ingest("transaction", payload)
        if not isinstance(batch, BatchRequest):
            self.boundary.fail("VALIDATION_FAILED")
        request = self.boundary.dump("transaction", batch)
        self._check_batch(request)
        try:
            with self.store.writer():
                return self._commit(request)
        except PublicationConflict as exc:
            raise CoreError(self.contracts, "REVISION_CONFLICT") from exc
        except (StorageError, OSError) as exc:
            # Lock-file failures can occur before a Git subprocess is started.
            raise CoreError(self.contracts, "REPAIR_REQUIRED") from exc
        except ValidationError as exc:
            raise CoreError(self.contracts, "VALIDATION_FAILED") from exc

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

    def _commit(self, request):
        parent, files, generation, records, metadata = self.repository.snapshot()
        replay = self.receipts.replay(request, files, records)
        if replay is not None:
            return replay
        if request["expected_generation"] != generation:
            self.boundary.fail("REVISION_CONFLICT")
        self.receipts.check_unused(request, files)
        seen, results = set(), []
        for operation in request["operations"]:
            if operation["request_id"] in seen:
                self.boundary.fail("VALIDATION_FAILED")
            seen.add(operation["request_id"])
            results.append(self._create(operation, records, files, metadata))
        self.domain.validate(records, metadata)
        generation = self.repository.generation(files)
        files[GENERATION] = encode(generation)
        receipt = self.receipts.record(request, generation, results, files)
        candidate = self.store.prepare(files, parent)
        self.store.publish(candidate, parent)
        return receipt

    def _create(self, operation, records, files, metadata):
        additions, revisions = self.mutations[operation["operation"]].prepare(
            operation, records, metadata
        )
        self.access.check_expectations(operation, records)
        for record in additions:
            key = record["kind"], record["id"]
            if key in records:
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
        payload: NodeCreate | RelationCreate | dict[str, object] | str | bytes,
        expected_generation: dict[str, object],
    ) -> CommittedReceipt:
        """Canonically revalidate typed inputs; keep the original generation on retry."""
        operation = self.boundary.ingest("operations", payload)
        if not isinstance(operation, NodeCreate | RelationCreate):
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

    def read(
        self, payload: NodeRead | RelationRead | dict[str, object] | str | bytes
    ) -> ReadResult:
        operation = self.boundary.ingest("operations", payload)
        wire = self.boundary.dump("operations", operation)
        if wire["instance_id"] != self.context.instance_id:
            self.boundary.fail("NOT_FOUND")
        strategy = self.readers.get(wire["operation"])
        if strategy is None:
            self.boundary.fail("VALIDATION_FAILED")
        _, _, generation, records, _ = self.repository.snapshot()
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
