# Implementation roadmap after M1.2

These are dependency targets, not delivery dates or authorization to implement every operation. [Per-capability deferrals](../contracts/contract-gaps.md) supply exact prerequisites, activation criteria and compatibility risks. The [coverage matrix](../contracts/contract-coverage-matrix.md) is the implementation inventory.

| Milestone | Scope | Required dependency / activation |
|---|---|---|
| M1 / M1.1 | Private single-membership Node/Relation create/read; atomic Git CAS; contract/generation/distribution quality | Existing tests establish fabricated local cases, not real deployment guarantees |
| M1.2 | Reconciled semantic authority, exhaustive coverage, explicit resource identity, immutable structural revision snapshots | Independent review plus existing deterministic gates; this is not full runtime domain completion |
| M2 — Mutable Revisions | Node/Relation updates, independent CAS, immutable content, authorized revision reads | Full NodeRevision.snapshot and RelationRevision.snapshot persisted; original create effect/admission bytes retained; explicit legacy backfill from original commit trees; receipt verification against original immutable effects, current replay rights; test later update/retirement/restart/history non-discovery before enabling handlers |
| M3 — Human Authoring & Reconciliation | Offline candidates/import/conflict preservation and coordinated refresh | M2 plus O1; preserve exact raw invalid/conflicting bytes and reject stale raw/base hashes |
| M4 — Authorization & MCP | Authenticated agents, principal/grant administration, current-policy resource scopes | M2 selections, registered capability semantics and physical isolation; O4 before multi-membership composition; no raw canonical filesystem ingress |
| M5 — Query, Collections & Graph | Collection hierarchy, SQLite FTS5, graph traversal/search, index rebuild | M2 independent Relations, M4 authorization before ranking/count/cursor, pinned generation, agreed hierarchy structural rules |
| M6 — Governance & Publication | Exact Proposal/Review/Approval/revocation, copy/fork/publication/selected revisions | M2 immutable evidence, M4 authority, O2 for Relation assertion approval and O3 for already-selected revocation effects |
| M7 — Lifecycle & Disposal | Archive/pending disposal/Trash/Global Archive/restore and separately reviewed purge/expiry | Current authority, durable preservation, M6 publication, Owner O3 and exact erasure scope |
| M8 — Portability & Services | Export/import ID remap, external Review intake, scoped event delivery/status/maintenance | Stable versioned bundle/API shapes, closure checks and source/destination policy; no distributed transactions |

## Next bounded M2 slice

First persist immutable revision snapshots and exact original creation/admission effect evidence without changing heads. Canonically validate the snapshots, digest and identity/version correspondence. Backfill legacy metadata-only Node revisions and missing Relation history from their original managed committed generations by an explicit recoverable migration; never synthesize bytes from a newer head or mutate records on read. Pin a durable locator/retention rule for every original receipt effect. Only then change verification to resolve those immutable effects while separately rechecking current policy. Add Node update as its own reviewed slice; Relation update follows with independent CAS and exact endpoint checks. Selected approved graph breadth remains O2; multi-membership serving remains O4. No full-graph snapshot engine is required.

The single managed Git ref remains the domain publication boundary. Physical durability, hosted platform behavior, real OS agent isolation and backup retention remain separate operational verification requirements.
