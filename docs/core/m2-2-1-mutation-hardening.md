# M2.2.1 mutation throughput and storage hardening

Status: implemented and independently reviewed with no unresolved blocking findings;
unified quality checks and the complete benchmark matrix passed. Evidence is recorded in
[validation evidence](m2-2-1-validation.md). Baseline:
`4b398cca2400cbf9bbf2e04c712e2e01fa80ab0f`.

## Measured baseline and existing authority

[ADR-011](../architecture/decisions/ADR-011-immutable-creation-effects.md),
[ADR-012](../architecture/decisions/ADR-012-derived-history-index.md) and the
[M2.2 semantics](m2-2-node-mutation.md) remain authoritative. Git is canonical;
the projection contains only authenticated locators and dependency metadata.
Current capabilities, canonical validation, CAS, immutable receipts/revisions,
single-membership restrictions and open Owner decisions are unchanged.

Stage A profiles real successful `submit` calls against disposable canonical Git
repositories built with the existing mutation benchmark helper. Fixture generation,
full verification and request generation are outside the measured update. The hot
Node has 6/51/501 revisions at 100/1,000/10,000 starting generations. Profiling is
instrumented and is not directly comparable to uninstrumented M2.2 latency.

At 100 and 1,000 generations respectively, one update took 1.711/1.770 seconds,
with Python process CPU 0.453/0.375 seconds. It launched 31 Git subprocesses;
`prepare_delta` took 0.512/0.501 seconds, including six separate `hash-object`
processes. Full SQLite publication took 0.095/0.104 seconds. Forking the projection
took 0.00028/0.00179 seconds. Two disk coherence hashes took 0.0041/0.0133 seconds.
The databases were 282,624/1,613,824 bytes: each update serialized twice, hashed
both old copies and the new complete database, and rewrote the complete database.
Thus projection byte amplification is confirmed, but SQLite was not the dominant
wall-clock cost in these observations. At 10,000 generations the update took
2.035 seconds (0.703 seconds Python CPU), with a 14,450,688-byte database: 28,901,376
bytes serialized, 43,352,064 bytes hashed across the two coherence checks and final
publication, and 14,450,688 database bytes rewritten. Fork took 0.0136 seconds,
coherence hashing 0.0872 seconds, full publication 0.1899 seconds, canonical path
digest 0.0331 seconds, Git preparation 0.5651 seconds and incremental verification
0.2322 seconds. Peak process working set was 134,852,608 bytes including fixture
construction/rebuild. The 10,000-generation full rebuild took 195.590 seconds.
These nested component times must not be added as independent elapsed costs.

The exact raw component measurements are retained in the coordinator's Stage A
evidence; final measurements belong to the validation/performance report.
`HistoryIndex.fork/publish/coherent` cause the whole-database work.
`TransitionVerifier.transition` additionally materializes all path/OID and immutable
obligation maps although it needs previous values only for changed paths.
`Core._next_generation` and verifier `_generation` hash the complete sorted
knowledge-path-to-content-digest map. That is the existing canonical GenerationRef
meaning: it cannot become an incremental digest without changing historical/public
semantics. This milestone retains and measures that O(path metadata) work; it does
not claim constant total update latency. Normal reads still load no full corpus.

## Design comparison

| Concern | A: optimized complete snapshot | B: mutable SQLite plus authenticated journal | C: authenticated immutable base plus bounded deltas |
|---|---|---|---|
| Mutation persistence | Fewer copies possible, but full bytes/hash/rewrite remain | SQLite page work plus journal; page authentication still required | Changed SQL bindings/rows plus compact anchor only |
| Missing-row integrity | Complete-file hash protects absence | A signed write log alone does not authenticate absent rows in mutable disk SQLite | Complete base and every accepted delta reconstruct the exact private set |
| Runtime trust | Exact bytes into private memory | Unsigned disk pages/WAL would require page proofs or full revalidation | Runtime queries remain private in-memory SQLite only |
| Restart | Read/hash complete base | WAL/page state must be authenticated before queries; difficult TOCTOU boundary | Read/hash complete base, then a bounded authenticated tail |
| Partial writes | Existing database/checkpoint mismatch requires rebuild | Coordinate WAL, journal and anchor; more recovery combinations | Immutable prepared delta is not accepted until signed terminal anchor advances |
| Rollback/ref divergence | Existing protected local anchor | Needs a separate terminal anchor, not a journal suffix | Signed terminal sequence/hash and Git descendant fence |
| Corruption | Hash rejects modified or omitted rows | SQLite integrity check is insufficient against valid injected/deleted rows | Altered/missing base or anchored delta rejects before deserialization/replay |
| Compaction | Every mutation effectively compacts | WAL checkpoints are not authentication checkpoints | Explicit authenticated new base; normal mutation never compacts |
| Windows | Existing atomic replacement retained | Open-file replacement and WAL ownership add complications | Closed immutable files, atomic small-anchor replacement; no disk SQL/WAL |
| M2.3 | No semantic coupling, but retains write amplification | More infrastructure than the current need | Existing fixed projection tables/DML can represent later independently reviewed operations |
| Complexity | Smallest but fails primary requirement | Largest: trusted mutable pages and complete absence proofs | Narrow journal around existing private connection and fixed verifier writes |

Select C. A cannot meet the required elimination of whole-projection
writes. B is rejected because mutable unauthenticated disk SQLite cannot safely
answer negative Membership/idempotency lookups; implementing authenticated pages
would add a storage framework. C preserves the existing private-memory trust
boundary, with a small derived journal rather than a second canonical event store.

## Proposed format and authenticated state

Projection authentication format 3 retains the existing fixed SQLite schema and
uses a uniquely named immutable base snapshot, immutable derived delta files,
and the existing protected key/enrollment plus atomically replaced signed checkpoint.
Every envelope binds instance, resolved repository/common directory, managed ref,
canonical contract fingerprint and projection format. A delta also binds the exact
previous authenticated state, contiguous sequence, new Git commit/generation and
the exact deterministic fixed-table DML statements and bound values produced by
verified transitions. Values are only projection metadata, never canonical bodies,
grants, requests or receipt content. Existing canonical Git remains sufficient for
a full rebuild. There is no generic user-submitted SQL or plugin journal API.

The checkpoint authenticates the base digest/source, base sequence, accepted
terminal sequence/hash, exact accepted commit/generation and tail byte/count bounds.
The terminal hash is independent of disk directory contents: deleted suffixes,
gaps, reordered, duplicated or modified deltas cannot masquerade as absent rows.
Replay follows only the complete anchored chain, validates envelopes and known DML
before executing them, and checks terminal generation against canonical Git.
The DML vocabulary is an exact allowlist of fixed statement templates with table
and parameter arity checks and bounded JSON-compatible values, not arbitrary SQL
accepted because an envelope has a MAC.
The complete base bytes are hashed before those same bytes are deserialized.
No disk SQLite connection, WAL, hash-then-reopen or unsigned-row fallback exists.

Warm operations use the already authenticated private connection. They recheck the
small anchor/key/binding and current Git ref, not the complete base file. Corruption
of old disk base/tail bytes cannot change private rows or become signed metadata;
it is detected at restart, explicit audit/rebuild or access to the affected journal
head. This deliberately changes detection timing from the old per-write full hash,
while preserving the prohibition on consuming or signing unverified disk rows.
The OS must protect key and anchor. Restoring Git, key and all old signed local
state together cannot be detected without an independent trust anchor; this was
already outside ADR-012's protection and is not claimed here.

When another trusted Core writer advances the same immutable base, a warm Core
authenticates the new signed terminal checkpoint and applies only its new complete
deltas to the existing private connection under a savepoint. It does not reload,
deserialize or hash the base. Exact prior authenticated state, binding, sequence,
terminal payload and canonical source generation are checked before acceptance.
An explicit compaction/rebuild that changes the base requires one complete
authenticated base load; this is a maintenance boundary, not a normal writer
advancement. Format-3 envelopes must use canonical exact serialization so the
previous-checkpoint byte identity cannot become ambiguous after reformatting.

## Candidate, Git publication and failures

Use a SQLite savepoint on the private connection instead of cloning it. Capture
only successful deterministic writes made by the fixed transition verifier. The
accepted frontier remains unchanged while the candidate is tentative. A context
manager rolls back on verification failure, CAS failure or any exception. A normal
Core read during its own active candidate must fail closed, never expose tentative
rows. Separate Core instances retain separate accepted connections and refresh
from authenticated publication. No new same-Core thread-sharing guarantee is made.

After candidate verification, conditional Git publication occurs first. Then write
and flush the immutable derived delta, and atomically replace the signed terminal
checkpoint. Only then accept the private transaction/frontier and return. Recheck
the exact prior anchor/key and Git source immediately before derived acceptance;
external anchor changes cannot become a signing oracle. Coherence compares the
exact cached checkpoint bytes and key, not just commit identity: compaction may
legitimately replace the authenticated state at the same canonical commit.
Any failure invalidates
tentative private state and forces authenticated reload before further delivery.
Git publication is never rolled back because derived persistence failed.

| Interruption | Required result |
|---|---|
| Before Git publication / failed CAS | Savepoint rolls back; no accepted delta/frontier advance |
| Git published, no complete delta | Old accepted state remains; canonical catch-up verifies the missing transition |
| Partial or fully written unanchored delta | Not accepted or replayed; next writer replaces the deterministic unanchored slot under lock |
| Anchor published before response | Restart replays the exact accepted delta; request retry returns original receipt |
| Accepted delta removed/truncated | Fail closed; explicit full rebuild retains signed commit rollback fence |
| Private SQLite failure | Roll back/invalidate; no unsigned disk fallback |
| Externally advanced Git | Verify every intervening transition in order before serving; publish bounded deltas |
| Git rollback, unrelated history, merge, shallow or missing ancestry | Existing fail-closed diagnostics; never serve prior rows as the new head |

The journal does not authorize partial batch replay. Original request/effect
verification and current operation-specific authorization remain unchanged.

## Restart, compaction and upgrade

Startup is O(base bytes) plus a strictly bounded accepted tail. The tail has hard
count/byte limits. Check count capacity early; compute exact encoded delta bytes
after bounded candidate verification/capture and before Git CAS. Oversize rolls
back the candidate and publishes no canonical commit. Exhaustion
requires explicit trusted-host compaction; no routine update performs a hidden
whole-database rewrite. The implemented hard bounds are 1,024 accepted projection advancements and
16 MiB of retained encoded deltas. Developmental real-Node updates captured about
7.2 KiB each (roughly 7.2 MiB for 1,024 such updates); final measured restart and
compaction costs remain acceptance evidence. An external catch-up advancement can
contain several sequentially verified Git transitions, but its encoded bytes count
against the same total limit. They are operational recovery budgets, not throughput or latency guarantees.
An oversized transaction fails before canonical publication with a maintenance
diagnostic rather than creating an unbounded restart tail.
External Git catch-up that would exceed capacity fails closed rather than invoking
a hidden full snapshot. Explicit full rebuild verifies the complete new source. Compaction requires the
current managed ref to equal the accepted frontier; it does not provide a special
mode for compacting a stale frontier while newer Git state remains unverified.

Explicit compaction owns the existing writer lock, verifies current source/anchor,
serializes the accepted private state once into a new uniquely named immutable base,
flushes it and atomically switches the signed checkpoint while retaining its prior
authenticated state identity. Before the switch the old base/tail remains usable;
afterward the new complete base is authoritative derived state. A new base never
overwrites bytes referenced by the old checkpoint. Fresh UUID filenames avoid reuse of any old referenced file. Old files are not
automatically destructively removed. Safe explicit cleanup can be deferred; disk
retention is documented. Interruption never deletes the last usable base/anchor.

Normal format-1/2 access remains explicitly stale. Trusted rebuild authenticates
the old key/checkpoint/enrollment with recognized complete old binding first,
retains its accepted commit fence, fully verifies canonical descendants and writes
format 3 without minting a replacement key. Mixed interrupted upgrade envelopes
remain unacceptable for reads but recoverable by explicit rebuild with retained
signed fences. Missing key/checkpoint/enrollment remains operator recovery, never
fresh enrollment. Canonical revisions, receipts and Git history are untouched.

## Implemented scope and verification

Production changes are limited to `history_index.py`, the narrow `projection.py`
DML-capture helper, `application.py` candidate lifetime, `verification.py` changed-path
lookups, `maintenance.py`/exports for trusted explicit compaction, and `git_store.py`
command batching. No dependencies or canonical/schema changes were added. Indexed
changed-path lookups replace complete previous-path/immutable maps. The canonical
generation digest remains unchanged and visible in counters.

Git `prepare_delta` already changes only requested paths but reads a temporary full
Git index and writes a tree. Those native metadata costs remain; no canonical blobs
are enumerated. Stage A measurements show six short-lived `hash-object` processes
are material. The implementation batches those file hashes through standard Git
invocations with bounded Windows argument chunks; exact Unicode/CRLF bytes pass
regressions. No Git daemon, temporary canonical ref, custom object store or persisted
path-layout change was introduced.

The real-Git regression suite covers absent Membership/receipt/idempotency rows, anchored
tail deletion/reorder/tamper, old anchor/current ref mismatch, every publication
boundary, savepoint rollback, cross-process restart, independent readers/writers,
explicit upgrades, compaction crash boundaries, lost trust files, rebuild and old
receipts after later revisions. Structural gates forbid full serialize/hash/rewrite,
fork, ancestry or corpus reads on healthy bounded updates, and assert changed rows
and persisted bytes depend on affected scope. Final benchmarks retain old artifacts,
use all three sizes, repeated/distributed mutations and enough samples for honest
percentiles. Full deterministic gates and independent completed-diff review passed;
the linked validation report records M2.3 readiness and operational limits.
