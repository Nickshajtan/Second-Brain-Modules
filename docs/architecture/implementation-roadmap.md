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

## M2.1 foundation and next bounded slice

M2.1 implements immutable creation snapshots, exact original creation/admission
resolution from retained managed ancestry, explicit legacy inventory/backfill and
durable migration evidence. No update/history handler is enabled. See the
[design and host procedure](../core/m2-1-immutable-history.md).

M2.2 is Node mutation: require a completed history baseline, immutable new revisions,
independent CAS and authorized history delivery with non-disclosure. M2.3 follows
with independently versioned Relation mutation and endpoint authorization. Current
M2.1 future-head fixtures validate unchanged original receipt meaning without
exposing mutation handlers or relaxing the create-only public profile. Selected
Relation approval breadth remains O2; multi-membership serving remains O4.

M2.1.1 is the blocking operational foundation before M2.2: authenticated disposable
SQLite locators, ordered incremental verification, bounded committed reads/replay,
explicit full audit/rebuild and recovery. See [design](../core/m2-1-1-history-hardening.md),
[measured performance](../engineering/history-performance.md) and
[validation/readiness](../core/m2-1-1-validation.md). A passing functional suite
alone does not open M2.2; the full benchmark matrix and independent final review
must also pass. SearchIndex/FTS5 and external maintenance protocols remain M5/M8.

M2.1.1's reviewed runtime passed the full quality gate, all 60 benchmark rows and
the additional bounded-create structural regression. Its
[readiness decision and limits](../core/m2-1-1-validation.md) allow the separate
M2.2 development slice; no Node/Relation mutation handler is enabled by M2.1.1.

The single managed Git ref remains the domain publication boundary. Physical durability, hosted platform behavior, real OS agent isolation and backup retention remain separate operational verification requirements.
