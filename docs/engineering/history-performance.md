# History performance measurements

Status: all 60 optimized cold/warm/recovery rows executed successfully on the
reviewed M2.1.1 runtime. The censored Phase A baseline is retained unchanged. See the [design](../core/m2-1-1-history-hardening.md).

Observed local tools: Python 3.12.6, Git 2.46.2.windows.1 and Node 24.19.0 on
Windows. Hosted CI and other operating systems are not represented by these timings.

Historical Phase A invocation, before the runtime changes below (running this
command on the current checkout does not recreate the original M2.1 runtime):

```powershell
.venv/Scripts/python.exe -m tools.benchmark_history --sizes 100 1000 10000 --git-budget 600 --output .cache/m211-baseline.json
```

The corpus has three public create transactions before fixture bulk construction,
then one two-Node/Relation create transaction per twenty commits and unique unrelated
generations between them. Bulk construction calls existing create strategies,
canonical packing and receipt generation, then Git fast-import; it does not add
production mutation handlers. Bodies range from short notes to 12 KiB. Corpus sizes
100/1,000/10,000 contain respectively 8/53/503 creation receipts, 16/106/1,006 Nodes
and 8/53/503 Relations. IDs are disposable; workloads and counters are reproducible
in shape rather than byte-identical signed histories.

Counter definitions: Git processes count `_run_bytes` calls; blob reads count
`cat-file blob`; trees count `store.read` entries (including an interrupted tree);
commits count returned ancestry entries; record validations count canonical
`ContractValidator.parse` invocations; receipt validations count pair checks.
Partial parse work and calls through other validator entry points are not silently
counted as this narrower parse-call metric. Counter limits interrupt before the
next Git subprocess. Timings of interrupted operations are censored lower bounds,
not successful latency measurements. Setup is outside operation counters.

Initial observed 100-commit Node read reached its 600-process budget after
28.267975 seconds: 590 blobs, six tree-read entries, 100 traversed commits,
86 canonical parse calls and eight receipt pair validations. Relation read reached
the same counters after 30.456569 seconds. Neither operation completed.

All 21 actual operation rows are retained in the
[baseline artifact](history-performance-baseline.json). Every row exhausted the
explicit 600-process budget. At 100 commits, ordinary operations read 590 blobs,
entered six trees and traversed 100 commits; canonical parse calls were 85/86
depending on input parsing, with eight receipt pair validations. Migration
inspection reached the same Git counts before canonical corpus parsing (one input
parse and zero receipt checks). At 1,000 and 10,000 commits, every operation used
597 blob reads in the first current-tree load and stopped before ancestry traversal.
No row is reported as successful or as a complete-operation latency.

| Operation | 100 commits seconds, censored | 1,000 commits seconds, censored | 10,000 commits seconds, censored |
|---|---:|---:|---:|
| Node read | 28.267975 | 30.878477 | 30.432895 |
| Relation read | 30.456569 | 29.901528 | 29.579578 |
| Generation | 28.540175 | 29.585082 | 28.980928 |
| Exact replay | 27.429392 | 28.888549 | 27.429307 |
| Bounded create | 29.504787 | 26.678650 | 27.844004 |
| Full historical verification | 29.424347 | 26.410684 | 28.216751 |
| Legacy migration inspection | 30.871589 | 26.607963 | 27.836234 |

The first process completed 100/1,000 rows, then was interrupted during an
unmeasured 10,000-corpus setup read. Those 14 rows were preserved. The updated
harness reused its known fixture generation instead of loading all current blobs
just for setup; a second invocation with `--sizes 10000` produced the remaining
seven rows. This does not alter the measured runtime access path. Earlier fixture
construction drafts were interrupted or failed before measurements and establish
no performance result. Peak per-operation memory was not captured in this baseline;
the final optimized matrix must capture it. No before/after ratio is inferred from
these censored observations.

## Structural gates and their scope

| Healthy warm operation | Full ancestry traversals | Full tree reads | Canonical delivered/dependency records |
|---|---:|---:|---:|
| Node read | 0 | 0 | At most 12 for current supported private/single-membership profile |
| Relation read | 0 | 0 | At most 24 including both endpoints and their memberships |
| Generation | 0 | 0 | One generation descriptor |
| Exact replay | 0 | 0 | Bounded by batch operations and deduplicated dependency closure, never total receipts |
| Bounded create | 0 previous-history scans | Commit construction may enumerate current paths | Validate new effects and relevant dependencies, not all historical effects |

These bounds follow the finite current dependency closure. The measured rows below
meet them; the real-adapter regression `test_warm_deliveries_are_targeted_and_restart_is_authenticated`
separately guards Node/Relation/replay against full-tree/history work. Its fixture
is intentionally CI-sized; the measurements below use all three required corpora.
Canonical parsing and authorization are required even when a locator is indexed.
Cold rebuild and exhaustive audit may traverse all commits and records and must
report that work. Restart hashing is O(index bytes) and is reported separately from
same-process warm lookup. SQLite statement count, memory and database bytes are
included in the optimized benchmark matrix; the initial M2.1 runtime has no
SQLite database.

## Optimized measurement procedure

```powershell
.venv/Scripts/python.exe -m tools.benchmark_history --optimized --sizes 100 1000 10000 --git-budget 100000 --output docs/engineering/history-performance-optimized.json
```

The baseline artifact remains unchanged. The optimized corpus retains the same
receipt/resource counts and transaction cadence. Fixture-generated Node bodies now
cycle through 208 B, 3,328 B and 13,312 B throughout history; the baseline
had this variation only in the first transaction. This makes direct wall-clock
ratios inappropriate even without the baseline censoring.

Each corpus runs twenty actual rows: initial full rebuild; five operations in
healthy new-Core, warm and missing-index recovery modes; then full audit and
explicit rebuild in new-Core and missing-index modes. Recovery read/replay/create
rows include the full explicit rebuild after deleting only SQLite. The checkpoint,
key and enrollment anchor remain intact. A missing-index audit verifies canonical
history and reports index absence without repairing it; an explicitly invoked,
unmeasured rebuild restores the projection before subsequent maintenance rows.
The read/replay/create recovery client is constructed before its measurement;
its full rebuild and requested operation are measured inside the row. Maintenance
recovery rows include construction of their new client. Bounded-create rows also
include obtaining the current expected generation and constructing the request.

Cold means a newly constructed Core and GitStore with an existing healthy index,
including authenticated SQLite deserialization; the canonical ContractValidator is
shared across benchmark clients. It does not mean cold OS page
cache or a new Python process. Cross-process restart correctness is covered by the
runtime regression suite, separately from these timings. Initial full verification
is an explicitly measured rebuild, never hidden setup. Corpus construction itself
is excluded. Three bounded creates add three commits before audit/rebuild rows;
`commits_at_corpus_start` labels the starting corpus size.

Optimized counters instrument class-level Git adapters so newly constructed Core
instances are included. Blob reads count requested blob OIDs, including batched
prefetch and repeated loads; one batch process may read many blobs. `trees_read`
counts full `GitStore.read` calls; `tree_enumerations` counts `entries` calls.
`commits_enumerated` counts entries returned by `changes` and `ancestry`, while
`commits_traversed` counts actual transition-verifier calls. Canonical parse and
receipt-pair metrics retain their narrow baseline definitions. The additional
`domain_records_checked` metric sums record-set sizes passed to DomainRules.validate;
it does not count every internal dictionary iteration as a separate record. SQLite statements
count trace callbacks on existing and newly created connections, including reads,
writes and transaction statements, rather than only SELECTs.

Memory is the Windows process-lifetime peak working set in bytes, including native
SQLite/Python memory. It is a conservative upper bound shared with setup and prior
rows, not an isolated operation allocation peak. Database size is the actual
serialized SQLite file after the operation. Audit with a missing index legitimately
reports zero bytes. Rebuild rows report actual wall-clock rebuild duration.
The artifact records environment and a digest of all handwritten Core Python
modules before and after execution; a changed digest invalidates frozen-runtime
comparisons. A passing functional suite does not establish scalability.

## Executed optimized results

Measured on 2026-10-27: Python 3.12.6, git version 2.46.2.windows.1, SQLite 3.45.3,
Windows-10-10.0.19045-SP0. No expensive test suite ran alongside these final measurements.
The two exact executed commands are retained in the [raw optimized artifact](history-performance-optimized.json);
100/1,000 ran in one process and 10,000 in another. Both exited zero, with all
60 rows complete and unchanged matching runtime, contract and harness fingerprints.

Reviewed and measured Core source SHA256:
`ebaf2adb29825700551b830bd9173be2d79462a0f4e074b36c1581f651a79f06`.
Canonical contract fingerprint: `7001c9e780a2276bd9b9d57b148590bf4fc8faa3278889008756d5b8b5e8738d`.

Each value below is one instrumented observation in seconds, rounded to three
decimals. These are neither latency guarantees nor percentile/throughput estimates.
Cold uses a healthy index and a new Core; recovery includes full index rebuild.

| Commits at start | Operation | Cold/new Core | Warm | Missing-index recovery |
|---:|---|---:|---:|---:|
| 100 | `node_read` | 0.804 | 0.558 | 2.776 |
| 100 | `relation_read` | 1.286 | 0.888 | 3.040 |
| 100 | `generation` | 0.426 | 0.205 | 2.497 |
| 100 | `exact_replay` | 1.445 | 1.198 | 3.291 |
| 100 | `bounded_create` | 1.996 | 1.771 | 4.016 |
| 1,000 | `node_read` | 0.772 | 0.571 | 12.615 |
| 1,000 | `relation_read` | 1.119 | 0.889 | 13.640 |
| 1,000 | `generation` | 0.448 | 0.215 | 12.349 |
| 1,000 | `exact_replay` | 1.390 | 1.169 | 12.932 |
| 1,000 | `bounded_create` | 1.999 | 1.826 | 13.490 |
| 10,000 | `node_read` | 0.830 | 0.534 | 162.965 |
| 10,000 | `relation_read` | 1.147 | 0.871 | 160.068 |
| 10,000 | `generation` | 0.490 | 0.204 | 163.413 |
| 10,000 | `exact_replay` | 1.480 | 1.183 | 164.700 |
| 10,000 | `bounded_create` | 2.289 | 1.981 | 167.842 |

| Commits at start | Initial full rebuild | Full audit, healthy index | Full audit, missing index | Rebuild, healthy index | Rebuild, missing index |
|---:|---:|---:|---:|---:|---:|
| 100 | 2.257 | 2.247 | 2.196 | 2.421 | 2.394 |
| 1,000 | 11.602 | 12.136 | 11.861 | 12.334 | 12.219 |
| 10,000 | 165.972 | 162.613 | 164.303 | 160.735 | 140.951 |

Audit/rebuild maintenance rows run after three new creates and therefore verify
103/1,003/10,003 commits and 11/56/506 receipts. Initial rebuild verifies exactly
100/1,000/10,000 commits and 8/53/503 receipts. Missing-index audit is verify-only
and leaves the database absent. Unmeasured setup/restoration work means total
harness duration is longer than the sum of recorded row durations.

The following warm counts were identical at all three corpus sizes:

| Operation | Git processes | Blob reads | Canonical parse calls | Domain records checked | Receipt pairs | SQLite statements | Verified transitions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `node_read` | 12 | 8 | 7 | 5 | 0 | 19 | 0 |
| `relation_read` | 19 | 15 | 13 | 11 | 0 | 41 | 0 |
| `generation` | 5 | 1 | 0 | 0 | 0 | 2 | 0 |
| `exact_replay` | 23 | 27 | 23 | 0 | 1 | 54 | 0 |
| `bounded_create` | 36 | 15 | 22 | 10 | 1 | 97 | 1 |

Warm Node/Relation/generation/replay enumerated zero historical commits and
read/enumerated zero full trees. Bounded create verified only its one new commit
and receipt, with zero full-tree reads. Its commit construction and SQLite
projection copying may still depend on current projection size. No claim of
constant write memory or constant total write complexity follows from these counts.
Generation uses direct canonical GenerationRef validation, outside the narrower
ContractValidator.parse counter. Replay here is the original three-operation batch.

| Commits at start | Initial DB bytes | DB bytes after three creates | Maximum process-lifetime peak working set bytes | Initial rebuild blobs | Initial rebuild parse calls |
|---:|---:|---:|---:|---:|---:|
| 100 | 278,528 | 311,296 | 71,680,000 | 191 | 343 |
| 1,000 | 1,339,392 | 1,355,776 | 84,520,960 | 1,541 | 2,233 |
| 10,000 | 11,669,504 | 11,681,792 | 175,116,288 | 15,041 | 21,133 |

The baseline cannot supply completed before/after latency ratios: every original
operation was censored at 600 Git processes. For example, its 100-commit Node read
had already read 590 blobs before interruption; the completed optimized warm read
used eight blobs and twelve Git processes at every measured corpus size. The
optimized body mix also differs as documented above. Full rebuild/audit still
performs substantial history work; it remains explicit maintenance, not an ordinary
read fallback.

These observations close the requested benchmark-execution criterion, not a
general scalability proof. Targets and authorization dependency shape are fixed
by the currently supported private, active, single-membership profile. OS caches
were not flushed; cold is not a new Python process. Memory includes setup/prior
operations and native SQLite, not an isolated allocation peak. No Linux/macOS,
power-loss, concurrent-throughput or large-instance deployment guarantee is made.
The coordinator records overall M2.2 readiness and the separate correctness,
security and independent-review evidence in the [validation report](../core/m2-1-1-validation.md).

## M2.2 mutation benchmark procedure

The opt-in mutation mode preserves both earlier CLI modes and the original M2.1.1
JSON evidence. The final reviewed-runtime matrix completed all 42 rows; the
[raw M2.2 artifact](history-performance-m22.json) contains counters, exact corpus
metadata and source fingerprints. Developmental probes are excluded from these
results.

```powershell
.venv/Scripts/python.exe -m tools.benchmark_history --node-mutation --sizes 100 1000 10000 --git-budget 100000 --output docs/engineering/history-performance-m22.json
```

Each disposable corpus starts with three public creation batches and the trusted
bootstrap generation. Bulk construction then calls the supported fixed mutation
strategies, canonical packing and receipt generation, publishing the resulting
linear fixture via Git fast-import. Every twentieth bulk commit creates two Nodes
and one Relation; offset ten updates one hot Node; other commits change only the
unique generation identity. Bodies vary across short notes and approximately
4/12 KiB content. Every corpus must pass a real explicit full index rebuild before
measurements. Its ancestry length must exactly match the requested starting size.
The 100/1,000/10,000-generation corpora contain approximately 5/50/500 updates of
one Node, rather than claiming one update per committed generation. Artifact rows
record the exact starting hot-Node revision and receipt counts. Each operation also
records its starting committed-generation count and hot-Node revision count;
revision_count is the target Node's current revision count for updates, the hot
Node's count for reads/replay/recovery, and zero before creating a new Node.
The initial ancestry length is asserted by full verification; subsequent counts
advance only for the explicitly asserted successful canonical publications.

Fourteen rows per size comprise the observable initial full rebuild (mode
explicit_full_rebuild) and thirteen
workloads: low-revision update, hot-Node update, revision-one read, previous-revision
read, update replay, creation replay after updates, stale CAS conflict, published
Git/index-failure recovery, current Node read, Relation read, generation lookup,
one-Node create and replay of an unaffected original creation batch. Read/update
requests and validation setup are prepared outside measured API calls; semantic
postconditions are checked after counters stop. Four retained warm rows use the
same API boundaries as M2.1.1: Node read, Relation read, generation and replay.
The retained create workload differs: M2.1.1 measures generation lookup plus
Core.submit, whereas M2.2 measures only Core.submit with its expected generation
prepared beforehand. Raw create counters therefore are not directly comparable,
and their difference does not establish a speedup. Corpus and revision mix also
differ, so no latency-ratio claim follows for any retained workload. The recovery
row intentionally
includes failed derived publication, a fresh Core instance and exact retry/catch-up.
It must observe REPAIR_REQUIRED after Git publication and no second canonical
publication on retry. CAS must return REVISION_CONFLICT without advancing the ref.

Existing instrumentation records Git subprocesses and requested blobs, full tree
loads/enumerations, commits enumerated and transition-verification calls, canonical
parse calls, domain records checked, receipt pair checks, SQLite statements, SQLite
file bytes and process-lifetime peak working set where available. The latter is a
bounded process memory observation, not per-call allocation attribution. Artifacts
bind all Core Python source bytes, canonical schema contents and harness bytes;
source changes during a run are explicitly detected. Synthetic IDs and timestamps
are disposable, so fixture shape rather than byte-for-byte history is reproducible.

M2.1.1's original optimized artifact remains the reference for its five warm API
workloads. The new corpus adds genuine immutable updates and receipts; direct
latency ratios against that differently mixed history would not establish a
speedup. Compare structural operation counts and report the different corpus mix.
No wall-clock CI guarantee or production throughput claim follows from this local
benchmark.

## M2.2 final measurements

The command above exited **0** with **42/42 complete rows** on Python 3.12.6,
Git 2.46.2.windows.1, Windows 10 build 19045. No other expensive validation was
run concurrently. All runtime, canonical-schema and harness unchanged-during-run
flags are true. Runtime SHA-256 is
`dff467475653c70752bff9db95bf52dd9693141fb8fbf277d02791a1e6715014`;
the artifact also records exact contract and harness fingerprints. These are
local observations, not CI timing guarantees or production capacity limits.

| Starting committed generations | Hot-Node revisions | Original receipts | Full rebuild seconds | SQLite bytes after rebuild | Canonical parse calls | Receipts verified |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 6 | 13 | 2.590 | 331,776 | 418 | 13 |
| 1,000 | 51 | 103 | 15.308 | 1,638,400 | 2,983 | 103 |
| 10,000 | 501 | 1,003 | 222.577 | 14,495,744 | 28,633 | 1,003 |

Full rebuild verified exactly 100/1,000/10,000 transitions. Fixture construction
is outside these rebuild and operation timings; its fast-import preparation cost
is not claimed as measured rebuild time. Each corpus then advances four canonical
generations through the two updates, recovery publication and one-Node create.
The hot Node begins at revisions 6/51/501 and finishes at 8/53/503. The low-revision
update targets a different Node starting at revision 1. Previous-revision reads
request 6/51/501 after the hot Node has advanced once, rather than reading its head.

| Workload, elapsed seconds | 100 generations | 1,000 generations | 10,000 generations |
|---|---:|---:|---:|
| Node update, revision 1 | 1.932 | 1.592 | 1.942 |
| Node update after accumulated revisions | 1.516 | 1.612 | 1.899 |
| Historical revision 1 | 0.686 | 0.666 | 0.631 |
| Historical latest minus one | 0.662 | 0.758 | 0.602 |
| Update replay | 0.786 | 0.707 | 0.723 |
| Creation replay after updates | 1.172 | 1.151 | 1.216 |
| Stale CAS conflict | 0.536 | 0.570 | 0.597 |
| Published Git / index failure recovery | 3.130 | 3.192 | 3.832 |
| Current Node read | 0.617 | 0.576 | 0.558 |
| Relation read | 1.026 | 0.909 | 0.885 |
| Generation | 0.210 | 0.219 | 0.211 |
| One-Node create (submit only) | 1.424 | 1.498 | 1.733 |
| Unaffected creation-batch replay | 1.056 | 1.082 | 1.137 |

At all three corpus sizes the following operation counts were identical. The
recovery row is a multi-call failure/restart scenario and is deliberately separate.
Git blob counts count requested OIDs, not filesystem cache misses. Canonical parse
calls are the existing narrow instrumentation metric, not every validator entry.

| Warm API workload | Git processes | Blob requests | Canonical parse calls | Receipt checks | New transitions | SQLite statements |
|---|---:|---:|---:|---:|---:|---:|
| Node update, revision 1 | 31 | 13 | 25 | 1 | 1 | 109 |
| Node update after accumulated revisions | 31 | 13 | 25 | 1 | 1 | 107 |
| Historical revision 1 | 13 | 9 | 8 | 0 | 0 | 26 |
| Historical latest minus one | 13 | 9 | 8 | 0 | 0 | 26 |
| Update replay | 14 | 9 | 11 | 1 | 0 | 25 |
| Creation replay after updates | 23 | 21 | 23 | 1 | 0 | 56 |
| Stale CAS conflict | 12 | 8 | 8 | 0 | 0 | 31 |
| Published Git / index failure recovery | 64 | 34 | 52 | 3 | 2 | 210 |
| Current Node read | 12 | 8 | 7 | 0 | 0 | 20 |
| Relation read | 19 | 15 | 13 | 0 | 0 | 43 |
| Generation | 5 | 1 | 0 | 0 | 0 | 2 |
| One-Node create (submit only) | 28 | 11 | 22 | 1 | 1 | 99 |
| Unaffected creation-batch replay | 21 | 16 | 23 | 1 | 0 | 56 |

Every healthy measured API call used zero full-tree loads/enumerations and zero
repeated blob OID requests. Updates and create each verified exactly one newly
committed transition and one receipt; historical reads and replay scanned no
ancestry. Recovery performed two bounded transition checks (candidate validation
and restart catch-up), three receipt checks and 21 repeated OID requests across
its separate failed submission and new-Core retry. It is not a single-request
blob-reuse budget violation. Full rebuild alone intentionally traversed retained
history and validated all receipts.

The focused CI regression budgets permit at most 20 requested blobs for an update
and 12 for a historical read, prohibit duplicate requests, and require exactly
one update transition. Separate regressions forbid ancestry, full-tree access,
rebuild and authenticated-index reload on the warmed update/history paths.
Measured update/history counts were 13/9 blobs at all sizes. SQL counts above are
observed bounds for this fixture, not separately enforced universal SQL limits.
Actual affected Relations may increase update cost when a type change requires
checking their predicate and endpoint invariants.

The maximum observed process-lifetime peak working set was 202,502,144 bytes.
This includes fixture construction, earlier corpora and explicit rebuilds; it does
not attribute allocations to an individual API call. Final SQLite sizes after
all workloads were 364,544, 1,667,072, 14,512,128 bytes.
Startup authentication/private-memory projection cost and explicit full rebuild
remain proportional to index bytes and retained history respectively; these
measurements do not establish constant memory or constant cold-start cost.

For the four comparable API boundaries, M2.1.1 to M2.2 Git/blob observations at
10,000 starting generations were: Node read 12/8 to 12/8; Relation read 19/15 to
19/15; generation 5/1 to 5/1; creation-batch replay 23/27 to 21/16. These count
observations have different historical revision mixtures and do not establish
latency speedups. M2.1.1 create's 36/15 includes an extra generation lookup; M2.2's
28/11 measures submission only, so its raw difference is not a direct performance
comparison. The original M2.1.1 JSON evidence remains unchanged.
