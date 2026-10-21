# Decision provenance register

Recorded 2026-10-21. “Confirmed” records the supplied Owner brief, not an inference from product features. Analyst defaults are reviewable and unapproved. External evidence never overrides Owner constraints.

| IDs | Provenance | Contract / decision |
|---|---|---|
| C01 | Owner brief §2.1 | Passive deterministic Core; external harness context/AI/fetch/scheduling; isolated instances; Git Markdown/YAML; JSON Schema/generated Python/TS; optional transports |
| C02 | Owner §2.2 | Authenticated Owner; granular capabilities; per-Cluster policies; every-ingress enforcement; non-discovery; filesystem bypass explicitly acknowledged |
| C03 | Owner §2.3 | Node/type/Revision; Cluster not folder; Shared not multi-membership; Orchestrator/Membership Service; private single-Cluster Collections; independent owner-scoped Relations; Git Assets; passive references |
| C04 | Owner §2.4 | Hybrid creation; policy direct/governed updates; immutable approved selections; distinct archive/disposal/Trash/Global Archive/purge; source AND destination publication checks; exact Proposal/Review/Approval; validity; atomic batches; export/import remap |
| C05 | Owner §2.5 | Native offline Obsidian authoring; usable graph/navigation/Properties/Collections; preserve invalid edits; protected raw files remain trust concern |
| C06 | Owner §0/§8/§10 | Documentation/evidence only; narrow PoCs proposed, never built; preserve illustrative toolchain and tests |
| O01 | Observed local commit b835974 | Embedded edges, Core Context module, eight ADRs and illustrative code/tests; exact divergences R01–R20 |
| T01 | Upstream source evidence, dated [research](../research/reuse-assessment.md) | Candidate implementation, dependency/license/release signals; partial source tracing is not security certification |
| P01 | Analyst recommendation | Option C as provisional authoring foundation; Option A shares domain invariants; B retained as genuine indexing alternative if P01/D08 pass |
| P02 | Analyst, D01–D10 | Single writer/journal backend candidate, snapshot publication identity, graph snapshot, reified Relation Markdown, conservative revocation behavior, bounded create admission delegation |
| P03 | Analyst catalogue | Operation/capability/event names, audit detail, proposed direct/governed defaults; no executable DSL or production fields approved |

Traceability: C01→I01/I17/I20/I21; C02→I01/I02/I03/I19; C03→I04–I09/I15/I16; C04→I04–I18/I21; C05→I06/I07/I18/I19. See [invariants](../domain/domain-model.md), [catalogue](../domain/operations-catalog.md) and [open decisions](../domain/open-decisions.md). P01–P03 must not be relabeled accepted without a later recorded Owner decision.
