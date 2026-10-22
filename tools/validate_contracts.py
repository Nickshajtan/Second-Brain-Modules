"""Validate production schema closure and the independent shared fixture corpus."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/python"))

from second_brain_contracts import ContractValidator  # noqa: E402
from second_brain_contracts.validation import load_json  # noqa: E402


def main():
    validator = ContractValidator(ROOT)
    cases = load_json(ROOT / "tests/fixtures/contracts/v1.json")
    for case in cases:
        errors = list(validator.validators[case["schema"]].iter_errors(case["instance"]))
        if bool(errors) == case["valid"]:
            raise AssertionError(f"Unexpected canonical verdict: {case['name']}")
        if case["valid"]:
            restored = validator.dump(
                case["schema"], validator.parse(case["schema"], case["instance"])
            )
            if restored != case["instance"]:
                raise AssertionError(f"Lossy generated round-trip: {case['name']}")
    print(
        f"PASS: {len(validator.schemas)} production schemas, "
        f"{validator.reference_count} offline refs, {len(cases)} fixtures/round-trips"
    )


if __name__ == "__main__":
    main()
