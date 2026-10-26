"""Durable request/receipt bindings, scoped idempotency and authorized replay."""

from generated.v1.transaction_schema import BatchRequest, CommittedReceipt

from .boundary import VERSION, ContractBoundary, digest, timestamp
from .codec import decode, encode
from .history import HistoricalEffects


class ReceiptStore:
    history: HistoricalEffects

    def __init__(self, boundary: ContractBoundary, strategies) -> None:
        self.boundary = boundary
        self.strategies = strategies

    def path(self, principal, key):
        scope = [self.boundary.context.instance_id, principal, "batch.submit", VERSION, key]
        return "control/receipts/" + digest(scope)["value"] + ".json"

    @staticmethod
    def request_path(receipt_path):
        return receipt_path.replace("/receipts/", "/requests/")

    def for_request(self, request):
        return self.path(self.boundary.context.principal.principal_id, request["idempotency_key"])

    def replay(self, request, files, records):
        path = self.for_request(request)
        if path not in files:
            return None
        receipt = decode(files[path])
        for result in receipt["results"]:
            self.strategies[result["operation"]].authorize_replay(result, records)
        if receipt["request_digest"] != digest(request):
            self.boundary.fail("IDEMPOTENCY_CONFLICT")
        return self.boundary.contracts.parse_as("transaction", receipt, CommittedReceipt)

    @staticmethod
    def operation_keys(request):
        return [
            (o["operation"], o["operation_version"], o["idempotency_key"])
            for o in request["operations"]
        ]

    def check_unused(self, request, files):
        keys = self.operation_keys(request)
        if len(set(keys)) != len(keys):
            self.boundary.fail("IDEMPOTENCY_CONFLICT")
        for path, raw in files.items():
            if not path.startswith("control/receipts/"):
                continue
            prior = decode(raw)
            if prior["actor"]["principal_id"] != self.boundary.context.principal.principal_id:
                continue
            previous = decode(files[self.request_path(path)])
            if (
                set(keys) & set(self.operation_keys(previous))
                or previous["transaction_id"] == request["transaction_id"]
            ):
                self.boundary.fail("IDEMPOTENCY_CONFLICT")

    def record(self, request, generation, results, files):
        receipt = dict(
            kind="committed_receipt",
            schema_version=VERSION,
            status="committed",
            instance_id=self.boundary.context.instance_id,
            transaction_id=request["transaction_id"],
            idempotency_key=request["idempotency_key"],
            request_digest=digest(request),
            actor={"principal_id": self.boundary.context.principal.principal_id},
            generation=generation,
            committed_at=timestamp(),
            results=results,
        )
        model = self.boundary.contracts.parse_as("transaction", receipt, CommittedReceipt)
        path = self.for_request(request)
        files[path] = encode(self.boundary.dump("transaction", model))
        files[self.request_path(path)] = encode(request)
        return model

    def validate_pair(self, path, files):
        receipt = self.boundary.contracts.parse_as(
            "transaction", decode(files[path]), CommittedReceipt
        )
        wire = self.boundary.dump("transaction", receipt)
        if wire["instance_id"] != self.boundary.context.instance_id or path != self.path(
            wire["actor"]["principal_id"], wire["idempotency_key"]
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        request_path = self.request_path(path)
        request = self.boundary.contracts.parse_as(
            "transaction", decode(files[request_path]), BatchRequest
        )
        request_wire = self.boundary.dump("transaction", request)
        if (
            digest(request_wire) != wire["request_digest"]
            or request_wire["transaction_id"] != wire["transaction_id"]
            or request_wire["idempotency_key"] != wire["idempotency_key"]
            or request_wire["instance_id"] != self.boundary.context.instance_id
            or len(wire["results"]) != len(request_wire["operations"])
        ):
            self.boundary.fail("REPAIR_REQUIRED")
        for operation, result in zip(request_wire["operations"], wire["results"], strict=True):
            if (
                operation["operation"] != result["operation"]
                or operation["request_id"] != result["request_id"]
                or any(
                    r["instance_id"] != self.boundary.context.instance_id
                    for r in result["resources"]
                )
            ):
                self.boundary.fail("REPAIR_REQUIRED")
        return request_path

    def validate_results(self, files, records, commit):
        self.history.validate(files, records, commit)
