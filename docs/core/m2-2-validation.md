# M2.2 validation evidence

Status: implementation, independent review, full quality gate and all 42 benchmark
observations complete. Final documentation checks are recorded below. M2.3 is ready
for its separate scoped development; no Relation mutation is introduced here.
Baseline: `625cdf5baf6385541effc6f385aded6b39c620a2`; the checkout was clean
and matched the supplied baseline before work began.

## Delegation and design gate

Configured implementer `/root/m22_implementation` performed the preliminary
contract/runtime audit and owns production changes, regression tests and the
[design](m2-2-node-mutation.md). Configured reviewer `/root/m22_review` independently
inspects the design and completed diff without editing files. Native invocation
and completion messages provide evidence; optional numeric session identifiers
are recorded where exposed. Behavioral read-only instructions do not establish
filesystem isolation. Neither agent may subdelegate.

Stage A found existing full-content NodeUpdate, CAS expectations, NodeRevision
previous/snapshot and typed historical-read/ReadResult structures sufficient;
no canonical schema amendment is currently justified. The catalogue's accepted
replacement-to-new-revision effect supports a fresh identical replacement creating
a revision, while exact retry has no new effects. The independent reviewer
accepted this interpretation from existing catalogue evidence.

The design review identified the existing exact index-format checkpoint binding
as an upgrade hazard. Trusted explicit rebuild must authenticate recognized old
binding and retain the old accepted commit/key before fully verifying and building
the new projection. Normal reads must not perform a silent migration.
The revised design gate returned PASS WITH WARNINGS, no unresolved blocking
findings, before production implementation was authorized. Required implementation
evidence includes interrupted format-upgrade recovery, mixed-batch endpoint
validity, bounded chain validation and changed-head/Membership effect explanation.

A subsequent design addendum identified a concrete historical-interpretation gap:
the baseline allowed overwrite of already-registered definition records and
metadata-schema IDs. A replacement that still accepts old content can change its
meaning silently. The independent reviewer confirmed M12-REV-06/I08 applicability
and returned PASS WITH WARNINGS for append-only meanings in the M2.2 subset.
Whole-record immutability, including descriptive fields, is an implementation
restriction, not a new universal domain rule. New versions/schema IDs remain
possible; incremental verification and full rebuild must reject prior overwrites
and preserve the existing rollback anchor on rejection. The append-only subset is
implemented; targeted overwrite/new-version and retention/shadow-version tests
passed. Completed-diff review and the unified gate remain pending.

Configured implementer `/root/m22_benchmark` separately owns the narrow benchmark
harness, performance documentation and M2.2 measurement artifacts. It must retain
M2.1.1 artifacts and wait for the reviewed runtime freeze before final measurement.

## Execution results

This chronological record preserves intermediate failures and pending statements
as historical evidence; the final verdict and measurements below supersede them.

The first real-Git integration case passed (17.90 seconds): create, revisions
2/3, exact old snapshots, original creation/update replay without head rollback,
full audit and explicit legacy inspection. The first expanded focused run passed
14 cases (141.06 seconds), covering CAS, distinct capabilities, fresh identical
replacement, duplicate/mixed batches, explicit old-format rebuild and bounded
history access. These are intermediate results, not the complete acceptance gate.

A later expanded development run stopped after 14 passing cases and one failing
interruption-test assertion (171.46 seconds): the test expected an exception from
trusted rebuild, whose established contract returns structured diagnostics. The
assertion was corrected to retain that contract. Targeted rerun of the three
upgrade boundaries, legacy supplement and unique-blob checks passed five cases
(53.39 seconds). Broad integration and subsequently added cases remain pending.

The original clean 41-case new-feature run subsequently passed (467.82 seconds).
Additional targeted runs passed 13 security/candidate cases (101.37 seconds), six
old-history/protected-state cases (90.55 seconds), three versioned-meaning cases
(40.09 seconds) and three retention/shadow-version cases (44.00 seconds). These
runs overlap; their counts are not summed as unique coverage.

The existing integration run stopped at 69 passed / one failed (608.93 seconds):
`test_inventory_distinguishes_ambiguous_generation` observed generic corrupt-effects
classification instead of `ambiguous_history`. Added projection checking had run
before the original forensic classification and could also publish derived state
during dry-run inspection. The fix retains original forensic planning first, then
fully verifies canonical history in private memory without depending on or
publishing SQLite. Targeted regression and the final complete gate must confirm
it; assertions are retained. This explicit forensic path may scale with history;
it is not used by routine Node reads, updates or replay.

The remaining existing M2.1/M2.1.1/error-boundary follow-up completed with
**107 passed, 713.52 seconds, exit 0**. Its process imported the pre-correction
source; it is historical regression evidence, not verification of the later
transition-verifier correction or a substitute for the final unified run.

Before final review, fault injection found that unexpected ingress-validator
exceptions escaped from read/submit because setup occurred before their existing
try boundaries: two failing regressions (5.08 seconds). Moving that setup inside
the protected boundaries retained known CoreError codes; the same two cases
passed (5.09 seconds). Execute-ingress consistency is also included in the final
boundary review. This fixes error containment without bypassing canonical ingress.

Development benchmark smoke at 20 generations completed 14/14 observations.
Profiling found six duplicate blob requests during update; request-scoped reuse
reduced the development counts from 37 Git processes/19 blob requests to 31/13,
with zero duplicate requests. Tests ran concurrently with developmental probes;
their timings are not final performance evidence or a speedup claim. Final
measurements must use a reviewed frozen runtime without expensive tests running.

Expanded regressions, complete quality/contract/distribution checks, final
performance measurements and completed-diff review remain pending. Results will
be recorded from actual executions, including failures and corrections.

Initial completed-diff review verdict: **BLOCK**, two confirmed P2 findings in
`TransitionVerifier._receipt` (reviewed lines 441 and 374 respectively):

1. Only target CAS was checked. Correct target CAS plus another existing Node's
   expected_revision=999 passed candidate verification and full audit.
2. A foreign operation.instance_id inside a local batch passed candidate
   verification and full audit.

The independent reviewer reproduced both in disposable real Git repositories by
bypassing only the respective application checks to synthesize the invalid
publication; the verifier was unchanged. Checks were restored before audit,
which returned verified. Ordinary API submission rejected these requests, but
external catch-up must enforce the same declared preconditions. The reviewer
also independently passed eight selected regressions (99.34 seconds); those
passes did not cover these defects. No other blocking finding was confirmed.
Correction/recheck cycle 1 of the three permitted automatic cycles checks every
operation's instance and all declared CAS against bounded, ordered original
pre-state, retaining valid earlier-operation dependencies. A small result-resource
overlay advances only after each operation; parent records/body OIDs reuse the
request's unique-blob cache. No current host grants are used as historical proof.
The 13-case external/ordered-CAS/blob-budget subset passed (110.81 seconds): Node,
Cluster and Relation revision/digest negatives, foreign operation/expectation
instance, stale overlay, both valid update orders, earlier-created Node CAS and
unique blob reads. Current new suite collection is 73 cases. The implementer's
related 16-case selection also passed (195.47 seconds), including historical
audit/rebuild with current grants revoked. Ruff format/lint, Pyright (zero errors
and warnings) and whitespace checks passed before the runtime was frozen.

Independent recheck 1 verdict: **PASS WITH WARNINGS**, no unresolved confirmed
P0/P1/P2 findings. Both original bypass probes now return REPAIR_REQUIRED before
canonical publication, leaving heads unchanged. Independently **14 passed,
59 deselected, 157.62 seconds**, covering external invalid publications,
audit/rebuild rejection, ordered CAS, create-dependent expectations and blob reuse.
No reviewer edits or delegation occurred. That completed production correction
cycle 1; the later test-only cycle 2 is recorded below. Final benchmarks have not
started. Passing these tests is not a scalability proof.

The first unified `.venv/Scripts/python.exe -m tools.check full` completed with
**477 passed / one failed, 1520.77 seconds**, exit 1. Lint, typing, documentation,
all eight schema families/768 offline refs/153 fixtures, 24-artifact regeneration
drift and independent validators passed first. Distribution build was not reached.
The sole failure was the original M1.2 test asserting Node revision reads remain
unsupported. M2.2 correctly returned NOT_FOUND for its fixture without historical
permission; Relation revision reads remain unsupported. Test-only correction and
independent review cycle 2 is underway, preserving the reviewed production bytes.
No passing full-suite result is claimed from that failed command.
The implementer's test-only update passed both parameter cases (9.99 seconds):
Node history denies the original unprivileged fixture, then returns the exact
canonical revision under an explicit history grant; Relation history still rejects
as unsupported. Canonical parsing and unchanged-Git assertions are retained.
Ruff and whitespace checks passed. Independent cycle 2 verdict: **PASS**,
**2 passed, 12 deselected, 9.90 seconds**, no files edited and no findings.
Seven runtime hashes matched saved reviewer evidence; the remaining operation
guard was independently inspected. The reviewer did not retain a complete earlier
cycle-1 fingerprint and therefore limits its temporal byte-identity claim.
Two of three automatic cycles were used. The final unified command and benchmark
subsequently completed against the recorded current fingerprint below.

Recorded production fingerprint before final rerun/measurement:
`dff467475653c70752bff9db95bf52dd9693141fb8fbf277d02791a1e6715014`
(SHA256 of sorted Core module names and bytes, matching the benchmark method).

The final `.venv/Scripts/python.exe -m tools.check full` returned **exit 0**:
**478 passed in 1508.43 seconds**. This includes all 73 new M2.2 cases and existing
regressions. Ruff (39 formatted files), Pyright (zero errors/warnings), ESLint,
TypeScript consumers, compilation, documentation (677 links), eight schema
families/768 offline refs/153 fixtures, 24 exact generated artifacts and independent
Python/Ajv checks passed. Fresh isolated distribution build and verification both
passed with **37 payload files**. Dependency deprecation warnings did not fail
the command. The earlier failed full run remains historical evidence above.

Final 42-row performance execution started only after that command completed,
without concurrent expensive tests. Each corpus includes one explicit initial
rebuild and 13 warm/new/retained/recovery observations. All 42 completed successfully;
runtime, contracts and harness remained unchanged throughout measurement.

Git remains canonical; SQLite remains authenticated derived state. No Relation
mutation, governance, multi-cluster policy, MCP, authoring integration or O1-O4
decision is authorized. Operational trust and physical durability limits from
[ADR-012](../architecture/decisions/ADR-012-derived-history-index.md) remain in force.

## Scope and operational limits

The supported domain subset is private, active, single-membership editable Nodes.
Protected/governed selection, multiple memberships, Relation mutation/history and
history range/list APIs remain unsupported. Exact Node history uses existing
NodeRevision/ReadResult contracts; no custom DTO or transport is introduced.

Git publication remains canonical. Prepared objects are not committed effects;
SQLite may lag after publication and must catch up or be explicitly rebuilt.
Signed local checkpoints depend on trusted OS protection of Git and trust-anchor
material, not independent remote/hardware attestation. Privileged replacement of
all trusted state is outside that integrity model. Windows ACL isolation, hosted
OS matrices, physical power-loss durability and production backup behavior are
not established by disposable-repository tests.

Warm canonical dependency and receipt work must stay bounded. Existing projection
copy/authentication and commit path/hash metadata work can still scale with index
size; neither the design nor benchmarks establish constant total update memory or
time. Type changes may depend on actual incident Relations. Full audit, rebuild
and explicit migration inspection intentionally scale with retained history.

Benchmark comparisons retain one important measurement-boundary difference:
M2.1.1's create row includes generation lookup plus submit; M2.2's prepared-request
create row measures submit only. Raw create counters are not directly comparable.
The other four retained warm API boundaries match, but the corpus/revision mix
differs, so no latency-speedup ratio is claimed for any retained workload.
This documentation-only correction changed no runtime or harness behavior.

## Final measurements and readiness

Executed command (exit 0):

```text
.venv/Scripts/python.exe -m tools.benchmark_history --node-mutation --sizes 100 1000 10000 --git-budget 100000 --output docs/engineering/history-performance-m22.json
```

All 42 observations completed: 14 per corpus, with 6/51/501 hot-Node revisions
at the respective starting generations. This is not a 10,000-update workload.
Python 3.12.6, Git 2.46.2.windows.1, Windows 10 build 19045; single observations,
no OS-cache flush and no concurrent expensive test workload.

| Operation | 100 generations | 1,000 generations | 10,000 generations | Git processes / blobs / SQLite statements |
|---|---:|---:|---:|---|
| Hot-Node update | 1.516 s | 1.612 s | 1.899 s | 31 / 13 / 107 |
| Exact revision-1 read | 0.686 s | 0.666 s | 0.631 s | 13 / 9 / 26 |
| Exact update replay | 0.786 s | 0.707 s | 0.723 s | 14 / 9 / 25 |
| Explicit full rebuild | 2.590 s | 15.308 s | 222.577 s | 14 processes; full retained history |

Those three warm paths had zero full-tree reads, zero duplicate blob requests
and no full-history enumeration. Each update checked one new transition and one
receipt; history reads checked no receipts; replay checked one original receipt.
The update's single enumerated commit is its new transition, not an ancestry scan.
Index size at 10,000-start rebuild was 14,495,744 bytes; after measured operations
it was 14,512,128 bytes. Full rebuild checked 10,000 commits, 1,003 receipts and
17,039 blobs. Process-lifetime peak working set reached approximately 203 MB;
this includes setup/rebuild and is not per-operation allocation attribution.

CI structural regressions enforce update <=20 unique blobs, historical read <=12,
one update transition, no full-history/full-tree fallback or warm index reload,
and no repeated canonical blob loading. The table's exact Git/SQL counts are
observed profiles, not universal fixed budgets for arbitrary dependency fanout.
The [performance report](../engineering/history-performance.md) and
[raw observations](../engineering/history-performance-m22.json) retain all rows,
source fingerprints and comparison limitations.

Independent reviewer verdict: PASS WITH WARNINGS after both confirmed P2 findings
were corrected; test-only second recheck PASS. No unresolved blocking findings.
Implementer, benchmark implementer and reviewer were actually invoked through the
native configured roles listed above; no independent deployment audit is claimed.
Documentation-only final reporting uses the AGENTS exception and changes no runtime.

M2.3 readiness: YES for a separate implementation/design slice. Node replacement,
exact history, immutable receipts, CAS/race and recovery behavior are implemented
and regression-tested in the supported subset. Domain decisions and existing
structural/API contracts remain authoritative; broader operations are deferred.
Deployment isolation, physical durability, privileged-host tamper resistance and
production throughput remain unverified. Passing tests and these measured corpora
do not prove correctness or scalability beyond the exercised cases.


Final factual-documentation checks after measurement (all exit 0):

- `.venv/Scripts/python.exe -m tools.validate_examples`: 680 portable links,
  two illustrative schemas, 20 schema refs, four fixtures, 11 rejection probes,
  three additional valid probes and two OpenAPI refs.
- `git diff --check`: no whitespace defects (line-ending notices only).
- `git diff --exit-code -- contracts packages/python/generated packages/typescript/generated docs/engineering/history-performance-baseline.json docs/engineering/history-performance-optimized.json`:
  canonical/generated and earlier measurement artifacts unchanged.
- Independent JSON assertions: exactly 42 complete rows (14 per size), all three
  unchanged-source flags true and runtime fingerprint equal to the reviewed one;
  healthy single-request rows have no full-tree or repeated blob loads.

An initial report assertion incorrectly applied the single-request duplicate-blob
condition to the composite crash/restart recovery row. Inspection showed 21 repeated
blob requests across its deliberately separate failed publication and fresh-Core
retry at each size. The corrected assertion scopes that condition to healthy
single-request rows; recovery semantics and production code were unchanged.
No full test repetition was needed for final factual documentation/artifact updates.
