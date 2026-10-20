import json
import shutil
import subprocess
from pathlib import Path

import pytest
from generated.cluster import ExampleCluster
from generated.node import ExampleKnowledgeNode

from tools.example_validation import ExampleValidator, load

ROOT = Path(__file__).resolve().parents[1]
CASES = load(ROOT / "tests/fixtures/parity.json")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_canonical_verdict_and_generated_round_trip(case):
    validator = ExampleValidator(ROOT).validators[case["schema"]]
    assert validator.is_valid(case["instance"]) == case["valid"]
    if case["valid"]:
        model = {"node": ExampleKnowledgeNode, "cluster": ExampleCluster}[case["schema"]]
        parsed = model.model_validate(case["instance"])
        serialized = parsed.model_dump(mode="json", exclude_unset=True, by_alias=True)
        assert serialized == case["instance"]
        validator.validate(serialized)


def test_optional_absent_and_explicit_null_are_distinct():
    data = load(ROOT / "docs/architecture/examples/fixtures/valid/cluster.json")
    explicit = ExampleCluster.model_validate(data)
    assert explicit.model_dump(mode="json", exclude_unset=True)["description"] is None
    data.pop("description")
    omitted = ExampleCluster.model_validate(data)
    assert "description" not in omitted.model_dump(mode="json", exclude_unset=True)


def test_python_typescript_validator_parity():
    node = shutil.which("node")
    assert node, "Install Node and run npm ci before the full test suite"
    result = subprocess.run(
        [node, str(ROOT / "tools/validate_typescript.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    actual = json.loads(result.stdout)
    validators = ExampleValidator(ROOT).validators
    expected = [
        {"name": case["name"], "valid": validators[case["schema"]].is_valid(case["instance"])}
        for case in CASES
    ]
    assert actual == expected
