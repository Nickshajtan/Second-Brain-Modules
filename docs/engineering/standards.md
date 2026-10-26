# Engineering baseline

Read the [current contracts](../contracts/README.md), [Core scope](../core/m1.md),
[semantic invariants](../domain/domain-model.md) and relevant
[ADRs](../architecture/decisions/README.md) before changing behavior. Root
[agent instructions](../../AGENTS.md) summarize the same rules. Historical research
is evidence with dated scope, not a current implementation checklist.

## Provisioning and checks

Use Python 3.12+ and the repository's Node engine range (CI: Python 3.12, Node 22.19).
Install the existing hash-locked Python environment and npm lock as described in
[the root README](../../README.md). No check command installs tools or changes source.

| Command | Coverage |
| --- | --- |
| `python -m tools.check` or `python -m tools.check quality` | Ruff lint/format, Pyright, ESLint, strict TS consumer checks, syntax compilation |
| `python -m tools.check contracts` | Example/docs validation, production schema/ref/corpus validation, full generation drift, Python/Ajv parity inputs |
| `python -m tools.check core` | M1 application, recovery and quality-boundary regressions |
| `python -m tools.check full` | Quality + contract gates, complete pytest suite and fresh isolated distribution build/integrity verification |

The runner resolves its repository independently of caller CWD, uses the invoking
Python interpreter for both tests and Pyright, invokes subprocesses without a shell,
and stops on the first nonzero check. CI uses this same full plan on its existing
Windows/macOS/Linux matrix. Full builds own temporary destinations; an existing
developer bundle is never overwritten/deleted. Individual commands remain usable;
the runner is a short list of existing CLIs, not a task-runner framework.
From an unrelated directory, invoke the absolute `tools/check.py` path; module
invocation assumes the repository is on Python's import path.

## Python and typing

Ruff is the sole formatter for handwritten Python: Python 3.12, 100 columns, LF.
The reviewed lint profile adds B, SIM, PIE, RET and RUF to E4/E7/E9/F/I/UP. The
initial probe found three immediately invoked loop closures; explicit partial
binding removes the latent capture risk and satisfies B023. C4 was deliberately
not enabled: its 20 `dict()` style findings would cause unrelated mechanical churn.
No global diagnostic ignores or new per-file lint exceptions are needed.

Pyright `basic` covers all handwritten Core and contract runtime modules plus the
new check runner. The committed configuration has no diagnostic suppressions or
baseline allowlist. Zero errors is required. New exported Core/contract APIs and
the narrow CommitStore protocol are annotated. `parse_as` narrows a canonically
parsed registry alternative to a generated model class; it does not bypass schemas
or duplicate DTOs. The registry continues selecting factories dynamically.

This is a transitional baseline, not a claim of full strict typing. Existing
canonical JSON wire views and internal schema dictionaries still have unknown
member types (`dict` internally); JSON Schema validates their fields and generated
models describe domain alternatives. `decode_json` publicly returns `object` so
new consumers must narrow its shape. Core's object-only managed codec does that
narrowing. Unknown-type diagnostics are not enabled by `basic`; progressively type
internal wire handling when those areas change. No `Any`, casts or type-ignore
annotations were added to silence the checker. Existing generator/tooling modules
outside the check runner are a later typing slice; they retain lint and tests.

## JavaScript and generated ownership

ESLint checks handwritten `.mjs` with its recommended correctness rules, equality,
const and var rules. Explicit Node globals apply only to the Node runtime/tooling;
portable TS consumer fixtures remain under strict TypeScript checking. This catches
undefined identifiers, unused values, invalid control flow and unsafe assignments
that the declaration-only TS project does not inspect. No Prettier, TS ESLint
plugin, extra formatter or generated-declaration lint is introduced. Pyright,
ESLint and its rule package are exact dev pins in the existing npm lock.

| Ownership | Required enforcement |
| --- | --- |
| Canonical JSON Schemas/registry | Offline references, corpus, compatibility and generation checks |
| Generated Python/TS and manifests | Existing generators, exact file/byte drift, imports, round trips and consumer typecheck |
| Handwritten Python runtime | Ruff, Pyright, focused tests and canonical validation |
| Handwritten JS runtime/tools | ESLint, TS consumer interfaces, independent Ajv tests |
| Disposable distribution | Reproducible fresh build, isolated consumers, exact hash/file inventory |

Never hand-edit or post-format generated models. Generator-owned Black/isort use
remains inside the existing reproducible generator, not a handwritten formatting
workflow. Generated directories stay tracked for current submodule consumption.
See [distribution policy](../contracts/distribution.md) before any dist-free change.

## Errors, state and future slices

Caller validation, concealed denials, revision conflicts, corrupt state and storage
failure retain distinct sanitized codes. Unexpected snapshot programming errors now
use `INTERNAL`, retaining their exception cause for trusted diagnostics, rather
than masquerading as corrupt state. The final catch at that application boundary
exists to prevent exception text/private paths entering an external envelope.
Git stderr is not returned to callers. A managed ref must be direct; publication
does not follow symbolic refs, including a concurrent alias replacement.

Receipt verification resolves immutable original Node/Relation creation and
admission from retained managed ancestry, separately checking current replay
authorization. [M2.1](../core/m2-1-immutable-history.md) adds complete creation
snapshots and explicit legacy backfill; it enables no update/history handlers.
Never replace original-effect integrity with present-head equality or historical
grants. Legacy migration is trusted-host-only, explicit, source-fenced and atomic.

Reads intentionally scan/validate the whole committed tree and retained receipts;
Git reads are per blob, and cross-record scans may be quadratic in this tiny
corpus. No performance benchmark or scalability claim is made. Future caching
may reuse a validated immutable snapshot keyed by exact commit and contract
version; current principal/grant checks still run before delivery. O1–O4 remain
Owner decisions, not engineering defaults. Coverage percentages were not added:
existing boundary regressions identify concrete failure cases; exhaustive coverage
and hosted/power-loss guarantees remain unverified.
