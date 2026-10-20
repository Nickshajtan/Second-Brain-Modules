"""Reusable offline validation of architecture examples; no runtime implementation."""

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from os.path import normpath
from pathlib import Path
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
        return (
            f"PASS: {self.schemas} schemas, {self.schema_refs} schema refs, "
            f"{self.fixtures} fixtures, {self.rejection_probes} rejection probes, "
            f"{self.valid_probes} additional valid probes, "
            f"{self.openapi_refs} OpenAPI refs, "
            f"{self.document_links} portable document links"
        )


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
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


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
        self.schema_paths = {
            p.stem.split(".")[0]: p for p in sorted(self.examples.glob("*.schema.json"))
        }
        require(
            set(self.schema_paths) == {"node", "cluster"},
            f"{self.examples}: expected node and cluster schemas",
        )
        schemas = {name: load(path) for name, path in self.schema_paths.items()}
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        require(
            len({schema["$id"] for schema in schemas.values()}) == len(schemas),
            "Schema IDs must be unique",
        )
        # Registry without a retrieval callback: unknown references fail offline.
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
        )
        checker = FormatChecker()
        if "date-time" not in checker.checkers:
            # The installed jsonschema may lack its optional RFC3339 dependency.
            # This project deliberately uses a narrower UTC-only timestamp profile.
            # Use Python's calendar parser; do not implement a general RFC3339 parser.
            @checker.checks("date-time")
            def project_timestamp(value):
                if not isinstance(value, str):
                    return True
                if not re.fullmatch(
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-5][0-9](\.[0-9]{1,6})?Z",
                    value,
                ):
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

    def local_reference(self, ref: str, source: Path) -> Path:
        """Allow only packaged schema resources; never retrieve arbitrary URLs/files."""
        parts = urlsplit(ref)
        if parts.scheme or parts.netloc:
            for name, schema in self.schemas.items():
                if ref.split("#", 1)[0] == schema["$id"]:
                    return self.schema_paths[name]
            raise ValueError(f"{source}: external reference is not packaged: {ref}")
        decoded = unquote(parts.path)
        require(
            not parts.query and "\\" not in decoded and not decoded.startswith("/"),
            f"{source}: unsafe reference: {ref}",
        )
        target = (source.parent / decoded).resolve() if decoded else source.resolve()
        require(target.is_relative_to(self.root), f"{source}: reference escaped root: {ref}")
        require(
            target in {p.resolve() for p in self.schema_paths.values()},
            f"{source}: reference is not a packaged schema: {ref}",
        )
        return target

    def check_schemas(self) -> int:
        schemas, registry, checker = self.schemas, self.registry, self.checker
        refs = 0
        for name, schema in schemas.items():
            Draft202012Validator.check_schema(schema)
            resolver = registry.resolver(base_uri=schema["$id"])
            for obj in walk(schema):
                if "$ref" in obj:
                    self.local_reference(obj["$ref"], self.schema_paths[name])
                    resolver.lookup(obj["$ref"])
                    refs += 1
                if "format" in obj:
                    require(
                        obj["format"] in checker.checkers,
                        f"Missing format checker: {obj['format']}",
                    )
        return refs

    def check_fixtures(self) -> int:
        validators = self.validators
        fixture_count = 0
        for name, validator in validators.items():
            validator.validate(load(self.examples / f"fixtures/valid/{name}.json"))
            errors = list(
                validator.iter_errors(load(self.examples / f"fixtures/invalid/{name}.json"))
            )
            keyword, field = ("type", "title") if name == "node" else ("format", "created_at")
            require(
                any(e.validator == keyword and list(e.path) == [field] for e in errors),
                f"Invalid {name} fixture failed for the wrong reason",
            )
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
        relation["relations"] = [
            {
                "id": "44444444-4444-4444-8444-444444444444",
                "type": "supports",
                "target_id": node["id"],
                "confidence": 0.5,
            }
        ]
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
                target = self.local_reference(ref, self.examples / "openapi-example.yaml")
                resource = load(target)
                registry.resolver(base_uri=resource["$id"]).lookup(
                    "#" + parts.fragment if parts.fragment else resource["$id"]
                )
                api_refs += 1

        # Give the semantic validator a standard, preloaded referencing registry.
        # There is no retrieval callback: unknown schemes/IDs cannot reach a URL
        # or filesystem handler, even when schemas change their reference scope.
        from jsonschema_path import SchemaPath
        from jsonschema_path.accessors import SchemaAccessor
        from openapi_spec_validator import OpenAPIV31SpecValidator
        from referencing.jsonschema import DRAFT202012

        self.check_schemas()
        api_uri = (self.examples / "openapi-example.yaml").as_uri()
        registry = self.registry.with_resource(
            api_uri, Resource.from_contents(api, default_specification=DRAFT202012)
        )
        for name, schema in self.schemas.items():
            registry = registry.with_resource(
                self.schema_paths[name].resolve().as_uri(), Resource.from_contents(schema)
            )
        schema_path = SchemaPath(SchemaAccessor(api, registry.resolver(base_uri=api_uri)))
        OpenAPIV31SpecValidator(schema_path).validate()

        return api_refs

    def check_document_links(self) -> int:
        link_count = 0
        paths = sorted((self.root / "docs").rglob("*.md"))
        paths += [self.root / "README.md"]
        for path in paths:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                parts = urlsplit(target)
                if parts.scheme:
                    require(
                        parts.scheme in {"http", "https", "mailto"},
                        f"Unsupported link scheme in {path.name}: {target}",
                    )
                    continue
                if parts.netloc or not parts.path:
                    continue
                dest = (path.parent / unquote(parts.path)).resolve()
                require(
                    dest.is_relative_to(self.root), f"Nonportable link in {path.name}: {target}"
                )
                require(dest.exists(), f"Broken link in {path.name}: {target}")
                # Windows exists() is case-insensitive; catch errors before Linux CI.
                current = self.root
                lexical = Path(normpath(path.parent / unquote(parts.path)))
                for component in lexical.relative_to(self.root).parts:
                    require(
                        component in {p.name for p in current.iterdir()},
                        f"Link filename casing mismatch in {path.name}: {target}",
                    )
                    current = current / component
                link_count += 1
        return link_count

    def run(self) -> ValidationReport:
        schema_refs = self.check_schemas()
        fixtures = self.check_fixtures()
        rejection_probes, valid_probes = self.check_probes()
        return ValidationReport(
            schemas=len(self.schemas),
            schema_refs=schema_refs,
            fixtures=fixtures,
            rejection_probes=rejection_probes,
            valid_probes=valid_probes,
            openapi_refs=self.check_openapi(),
            document_links=self.check_document_links(),
        )
