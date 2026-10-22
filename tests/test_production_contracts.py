"""External validator agreement and generated artifact conformance, not domain handlers."""

import hashlib
import json
import re
import shutil
import socket
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from second_brain_contracts import ContractValidator, UnsupportedContractVersion
from second_brain_contracts.validation import load_json

from tools.generate_contracts import files, generate

ROOT = Path(__file__).resolve().parents[1]
CASES = load_json(ROOT / "tests/fixtures/contracts/v1.json")


def all_errors(errors):
    for error in errors:
        yield error
        yield from all_errors(error.context)


@pytest.fixture(scope="module")
def contracts():
    return ContractValidator(ROOT)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_external_canonical_verdict_and_generated_round_trip(contracts, case):
    original = deepcopy(case["instance"])
    errors = list(contracts.validators[case["schema"]].iter_errors(original))
    assert (not errors) == case["valid"]
    assert original == case["instance"]
    if case["valid"]:
        model = contracts.parse(case["schema"], original)
        assert contracts.dump(case["schema"], model) == original
    else:
        expected = case["error"]
        assert any(
            error.validator == expected["keyword"] and list(error.absolute_path) == expected["path"]
            for error in all_errors(errors)
        ), f"Invalid fixture failed for wrong reason: {case['name']}"


def test_independent_ajv_parity(contracts):
    result = subprocess.run(
        [shutil.which("node"), "tools/validate_production_typescript.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    assert json.loads(result.stdout) == [
        {"name": c["name"], "valid": contracts.validators[c["schema"]].is_valid(c["instance"])}
        for c in CASES
    ]


def test_semantic_rejections_are_not_claimed_structural(contracts):
    cases = load_json(ROOT / "tests/fixtures/contracts/semantic.json")
    for case in cases:
        contracts.validate(case["schema"], case["instance"])
        assert case["structurally_valid"] is True
        assert case["semantic_verdict"] == "reject"
        assert case["obligation_ids"] and case["reason"]


def test_every_root_variant_has_a_positive_fixture(contracts):
    for name, schema in contracts.schemas.items():
        branches = schema.get("oneOf", [schema])
        for branch in branches:
            validator = contracts.validators[name].evolve(schema=branch)
            assert any(
                c["schema"] == name and c["valid"] and validator.is_valid(c["instance"])
                for c in CASES
            ), (name, branch.get("$ref", "root"))


def test_registry_is_offline_and_fail_closed(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Attempted schema network access")

    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    assert ContractValidator(ROOT).reference_count > 0
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    p = tmp_path / "contracts/schemas/v1/knowledge.schema.json"
    schema = load_json(p)
    schema["$defs"]["Node"]["properties"]["content"] = {"$ref": "https://untrusted.invalid/schema"}
    p.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(ValueError, match="Unpackaged reference"):
        ContractValidator(tmp_path)


def test_registry_exact_coverage(tmp_path):
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    p = tmp_path / "contracts/registry/v1.json"
    manifest = load_json(p)
    manifest["schemas"].append(manifest["schemas"][0])
    p.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate registry name"):
        ContractValidator(tmp_path)


def test_generated_manifest_matches_checkout(contracts):
    contracts.verify_generated()


def test_documentation_schema_references_and_operation_inventory(contracts):
    for document in (ROOT / "docs/contracts").glob("*.md"):
        for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "contracts/schemas/v1/" not in href:
                continue
            path, _, fragment = href.partition("#")
            target = (document.parent / path).resolve()
            resource = load_json(target)
            contracts.registry.resolver(resource["$id"]).lookup("#" + fragment)
    documentation = (ROOT / "docs/contracts/operations.md").read_text(encoding="utf-8")
    for branch in contracts.schemas["operations"]["oneOf"]:
        definition = contracts.schemas["operations"]["$defs"][branch["$ref"].rsplit("/", 1)[1]]
        assert definition["properties"]["operation"]["const"] in documentation


def test_strict_ingress_does_not_trust_generated_coercion(contracts, tmp_path):
    node = deepcopy(next(c["instance"] for c in CASES if c["name"] == "knowledge-node"))
    node["revision"] = "1"
    with pytest.raises(ValidationError):
        contracts.parse("knowledge", node)
    for raw in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}']:
        p = tmp_path / "raw.json"
        p.write_text(raw, encoding="utf-8")
        with pytest.raises(ValueError):
            load_json(p)
    with pytest.raises(UnsupportedContractVersion) as error:
        ContractValidator(ROOT, version="2.0.0")
    assert error.value.code == "UNSUPPORTED_VERSION"
    with pytest.raises(UnsupportedContractVersion):
        contracts.validate("knowledge", {"schema_version": "2.0.0"})


def test_two_clean_generations_are_equal_and_match_committed(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    before = files(ROOT)
    generate(first)
    generate(second)
    assert files(first) == files(second) == before
    assert files(ROOT) == before


def test_illustrative_inputs_preserved():
    manifest = load_json(ROOT / "tests/fixtures/contracts/illustrative-hashes.json")
    for name, expected in manifest.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


def test_synthetic_directional_compatibility():
    suite = load_json(ROOT / "tests/fixtures/contracts/compatibility.json")
    verdicts = []
    for case in suite["cases"]:
        validator = Draft202012Validator(
            suite["schemas"][case["schema"]], format_checker=FormatChecker()
        )
        verdicts.append({"name": case["name"], "valid": validator.is_valid(case["instance"])})
        assert verdicts[-1]["valid"] == case["valid"]
    result = subprocess.run(
        [shutil.which("node"), "tools/validate_production_typescript.mjs", "--compatibility"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    assert json.loads(result.stdout) == verdicts
