# Phase 1 domain and reuse assessment

Prepared 2026-10-21–22 against local commit `b835974491890e7bad8a2193643f5217686e5cdf`. Documentation/evidence phase only. No runtime, production schemas, dependencies, databases, migrations or plugins were implemented. Candidate projects were inspected remotely, not executed.

## Executive finding

Provisional recommendation: **Obsidian-first authoring with a minimum passive governance Core**, retaining Basic Memory as a serious bounded indexing alternative. Existing editors, file formats, Git UI, schema validators/generators and lexical search primitives can avoid substantial bespoke work. No inspected tool establishes the exact cluster/membership/publication/disposal/recovery semantics required here. A platform's tags, project scopes or MCP surface do not replace these contracts.

The architecture has three critical falsifiers: usable standalone Relation navigation without two canonical graphs; genuine agent isolation without raw vault/history access; and all-or-none domain commits/recovery despite external editor races. Approved Node snapshots alone do not freeze independently revised Relations: approved graph selection needs an explicit decision. Recommendation remains conditional on those results, not a mandate to implement a custom engine.

## Review map

| Artifact | Purpose |
|---|---|
| [Glossary](../domain/glossary.md) | Precise identities, authority, persistence and normalized aliases |
| [Domain model](../domain/domain-model.md) | Aggregate ownership, independent state axes, I01–I21 and brief §2 coverage |
| [Operation catalogue](../domain/operations-catalog.md) | Explicit operations/capabilities, direct/governed modes, guards/CAS/events/errors/audit/Obsidian impact |
| [Reuse assessment](reuse-assessment.md) | All requested candidates, ten-dimension scored evidence, code savings versus adapter cost |
| [Upstream evidence ledger](upstream-evidence.md) | Source commit/release distinction, file hashes, links, relevant issue sample and retrieval limits |
| [Obsidian assessment](obsidian-integration-assessment.md) | Concrete notes/workflows, editable typed Relations, Collections, protected/offline behavior and Experience Gap |
| [Architecture options](architecture-options.md) | A/B/C and canonical-store D against shared U1–U7 cases, failure/recovery and migrations |
| [PoC plan](poc-plan.md) | Four proposed reproducible, bounded falsification experiments; no PoC run |
| [Reconciliation register](../architecture/reconciliation-register.md) | R01–R20 exact historical conflicts, migration consequences and amendments |
| [Decision provenance](../architecture/decision-provenance.md) | Owner-confirmed versus observed, tool-evidenced and analyst-proposed decisions |
| [Open decisions](../domain/open-decisions.md) | Only material unresolved choices, defaults/risks/evidence/milestone gates |
| [ADR-009](../architecture/decisions/ADR-009-phase-1-domain-baseline.md) | Explicit partial supersession of embedded Relation ownership and Core scope correction |

## Proposed Phase 2 sequence

1. Review D01 trust boundary, D02 durability/transaction authority and D03 approved graph semantics. Confirm D04 publication identity, D05 revocation effects, D06 retention and D07 human navigation before corresponding production contracts. D08 gates Basic Memory adoption; D09 gates published schema namespace/operation names; D10 gates policy composition/applicability across memberships and hierarchy.
2. Run P02 native Relation/Collection experiment early; run P03 ACL/OS isolation before real agents; run P04 crash/reconciliation before production storage. Compare P01 Basic Memory indexing to focused FTS using the same canonical fixtures and actual adapter effort. Proposed harness commands are specifications, not runnable repository tools.
3. Select the smallest proven foundation. Review a minimal production contract slice: Node, standalone Relation, Cluster/Membership, exact Proposal/Review/Approval, Revision/snapshot and transaction/error primitives. Preserve current illustrative fixtures and toolchain; introduce production schemas through explicit new version/review, not an in-place example rewrite.
4. Implement safe authenticated read/create/update/reconciliation and atomic commit/receipt boundary, then governed selection/publication. Add Collections, Asset budgets/references, passive check intake and durable disposal/restore only with their negative-policy/retention tests. Build a narrow CLI first; add MCP for a concrete consumer. Context compilation remains external.
5. Revisit semantic/temporal retrieval and remote services only after a measured unmet need. No generic workflow engine, universal plugin loader or custom editor/Git UI belongs in this plan.

## Reuse priority

**Reuse now:** existing contract stack and native Obsidian authoring/view/Git-diff surfaces. **Prototype first:** typed Relation notes, Core/OS policy boundary with PyCasbin candidate, durable batches/reconciliation and Basic Memory bounded index. **Custom build after gates:** exact domain guards, membership/governance/approved selection/disposal/recovery. **Defer:** Cognee/Graphiti semantic adapters, OpenFGA service, Mem0 harness memory, SilverBullet alternative and remote transports. **Drop from Core:** agent planning/context/workflow runtime, sole canonical semantic database and redundant editor/Git infrastructure.

## Validation and review gates

Local Windows validation passed: 60 pytest tests; example schema/ref/fixture/OpenAPI/document-link validation; strict TypeScript typecheck; all 24 Python/Ajv parity cases; all five generated artifacts match with no extra files; Ruff lint and format checks. Generator emitted its existing Black/isort future-dependency warning, with no drift or failure. Hosted CI/all-OS success cannot be claimed from this workspace. Existing tests verify illustrative contracts only; they do not prove proposed domain/runtime/Obsidian/ACL behavior.

Evidence limitations: source tracing is partial; API rate limits prevented immutable pins for three projects and some release/source mapping remains unresolved; no tool benchmark, live Obsidian test, adversarial deployment test, crash experiment or legal conclusion is claimed. These are explicit next-phase adoption gates, not silently assumed capabilities.
