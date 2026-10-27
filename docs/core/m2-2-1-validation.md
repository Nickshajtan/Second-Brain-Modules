# M2.2.1 validation evidence

Status: complete for the scoped milestone. Production implementation, independent
corrected-diff review, unified quality checks and the complete benchmark matrix
passed. M2.3 may begin as a separately scoped implementation, subject to the
operational limits below; no Relation mutation is introduced here.

Baseline: `4b398cca2400cbf9bbf2e04c712e2e01fa80ab0f`. The checkout matched this
commit and was clean before work began. Historical M2.2 measurements remain
unchanged; new results must identify their source and workload boundaries.

## Delegation and design gate

Configured implementer `/root/m221_implementation` performed the initial code/trust
audit, disposable profiling, reviewed design and production implementation.
Production modifications began only after the independent design gate passed. Configured reviewer
`/root/m221_review` independently examines the actual design and, subsequently,
the completed diff. Native invocation messages establish both delegations;
optional numeric session IDs are not exposed. Neither agent may subdelegate.
Read-only reviewer instructions do not establish filesystem isolation.

The coordinator owns integration, deterministic final checks and this evidence
record. The repository allows three automatic correction/recheck cycles;
one was used for the independently confirmed cold-audit defect described below.

## Stage A observations (historical)

Code inspection identifies complete database serialization in candidate cloning
and publication, a complete disk-file hash in the coherence check, and full
path/immutable metadata enumeration in transition verification. These observations
do not establish which component dominates elapsed time.

The implementer's disposable baseline profiles completed at 100/1,000/10,000
committed generations. Successful submit elapsed times were 1.711/1.770/2.035
seconds, with 31 Git subprocesses each. The corresponding databases contained
282,624/1,613,824/14,450,688 bytes. At 10,000 generations the update serialized
28,901,376 bytes, hashed 43,352,064 database bytes and rewrote 14,450,688 bytes.
Git preparation took 0.565 seconds, compared with 0.190 seconds for complete
projection publication. This confirms byte amplification, not SQLite dominance
over total latency. Instrumented elapsed times are not direct speedup comparisons
against earlier uninstrumented measurements. Python CPU excludes child Git CPU.

The independent design review found the immutable authenticated base plus bounded
authenticated deltas approach viable, subject to precise pre-CAS capacity checks,
immutable compaction publication and exact cached anchor/key comparison. Production
implementation was withheld until the revised design gate completed. The revised
gate returned **PASS WITH WARNINGS** after inspecting all three baseline sizes
and the amended actual design; the coordinator then authorized implementation.
This is design approval only, not completed-diff correctness approval. Measured
tail thresholds, real corruption/crash/upgrade regressions and final independent
review remain required.

## Acceptance status

Production regression and independent review gates passed as recorded below.
The complete benchmark matrix passed; measured performance acceptance permits the
separate M2.3 development slice within the documented trust and maintenance model. Measurements, structural regression guarantees and deployment
assumptions are reported separately.

## Baseline component and byte evidence

The [tracked baseline artifact](../engineering/history-performance-m221-baseline.json)
retains the baseline/runtime/harness fingerprints, exact profiling-helper source
and hash, environment and raw observations. Each row is one instrumented successful
update; component timings are nested and must not be summed.

| Starting generations | Hot Node revisions | Submit seconds | Git preparation seconds | Full projection publication seconds | SQLite bytes rewritten | SQLite bytes serialized | Full database bytes hashed |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 6 | 1.711 | 0.512 | 0.095 | 282,624 | 565,248 | 847,872 |
| 1,000 | 51 | 1.770 | 0.501 | 0.104 | 1,613,824 | 3,227,648 | 4,841,472 |
| 10,000 | 501 | 2.035 | 0.565 | 0.190 | 14,450,688 | 28,901,376 | 43,352,064 |

Each submit used 31 Git subprocesses. The full-database hash total includes two
coherence checks and the new database hash at publication. Process-lifetime peak
memory includes fixture construction and rebuild; it is not an allocation claim
for one update. Full rebuild at 10,000 generations took 195.590 seconds in this
baseline profiling run. Different instrumentation from the earlier M2.2 artifact
precludes a direct latency-speedup claim.

## Selected design and required limits

Design C retains an authenticated immutable SQLite base and a bounded,
authenticated delta tail, with private-memory queries only. Complete-file
authentication on the base plus exact ordered replay protects present and absent
rows. The protected terminal checkpoint binds the whole accepted tail to instance,
repository, ref, contract fingerprint and accepted Git frontier. Git publishes
first; derived failure leaves canonical knowledge committed and requires verified
catch-up. Explicit trusted compaction bounds restart replay without adding a
hidden full-database rewrite to normal mutations.

The complete canonical generation path/hash digest and native Git tree/index
metadata work remain proportional to path metadata. Startup still authenticates
the entire base. Full audit, rebuild and compaction intentionally perform broad
work. Removing projection write amplification must not be reported as constant
total mutation cost, constant memory or a production throughput guarantee.

The local key/checkpoint rely on the existing trusted-process and OS boundary.
Replacing all protected Git and trust state defeats this local mechanism; no
remote or hardware trust anchor is introduced. Physical power-loss durability,
production backup consistency, deployed Windows ACL isolation and other operating
systems require separate verification.

## Implementation and review execution record

Configured implementer `/root/m221_benchmark` separately owns the existing
benchmark-harness extension and measurement artifact. No subagent delegated
further. Small disposable smoke runs exercised the new counters: explicit
compaction produced positive serialization/hash counts while bounded updates
produced none. These are development observations, not final benchmark acceptance.

The production implementer added 36 focused cases. Intermediate runs exposed
physical-layout fixture assumptions, a guessed DML budget below the measured
statement count, two test assertions using the wrong generated field name, and
one actual refresh-corruption error-classification defect. The latter returned
sanitized `INTERNAL` from submit instead of `REPAIR_REQUIRED`; the narrow refresh
boundary correction and real-Git regression passed before review freeze.

Integration also reproduced whole-base reload between alternating warmed Core
instances. Same-base refresh now authenticates and applies only new deltas; its
structural regression passed while forbidding full serialization, deserialization,
load, fork and history access. A noncanonical checkpoint representation could
otherwise produce an unreplayable exact-byte link; format-3 acceptance now rejects
noncanonical authenticated envelopes before publication.

The first full command was intentionally interrupted because a final source fix
crossed its import boundary. A fresh frozen-source full run was then interrupted
when independent review found a confirmed P2 audit defect: fresh format-3 audit
checked the legacy database filename before resolving the authenticated base.
Neither interrupted run is reported as a passing full gate. Their local logs are
retained under `.cache`; the final command must run after reviewed corrections.

Initial completed-diff independent review returned **BLOCK**, with exactly one
confirmed P2 at the fresh-audit filename gate and no other confirmed P0/P1/P2.
The reviewer independently ran 25 real-Git cases (201.18 seconds) covering missing
rows, tail ordering/removal, publication interruptions, bindings, capacity,
reentrant reads and alternating writers. Additional disposable Git probes confirmed
ref rollback rejection, current revoked replay denial and original receipt replay
without restoring an old Node head.

Correction/recheck cycle 1 of 3 completed. The minimal audit correction and five
fresh healthy/missing/corrupt base/tail cases passed in the implementer's run
(24.77 seconds), preserving Git and projection files. The reviewer independently
reproduced healthy cold audit returning `OK` and corrupted base returning
`INDEX_CORRUPT`, and ran the five new cases (30.66 seconds).
Verdict: **PASS WITH WARNINGS**, with no unresolved confirmed P0/P1/P2 findings.
One automatic correction/recheck cycle was used; the other two remain unused.

Reviewed runtime SHA-256:
`4f426bff8a2c14eba89e1329f222d8469ed4dfc0fae5e2cfc883f7958aee2df3`.
Benchmark-harness SHA-256:
`76a3282f70a0832a794e2fef83d9a63330c91324a0017ac8b684ffafb096ac87`.
The full unified command and final benchmark passed against that frozen source.
The readiness decision and remaining limits are recorded below.

## Unified quality command

Command: `.venv/Scripts/python.exe -m tools.check full`.
The reviewed-source run exited **0** and passed Ruff lint/format (41 files), Pyright (zero
errors/warnings), ESLint, strict TypeScript consumer compilation, Python syntax
compilation, documentation/examples (694 links), eight production schemas with
768 offline references and 153 fixtures/round-trips, and exact regeneration of
24 artifacts. Independent TypeScript validation produced the expected outcomes
for all 24 parity probes. The complete pytest suite passed **520 tests in
1704.41 seconds**. Fresh isolated distribution build and integrity verification
both passed, each reporting 37 payload files. Local command log:
`.cache/m221-full-check.log`; execution session `2933` completed with exit 0.

The generator emits its existing Black/isort future-deprecation warning. It has
not been treated as a failing check or suppressed by changing dependencies.

## Regression coverage and structural budgets

`tests/test_core_m221.py` adds 41 real-Git cases covering complete anchored tails,
fixed DML/bindings, removed Membership/receipt/idempotency rows, mutation and
compaction interruption points, SQLite transaction failures, capacity rejection
before CAS, reentrant reads, ignored untrusted WAL sidecars, key/checkpoint changes,
over-capacity catch-up, alternating writers, canonical envelopes, trusted-host
authority, batched Git hashing, corruption error classification and cold audit.
The old format-1 upgrade fixture now also exercises format 2.

For the bounded body-changing update fixture the structural gate requires exactly
two derived writes, fewer than 20,000 payload bytes, at most 26 captured DML
statements and 19 SQLite-reported changed rows. It forbids serialization, complete
database hashing, fork, load, rebuild and whole-tree/ancestry access; the immutable
base bytes must remain unchanged. The alternating-writer gate also forbids
deserialization and retains both original private connections across four updates.
These are fixture-specific work budgets, not universal limits on batches or
type changes affecting additional Relations. Existing M2.2 blob/history budgets
and authorization, CAS, receipt and recovery regressions remain in the full suite.

Physical-format fixture adaptations compact first before editing authenticated
base rows. Warm delivery/replay uses the original complete private state, while
restart rejects altered bytes and Git remains unchanged. The old pre-write
whole-file corruption-detection timing is deliberately superseded, not silently
claimed as preserved. Crash fixtures now target delta/checkpoint publication,
and explicit upgrade fixtures preserve old signed bindings and keys.

The 250-file Git batching regression checks exact Unicode/CRLF bytes and bounded
Windows argument chunks. No hostile same-process isolation, deployed ACL or
physical crash-durability proof follows from these tests.

## Final measured mutation and maintenance evidence

The [measurement artifact](../engineering/history-performance-m221.json) retains
raw counters and source fingerprints for the 100/1,000/10,000-generation corpora.
The hot-update samples are 100/100/1,000 respectively. At 10,000 starting
commits, the 1,000 measured submit calls produced p50 1.802206 seconds, p95
2.055274 seconds and empirical p99 2.449563 seconds.
Their aggregate submit-time rate was 0.54756 updates/second. This excludes request
construction, generation lookups, postcondition reads and maintenance; it is not
end-to-end agent throughput or a deployment SLA. Smaller sample sets deliberately
withhold p99.

The independent reviewer checked all 1,230 hot/distributed updates: each changed
18 projection rows, used 26 Git subprocesses, verified one incremental transition
and one receipt, and wrote 7,315?7,326 derived payload bytes. All completed with
zero full SQLite serialization, backup, deserialization, database hash or snapshot
rewrite, no whole-tree reads and no duplicate requested blobs. The baseline
10,000-generation update rewrote 14,450,688 database bytes and hashed 43,352,064
bytes. The selected design removes that byte work; differing corpus growth and
instrumentation prevent a general latency-speedup claim.

At the 1,024-delta capacity limit the exercised authenticated tail contained
5,935,739 bytes. The next update returned `REPAIR_REQUIRED` without Git publication
or derived writes. Cold restart took 7.458760 seconds. Explicit compaction took
0.366680 seconds and wrote 19,588,603 payload bytes, including a 19,587,072-byte
new base; it performed the expected one serialization and complete database hash.
Restart after compaction took 0.668047 seconds. The 16 MiB hard limit is covered
by arithmetic/pre-publication regressions, not a saturated-16-MiB restart benchmark.

Warm accepted-frontier refresh took 0.400094 seconds without complete base loading
or derived writes. Recovery when Git had published but the derived delta had not
been accepted took 1.181839 seconds and wrote 7,327 derived bytes, with one bounded
transition and no full database serialization/hash.

Byte counters measure Python write payloads, not physical storage sectors or flush
durability. Python CPU excludes child Git CPU. Peak memory is process-lifetime
working set including corpus setup/rebuild. Cold-restart changed-row counters
observe the replaced original connection and are not meaningful replay-row counts;
use the global SQL/hash/deserialization counters for that operation. Native Git
index/tree metadata and the canonical sorted-path generation digest retain O(N)
work. Startup, audit, compaction and rebuild intentionally retain broad work.

The evidence-only reviewer addendum returned **PASS WITH WARNINGS**, independently
matching runtime/harness/baseline fingerprints and the raw full-tail counters.
No new confirmed defect was found. Final benchmark completion is recorded below.

## Benchmark completion and M2.3 readiness

Command: `.venv/Scripts/python.exe -m tools.benchmark_history --mutation-hardening --sizes 100 1000 10000 --git-budget 100000 --output docs/engineering/history-performance-m221.json`.
The benchmark implementer executed this in session `93856`; it exited **0**.
All **1,293 observations** report `complete`; runtime, harness and contracts
unchanged-during-measurement flags are true. The final 10,000-starting-generation
corpus rebuild verified 11,026 retained commits, 2,027 receipts and 22,153 blobs
in 559.217735 seconds (526.593750 seconds Python CPU). Its new base contained
19,591,168 bytes. Process-lifetime peak working set reached 229,548,032 bytes,
including corpus creation and broad rebuild work; this is not per-update allocation.
The retained derived directory reached 59,827,825 bytes because old authenticated
bases/deltas are deliberately retained, requiring operator disk monitoring.

**M2.3 readiness: yes, for separately scoped Relation-mutation development.**
The bounded-write goal, current authorization, immutable receipts/revisions,
canonical Git CAS authority and explicit recovery gates passed their specified
regressions, reviewed implementation and measured workloads. No public operation
contract, canonical schema, generated artifact or dependency was changed. The
only new exported interface is trusted-host compaction; no Relation update,
transport, search, governance or background maintenance was implemented.

This does not certify production throughput, physical power-loss durability,
backup coherence or deployed filesystem/process isolation. Protected local key,
checkpoint and OS trust remain prerequisites. An actor replacing Git and all trust
material is outside that integrity claim. Warm private state safely retains its
previous authenticated bytes if disk base/tail data is later corrupted; corruption
is detected on restart/audit/relevant refresh, not necessarily the next warm write.
Compaction is explicit at the 1,024-transition/16-MiB ceiling; over-capacity external
catch-up needs trusted rebuild. Old derived files are not automatically deleted.
Canonical path-digest and native Git metadata costs remain O(N); ordinary mutation
projection persistence is bounded. These limits are carried into the M2.3 slice.

## Final closure checks

The independent reviewer's final evidence closure returned **PASS WITH WARNINGS**:
all 1,293 rows, final rebuild and unchanged-source flags were inspected; no
unresolved confirmed blocking finding remains. The implementer and reviewer were
actually invoked under `/root/m221_implementation`, `/root/m221_benchmark` and
`/root/m221_review` with the scopes above. No delegation step was bypassed and
one of three correction/recheck cycles was used. Optional numeric agent IDs were
not exposed; native task invocations, completion messages, command sessions and
tracked measurement artifacts are the available evidence.

After factual documentation updates, the coordinator reran
`.venv/Scripts/python.exe -m tools.validate_examples`: **PASS**, including 698
portable document links. `git diff --check` passed. A final SHA-256 assertion
checked all frozen runtime/test files and benchmark harness, baseline-artifact
binding, all 1,293 completed observations and all three unchanged-source flags.
Canonical/generated/dependency/config boundaries remained unchanged. Historical
M2.1.1/M2.2 benchmark artifacts were retained. The full 520-test command was not
repeated for these report-only changes; its reviewed production source is identical.
