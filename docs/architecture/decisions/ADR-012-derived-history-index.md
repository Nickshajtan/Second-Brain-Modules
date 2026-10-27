# ADR-012: Authenticated disposable history projection

Status: adopted for M2.1.1 after independent design stress review. Unreleased
1.0.0. Implementation validation is recorded separately in the
[M2.1.1 validation report](../../core/m2-1-1-validation.md).

M2.2.1 [ADR-013](ADR-013-incremental-derived-index.md) supersedes the whole-file
per-mutation clone/hash/rewrite with authenticated bounded projection deltas.
The private-memory, current-authorization and protected-local-anchor boundaries
below remain applicable. This document preserves the historical M2.1.1 decision.

## Decision

Git remains the only canonical transaction authority. A stdlib SQLite projection
outside its tree stores minimal path/blob/hash, resource dependency, revision,
generation and scoped idempotency locators. No canonical request/content bodies or
permission verdicts are retained there. The managed ref and existing writer lock
and conditional publication remain the domain commit boundary.

A separate random local key authenticates a checkpoint binding instance,
repository/common path, managed ref, index format, exact schema fingerprint,
accepted commit/generation and complete SQLite file hash. Startup authenticates
the exact bytes passed to SQLite deserialize into a private read-only in-memory
connection. Runtime SQL never queries a mutable disk database. Missing rows,
including negative idempotency lookups and all Membership dependencies, therefore
cannot be forged by mutating disk rows or restoring mtime. This replaces the
proposed per-row signature approach with one authenticated immutable lookup set.

Ordered incremental verification checks every intervening commit, exact generation,
new receipts/requests/effects and retained immutable path/OID obligations. Deleting
an entire transaction cannot remove its prior obligation. Warm reads canonically
load only requested Git blobs and current authorization dependencies. Git blob
hashes are recomputed. Current grants are evaluated independently on every delivery.
History lookup never makes original admission a current grant.
Authenticated scope/lifecycle facts support denial-only screens before private
blob/evidence loading; they cannot authorize a positive result. Canonical records
and the existing full authorization checks remain required for delivery/execution.

Canonical Git publication precedes derived replacement. A crash may leave the
projection behind, never ahead. Atomic database replacement precedes checkpoint
publication; a crash in between retains the old signed rollback anchor and rejects
the mismatched database. Explicit rebuild fully verifies Git into an isolated
projection, fences the source ref and preserves existing accepted ancestry.
Missing/corrupt trust-anchor material requires operator recovery, not silent reset.
An existing empty enrollment directory is rejected too: lost files cannot turn an
already enrolled history into an apparently pristine instance.

## Consequences and limits

SQLite loss is rebuildable from Git; local checkpoint continuity constrains recovery
even when SQLite is absent. Existing unenrolled repositories require explicit
trusted-host enrollment/rebuild. Fresh trusted bootstrap may establish the initial
frontier. Interrupted enrollment retains an authenticated initial commit and can be
retried explicitly. A copied checkout is not a new instance or implicit authority.

Startup/private memory scales with index bytes. Exhaustive audit/rebuild scales
with retained history and uses a verification-scoped unique-blob cache. Commit
construction may enumerate path/hash metadata; it does not revalidate all original
transactions. The benchmark records actual work and these costs, not a constant
memory or latency promise.

The OS must protect key, checkpoint, index and canonical Git from agent processes.
Mode bits alone do not establish Windows ACLs. A privileged actor replacing Git,
key and checkpoint defeats this local trust anchor. No independent remote/hardware
tamper resistance is claimed. Warm generation lookup is not an exhaustive object
availability audit; missing unrequested retained objects are detected by explicit
audit or requested evidence access. Audit is required after restore or suspected GC.
Shallow histories, merges, grafts, divergence and rollback fail closed.

No canonical schemas, public operation discriminators, update/history handlers,
search tables, new dependencies or generic indexing framework are introduced.
See [runtime design](../../core/m2-1-1-history-hardening.md),
[performance](../../engineering/history-performance.md) and
[recovery](../../engineering/history-recovery.md).
