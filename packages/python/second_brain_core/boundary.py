"""Instance bindings and canonical contract ingress/output."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jsonschema.exceptions import ValidationError
from pydantic import BaseModel

from .codec import decode, encode

VERSION = "1.0.0"
GENERATION = "control/generation.json"


def uid():
    return str(uuid4())


def digest(value):
    return {"algorithm": "sha256", "value": hashlib.sha256(encode(value)).hexdigest()}


def timestamp():
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class CoreError(Exception):
    """Sanitized failure carrying the generated, canonical DomainError model."""

    def __init__(self, contracts, code):
        payload = dict(
            schema_version=VERSION,
            code=code,
            message=code,
            retryable=code == "REVISION_CONFLICT",
            correlation_id=uid(),
        )
        self.error = contracts.parse("common", payload)
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class TrustedPrincipal:
    """Server/bootstrap binding, never deserialized from operation JSON.

    Grants are explicit (cluster UUID, action) pairs. Replace the binding on
    revocation; no caller-controlled owner flag, role ladder or wildcard action.
    """

    principal_id: str
    grants: frozenset[tuple[str, str]] = frozenset()
    bootstrap: bool = False

    def __post_init__(self):
        object.__setattr__(self, "grants", frozenset(self.grants))


@dataclass(frozen=True)
class InstanceContext:
    instance_id: str
    repository: Path
    managed_ref: str
    principal: TrustedPrincipal
    contract_version: str = VERSION


class ContractBoundary:
    def __init__(self, context, contracts):
        self.context = context
        self.contracts = contracts

    def fail(self, code):
        raise CoreError(self.contracts, code)

    def resource(self, kind, identifier):
        value = {"instance_id": self.context.instance_id, "resource_kind": kind, "id": identifier}
        schema = self.contracts.schemas["common"]["$defs"]["ResourceRef"]
        self.contracts.validators["common"].evolve(schema=schema).validate(value)
        return value

    def ingest(self, family, payload):
        try:
            if isinstance(payload, BaseModel):
                payload = payload.model_dump(mode="json", by_alias=True, exclude_unset=True)
            elif isinstance(payload, str):
                payload = decode(payload.encode("utf-8"))
            elif isinstance(payload, bytes):
                payload = decode(payload)
            # Deep copy freezes caller-owned dictionaries before execution.
            return self.contracts.parse(family, decode(encode(payload))).root
        except (ValueError, TypeError, KeyError, ValidationError) as exc:
            raise CoreError(self.contracts, "VALIDATION_FAILED") from exc

    def dump(self, family, model):
        return self.contracts.dump(family, model)
