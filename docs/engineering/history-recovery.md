# History operations and recovery

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
