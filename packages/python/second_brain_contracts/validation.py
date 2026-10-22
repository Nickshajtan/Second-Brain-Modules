"""Offline registry adapter around independent JSON Schema validation.

No domain handlers or business-rule evaluator. Pydantic is a derivative model,
never the structural authority.
"""

import hashlib
import importlib
import json
from pathlib import Path
from urllib.parse import urljoin

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


class UnsupportedContractVersion(ValueError):
    code = "UNSUPPORTED_VERSION"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError(f"Non-JSON numeric constant: {value}")


def load_json(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=_unique,
        parse_constant=_nonfinite,
    )


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class ContractValidator:
    """Validate packaged schemas with jsonschema; unknown references fail offline."""

    def __init__(self, root=None, *, version="1.0.0"):
        if version != "1.0.0":
            raise UnsupportedContractVersion(version)
        self.root = Path(root or Path(__file__).resolve().parents[3]).resolve()
        self.manifest = load_json(self.root / "contracts/registry/v1.json")
        if self.manifest["contract_version"] != version:
            raise UnsupportedContractVersion(self.manifest["contract_version"])
        self.entries = {entry["name"]: entry for entry in self.manifest["schemas"]}
        self.schemas = {}
        ids = set()
        for entry in self.entries.values():
            path = (self.root / entry["path"]).resolve()
            if not path.is_relative_to(self.root / "contracts/schemas/v1"):
                raise ValueError("Schema path escapes production bundle")
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            if schema["$id"] != entry["id"] or schema["$id"] in ids:
                raise ValueError("Registry/schema identity mismatch")
            if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
                raise ValueError("Unsupported schema dialect")
            ids.add(schema["$id"])
            self.schemas[entry["name"]] = schema
        if len(self.entries) != len(self.manifest["schemas"]):
            raise ValueError("Duplicate registry name")
        actual = {
            p.relative_to(self.root).as_posix()
            for p in (self.root / "contracts/schemas/v1").glob("*.schema.json")
        }
        if actual != {e["path"] for e in self.entries.values()}:
            raise ValueError("Registry does not cover exact schema file set")
        self.registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in self.schemas.values()
        )
        checker = FormatChecker()
        self.reference_count = 0
        for schema in self.schemas.values():
            for part in walk(schema):
                if "$dynamicRef" in part or "$dynamicAnchor" in part:
                    raise ValueError("Dynamic references are outside the generation profile")
                if "$id" in part and part is not schema:
                    raise ValueError("Nested resource IDs are outside the generation profile")
                if "$ref" in part:
                    absolute = urljoin(schema["$id"], part["$ref"])
                    if absolute.split("#", 1)[0] not in ids:
                        raise ValueError(f"Unpackaged reference: {part['$ref']}")
                    self.registry.resolver(schema["$id"]).lookup(part["$ref"])
                    self.reference_count += 1
                if "format" in part and part["format"] not in checker.checkers:
                    raise ValueError(f"Missing external format checker: {part['format']}")
        self.validators = {
            name: Draft202012Validator(schema, registry=self.registry, format_checker=checker)
            for name, schema in self.schemas.items()
        }

    def validate(self, family, payload):
        """Validate without mutation/coercion; return the caller's original JSON value."""
        if isinstance(payload, dict) and payload.get("schema_version", "1.0.0") != "1.0.0":
            raise UnsupportedContractVersion(payload["schema_version"])
        json.dumps(payload, allow_nan=False)
        self.validators[family].validate(payload)
        return payload

    def parse(self, family, payload):
        """Validate canonical JSON before constructing the generated root model."""
        self.validate(family, payload)
        entry = self.entries[family]
        module = importlib.import_module(entry["python_module"])
        return getattr(module, entry["python_type"]).model_validate(payload)

    def dump(self, family, model):
        """Preserve aliases and supplied optional values, then revalidate canonically."""
        payload = model.model_dump(mode="json", by_alias=True, exclude_unset=True)
        self.validate(family, payload)
        return payload

    def verify_generated(self):
        """Check the pinned checkout's canonical-source and generated-artifact hashes."""
        manifest = load_json(self.root / "packages/python/generated/v1/manifest.json")
        if manifest["contract_version"] != self.manifest["contract_version"]:
            raise UnsupportedContractVersion(manifest["contract_version"])
        for group in ("source_hashes", "artifact_hashes"):
            for name, expected in manifest[group].items():
                path = (self.root / name).resolve()
                if not path.is_relative_to(self.root):
                    raise ValueError("Generated manifest path escaped checkout")
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Generated contract drift: {name}")
