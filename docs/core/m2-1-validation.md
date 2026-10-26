# M2.1 implementation and validation record

Baseline: `524d954ea1c6e26efc8a81d83052bc5ebf0e46a5`; the initial checkout was
clean. Authority: the Owner-supplied M2.1 specification. This report records
observed local checks; it is not a hosted CI or deployment attestation.

## Design gate and delegation evidence

The configured `implementer` was invoked as `/root/m21_implementation` for the
preliminary audit, bounded production implementation, regressions and documentation.
The configured `reviewer` was invoked independently as `/root/m21_review`.
Both delegations are evidenced by native invocation and completion/message events;
optional numeric trace/session identifiers are not exposed here.

Before production changes, the reviewer inspected actual baseline code and the
[concrete audit/design](m2-1-immutable-history.md). Stage A verdict:
**PASS WITH WARNINGS**. Required implementation safeguards were exact original
receipt/request and generation binding, unique retained first-parent origin,
cross-resource revision identity uniqueness, immutable legacy supplements,
publication-bound migration evidence and separation of current authorization.
This design verdict does not approve an unseen implementation.

Reviewer instructions are read-only behavioral constraints; inherited runtime
permissions do not prove filesystem isolation. The reviewer reported no execution
or writes during the implementation review.

Initial completed-diff verdict: **BLOCK**, one confirmed P2 in `history.py`.
Retention validation iterated only current receipts/history, allowing a later
committed tree to remove an entire transaction's receipts, requests and resources
together. The remaining bootstrap records could validate despite retained original
ancestry. One implementer correction now derives immutable receipt/request/revision
and supplement retention from every ancestor, leaving mutable heads and live
Memberships separate. Both whole-transaction removal regressions pass, as do real
shallow-clone and two-parent-commit rejection cases. The single independent reviewer
recheck returned **PASS WITH WARNINGS**: P2 resolved, no remaining confirmed
P0/P1/P2. The reviewer inspected the actual correction and all four added cases;
it did not execute tests or write files. Coordinator-executed checks are separate
evidence. No workflow bypass or additional correction/recheck cycle occurred.

## Verification status

The final production diff passed the unified full command with native exit code 0:
**346 tests passed in 1144.65 seconds (19:04)**. Independent review recheck is
complete with the verdict above. Tests establish only the exercised cases.

Local tools: Python 3.12.6 (`.venv/Scripts/python.exe`), Node 24.19.0 and
Git 2.46.2.windows.1. Other operating systems and the CI Python/Node matrix
are not established by these local results.

Development checks included an initial history suite with 19 passes and five
failures: deterministic UUIDv5 supplement IDs violated the canonical v4-only
EntityId pattern, and an isolated fixture used a generated wrapper instead of its
value. These were corrected. Independent Ajv also rejected a draft conditional
schema's strictRequired locality; canonical branches were corrected and regenerated.
Affected cases subsequently passed (six cases); corpus/Ajv checks passed (155 cases).
These checks preceded the final baseline-record amendment and are developmental
evidence, not final-diff certification. A superseded long focused run was interrupted
through its own session; no result is claimed for it.

| Final-diff command | Observed result |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_core_m21_history.py -k 'joint_transaction or shallow_managed or merge_in_managed' -q --tb=short` | 4 passed, 28 deselected, 39.06 seconds |
| `.venv/Scripts/python.exe -m tools.check quality` | Ruff lint/format, Pyright (zero errors), ESLint, TypeScript consumer and compilation passed |
| `.venv/Scripts/python.exe -m tools.check full` | Exit 0; 346 tests passed; quality, schemas, exact generation, parity and fresh distribution build/integrity passed |
| `.venv/Scripts/python.exe -m tools.validate_examples` | 620 portable documentation links; example/ref/rejection/OpenAPI checks passed; final exit 0 |
| `git diff --check` | Passed |

The full run explicitly propagates the native exit code after PowerShell log
redirection. Generator Black/isort FutureWarnings are retained in its log; they
are not treated as test failures or proof of a failed native command.

The full command validated eight production schema families, **768 offline
references**, **153 portable fixtures/round-trips**, **24 exact generated
artifacts** with no extras and a fresh **37-payload-file** distribution plus its
integrity check. Strict TypeScript consumer checks and independent Ajv tests are
included. No existing developer distribution was overwritten.

## Delivered evidence and migration boundary

New creations commit exact NodeRevision and independent RelationRevision snapshots
with heads, original admission, normalized request and receipt under one managed-ref
publication. Original receipt generations resolve uniquely in retained linear
ancestry; their complete canonical tree, exact request/receipt pair, original parent,
actor, result identities, digests and admission effects are checked. Current heads
are not the historical proof. Current live scopes and grants separately authorize
replay, without inheriting historical grants.

`history.py` contains original-effect resolution; `migration.py` exports the narrow
trusted-host `inspect_history` and `apply_history_migration` functions. Dry-run
allocates no objects or generations. Explicit apply requires the exact deterministic
source-fenced plan, preserves existing historical bytes and receipt identities,
validates destination records and publishes once through writer lock and Git CAS.
Exact reapplication returns the durable baseline even after unrelated commits.
Unverifiable sources produce a blocking report rather than guessed content.

Canonical amendments are confined to existing `knowledge` and `transaction`
families: NodeRevisionSnapshot supplements metadata-only legacy revisions;
HistoryBaseline binds fresh/migrated profile, publication generation and migration
source/plan/additions. Python/TypeScript and manifests were regenerated. Old closed
consumers reject the new variants; this explicitly amends unreleased 1.0.0 and
requires coordinated pinned consumer/runtime updates. See
[compatibility](../contracts/compatibility.md) and
[ADR-011](../architecture/decisions/ADR-011-immutable-creation-effects.md).

## Verification limits and next slice

The focused [automated regression suite](../../tests/test_core_m21_history.py)
contains 32 cases. Its evidence boundaries are:

| Requirement boundary | Regression evidence |
|---|---|
| H01–H04 identity, sequence, snapshot binding/digest | `test_fresh_exact_history_and_replay_after_unrelated_commit`; parameterized `test_corrupt_or_missing_immutable_effects_fail_closed` |
| H05–H08 original effects versus current heads/authority | `test_historical_verifier_ignores_future_heads_and_live_admission`; exact restart/unrelated-commit replay; changed request and partial-batch replay rejection |
| H09 retained evidence and unavailable/ambiguous origins | Corrupt/missing effects, whole-transaction deletion, marker/supplement retention, ambiguous-generation inventory and real shallow/merge cases |
| H10 migration publication/recovery | `test_explicit_migration_preserves_original_bytes_and_receipts`; interruption, stale source, real ref-race and host-only cases |

Portable fixtures and actual migration outputs also pass through independent
Python JSON Schema and TypeScript Ajv validators in the automated suite. These
cases establish their specific fabricated inputs, not exhaustive payload coverage.

Original creation and migration commits must remain reachable in complete linear
managed ancestry. Missing objects, shallow history, merges and ambiguous origins
fail closed. This is unsigned local integrity under trusted retained Git, not an
external attestation against an administrator replacing all history.

The M2.2 readiness test changes live Node heads to 2/3, independently changes a
Relation and live Membership metadata, then invokes historical verification and
replay directly against isolated fixtures. The history-permission portion checks
separate capability denial/admission and exact original snapshot selection. It does
not execute production updates or historical delivery: neither handler exists.
Normal public snapshot invariants are not relaxed for these fixtures.

No Node/Relation update, historical-read handler, MCP/Obsidian integration, index,
background migration, dependency or Harness enforcement is introduced. O1–O4
remain open. The next slice is M2.2 Node mutation and authorized historical reading,
followed by M2.3 independent Relation mutation. Logical atomicity/process recovery
does not certify filesystem flush, hardware/power-loss durability, backup coherence,
raw vault visibility, deployed isolation or other operating systems.
Full ancestry/tree scans are deliberate for this small corpus; scalability and
latency have not been benchmarked. No signing or external trusted ledger is added.
