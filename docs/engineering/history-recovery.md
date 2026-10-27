# History operations and recovery

## M2.2.2 explicit upgrade and maintenance

The [versioned commitment design](../core/m2-2-2-merkle-hardening.md) retains
ADR-013's authenticated immutable base/tail and private-memory read boundary.
Derived format 4 adds commitment locators; it does not become canonical knowledge.
Existing instances require explicit `upgrade_history_index(core)` before the
separate `adopt_generation_commitment(core)` publication. Authenticate the old
known schema binding, key, enrollment and accepted frontier first. Missing trust
material is operator recovery, never permission to reenroll. Legacy generations
and receipts keep their exact original digest interpretation.

Direct predecessor authentication targets the supplied M2.2.1 format-3 baseline.
For format 1/2, first run its documented explicit upgrade using the M2.2.1 runtime,
retaining the same protected anchors, before switching to M2.2.2. Never reset an
enrollment directory or discard a checkpoint as an upgrade shortcut.

The trusted host calls `maintain_history_index(core)` between requests. At 512
deltas or 8 MiB it compacts before the 1,024/16 MiB hard limit; this is an explicit
host action, not a Core scheduler. Returned count/byte reserves do not guarantee
that an arbitrary large next transaction fits. Exact encoded capacity is still
checked before Git publication. Oversized catch-up may require full rebuild.

Compaction archives the exact previous signed checkpoint under its SHA256 name
before accepting a new base. Explicit `collect_history_index(core, apply=False)`
reports candidates and retained reasons; `apply=True` deletes only recognized
unreachable derived files. It authenticates the current base/tail and required
prior checkpoint/base/tail under the repository lock. Cold loading and refresh
take that same lock; warm readers use already authenticated private memory.
Unknown files, links, trust keys and canonical Git objects are preserved.

Back up the complete managed Git history and protected key/enrollment/checkpoint
together with the current and required prior derived bases/tails under the same
host coordination lock. A partial derived backup can require explicit rebuild
from Git with the authentic rollback fence; lost anchors cannot be replaced
silently. GC is repeatable after interruption, but does not promise physical
erasure, Windows ACL isolation or hardware power-loss durability. See
[compatibility](../contracts/compatibility.md) and
[executed validation](../core/m2-2-2-validation.md) for tested recovery boundaries.

## Historical M2.2.1 persistence procedure

M2.2.1 projection persistence follows
[ADR-013](../architecture/decisions/ADR-013-incremental-derived-index.md) and the
[mutation hardening design](../core/m2-2-1-mutation-hardening.md). The older
whole-database replacement boundaries below describe M2.1.1; the current procedure
and supersession are explicit in the following section. Its no-GC statement is
historical; the explicit M2.2.2 procedure above supersedes it.

## M2.2.1 bounded projection operation

Git remains canonical. Authentication format 3 stores uniquely named immutable
`history-<uuid>.sqlite3` bases, `delta-<sequence>.json` derived metadata deltas,
`checkpoint.json`, `checkpoint.key` and signed `enrollment.json` in the same
ref-scoped trusted directory. Runtime never opens mutable disk SQLite or WAL;
it authenticates exact base bytes and every accepted tail delta into private memory.
No agent filesystem interface or public operation discriminator is added.

Batched Git hashing briefly stages exact canonical bytes in the trusted Core
account's OS temporary directory. That directory needs the same agent isolation
as Git and the projection; do not use an agent-visible shared directory or vault.
Interrupted processes may leave unpublished temporary files. They are not
historical authority, and logical cleanup does not establish physical erasure.

The signed terminal checkpoint authenticates the complete base and exact accepted
tail sequence/hash, previous state and source Git generation. Removing a Membership,
receipt or key row in disk SQLite cannot change trusted private negative lookups;
restart rejects it. Missing, truncated, reordered or modified anchored deltas are
not interpreted as absent domain state. A partially written next delta is unaccepted
and may be replaced only after verified canonical catch-up under the writer lock.

An ordinary successful mutation writes only its captured fixed-table delta and
compact checkpoint after Git CAS. It never clones, serializes, hashes or rewrites
the complete projection. Warm reads still pin one verified generation and evaluate
current capabilities independently. Old immutable disk base/tail corruption does
not change already authenticated memory; detection occurs at restart, explicit
audit/rebuild or bounded access to the journal head. This supersedes the older
pre-write full-file hash timing, without permitting consumption or signing of
unsigned disk rows.

Other trusted writers' same-base advancements refresh only newly authenticated
deltas into the existing private connection. Replacing the base through explicit
compaction/rebuild causes a complete authenticated cold load. Do not pretty-print
or otherwise rewrite format-3 signed checkpoint/delta files: their canonical exact
bytes participate in the previous-state chain. Operator edits are rejected rather
than producing a subsequently unreplayable projection.

The hard online tail budgets are 1,024 projection advancements and 16 MiB encoded
deltas. Count capacity is checked early and exact candidate size before Git CAS.
Exhaustion fails with sanitized `REPAIR_REQUIRED`; trusted diagnostics identify
`INDEX_COMPACTION_REQUIRED` and recommend explicit compaction/rebuild. Exact receipt
replay may still complete without a new advancement. A large external catch-up
that exceeds the budget requires explicit full rebuild; no hidden full snapshot
is performed by reads or mutation.

```python
from second_brain_core import compact_history_index, rebuild_history_index

result = compact_history_index(core)  # Existing trusted bootstrap/recovery authority.
# result["status"] == "compacted" on success; canonical Git is untouched.
# Use explicit full rebuild when the index is damaged or catch-up exceeds capacity.
recovery = rebuild_history_index(core)
```

Compaction checks the accepted current Git/source fence, writes and flushes a new
immutable base, then atomically switches the signed checkpoint. Old referenced
bases are never overwritten. Crash before the switch retains the old base/tail;
crash afterward permits loading the complete new base. Old derived files are
retained rather than automatically removed; monitor disk space and preserve them
until operator-reviewed disposal. This milestone does not provide a cleanup engine.
Compaction/startup remain O(base bytes); restart replays at most the bounded tail.
Rebuild and full audit remain O(retained canonical history).

Existing format-1/2 instances require explicit trusted rebuild, which authenticates
the old signed binding/key and accepted Git commit fence before full verification
and format-3 publication. A mixed interrupted upgrade cannot authorize ordinary
reads; explicit rebuild may retry using the preserved authenticated fence and key.
Missing key/enrollment/checkpoint is never permission to reset trust or reenroll.
Backups must retain canonical Git ancestry and protected local trust material;
SQLite bases/deltas remain disposable with the anchor preserved. Physical flush
durability, backup coherence, Windows ACL isolation and privileged replacement of
all Git/key/anchor state remain outside the local process guarantees.

This is trusted-host guidance for the [M2.1.1 design](../core/m2-1-1-history-hardening.md),
not an agent filesystem interface. Runtime/test status is in the
[validation report](../core/m2-1-1-validation.md).

## Normal operation

Run one dedicated canonical Git instance with complete retained linear managed
ancestry. Do not shallow-clone, merge, reset, force-update, rewrite or graft its
managed history. Replacement objects are disabled; nonempty `info/grafts` is
rejected. Do not prune objects required for retained revisions, receipts, migration
evidence or audit. Uncommitted files are never domain state. Sharing canonical
history, keys or backing files across independent instances is unsupported.

Git is canonical. `history.sqlite3`, `checkpoint.json`, `checkpoint.key` and signed
`enrollment.json` live in a ref-scoped directory under Git's common directory.
Only the trusted Core process owns them. The code requests directory mode 0700 and
file mode 0600 where supported; Windows deployments must establish restrictive ACLs
and physical isolation separately. These files contain sensitive resource metadata.
Neither agent access nor production deployment isolation is established by Python
permissions or by an authenticated MCP transport alone.

Healthy warm queries use an authenticated private SQLite snapshot and load canonical
requested blobs from pinned Git. Every protected delivery evaluates current grants.
Denial-only current scope screens run before private blob/receipt/origin retrieval,
so unavailable hidden bytes do not change an unauthorized result from `NOT_FOUND`
to a corruption signal. Positive results still require canonical records and full
business authorization; index metadata cannot grant access.
Deleting or modifying the disk database cannot mutate that private snapshot. Such
disk damage is detected on restart, before publication or explicit maintenance;
it is not claimed to be continuously detected while serving already authenticated
metadata for an unchanged commit. Ref changes require verified catch-up before use.

## Explicit host interfaces

```python
from second_brain_core import audit_history, rebuild_history_index

report = audit_history(core)  # Full retained history; no canonical/index disk writes.
verification = audit_history(core, recommend_rebuild=False)  # Verify-only result.
result = rebuild_history_index(core)  # Explicit, source-fenced derived replacement.
```

The host supplies a verified `TrustedPrincipal` with its existing bootstrap/recovery
authority. Ordinary callers receive `FORBIDDEN` before private diagnostic work.
There is no `history.audit` public operation discriminator or agent maintenance
transport. Existing legacy migration remains separately explicit through
`inspect_history` / `apply_history_migration`; neither silently repairs committed
bytes or bypasses an enrolled rollback anchor.

Rebuild verifies complete canonical history, creates an isolated in-memory SQLite
database, writes a prepared file and atomically replaces derived files under the
existing writer lock after checking the exact source ref. It does not checkout or
overwrite a human vault, rewrite history or delete a known-good index before the
replacement is validated. The ref can still change through a noncooperating writer;
the final source fence then rejects the stale candidate.

## Diagnostics and actions

| Code/status | Meaning | Supported action |
|---|---|---|
| `INDEX_MISSING` | Projection file absent; canonical history may be intact | Explicit full rebuild using retained authenticated anchor |
| `INDEX_STALE` | Projection/source frontier does not match current publication | Verified catch-up or explicit rebuild; never serve it as the new head |
| `INDEX_CORRUPT` | Disposable database differs from authenticated bytes or cannot be decoded | Full canonical audit and explicit rebuild |
| `INDEX_IDENTITY_MISMATCH` | Instance, repository, ref, schema fingerprint or format mismatch | Check host configuration; operator-reviewed relocation/upgrade, no automatic adoption |
| `VERIFICATION_FAILED` | Key/checkpoint/enrollment trust cannot be established | Preserve files; operator recovery required, ordinary rebuild cannot replace a lost anchor |
| `MISSING_ANCESTOR` | Required commit/tree/blob is missing or retained continuity cannot be established | Restore complete canonical objects from a verified backup; do not invent bytes |
| `NONLINEAR_HISTORY` | Merge/graft or unsupported ancestry | Preserve evidence; operator review, no automatic reset/rebase |
| `AMBIGUOUS_ORIGIN` | Generation identity is reused/conflicting | Investigate canonical history; rebuilding an index cannot repair it |
| `INVALID_RECEIPT` | Retained request/receipt/effect binding changed or is unexplained | Canonical operator investigation |
| `MISSING_REVISION` / `REVISION_DIGEST_MISMATCH` | Required immutable evidence removed or altered | Restore verified original evidence; no read-time reconstruction |
| `MIGRATION_CONFLICT` | Canonical migration source/plan/additions disagree | Preserve source, inspect explicit migration evidence |
| `CANONICAL_STATE_CORRUPT` | Canonical structure or domain dependency validation failed | Operator investigation; SQLite replacement is insufficient |

Maintenance results contain stable codes, bounded generation/commit context and
recovery recommendations, not Git stderr or private filesystem paths. Ordinary
`CoreError` remains sanitized. A missing database differs from a missing key: the
former is disposable; the latter may destroy independent rollback continuity.

## Crash boundaries

Prepared Git objects are unpublished. A failed CAS has no domain effect. A published
Git transaction survives a failed index update; the index may lag and catch up from
its previous authenticated frontier. If database replacement succeeds but checkpoint
publication fails, the old signed anchor remains and the mismatched database is
rejected. Explicit rebuild verifies the descendant canonical history and recovers.
Interrupted first enrollment can be retried only using its retained authenticated
initial commit. Loss of complete enrollment/checkpoint/key material is not treated
as permission to enroll a new history silently.
An existing empty local-state directory is also rejected as `VERIFICATION_FAILED`,
including after a ref rollback. Preserve it and recover the protected anchor through
operator review; ordinary rebuild does not create replacement keys. The code does
not claim to detect privileged removal/replacement of the entire local trust state.
Bootstrap checks retained enrollment before publication too, so deleting the
managed ref cannot bypass this rejection and publish a replacement canonical root.

These are logical atomicity/recovery properties, not proof of power-loss durability,
filesystem flush ordering, hardware persistence or backup coherence.

## Backup and restore

Back up the managed ref and complete reachable Git object graph, including original
receipt/effect generations and migration origins. Preserve instance configuration,
current host credentials/policy sources and protected checkpoint/key/enrollment
material securely when continuity is required. SQLite backup is optional because
it can be rebuilt. A backup of only the current working tree is insufficient.

For a restored instance: keep it isolated, verify identity/configuration and retained
ancestry, run explicit full audit and rebuild the disposable index, then compare
authorized current reads and exact original receipts. A relocated repository has a
different bound path; it needs explicit operator-reviewed enrollment/recovery rather
than silently accepting copied local trust files. If starting from Git alone, full
verification establishes a new local anchor but cannot prove continuity against an
older lost external/local anchor. Report that limit.

The disposable regression clones real canonical Git into a separate backing path,
rebuilds without SQLite and checks equivalent readable knowledge and original
receipt identity. This establishes the exercised logical restore case, not a
production backup service or crash-durability guarantee. Missing historical effects
require operator restoration; current heads are not substitutes. A copied checkout
keeps the old instance identity and is not an independent Brain Instance. Explicit
export/import with remapping remains the cross-instance mechanism. Logical
tombstones do not prove physical erasure from Git objects or backups.
