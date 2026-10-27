# M2.1.1 validation evidence

Status: **COMPLETE for the stated M2.1.1 scope**. The Owner authorized the remaining focused
production/fixture correction and independent review, and increased the automatic
correction/recheck limit to three cycles. The reviewed production runtime passed
the full gate and all 60 benchmark rows. The final test-only structural regression
also passed implementer and independent reviewer execution. M2.2 is ready for its
separate bounded Node-mutation specification; no mutation handler is enabled here.
Baseline: `d00fb9b6be83a9a83d6f15c26062df0530c2b192` (clean checkout at start).
This report distinguishes observed checks from design expectations. Passing tests
do not establish scalability, deployment isolation or physical durability.

## Delegation and design review

Configured `implementer`: `/root/m211_implementation`, invoked for baseline profiling,
design, production implementation, regression tests, benchmarks and documentation.
After the baseline/design gate, a second invocation of the same configured
`implementer` role, `/root/m211_benchmark`, took exclusive ownership of the
benchmark harness, performance documentation and optimized result artifact.
The original implementer retained production, tests and recovery/design documents.
Configured `reviewer`: `/root/m211_review`, invoked independently and read-only for
Phase A architecture review and subsequently the actual completed diff.
Native invocation/message events identify these tasks; optional numeric session or
trace identifiers are not exposed by the delegation interface. Behavioral read-only
instructions do not independently establish reviewer filesystem isolation.

Phase A initially held on a concrete authorization omission: authenticating returned
SQLite rows cannot prove a Membership or idempotency lookup row was not deleted.
The reviewed design instead authenticates the exact completed SQLite bytes and
deserializes them into a private in-memory connection. Runtime lookup and carryforward
must use that private projection exclusively. This closes the incomplete-dependency
and missing-key mechanisms without treating SQLite as canonical content.

Independent design verdict: PASS WITH WARNINGS. Required conditions include exact
instance/ref/schema/repository binding, retained signed rollback anchor, explicit
enrollment, authenticated same-byte deserialization, coherent checkpoint/index
replacement, ordered intermediate verification, current authorization and canonical
blob validation. Startup and memory cost scale with index bytes; a privileged actor
replacing the trusted key and all state is outside the integrity claim.

Independent initial final-diff verdict: **BLOCK**, two confirmed P2 findings:

1. Private canonical blob loading preceded current authorization. An unauthorized
   Node read returned `REPAIR_REQUIRED` for a hidden missing body and `NOT_FOUND`
   for an unknown ID. The coordinator independently reproduced this in disposable
   Git; the reviewer also reproduced denied replay. Correction must check current
   operation-specific denial conditions from authenticated projection metadata
   before private loading, retaining canonical and authorization checks for every
   successful delivery.
2. An existing empty trust directory was mistaken for a pristine unenrolled
   repository. Deleting its files and rolling the ref backward allowed rebuild to
   establish a new anchor and serve the older root. This distinguishable anchor
   loss must require operator recovery, without automatic reenrollment.

The single automatic implementer correction cycle completed both fixes. Denial-only
screens evaluate current grants over authenticated scope/lifecycle facts before
private loading; canonical validation and the original positive authorization
checks remain required. Creator replay without read authority remains supported.
Empty trust directories require operator recovery, and bootstrap cannot bypass
retained/lost enrollment by recreating a deleted managed ref.

The sole independent reviewer recheck returned **PASS WITH WARNINGS**, with no
remaining confirmed P0/P1/P2 findings. It inspected the actual corrected files and
ran six targeted regressions: **6 passed, 50 deselected**, exit 0, 39.07 seconds.
No reviewer edits or subdelegation occurred. That exhausted the then-current
one-correction/one-recheck limit; later corrections required the Owner's direction.

The coordinator's first unified run subsequently exposed two legacy M1 fixtures
with a second unintended invalid condition: changing fallback Node identity left
Relation endpoints dangling, so authorization screens returned `NOT_FOUND` before
the intended duplicate-request/collision check. Both failures were reproduced in a
focused run (2 failed, 40 deselected, 10.66 seconds). Disposable probes preserving
the resource references returned the original `VALIDATION_FAILED` and
`REVISION_CONFLICT`, with unchanged Git refs. No production fix was indicated.
The first unified run was interrupted after those failures; it is not a passing
full-suite result. The Owner explicitly authorized the proposed fixture-only
corrections and an additional independent review. Original assertions remain;
this authorization does not open another automatic production correction cycle.
The implementer applied only the proposed fixture changes: **2 passed, 40
deselected** (8.79 seconds), Ruff and diff checks passed. The additional authorized
independent narrow review returned **PASS** and independently ran the same two
cases: **2 passed, 40 deselected**, exit 0 (10.59 seconds). Expected errors and
zero-effect assertions were retained. No additional production changes occurred.
The reviewer did not retain a pre-follow-up runtime hash and explicitly limited
its historical byte-equality claim; final benchmark runs capture and check their
own runtime/schema/harness fingerprints. The unified full gate was then rerun.

That full run completed with **398 passed, 4 failed** (956.82 seconds), exit 1.
Three documentation-validator tests used a copied-repository fixture that omitted
the newly linked `tools/benchmark_history.py`. The fourth injected domain failure
through `generation()`, whose bounded descriptor path intentionally does not run
domain validation. A separate disposable probe on the actual fast Node read found
an unsanitized unexpected `RuntimeError`, a genuine lost boundary guarantee that
required restoration. That run did not pass quality and distribution gates.
The Owner subsequently authorized the remaining focused correctness/fixture fixes
and independent review, and raised the automatic cycle limit to three. The
preceding approval had been fixture-only.

Implementer correction checks: 15 focused cases passed (79.25 seconds); the
expanded hardening suite plus selected existing creator/migration/CAS cases passed
62 tests (435.82 seconds); the added bootstrap case separately passed (3.62 seconds).
Quality, 646 documentation links and diff whitespace checks passed. At that stage,
the coordinator's unified gate and same-runtime benchmark matrix remained pending.
The reviewer independently ran seven focused cases (all passed), covering
restored-stat projection changes, transaction deletion/rollback and copied trust
material; those cases did not cover the two newly reproduced defects.

The independent reviewer also assessed the old test that deleted an unrelated Node
body and expected `generation()` to discover it. Under the required separation,
generation lookup verifies the pinned descriptor and accepted frontier; it is not
a repository-wide availability audit. Targeted reads/replay must fail on missing
required objects, and explicit full audit must detect missing unrelated current
or historical objects. Regression evidence for all three scopes is required.
This changes detection timing and must not be described as identical per-call
corruption coverage or complete object revalidation at restart.

## Observed baseline

The disposable benchmark ran the original M2.1 implementation before production
changes. Seven operations at each of 100, 1,000 and 10,000 commits produced 21 actual
observations. Every operation reached its explicit 600-Git-process budget.

| Corpus | Receipts / Nodes / Relations | Git processes | Blob reads | Tree-read entries | Ancestry entries |
| --- | --- | ---: | ---: | ---: | ---: |
| 100 commits | 8 / 16 / 8 | 600 | 590 | 6 | 100 |
| 1,000 commits | 53 / 106 / 53 | 600 | 597 | 1 | 0 |
| 10,000 commits | 503 / 1,006 / 503 | 600 | 597 | 1 | 0 |

These are interrupted-operation counts, not completed-operation costs. At the larger
sizes the budget exhausted while loading the current tree, before ancestry traversal.
Elapsed cutoff times were 26.410684–30.878477 seconds. They are censored observations;
no successful before-change latency or speedup ratio is inferred from them.

Measured operations: Node read, Relation read, generation lookup, exact receipt
replay, bounded create, historical verification and legacy migration inspection.
The corpus contains growing create-only transaction evidence and unrelated unique
generations, with varied body sizes. Setup is outside operation counters. An earlier
fixed-corpus experiment and an interrupted unmeasured 10,000-commit setup are not
claimed as completed measurements.

See [performance methodology](../engineering/history-performance.md) and
[design](m2-1-1-history-hardening.md). Optimized measurements, full regression results,
recovery evidence and the final readiness decision will be recorded after execution.

An initial optimized 100/1,000-commit run completed 40 rows, but the subsequent
security correction changes the runtime hash. Those rows are superseded development
evidence, not final measurements. The 10,000-commit run was interrupted before any
operation row completed. Final performance claims require a new same-runtime matrix.

## Final integration evidence

The final reviewed runtime passed `.venv/Scripts/python.exe -m tools.check full`
with exit 0: **404 passed in 993.11 seconds**. Ruff, Pyright, ESLint, TypeScript,
documentation and contract validation, generation drift and independent validator
checks passed. Fresh isolated distribution build and verification both passed
with **37 payload files**. The earlier failed runs below remain historical
evidence; they do not describe the final gate result. Final benchmark execution
started after the full gate completed, without concurrent expensive test runs.

Coordinator commands (using the existing locked environment):

```text
.venv/Scripts/python.exe -m tools.check full
.venv/Scripts/python.exe -m pytest tests/test_core_m1.py -k "duplicate_request or stale_generation_and_entity_collision" -q --tb=short
.venv/Scripts/python.exe -m tools.validate_examples
git diff --check
```

- Earlier failed unified command: exit 1, **398 passed / 4 failed**, 956.82 seconds.
  Its fresh distribution build stage did not execute after the pytest failure.
- Quality gates passed: Ruff (38 formatted files), Pyright (zero errors/warnings),
  ESLint, strict TypeScript consumer checks and compilation.
- Contract gates passed: eight families, 768 offline references, 153 fixture
  round-trips, 24 exact generated artifacts and independent validator checks.
- Final standalone documentation validation: 646 portable links and existing
  schema/example/rejection checks passed; `git diff --check` exited 0. Existing
  CRLF normalization notices are not whitespace failures.
- Final optimized matrix: **60/60 complete**, 20 rows each at 100/1,000/10,000
  starting commits; both measurement processes exited 0 with unchanged runtime,
  contract and harness fingerprints. Superseded development rows are excluded.

The bounded production corrections below are complete and reviewed. Measurements
finished before the added test-only structural guard was executed.

The earlier root `AGENTS.md` limit of one automatic implementer correction and one
reviewer recheck was honored. The Owner separately authorized the two ID-fixture
corrections and additional narrow review, then authorized the remaining focused
fixes and independent review. The Owner also increased the repository limit to
three automatic correction/recheck cycles; root instructions and workflow guidance
now agree. The remaining boundary correction completed: unexpected errors in
read/submit/generation return sanitized `INTERNAL`, while typed errors retain
their codes. Outgoing read validation is inside the protected boundary. The
documentation fixture includes linked benchmark and test sources. Implementer
checks passed 18 boundary and 34 documentation tests plus the quality command.
The independent reviewer inspected these actual changes and the three-cycle
policy update: **PASS WITH WARNINGS**, no confirmed P0/P1/P2 findings; independently
**18 passed** (23.95 seconds), and `git diff --check` passed. The complete unified
gate subsequently passed (404 tests and fresh distribution build/check); the
final benchmark matrix subsequently completed successfully.

After the full gate, one test-only coverage gap was closed:
`test_warm_create_verifies_only_its_new_transition_and_receipt` establishes six
prior batches, then requires exactly one new receipt validation and one new
transition, forbidding full-tree, ancestry and exhaustive historical-effect calls.
Implementer: **1 passed, 19.08 seconds**; independent reviewer:
**PASS**, **1 passed, 19.59 seconds**, exit 0. Ruff lint/format passed. No
production or benchmark code changed. The complete suite was not rerun after this
test-only addition: the evidence is the prior **404-test full run plus the new
targeted regression**, not a claimed 405-test full run. Measurements were finished
before either new-test execution, avoiding benchmark/test-load overlap.
After final report/roadmap reconciliation, `tools.validate_examples` passed
**652 portable documentation links** plus its existing schema/reference/example
checks; `git diff --check` exited 0 (CRLF normalization warnings only).

## Measured performance and scope

The original runtime exhausted its 600-process measurement budget for all 21
baseline observations. These are censored observations, not successful latencies;
body-size distribution also differs, so no speedup ratio is claimed. See the
[methodology and complete results](../engineering/history-performance.md) and
[60-row raw artifact](../engineering/history-performance-optimized.json).

| Warm operation | Git processes, all sizes | Blob reads, all sizes | Historical commits traversed | 10,000-commit seconds |
|---|---:|---:|---:|---:|
| Node read | 12 | 8 | 0 | 0.533589 |
| Relation read | 19 | 15 | 0 | 0.871273 |
| Generation | 5 | 1 | 0 | 0.204055 |
| Exact replay | 23 | 27 | 0 | 1.183029 |
| Bounded create | 36 | 15 | One new transition | 1.980962 |

Warm Node/Relation reads validate 7/13 canonical parse calls and 5/11 domain
records respectively, with zero full-tree enumeration and zero receipt checks.
Replay validates one receipt pair and bounded original effects. Canonical parse
counts exclude direct schema-validator calls, including generation validation.
These are measured work counts for the supported create-only authorization profile,
not a general constant-cost guarantee for future mutation or policy features.

The 10,000-commit initial full build took 165.972045 seconds and produced an
11,669,504-byte database. Healthy-client full audit took 162.612840 seconds;
audit with SQLite absent took 164.303086 seconds and left SQLite absent.
Explicit healthy/missing-index rebuild took 160.735221/140.950907 seconds.
Recovery rows include real full rebuilds. Process-lifetime peak memory is a
bounded observation rather than independently attributed per-operation memory.
Startup authenticates and copies O(index bytes); writes may enumerate current
path/hash metadata. Full audit/rebuild intentionally scales with retained history.

Runtime fingerprint across review and both final runs:
`ebaf2adb29825700551b830bd9173be2d79462a0f4e074b36c1581f651a79f06`.
Baseline artifact SHA256 remains
`9a9ba34c921b7698dd323b515933c5dcf69953b6ed0c67a27daae01f9f433de3`.

## Changed boundaries and remaining risks

New production modules are `history_index.py`, `verification.py` and
`maintenance.py`. Git adapter/ports expose targeted blob access and delta
publication; application/operation/access code loads bounded dependencies and
checks current authorization. Repository/migration forensic views retain the
verified frontier and trusted-host recovery boundary. See the
[implemented module responsibilities](m2-1-1-history-hardening.md#implemented-boundaries).
SQLite uses the Python standard library: no dependencies were added.

No update/history handlers, canonical schema/generated edits, dependencies, commits,
pushes or global configuration changes were introduced. Deployment isolation,
Windows ACL guarantees, other platforms, physical durability and privileged
replacement of the complete trusted state remain unverified/outside the stated
local integrity claim. Legacy migration inspection remains an explicit forensic
path, not a bounded ordinary read. Signed checkpoints assume trusted OS protection;
replacing Git, SQLite and trust-anchor material together defeats this local
integrity boundary. Generation lookup is not an exhaustive availability audit;
audit remains required after restore or suspected object loss. Future mutation
requires its own transition-verifier and authorization conformance work.
**M2.2 readiness: YES for the next bounded development slice**, with those limits;
this is not production-deployment certification or authorization to enable updates.
