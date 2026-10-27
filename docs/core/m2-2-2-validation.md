# M2.2.2 validation evidence

Status: **M2.2.2 complete; M2.3 GO for its separately scoped implementation.**
Full working-tree unified gates and the complete benchmark matrix passed.
The subsequently confirmed P2 clean-checkout manifest defect was corrected;
independent final review returned PASS WITH WARNINGS, with no unresolved P0/P1/P2
findings. This is an engineering readiness decision, not a production deployment
or durability certification.

Baseline: `80a24eedb0379b15e4fd9a9d5975486d04cc0558`, clean before work.
Configured implementer `/root/m222_implementation` owns runtime/schema/tests and
design; `/root/m222_benchmark` owns only the existing benchmark harness and final
artifact. Independent reviewer `/root/m222_review` inspected the actual Stage A
proposal/code and returned PASS WITH WARNINGS before production changes. Warnings:
hashing is not the dominant measured latency; bucket and Git directory fanout can
still be linear; final measured counter evidence is mandatory. The coordinator
owns final integration and quality gates. No subagents delegated further.

## Measured baseline

[Raw profile/source/environment evidence](../engineering/history-performance-m222-baseline.json)
records 100/1,000/10,000 generations. Each successful warm update used 26 Git
subprocesses and computed two full maps of 70/565/5,515 paths, respectively.
Generation construction took 0.000632/0.003198/0.030482 seconds. This proves growing
metadata work, not latency dominance or an overall before/after speedup.

## Executed focused checks

Final focused rerun: `pytest tests/test_core_m222.py tests/test_commitment.py -q`
passed **28 tests in 151.01 seconds**, including fixed golden values, the independent
full-tree reference, exact predecessor/crash cases, GC interruption, partial backup,
real two-process cold-reader/GC serialization and forced empty-lock initialization
race on Windows. `pytest tests/test_core_m221.py -q -x` passed all **41 tests in
309.18 seconds**. The earlier observations below record why corrections were made.

`tools.generate_contracts --check` passed all 24 emitted artifacts;
`tools.validate_contracts` passed 8 schemas, 768 offline references and 156 portable
fixtures/round-trips. `npm run parity`, `npm run typecheck`, Ruff runtime/test lint,
Pyright and `git diff --check` passed. Independent production Ajv parity also passed
in the focused consumer run. These do not replace the coordinator's full unified
quality/distribution/test command or acceptance benchmark/review recorded below.

- `pytest tests/test_commitment.py -q`: 4 passed before adding fixed golden values;
  independent full 65,536-leaf reference, incremental reuse, empty/absent, deletion,
  instance separation, duplicate keys, colliding buckets and altered witnesses.
- `pytest tests/test_core_m222.py -x -q`: initial 19 passed in 79.53 seconds;
  fresh bounded roots/old receipts, mixed legacy adoption/audit, downgrade/invalid
  adoption, exact predecessor upgrade, four interrupted upgrade boundaries,
  capacity maintenance/GC retention and denied maintenance.
- Additional GC interruption and partial-backup/rebuild cases passed. The real
  two-process cold-reader/GC test initially reproduced Windows lock acquisition
  reading an already locked byte before requesting the lock. The minimal fix uses
  `fstat` length and unbuffered initialization; the two-process case then passed.
- Focused portable GenerationRef fixtures plus independent Ajv parity: 4 passed,
  168 deselected. Generated artifacts came only from `tools.generate_contracts`.
- Ruff handwritten runtime checks and Pyright: passed at the first runtime slice.

Historical M2.2 tests first passed 27 cases before a legacy-only fixture copied the
new bootstrap scheme and later emitted an old flat descriptor. The fixture now
explicitly creates its intended legacy root; its targeted regression passed.
The M2.2.1 bounded-work regression now counts its original domain DML budget
separately from the new bounded commitment rows. No production downgrade exception
or relaxed historical integrity check was added to accommodate tests.

These are intermediate observations, not final suite/scalability approval.
Final reruns, reviewer findings/corrections, benchmark and readiness verdict are
recorded below; intermediate results alone were not treated as acceptance.

## Correction cycle 1: same-scheme historical test fixtures

The coordinator's first full run reproduced a competing-writer test expecting
`NOT_FOUND` but receiving `REPAIR_REQUIRED`. Its supposedly valid competitor used
the explicitly legacy fixture generation helper after a modern bootstrap, creating
a forbidden algorithm downgrade. The fixture now preserves the committed scheme
and asserts the competitor remains readable before checking the absent resource.

The implementer inspected every test call to `repository.generation`, separating
intentional legacy/downgrade cases from valid external generations and negative
fixtures intended to isolate other integrity failures. Those external builders now
preserve their source scheme; intentional legacy roots and the explicit downgrade
regression remain unchanged. Negative effect/metadata/meaning tests retain their
specific corruption rather than being accidentally satisfied by a bad generation
digest. No production compatibility rule or rejection was weakened.

Focused competing-writer, M1.2 new/legacy/tampered snapshot and valid M2.2 definition
evolution probes passed **6 tests in 44.12 seconds**. The independent reviewer
rechecked the actual six-file fixture diff and ran five focused cases successfully
in 39.72 seconds, returning **PASS** with no confirmed blocking findings. The
production review remains **PASS WITH WARNINGS**; its independent commitment/runtime
run passed all 28 tests in 146.69 seconds. One of the three automatic correction
cycles has been used. Available delegation evidence is the native role/task
invocation and returned results; optional session/trace IDs are not available.
Reviewer filesystem isolation was not independently verified. Full integration and
performance gates remain separate from these review verdicts.

## Unified integration gate

The coordinator ran the following command with process-local
`PYTEST_ADDOPTS=-x` (stop on failure; no tests are omitted on a successful run):

```powershell
.venv/Scripts/python.exe -m tools.check full
```

Exit status **0**. Ruff lint/format, Pyright, ESLint, strict TypeScript consumers,
syntax compilation and documentation checks passed. Canonical validation passed
8 schemas, 768 offline references and 156 fixtures/round-trips. Generation drift
matched all 24 artifacts. The complete pytest run passed **551 tests in 1864.90
seconds**. Fresh isolated distribution build and integrity verification each
passed **37 payload files**. A separate `npm run parity` also passed.

The first diagnostic full run was interrupted after the reproduced fixture
failure described above; it is not counted as a passing gate. The fresh run used
the corrected fixtures. The benchmark harness subsequently gained two explanatory
counter-scope notes only; its Ruff/format and diff checks passed before measurement.
The full benchmark matrix completed against frozen production/harness sources.

## Correction cycle 2: clean-checkout source hashes (resolved)

Independent review confirmed that the generated source manifests currently hash
CRLF bytes in three local schema inputs, while the repository's Git attributes
produce LF bytes on checkout. The passing working-tree drift check therefore
does not establish clean-checkout reproducibility. Git's actual filtered output
and indexed blobs were independently checked; this is a confirmed P2 defect.

The narrow correction is to normalize those inputs to the existing LF policy,
regenerate through the established tool and add a focused regression plus an
isolated Git-normalized export check. Exact raw-byte source hashing must remain
unchanged. Measurement completed before this correction began. Parsed-schema
fingerprints, runtime and harness identities are checked separately from this
raw-byte manifest correction.

The implementer normalized exactly `common.schema.json`, `knowledge.schema.json`
and `operations.schema.json`, regenerated all 24 artifacts through the existing
generator and added `test_generator_inputs_follow_declared_lf_checkout_contract`.
Decoded schema objects and runtime/harness fingerprints are unchanged. Post-fix
`pytest tests/test_production_contracts.py -q` passed **173 tests in 51.49 seconds**;
`tools.check quality`, generation drift (24), canonical validation (8 schemas,
768 references, 156 fixtures), `npm run parity` (24 probes) and diff checks passed.
The earlier full run remains 551 tests; it is not represented as a post-fix full
552-test run. Distribution tests passed **13 cases in 93.80 seconds**. The isolated
LF source-only export's own generator matched all 24 artifacts; this was an export,
not a literal fresh Git clone. Independent actual Git attribute/filter checks
established that its LF bytes equal the committed checkout policy. All 17 declared
raw-hashed inputs now match their manifests and contain no CRLF. Independent
`verify_generated` and two focused regression checks also passed, and the reviewer
independently matched all four current fingerprints to the completed matrix.
The coordinator's final `tools.validate_examples` passed 720 portable
document links and all existing example/rejection/OpenAPI probes.

## Measured mutation samples

The [matrix artifact](../engineering/history-performance-m222.json) records the
following completed hot-Node update samples. The full command exited 0 with
**1,307 completed rows, zero failed rows**, and unchanged runtime, harness,
parsed-schema and fixture-helper fingerprints throughout measurement:

```powershell
.venv/Scripts/python.exe tools/benchmark_history.py --merkle-hardening --sizes 100 1000 10000 --git-budget 100000 --output docs/engineering/history-performance-m222.json
```

| Starting generations | Samples | p50 seconds | p95 seconds | p99 seconds | Update service rate/s | Whole-loop rate/s |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 100 | 1.598756 | 1.783080 | Not estimated | 0.615883 | 0.322032 |
| 1,000 | 100 | 1.602181 | 1.706610 | Not estimated | 0.619165 | 0.319179 |
| 10,000 | 1,000 | 1.579854 | 1.665854 | 1.732004 | 0.630938 | 0.307481 |

The whole loop includes dependency reads, request construction, trusted-host
maintenance, instrumentation and report/log I/O. Service rate covers measured
submit calls. Ten distributed updates per corpus also passed; that sample is too
small for reported percentiles. These timings are instrumented Windows observations,
not production latency guarantees or a matched overall speedup claim.

Baseline-matched replacements used 26 Git processes and 13 blob reads at all three
sizes. Python-observed SHA256 input was 200,267 / 200,123 / 200,018 bytes,
respectively, while the old flat representation alone encoded 9,137 / 73,847 /
720,947 bytes twice per update. The new path changes bounded commitment metadata
instead of enumerating the full map; native Git directory/index work remains.
Counters exclude Git's internal hashing and C-internal HMAC work. Ordinary updates
performed no full SQLite serialization or full database hash. Added branch metadata
increases delta payload size; lower hash work is not free storage or proof that
hashing was the dominant latency cost.

| Starting generations | Final rebuild seconds | Rebuilt SQLite bytes | Explicit compaction seconds | Post-compaction restart seconds | GC apply seconds |
| --- | --- | --- | --- | --- | --- |
| 100 | 23.507099 | 1,273,856 | 0.255698 | 0.460892 | 1.046386 |
| 1,000 | 56.985780 | 3,162,112 | 0.262519 | 0.509490 | 1.099591 |
| 10,000 | 469.319551 | 25,665,536 | 0.420014 | 0.572146 | 3.870444 |

The final large rebuild verified 11,018 commits and 2,018 receipts, used 586,286
SQLite statements and wrote 25,668,766 derived payload bytes. Python CPU was
454.875 seconds. Process-lifetime peak working set reached 320,098,304 bytes;
this includes corpus construction and full rebuilds, not a per-update allocation.
The frozen M2.2.1 final corpus differs, so these rebuild values do not establish
a direct speedup. Compaction authenticates and writes a complete base explicitly;
cold base authentication, rebuild, audit and GC inventory remain input-sized work.

Full historical audits also passed at all three corpus sizes in 23.177151 /
49.677150 / 467.104258 seconds. The final audit verified the same 11,018 commits
and 2,018 receipts as the rebuild and wrote no derived files. Replays of creation
and earlier updates, exact historical reads, stale CAS, mixed create/update batches,
large-body/high-churn replacements, long-tail restart, explicit capacity maintenance,
GC dry-run/apply, restart after GC and Git-only publication catch-up all completed.

Across all 1,200 measured hot updates, each used 26 Git processes, 13 blob reads,
one committed transition and one receipt verification. Point file-metadata results
remained 32 per update; changed projection rows were 45–53 overall. No full file
metadata scan, full SQLite serialization or full database hash occurred on those
updates. The large-corpus delta payload was 11,229–12,287 bytes. Its initial hot
Node already had 501 revisions; 1,000 more hot updates exercised deep history.
The corpus includes independently created Relations and many unrelated Nodes;
the large-body replacement is 655,360 bytes. Fixed-depth hashes do not remove
chosen-key bucket concentration or native Git tree/index fanout costs.

Tagged commitment hash inputs for the matched replacements were 23,173 / 23,007 /
23,007 bytes and five bucket entries each. The large hot workload used 206-229 SQL
statements, 20,683-23,623 tagged hash bytes and no duplicate blob requests; largest
touched bucket cardinality was three. This is not a bound against adversarial
path concentration. GC reclaimed 25,232,416 bytes while retaining required current
and prior anchors. The final rebuild creates another base, so final derived
directory size was 79,440,841 bytes; GC does not guarantee a universally smaller
final footprint. Explicit maintenance remains necessary.

The benchmark's semantic contract fingerprint is
`b95f9eba50136cdcb37490962241a2fdbf152f4847d64568caa3faba4d6f8e0e`;
runtime is `a03434ff8a46d837318cfee3d238a98befa491ae286d61147c63d4504c816369`
and harness is `a6f7b4833f34c80502bf7ba6abed6c887571522bd7841131a5617aa4ca775d77`.
The post-measurement newline correction affects raw source/manifests, not these
semantic/runtime/harness identities; its validation is recorded separately.

## Verification limits and remaining work

Git remains the only canonical authority. The protected local key/checkpoint and
trusted host/OS boundary remain required: an actor replacing Git, the key and all
rollback anchors can defeat these local integrity guarantees. Windows process
locking was exercised; production ACLs, agent sandbox isolation, other OSes,
hardware power-loss durability and production disaster recovery were not verified.
Partial derived-backup/rebuild fixtures are not a production backup guarantee.

The optional generation field changes closed old consumers' accepted shape despite
the unreleased `1.0.0` label; pin canonical inputs and regenerated consumers together.
Historical flat digests remain exact; known format-3 indexes require authenticated
explicit upgrade, then generation-only adoption. Missing trust material never
authorizes fresh enrollment. O1-O4 remain open. No Relation mutation, public
maintenance discriminator, transport, search, autonomous scheduler or semantic
index was introduced. The next slice is independently revisioned Relation mutation
under the existing receipt, current-authority and committed-transition guarantees.

The executed tests cover their named cases; they do not prove all possible domain
behavior or scalability. Actual corpus measurements and instrumentation scopes
above are the performance evidence. Independent final correction-cycle-2 review
returned **PASS WITH WARNINGS**, with no unresolved P0/P1/P2 findings. Two of three
automatic correction/recheck cycles were used; none were bypassed. Implementer
`/root/m222_implementation` and reviewer `/root/m222_review` both completed their
configured roles; `/root/m222_benchmark` completed the bounded benchmark assignment.
Native invocation/results are the available execution evidence; optional session
and trace IDs are unavailable and reviewer filesystem isolation is unverified.

**M2.3 GO:** the historical, authorization, publication and bounded-commitment
foundation is ready for a separately specified Relation mutation slice. No Relation
update handler was added here. That slice must preserve independent endpoint
revisions, exact old receipts, current permissions and the same hot-path work gates.
