# Architecture alternatives

Historical Phase 1 comparison. The [Phase 1.1 decision](phase-1-1/architecture-decision.md) recommends C with SQLite FTS5, a single committed Git ref and authenticated MCP-only agent ingress; Basic Memory remains optional future reuse. Its four-PoC prerequisite is superseded. Storage and approval defaults remain recommendations pending the stated Owner choices.

Status: analyst comparison, 2026-10-22. Confirmed requirements constrain every option; recommendation is conditional. Sources and confidence are in [reuse evidence](reuse-assessment.md); unresolved choices in [D01–D10](../domain/open-decisions.md).

## Shared use cases

| Case | Traceable contract and falsifier |
|---|---|
| U1 Human offline authoring | I04/I18; edit valid/invalid note while Core stopped; no lost bytes; P01/P04 |
| U2 Private edge to Shared Node | I07/I09; independent Relation revision, usable navigation, no Shared-side private backlink; P02 |
| U3 Two agents and non-discovery | I01–I03/I19; hidden direct/search/count/graph/history/FS denial; P03 |
| U4 Governed publication and revocation | I09–I11; private draft and approved snapshot coexist, exact approval/current policy; P04 |
| U5 Disposal/restore/retention | I12–I15; durable routing before expiry, source/destination copy permissions, current-rights recovery |
| U6 Atomic crash and index rebuild | I17/I20; all-or-none Core state, recover audit/outbox/receipts, discard/rebuild graph/search; P04 |
| U7 Logical organization and transfer | I06/I21; nested private Collections without Node copies; explicit snapshot remap/import |

## Options and authority

**A — Custom Markdown/Git knowledge foundation + custom governance.** Core owns file codec, reconciliation, immutable revisions, operations and policy enforcement, using established validators, SQLite FTS and possibly PyCasbin. Humans directly edit canonical working files as unmanaged input. This gives exact domain fit and avoids adapting platform IDs/edge conventions, but requires custom reconciliation, query mapping and most authoring integration work. Minimal dependencies do not make storage correctness cheap.

**B — Basic Memory bounded indexing component + custom governance.** Core retains sole authority for committed domain operations and canonical Git files. Basic Memory consumes a committed read-only mirror or permission-scoped projection; its DB/index is disposable. Its native read/search services may replace parser/watcher/index/MCP-adjacent effort, but all mutation tools/routes must be unreachable to untrusted clients and its process must lack canonical write permission. Core remains the public authenticated boundary and resolves source IDs/revisions before returning results. Project scoping is not proof of our ACL. Generated wiki writes require a separate projection root. This is a substantive reusable foundation, but integration must preserve standalone Relations and exact approved snapshots. A same-writable-vault setup is rejected as a governance boundary, not a rejection of Basic Memory as software.

For P01's AI-create/update workflow under B, AI submits to Core, Core commits, Basic Memory indexes. Native Basic Memory mutation is tested only on disposable fixtures to discover how it behaves; it is not the production authorization path. “Accepted content” indexing in current source is not synonymous with our Approval record.

**C — Obsidian-first vault + minimum Core governance + derived indexes.** Humans use existing editor, Properties, links/Bases/templates and optional Git diff UI. Core implements hard invariants, control/durability and reconciliation; it does not own an editor, context compiler or generalized memory platform. Start with native ordinary links, separately canonical Relations, native Collection link notes if P02 accepts, and a narrow governance command surface. FTS remains replaceable. Compared with A, C deliberately constrains the initial user-facing foundation to native Obsidian workflows rather than building a broad knowledge API/editor platform. A and C converge technically when A also chooses native authoring; they are product-scope alternatives, not incompatible storage technologies.

**D — Cognee/Graphiti sole canonical store.** Current source demonstrates useful derived semantic retrieval/temporal extraction, but no evidence establishes round-trip Git Markdown/Obsidian authority, standalone governed revisions, disposal or our transaction semantics. Serving as sole store would revise confirmed requirements; not recommended. Either remains optional external enrichment/retrieval behind Core, with source-revision provenance, authorized egress and revalidation. No LLM requirement may leak into Core.

| Concern | A | B | C |
|---|---|---|---|
| Canonical files | Core-managed Git Markdown/YAML, human raw input | Same Core authority; Basic Memory mirror/index only | Native human vault working files + Core validated Git commits |
| Write entry points | Core operations; raw human reconciler | Core only for managed commit; BM writes unavailable against canonical root | Human Obsidian authoring + Core operations/reconciler |
| Offline reconciliation U1 | Custom scan/CAS/byte preservation | Custom Core reconcile then mirror/index; BM watcher not policy authority | First-class Core reconciliation; native notes remain editable offline |
| Approved/shared U4 | Explicit immutable locators/materialization/selection | Core selection projected as approved bytes; no candidate substitution | Draft notes + separately materialized approved snapshots/status |
| Relations U2 | Native custom domain aggregate/index | Adapter must map independent edge IDs/owner/revisions; cannot trust BM note-edge graph as canonical | Relation notes/reified navigation first; narrow sidebar only if P02 fails |
| ACL U3 | Core all ingress + OS isolation | Core plus BM service/mirror/token isolation; no postfilter-only global ranking | Same Core/OS guards; human vault not scoped-agent surface |
| Rebuild U6 | Replay committed knowledge into FTS/graph | Drop BM DB and rebuild mirror-derived data; confirm no needed metadata exists only there | Drop indexes; regenerate views from Git/control selections |
| Failure/recovery U6 | Durable coordination still custom D02 | Core D02 plus mirror lag/generation mapping and BM process failure; BM cannot decide commit outcome | D02 plus native editor races; human view may transiently differ |
| Disposal U5 | Custom policy/routing/holds/history scope | Same custom governance; BM delete cannot substitute | Same; raw file deletion is pending reconciliation input |
| Collections/import U7 | Custom logical models/export remap | Custom models plus mapping; BM folders/projects not direct replacement | Native link navigation plus validated organization; import new IDs |
| Dependencies | Validators + Git + chosen SQLite/policy libraries | A dependencies + BM Python/web/index stack; AGPL review | Existing Obsidian + small Core dependencies; plugins optional |
| Cost avoided / added | Libraries avoid primitives; much domain/application work remains | Parser/watch/index/query surfaces avoided if source conventions fit; mapping/scope/recovery/version coupling added | Editor/diff/search/basic structured UI avoided; hard governance still custom |

## Equal-case fit score

Scores are analyst estimates, not benchmarks: 0 = conflicts, 1 = substantial unproven gap, 2 = feasible custom/adapter work, 3 = close native fit. No weighted total hides a mandatory requirement failure.

| Case | A | B | C | Reason |
|---|---|---|---|---|
| U1 offline authoring | 2 | 2 | 3 | All need validated ingestion; C gives it product priority |
| U2 independent typed edges/navigation | 2 | 1 | 2 | B's note-derived edges add mapping; C reified navigation untested |
| U3 ACL/non-discovery | 2 | 1 | 2 | No option inherits security from Markdown/MCP; B adds trusted surface |
| U4 approved snapshots/revoke | 2 | 1 | 2 | All custom selection; B must isolate candidate indexing |
| U5 disposal/retention | 2 | 2 | 2 | No evaluated platform replaces exact lifecycle |
| U6 crash/rebuild | 1 | 1 | 1 | D02 is an unproven architecture-wide gate |
| U7 organization/transfer | 2 | 1 | 2 | Native folders/projects do not encode domain membership |

B can outperform C on search/index breadth if P01 proves fewer adapter hours than maintaining a focused FTS pipeline, source mapping is lossless, and D08 clears. C can lose if native two-hop typed graph/navigation is unacceptable or protected approved display demands a complex custom client. A is justified over C when real consumers need a richer domain query surface that native authoring cannot supply; do not build it preemptively.

## Conditional recommendation and migration

Prototype C as the default human workflow and B as an indexing alternative against the same fixtures. Resolve D01/D02/D03 before production schema freeze. This chooses a small reversible surface, not a final engine winner. D is dropped as sole authority because no inspected evidence overcomes the explicit source requirements.

Keep IDs, canonical file conventions, operation semantics and snapshot manifests independent of any index. C→B adds a scoped mirror/project mapping and rebuild; B→C discards BM index after proving no canonical metadata exists only in BM. A↔C changes authoring/integration scope while retaining contracts. For all transitions, stop writes, capture coherent Git/control/runtime backup, validate ID/revision mapping and replay fixtures, rebuild index, compare authorized query results, then resume. Rollback restores matching code/config/state; do not merely checkout old code after new writes.

Moving to a database-canonical D would require an explicit new Owner decision, lossless export/round-trip offline-authoring proof and a separately approved migration. No performance or maintenance advantage is asserted without measurements.
