# ADR-013: Authenticated bounded projection deltas

M2.2.2 amendment: [ADR-014](ADR-014-versioned-content-commitments.md) adds a
versioned canonical content commitment and derived format 4 bucket/branch rows.
The existing complete authenticated base/delta boundary remains; no per-row grant
or mutable disk SQL is introduced. Explicit host maintenance compacts at half the
hard capacity thresholds. Compaction archives the exact prior signed checkpoint
under its SHA256 name before switching the current checkpoint. Explicit GC retains
the current and one exact prior base/tail set. Cold load/refresh and GC share the
writer lock, protecting cross-process readers during derived-file deletion.
See [current maintenance and recovery](../../engineering/history-recovery.md).

Status: adopted design for M2.2.1 after independent Stage A review; implementation
and measured acceptance are recorded separately in the
[validation report](../../core/m2-2-1-validation.md). Baseline:
`4b398cca2400cbf9bbf2e04c712e2e01fa80ab0f`.

## Decision

Preserve ADR-012's exact-byte authenticated base snapshot and private in-memory
SQLite boundary. Replace ordinary full snapshot cloning/publication with a private
SQLite savepoint, capture of the fixed verifier DML vocabulary, an immutable
authenticated derived delta and a compact atomically replaced HMAC checkpoint.
Git remains the only canonical transaction authority. This supersedes ADR-012's
whole SQLite rewrite and complete on-disk database hash before every mutation;
its instance isolation, current authorization, retained historical verification,
explicit recovery and protected-local-anchor assumptions remain in force.

Format 3 binds instance, repository/common path, managed ref, contract fingerprint,
base digest, contiguous projection sequence, exact previous authenticated state,
accepted delta hash and committed Git generation. Every accepted tail element is
required. Absence of Membership, receipt and idempotency rows is trustworthy only
because private SQLite is reconstructed from a complete authenticated base plus
the complete anchored tail. Runtime never queries mutable disk SQLite or WAL.
Signed arbitrary SQL is not an interface: delta replay validates exact fixed DML
templates, arity and value types. Canonical content/grants/receipts stay in Git.

Conditional Git publication precedes derived acceptance. Verification or CAS
failure rolls back tentative rows. After Git succeeds, derived failure leaves
canonical effects committed and invalidates uncertain private state; retry loads
the authenticated accepted frontier and verifies catch-up. An unanchored or partial
next delta is never replayed and may be replaced under the existing writer lock.
Missing or altered anchored deltas fail closed, even if canonical Git could supply
them; explicit rebuild retains the signed rollback fence.

Normal mutations never serialize/hash/rewrite the full projection and never
compact automatically. The bounded tail uses explicit trusted-host compaction.
Count capacity is checked early; exact encoded byte capacity is checked after
candidate verification and before canonical Git CAS. Exhaustion reports
`INDEX_COMPACTION_REQUIRED`/sanitized `REPAIR_REQUIRED` without publication.
Catch-up beyond capacity requires explicit full rebuild. No unverified newer
generation becomes deliverable by compacting an older accepted view.

Compaction writes a new uniquely named immutable base and then switches the signed
checkpoint, retaining the prior authenticated state identity. It never overwrites
the old referenced base. Old base/delta files are preserved; automatic destructive
cleanup is outside this change. Formats 1/2 upgrade only through explicit full
canonical rebuild after authenticating the old signed binding/key and accepted
commit fence. Missing trust material cannot authorize reenrollment.

## Alternatives and limits

Stage A compared optimized whole snapshots, mutable SQLite with an authenticated
journal, and this bounded base/delta design. Whole snapshots retain O(index bytes)
write amplification. Mutable disk SQLite would require authenticated pages and
absence proofs beyond SQLite transaction integrity. The chosen narrow delta
mechanism retains the existing private-memory trust model without a storage engine.
See the [comparison and measured audit](../../core/m2-2-1-mutation-hardening.md).

Startup and explicit compaction remain O(base bytes); audit/rebuild remain
O(retained history). The canonical generation's sorted path-digest contract remains
O(knowledge-path metadata); native Git tree/index preparation still has metadata
cost. No constant total mutation latency or memory guarantee is made.

Warm operations do not continuously hash old immutable disk base/tail files.
Tampering cannot change an already authenticated private connection; detection is
on restart, explicit audit or bounded journal-head access. New signatures contain
only trusted private state and verified changes, never altered unsigned disk rows.
The OS must protect local keys/anchors and isolate agents. Replacement of canonical
Git and all protected old signed local state together remains undetectable without
an independent anchor. Windows ACL isolation and physical power-loss durability
are deployment obligations, not established by the derived journal.

No canonical schema, public operation, Owner policy decision, Relation mutation,
transport, search subsystem, dependency or generic event store is introduced.
