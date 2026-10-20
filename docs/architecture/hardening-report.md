# Repository hardening report

## Implemented

Promoted the prior contract wrapper into the Second-Brain-Modules Git root. Existing
architecture material, schemas and fixtures were retained. Root README, MIT license,
text settings, Python/npm configuration, lockfiles and `.github/workflows/ci.yml`
now form one reusable repository boundary. No nested Git repository/submodule was
created. Local original inventory/export directories are ignored, not modified.

The reusable `ExampleValidator` now has strict JSON diagnostics, schema/ref checks,
offline allowlisting, semantically validated OpenAPI through openapi-spec-validator
with a preloaded offline SchemaPath registry, scoped documentation traversal and a nonzero
CLI failure exit. No schema translator or custom generator was introduced.

Tests exercise invalid schemas, missing/unresolved/external refs, malformed/duplicate
JSON, wrong-reason fixture rejection, unexpected acceptance, unsafe paths, unknown
formats, offline behavior, source non-mutation, independent roots, spaces/other cwd,
structured reports, immutable results and CLI diagnostics. Contract spike tests compare
the same 24 fabricated cases between Python jsonschema and Ajv2020 and round-trip
valid cases through generated Pydantic models. Strict TS checks cover generated types.

Generated Python/TS files are committed-source candidates under `packages/`; the
generator uses locked mature tools, writes a source/lock/config hash manifest and
checks exact bytes plus extra/missing files. No artifact was hand-edited. Tooling
imports no future knowledge runtime, provider, agent, MCP or Obsidian SDK.

## Validation status

Local target: Windows, CPython 3.12.6, Node 24.19.0. CI selects Python 3.12 and Node
22.19.0 on Ubuntu, Windows and macOS. Development dependencies installed with a
Python hash lock and npm integrity lock. Local commands and final counts are recorded
at completion below; hosted Actions and macOS/Linux remain **unverified** until run.
No green CI is inferred from local tests. No commits or pushes are made by this task.

| Local check | Result |
|---|---|
| Pytest | **60 passed**: 34 validator tests and 26 contract-spike/parity tests |
| Shared corpus | **24 matching Python/Ajv verdicts**, including valid-model round trips and optional/null preservation |
| Example validation | **2 schemas, 20 refs, 4 fixtures, 11 rejection probes, 3 valid probes, 2 OpenAPI refs, 54 document links** |
| Generated output | **5 artifacts** generated; clean regeneration matches; an extra-file probe correctly fails drift detection |
| Ruff / syntax / imports | Lint and format checks pass; compileall and pytest imports pass |
| TypeScript | Strict typecheck passes |
| Dependency consistency | `pip check` passes; Python hash lock and npm integrity lock used |
| Workflow | YAML/trigger/matrix/read-only permissions/SHA-pin checks pass locally; hosted execution unverified |
| Data preservation | **112 inventory file hashes unchanged; all 861 original source hashes verified** |

GitHub Actions uses reviewed immutable release commit pins for
[checkout v4.2.2](https://github.com/actions/checkout/releases/tag/v4.2.2),
[setup-python v5.6.0](https://github.com/actions/setup-python/releases/tag/v5.6.0),
and [setup-node v4.4.0](https://github.com/actions/setup-node/releases/tag/v4.4.0).
It runs on PRs and pushes to `main`, with read-only token permissions, no production
secrets, a 20-minute timeout and redundant-run cancellation. Dependency acquisition
uses public registries; validation/generation calls no AI service or private vault.

Local setup encountered a blocked pip-tools cache and npm certificate-chain failure.
Locking used approved access; npm succeeded with Node's system certificate store,
without disabling TLS validation. CI does not embed this machine-specific setting.
The generator emits an upstream notice that Black/isort will become optional; the
current locked toolchain includes and explicitly selects both. It is not a failed check.

## Changed-file map

Moved existing wrapper README/settings, `docs/` and `tools/` to the root, preserving
valid specifications and examples. Added root `pyproject.toml`, `requirements-dev.in`,
`requirements-dev.lock`, `package.json`, `package-lock.json`, and CI workflow. Added
`tools/generate_contracts.py`, `generate_typescript.mjs`, `validate_typescript.mjs`;
hardened `example_validation.py` and `validate_examples.py`. Added pytest tests/shared
fixtures, five generated artifacts and TS strict config/type tests. Added this report,
impact assessment, monorepo/versioning/Stable-review documents and ADR-008; updated
ADRs 002/003/006/007, decision index, contracts, toolchain, plan and question register.
Original delivery/validation reports are labeled historical and linked here.

## Architecture changes

[ADR-008](decisions/ADR-008-monorepo-consumption.md) establishes whole-repository
reuse, explicit per-workspace state/configuration and no process-global active
workspace. [Monorepo architecture](monorepo-architecture.md) specifies logical
responsibilities/dependencies, state ownership and future import-boundary testing.
[Consumption/versioning](versioning-and-consumption.md) gives a concrete host layout,
submodule commands, independent upgrades and migration responsibilities.

The [Stable revision review](stable-revisions.md) recommends retaining the approved
revision while a candidate changes; promotion replaces a pointer only after approval
and concurrency checks. Historic Markdown/Git bytes remain authoritative; current
authorization still applies. This remains a Q03 proposal; no storage/promotion code
is implemented. Trust documentation distinguishes trusted code, cooperative scoped
agents and hostile execution sharing human filesystem privileges. No sandbox is built.

## Limits, risks and next milestone

Pydantic uses `class_` internally; JSON serialization requires `by_alias=True`.
`exclude_unset=True` preserves omission versus explicit null. UUID/datetime conversion,
optional null acceptance and coercion can differ from canonical schema; validators
remain authoritative. TS types do not enforce patterns, bounds or format semantics.
The 24-case proof covers the existing example subset, not every Draft 2020-12 feature.
Cross-platform generation stability still needs the defined CI matrix.

Production schema namespace/package names (Q01), approved revision semantics (Q03),
crash-consistent storage (Q04), trust isolation (Q07), advanced generator features and
release compatibility (Q13) remain open. Repository identity/license are established;
unrelated questions were not closed. Dependencies remain development-only, not a
published runtime installation contract.

Next: confirm hosted CI on the target OS matrix, review production primitives/schema
namespace and Stable pointer rules, then design/test the narrow M3 repository/recovery
slice. No CRUD engine, database runtime, graph engine, workflow engine, remote server
or agent runtime was added.
