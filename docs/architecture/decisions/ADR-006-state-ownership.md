# ADR-006: Separate canonical, desired, execution and derived state

Supersession notice: [ADR-009](ADR-009-phase-1-domain-baseline.md), [Core M1](../../core/m1.md) and [M1.2 decisions](../../domain/accepted-decisions.md) replace embedded-Relation and separate durable journal requirements with independent Relations and one managed Git-ref publication boundary. Original text is retained as historical evidence, not a competing current authority.

Status: separation task-mandated; transaction and backend details proposed pending M3. Date: 2026-10-20.

## Context

The vault says Markdown and explicit relations are authoritative. Graph queries and resumable jobs need different persistence/recovery guarantees. Git cannot atomically commit filesystem and SQLite changes by itself.

## Decision

Keep managed Markdown/YAML knowledge, embedded relations and manifests canonical. Keep desired policy/config separate from runtime runs/attempts/checkpoints. Indexes/caches are rebuildable. Temporary sessions expire independently. Propose SQLite for execution/audit coordination and separately disposable graph indexes, a single managed writer and a durable staged commit journal. Do not claim this recovery protocol proven before crash/locking tests. No Global State object and no mandatory event sourcing. The hardening review additionally recommends an approved-revision Stable pointer alongside an editable candidate (see ../stable-revisions.md); this is a new proposal, not implemented revision storage. Referenced historic Git bytes remain canonical and recoverable, current policy applies to historical reads, and pointer updates need optimistic concurrency and approval. Q03/Q04 remain review gates.

## Alternatives

A canonical graph database would conflict with current file authority without explicit migration. A single mutable global store blurs ownership. Pure Git/file writes lack execution fencing and coordinated audit/idempotency recovery. Full event sourcing adds replay/migration obligations without a demonstrated requirement.

## Consequences

Rebuilding an index cannot restore lost runs or audit; backups must distinguish them. External editor changes require reconciliation. Readers must not serve prepared writes after a crash. Multi-aggregate operations require explicit staged semantics. SQLite is not a hidden second authority for node content.

## Reversibility

Derived stores are replaceable by rebuild. Execution-store migration needs preserved run/idempotency/audit semantics. Changing canonical authority requires a new ADR and explicit migration. Q04 determines whether proposed local recovery is viable.
