"""Reusable offline validation of architecture examples; no runtime implementation."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


@dataclass(frozen=True)
class ValidationReport:
    schemas: int
    schema_refs: int
    fixtures: int
    rejection_probes: int
    valid_probes: int
    openapi_refs: int
    document_links: int

    def summary(self) -> str:
        return (f"PASS: {self.schemas} schemas, {self.schema_refs} schema refs, "
                f"{self.fixtures} fixtures, {self.rejection_probes} rejection probes, "
                f"{self.valid_probes} additional valid probes, "
                f"{self.openapi_refs} OpenAPI refs, "
                f"{self.document_links} portable document links")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-JSON numeric constant: {value}")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class ExampleValidator:
    """One portable repository root, with independently callable check groups.

    run() returns a report and raises on the first failure. It performs no
    printing or writes. Construct another instance to validate another root.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.examples = self.root / "docs/architecture/examples"
        schemas = {p.stem.split(".")[0]: load(p)
                   for p in sorted(self.examples.glob("*.schema.json"))}
        require(set(schemas) == {"node", "cluster"}, "Expected two example schemas")
        # Registry without a retrieval callback: unknown references fail offline.
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema))
            for schema in schemas.values())
        checker = FormatChecker()
        if "date-time" not in checker.checkers:
            # The installed jsonschema may lack its optional RFC3339 dependency.
            # This project deliberately uses a narrower UTC-only timestamp profile.
            # Use Python's calendar parser; do not implement a general RFC3339 parser.
            @checker.checks("date-time")
            def project_timestamp(value):
                if not isinstance(value, str):
                    return True
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-5][0-9](\.[0-9]{1,6})?Z", value):
                    return False
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return True
                except ValueError:
                    return False
        self.schemas = schemas
        self.registry = registry
        self.checker = checker

        self.validators = {
            name: Draft202012Validator(schema, registry=registry, format_checker=checker)
            for name, schema in schemas.items()
        }

    def check_schemas(self) -> int:
        schemas, registry, checker = self.schemas, self.registry, self.checker
        refs = 0
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
            resolver = registry.resolver(base_uri=schema["$id"])
            for obj in walk(schema):
                if "$ref" in obj:
                    resolver.lookup(obj["$ref"])
                    refs += 1
                if "format" in obj:
                    require(obj["format"] in checker.checkers,
                            f"Missing format checker: {obj['format']}")
        return refs

    def check_fixtures(self) -> int:
        validators = self.validators
        fixture_count = 0
        for name, validator in validators.items():
            validator.validate(load(self.examples / f"fixtures/valid/{name}.json"))
            errors = list(validator.iter_errors(load(self.examples / f"fixtures/invalid/{name}.json")))
            keyword, field = (("type", "title") if name == "node"
                              else ("format", "created_at"))
            require(any(e.validator == keyword and list(e.path) == [field] for e in errors),
                    f"Invalid {name} fixture failed for the wrong reason")
            fixture_count += 2

        return fixture_count

    def check_probes(self) -> tuple[int, int]:
        validators = self.validators
        node = load(self.examples / "fixtures/valid/node.json")
        probes = [
            ("unknown field", "unexpected", True, "additionalProperties"),
            ("zero revision", "revision", 0, "minimum"),
            ("unsafe integer", "revision", 9007199254740992, "maximum"),
            ("numeric string", "revision", "1", "type"),
            ("boolean integer", "revision", True, "type"),
            ("bad lifecycle", "lifecycle", "promoted", "enum"),
            ("bad UUID", "id", "synthetic-path", "pattern"),
            ("offset timestamp", "created_at", "2026-10-20T09:00:00+00:00", "pattern"),
            ("leap second", "created_at", "2026-10-20T09:00:60Z", "pattern"),
            ("nested bad ref", "provenance_refs", [{"record_id": "bad"}], "pattern"),
            ("null optional", "topics", None, "type"),
        ]
        for name, field, value, keyword in probes:
            instance = deepcopy(node)
            instance[field] = value
            errors = list(validators["node"].iter_errors(instance))
            require(any(e.validator == keyword for e in errors), f"Probe failed: {name}")
        relation = deepcopy(node)
        relation["relations"] = [{"id": "44444444-4444-4444-8444-444444444444",
                                  "type": "supports", "target_id": node["id"],
                                  "confidence": 0.5}]
        validators["node"].validate(relation)
        cluster = load(self.examples / "fixtures/valid/cluster.json")
        del cluster["description"]
        validators["cluster"].validate(cluster)
        cluster["description"] = "Fabricated description"
        validators["cluster"].validate(cluster)

        return len(probes), 3

    def check_openapi(self) -> int:
        registry = self.registry
        # Syntax plus targeted reference/security checks; not a full OpenAPI linter.
        api = load(self.examples / "openapi-example.yaml")
        require(api["openapi"] == "3.1.2", "Unexpected OpenAPI profile")
        require(api.get("security"), "Example must declare authentication binding")
        api_refs = 0
        for obj in walk(api):
            if "$ref" in obj:
                ref = obj["$ref"]
                parts = urlsplit(ref)
                require(not parts.scheme and not parts.netloc, "Expected local OpenAPI schema ref")
                target = (self.examples / unquote(parts.path)).resolve()
                require(target.is_relative_to(self.root), "Reference escaped portable root")
                resource = load(target)
                registry.resolver(base_uri=resource["$id"]).lookup(
                    "#" + parts.fragment if parts.fragment else resource["$id"])
                api_refs += 1

        return api_refs

    def check_document_links(self) -> int:
        link_count = 0
        for path in sorted(self.root.rglob("*.md")):
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                dest = (path.parent / unquote(parts.path)).resolve()
                require(dest.is_relative_to(self.root), f"Nonportable link in {path.name}: {target}")
                require(dest.exists(), f"Broken link in {path.name}: {target}")
                link_count += 1
        return link_count

    def run(self) -> ValidationReport:
        schema_refs = self.check_schemas()
        fixtures = self.check_fixtures()
        rejection_probes, valid_probes = self.check_probes()
        return ValidationReport(
            schemas=len(self.schemas), schema_refs=schema_refs,
            fixtures=fixtures, rejection_probes=rejection_probes,
            valid_probes=valid_probes, openapi_refs=self.check_openapi(),
            document_links=self.check_document_links())
