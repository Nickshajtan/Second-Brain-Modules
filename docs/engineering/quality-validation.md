# M1.1 quality validation

Baseline: `ed356827de35bba5ea5cc97bb04577aafdb0f5bd`, freshly fetched main on
2026-10-23. Initial status had only the user-authored replacement `task.md`.

## Findings and fixes

| Severity | Evidence | Action |
| --- | --- | --- |
| P1 | A fabricated symbolic managed ref redirected `publish` into another branch; new regression failed before the fix | Reject symbolic managed refs and publish with `update-ref --no-deref` to prevent alias traversal |
| P2 | Injected snapshot programmer failure was classified `REPAIR_REQUIRED`; new regression expected `INTERNAL` and failed | Separate known data/storage failures from unexpected defects; preserve cause and sanitize envelope |
| P2 | Replacing the disposable writer lock with a directory caused `submit` to raise a raw `PermissionError` with a private path | Sanitize writer-lock OS failures as `REPAIR_REQUIRED`, preserve cause, and prove the managed ref is unchanged |
| P2 quality boundary | Core imported `_unique`, `_nonfinite`, `_finite_float` from contract-private implementation | Export one typed strict JSON API, share encoding/decoding, and retain canonical validation |
| P2 maintainability | No Python type gate or lint on handwritten JS; runtime public APIs and storage boundary lacked types | Add Pyright basic, typed public APIs/CommitStore, and minimal ESLint correctness coverage |
| Deferred compatibility risk | Historical receipt verification compares immutable create results to current resource heads | Document exact coupling and required immutable-revision lookup before M2; no unsupported mutation added |

No P0 defect was confirmed. Review of path selection, CAS, instance binding,
receipt key/digest checks and process recovery found no additional reproduced
defect warranting a production change. Existing M1 tests remain, including actual
Git repositories, independent Ajv validation and separate-process retry recovery.

## Verification

| Executed check | Actual result |
| --- | --- |
| `python -m tools.check full` | Passed after the final code change; complete pytest suite: **280 passed in 222.88 seconds** |
| Ruff lint/format | Passed, 29 handwritten Python files formatted |
| Pyright via the invoking Python environment | 0 errors, 0 warnings |
| Additional Pyright logical targets Linux and Darwin | 0 errors, 0 warnings each; static analysis only |
| ESLint on handwritten JS and strict TS consumer typecheck | Passed |
| Python syntax compilation, including generated modules | Passed |
| Production contracts | 8 schemas, 717 offline refs, 133 fixtures/round-trips passed |
| Example/document validator | Passed, including 294 portable document links |
| Exact generation drift | 24 artifacts match; no extras |
| Legacy Python/Ajv parity | All 24 shared cases matched; full pytest also retains production parity |
| Isolated distribution build and integrity | Passed, 37 payload files |
| Focused quality-boundary and documentation tests after harness correction | 49 passed |
| Quality runner invoked by absolute path from `.cache/` | Passed independently of caller CWD |
| Ignore visibility probes | All five assessed canonical/source/generated/fixture paths remain visible |
| Scoped `git diff --check` excluding untouched user `task.md` | Passed |

The three correctness regressions failed before their fixes and passed afterward.
The final suite adds 16 quality-boundary cases, including committed invalid metadata
schema classification and writer-lock filesystem failure. The isolated consumer test now exercises the public JSON
and typed parsing APIs from the built bundle, outside the source checkout.
No test or fixture was discarded to obtain the passing run.

The first full run exposed test-harness integration failures: reusable Git fixtures
were not visible in full-suite collection, and cloned documentation omitted the new
root AGENTS file. Shared fabricated fixtures now live in `tests/conftest.py`, and
the isolated repository copy includes AGENTS. The complete verification above was
rerun afterward. The pre-existing generator formatter deprecation warning remains;
the generator/toolchain was intentionally retained. No manual or hosted CI tests
were executed, and no coverage percentage or power-loss guarantee is asserted.

## Inventory and limits

See [the evidence inventory](repository-hygiene.md) for classifications and actions.
No tracked files were removed or moved. Ignored local caches, environments and
user material were retained. Narrow ignore patterns were added for tool/coverage
and editor output. Historical records, illustrative fixtures and tracked generated
consumers remain. Only generator-produced hash provenance needs regeneration for
the new tooling inputs; canonical schemas and model formats remain unchanged.

New Node dev tools are exact pins in `package-lock.json`; comparing the prior and
current lock found **no changed versions among existing packages**. Python
locks/toolchain were retained. No second Python linter/formatter or new domain operation was added.
The broad exception fallback is confined to sanitizing unexpected snapshot defects,
with `INTERNAL` and the original cause. It is not proof that every programming
error or failure mode has been exercised.

Local Windows execution does not establish hosted Linux/macOS results, filesystem
power-loss guarantees or full strict typing. Basic Pyright deliberately leaves
legacy dynamic JSON fields unknown; no diagnostics are globally suppressed.
Recommended next milestone: bounded immutable Node update with revision CAS,
receipt-to-historical-revision verification and current authorization, before
reconciliation/governance/MCP expansion. O1–O4 remain unresolved.
