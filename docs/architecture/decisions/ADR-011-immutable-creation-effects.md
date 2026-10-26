# ADR-011: Retained original generations bind creation effects

Status: adopted for the Owner's M2.1 immutable-history foundation after independent
Stage A design review. Unreleased baseline 1.0.0. Date: 2026-10-26.

## Decision

A receipt's exact GenerationRef locates one original publication in complete linear
managed Git ancestry. Verify the original generation's canonical bytes and exact
receipt/request pair, original parent generation, newly introduced resource/revision
identities and original admission. Current resource heads are not historical proof;
current authorization is independently checked before receipt replay.

New Node/Relation creation persists complete immutable revision-1 snapshots in the
same managed-ref transaction as heads, admission, request and receipt. Original
Membership bytes and Relation owner/endpoints remain available in that creation
tree. No duplicate admission/event-sourcing ledger is added.

Explicit trusted-host backfill preserves metadata-only NodeRevision bytes and adds
NodeRevisionSnapshot evidence, recovers absent RelationRevision under its existing
receipt UUID, and publishes a canonical HistoryBaseline. Its exact plan, source
generation/parent commit, added paths, effects digest and resulting generation are
verified against its publication. Fresh bootstrap also establishes a baseline;
retained markers prevent missing fresh evidence from becoming implicit legacy.

## Consequences

Logical revision UUID, resource UUID, generation and physical Git hash stay distinct.
No tree contains its own final commit hash. Managed first-parent ancestry and all
referenced objects must be retained in backups too. Missing/shallow/nonlinear or
ambiguous origins fail closed; no read repair, rewrite or working-tree evidence.
Recreating entirely forged trusted history is outside unsigned local integrity.

Retained commit lookup avoids a duplicate complete effect ledger. The narrow legacy
snapshot supplement materializes historical content without changing original
revision records. A universal migration framework, parallel graph snapshot or
mutable update handler is unnecessary and not implemented here.

This does not choose O1–O4 or establish physical flush/power-loss durability.
See [M2.1 design and migration](../../core/m2-1-immutable-history.md),
[compatibility](../../contracts/compatibility.md) and
[validation](../../core/m2-1-validation.md).
