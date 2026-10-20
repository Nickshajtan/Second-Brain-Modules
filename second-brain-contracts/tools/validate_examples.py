"""CLI for offline architecture example validation. Python 3.12+."""
from pathlib import Path

if __package__:
    from .example_validation import ExampleValidator
else:
    from example_validation import ExampleValidator


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    print(ExampleValidator(root).run().summary())
    print("Not checked: full OpenAPI lint, generated models, Ajv parity, runtime behavior, OS matrix.")


if __name__ == "__main__":
    main()
