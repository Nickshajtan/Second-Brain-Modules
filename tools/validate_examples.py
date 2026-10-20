"""CLI for offline architecture example validation. Python 3.12+."""

import argparse
import sys
from pathlib import Path

if __package__:
    from .example_validation import ExampleValidator
else:
    from example_validation import ExampleValidator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(ExampleValidator(args.root).run().summary())
    except Exception as exc:
        print(f"FAIL ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    print("Not checked: generated-model parity (run pytest/npm), runtime behavior, OS matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
