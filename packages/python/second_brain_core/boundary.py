"""Instance bindings and canonical contract ingress/output."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from generated.v1.common_schema import DomainError
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel, RootModel
from second_brain_contracts import ContractValidator

from .codec import decode, encode

VERSION = "1.0.0"
GENERATION = "control/generation.json"


def uid() -> str:
    return str(uuid4())


def digest(value: object) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(encode(value)).hexdigest()}


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class CoreError(Exception):
    """Sanitized failure carrying the generated, canonical DomainError model."""

    def __init__(self, contracts: ContractValidator, code: str) -> None:
        payload = dict(
            schema_version=VERSION,
            code=code,
            message=code,
            retryable=code == "REVISION_CONFLICT",
            correlation_id=uid(),
        )
        self.error = contracts.parse_as("common", payload, DomainError)
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "grants", frozenset(self.grants))


@dataclass(frozen=True)
class InstanceContext:
    instance_id: str
    repository: Path
    managed_ref: str
    principal: TrustedPrincipal
    contract_version: str = VERSION


class ContractBoundary:
    def __init__(self, context: InstanceContext, contracts: ContractValidator) -> None:
        self.context = context
        self.contracts = contracts

    def fail(self, code: str) -> NoReturn:
        raise CoreError(self.contracts, code)

    def resource(self, kind: str, identifier: str) -> dict[str, object]:
        value: dict[str, object] = {
            "instance_id": self.context.instance_id,
            "resource_kind": kind,
            "id": identifier,
        }
        schema = self.contracts.schemas["common"]["$defs"]["ResourceRef"]
        self.contracts.validators["common"].evolve(schema=schema).validate(value)
        return value

    def ingest(
        self, family: str, payload: BaseModel | dict[str, object] | str | bytes
    ) -> BaseModel:
        try:
            if isinstance(payload, BaseModel):
                payload = payload.model_dump(mode="json", by_alias=True, exclude_unset=True)
            elif isinstance(payload, str):
                payload = decode(payload.encode("utf-8"))
            elif isinstance(payload, bytes):
                payload = decode(payload)
            # Deep copy freezes caller-owned dictionaries before execution.
            model = self.contracts.parse(family, decode(encode(payload)))
            if not isinstance(model, RootModel):
                raise ValueError("Expected generated root contract")
            if not isinstance(model.root, BaseModel):
                raise ValueError("Expected generated record alternative")
            return model.root
        except (ValueError, TypeError, KeyError, ValidationError) as exc:
            raise CoreError(self.contracts, "VALIDATION_FAILED") from exc

    def dump(self, family: str, model: BaseModel) -> dict:
        return self.contracts.dump(family, model)
