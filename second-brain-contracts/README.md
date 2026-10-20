# Second Brain contract foundation

Phase 2.1 architecture package, prepared from `spec.md` on 2026-10-20. This folder is the portable root: all deliverable links and example validation work after copying it into a separate repository. It contains specifications and illustrative fixtures, not a knowledge engine or production contract release.

## Read in this order

1. [Repository evidence and assumptions](docs/architecture/repository-assessment.md).
2. [Core contracts](docs/architecture/contracts-spec.md).
3. [Integration protocols and capability matrix](docs/architecture/integration-protocols-spec.md).
4. [Generation and validation toolchain](docs/architecture/contract-toolchain-spec.md).
5. [Implementation plan and dependency graph](docs/architecture/phase-2-plan.md).
6. [Decisions](docs/architecture/decisions/README.md), [open questions](docs/architecture/open-questions.md), and [delivery report](docs/architecture/delivery-report.md).

Requirements inherited from the task are identified separately from proposed decisions. MUST/SHOULD language specifies the proposed implementation contract; it does not imply that a runtime exists. The example namespace `example.invalid` is deliberately unpublished.

## Validate the examples

From this folder, with Python 3.12+ and `jsonschema>=4.26,<5` available:

```text
python tools/validate_examples.py
```

The check is offline. It checks Draft 2020-12 schemas, local references, valid/invalid fixtures, the JSON-syntax YAML OpenAPI example, and local Markdown file links. It does not claim OpenAPI semantic linting, cross-language generation, or runtime conformance. See [validation record](docs/architecture/validation.md).

The command is a thin wrapper around `tools.example_validation.ExampleValidator`.
For Python callers, run from the module root:

```python
from pathlib import Path
from tools.example_validation import ExampleValidator

report = ExampleValidator(Path.cwd()).run()
print(report.summary())
```

Each validator owns its repository root and exposes separate schema, fixture,
probe, OpenAPI and document-link checks. `run()` returns an immutable
`ValidationReport`, prints nothing, and raises on failure. The command also works
as `python -m tools.validate_examples`; direct-script usage remains supported.

## Reuse as a submodule

This delivery is an ordinary subfolder. No nested Git repository, remote, commit, or parent `.gitmodules` change was created. Later, place **the contents of this folder** at the root of a dedicated repository, choose a license and schema publishing namespace, and publish it. A consuming project can then use:

```text
git submodule add <repository-url> vendor/second-brain-contracts
git submodule update --init --recursive
```

Commit the selected submodule revision in each consumer. Upgrades must be explicit; do not track a floating branch in deployment. Keep project vaults, credentials, private agent memory, raw exports, inventory outputs, and runtime databases outside the submodule. Each project supplies local configuration and a unique workspace ID. Shared schemas must not hard-code consumer filesystem paths. Generated packages will be built/released from this repository at milestone M2; do not import Python by manipulating a parent vault's `sys.path`.

No Phase 1 datasets or upstream parser checkout are copied into this package. The existing inventory tooling stays where it is; a future importer consumes it through an explicit configured path. The package can be reviewed or versioned independently without publishing personal knowledge.
