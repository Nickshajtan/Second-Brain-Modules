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
