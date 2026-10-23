# Second-Brain-Modules

Reusable modular-monolith foundation for multiple isolated Second Brain installations.
This repository is the single code/submodule boundary. Each consumer owns its vault,
workspace identity, configuration, knowledge Git history, runtime stores and secrets.
The [M1 Python Core](docs/core/m1.md) implements private-Cluster Node/Relation creation,
atomic Git batches and committed reads. No graph engine, agent runtime or server is implemented.

The [production contract baseline](docs/contracts/README.md) now supplies eight canonical
Draft 2020-12 resources, generated Python/TypeScript models and 34 typed operation requests.
Version 1.0.0 is an unreleased contract baseline; illustrative 0.1.0 examples remain separate.

## What works today

- Instance-bound Core with explicit trusted grants, immutable initial revisions,
  committed Git reads, conditional ref publication and durable retry receipts.
- Offline Draft 2020-12 schema and local-reference checks.
- Valid/invalid fabricated fixtures, semantic OpenAPI example validation and local documentation-link checks.
- OOP validation API and thin CLI, unit tests, Ruff lint/format checks.
- Generated illustrative Pydantic/TypeScript models, shared Python/Ajv parity corpus and strict TS checks.
- Exact dependency locks and generated-artifact drift detection.
- GitHub Actions matrix for Ubuntu, Windows and macOS; remote results remain unverified until Actions runs.

## Development

Use Python 3.12 and Node 22.19 through 24; create/activate a local virtual environment.
All commands below run from this Git root:

```text
python -m venv .venv
```

PowerShell: `.venv\Scripts\Activate.ps1`. macOS/Linux: `source .venv/bin/activate`.
Then:

```text
python -m pip install --require-hashes -r requirements-dev.lock
npm ci --ignore-scripts --no-audit --no-fund
python -m tools.check full
```

Use `python -m tools.check quality`, `contracts` or `core` for focused checks.
See [engineering standards](docs/engineering/standards.md),
[hygiene inventory](docs/engineering/repository-hygiene.md) and
[executed results](docs/engineering/quality-validation.md).

Regenerate with `python -m tools.generate_contracts`. Generated files are committed,
never edited by hand. The checker compares bytes and the complete file set in a
clean temporary directory. Tools use only synthetic fixtures, no external vault.
The illustrative schemas retain unpublished `example.invalid` IDs. Production schema
IDs and offline registry are separate under `contracts/`; no schema hosting or package
publication is claimed. O1–O4 policy decisions remain open.

Python API: `ExampleValidator(root).run()` from `tools.example_validation` returns
an immutable `ValidationReport` and raises on failure without printing. Individual
check methods are callable. The CLI supports `--root PATH`, works from other working
directories and returns nonzero with diagnostics on failure. Development dependencies
are required; consuming schema JSON or TS declarations does not import Core runtime modules.

## Architecture and consumption

- [Latest: Phase 1.1 lean architecture decision](docs/research/phase-1-1/architecture-decision.md),
  [Obsidian fit](docs/research/phase-1-1/obsidian-fit.md) and
  [remaining Owner decisions](docs/research/phase-1-1/open-decisions.md).
- [Phase 1 domain and reuse baseline](docs/research/README.md), including the
  [historical-spec reconciliation register](docs/architecture/reconciliation-register.md).
  Use this baseline for the latest domain decisions; older specifications below retain historical assumptions.
- [Monorepo boundaries and workspace isolation](docs/architecture/monorepo-architecture.md).
- [Versioning, upgrades and submodule example](docs/architecture/versioning-and-consumption.md).
- [Contracts](docs/architecture/contracts-spec.md), [integration](docs/architecture/integration-protocols-spec.md),
  [toolchain](docs/architecture/contract-toolchain-spec.md), [implementation plan](docs/architecture/phase-2-plan.md).
- [Decisions](docs/architecture/decisions/README.md), [Stable revision proposal](docs/architecture/stable-revisions.md),
  [open questions](docs/architecture/open-questions.md).
- [Hardening report](docs/architecture/hardening-report.md) and [original repository assessment](docs/architecture/repository-assessment.md).

A consumer adds the whole repository once:

```text
git submodule add https://github.com/Nickshajtan/Second-Brain-Modules.git vendor/second-brain-modules
```

Pin its commit in the consumer repository. Keep knowledge/configuration/`.brain/`
outside the submodule; independently upgrade each installation. There is no second
contract submodule, checkout-time hook, universal loader or provider dependency.
See [MIT license](LICENSE). Existing local exports and inventory remain ignored and untouched.
