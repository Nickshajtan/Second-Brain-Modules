# Second Brain — Phase 1: Domain Contract Baseline, Repository Reconciliation & Reuse Assessment

**Status:** research/design specification for Codex; **not** authorization to implement the runtime.
**Repository:** https://github.com/Nickshajtan/Second-Brain-Modules
**Language of deliverables:** English for normative schemas/technical docs (Ukrainian explanations acceptable); preserve consistent terminology.
**Date:** 2026-10-22

## 0. Mission

Before building a custom Second Brain runtime, rigorously establish **what we actually need to build**. Read the existing repository and its ADRs, consolidate the agreed domain semantics below into a coherent, versionable contract catalogue and glossary, investigate reusable OSS tools with source-level evidence, and assess whether Obsidian can remain a genuinely first-class authoring environment.

This is an **architecture and evidence phase**. The output is a reviewable set of Markdown documents, decision records, a gap/contradiction register and narrow PoC proposals. Do not implement business services, expand illustrative schemas into production schemas, add databases, install dependencies or build speculative plugin infrastructure in this phase.

### Questions this phase must answer

1. Which business concepts and operations are genuinely necessary, and what are their invariants and authority boundaries?
2. What do the existing repository docs already specify, where do they conflict with the current decisions, and what must be amended/deprecated?
3. Which OSS libraries or platforms can replace a planned subsystem **without violating domain semantics**?
4. How much of the *human authoring workflow* can stay native to Obsidian? Where would adapters/projections/custom plugins be genuinely required?
5. What minimal experiments would *falsify* our preferred architecture before we commit implementation effort?

## 1. Current repository: inspect first, do not assume

Read at minimum:

- `docs/architecture/contracts-spec.md`
- `docs/architecture/integration-protocols-spec.md`
- `docs/architecture/contract-toolchain-spec.md`
- `docs/architecture/monorepo-architecture.md`
- `docs/architecture/stable-revisions.md`
- `docs/architecture/open-questions.md`
- `docs/architecture/phase-2-plan.md`
- `docs/architecture/decisions/` (all ADRs)
- `docs/architecture/examples/` plus relevant contract tests and toolchain.

**Known drift to investigate:** the previously fetched `contracts-spec.md` describes **embedded Relations** inside Node and `monorepo-architecture.md` includes a **Context** module. The latest domain decisions require **canonical standalone Relations** and **context assembly outside Core, in the agent harness**. Other old assumptions may similarly have been superseded. Record the exact file/section, old assumption, new decision, migration consequence and recommended amendment. Do not silently harmonize contradictions.

Existing JSON Schema 2020-12 resources under `examples/` are illustrative, not production domain authority. The repository already has generated Python/TS examples, cross-runtime fixtures and CI; preserve this toolchain unless evidence warrants change.

## 2. Normative architectural boundaries (agreed)

### 2.1 Core and execution

- **Second Brain Core is passive**: a deterministic, authorized **knowledge and state store**, not an AI agent, self-directed planner or generic workflow engine. It can react deterministically to explicit operations/events.
- Agent orchestration, prompt/context compilation, tokenizer limits, summarization, content evaluation, web fetching and scheduled content refresh belong to external **harnesses/services**.
- Core offers query/search, read/write, graph, governance, state and event contracts. Search can use optional semantic adapters, but Core does not require an LLM.
- One reusable modular-monolith codebase serves multiple **fully isolated Brain Instances**, each with its own identity, data, Git history, policy, runtime state, credentials and cache. Shared code may be consumed as a pinned monorepo submodule. No mandatory microservices or universal plugin loader.
- Canonical managed knowledge: **Git-versioned Markdown + constrained YAML frontmatter**. Derived indexes (e.g. SQLite) are rebuildable. Runtime journal/audit/control records require explicit authority and durability decisions; do not pretend every kind of state naturally fits inside Markdown.
- Domain structural schemas: JSON Schema Draft 2020-12, with generated Python/Pydantic and TypeScript. Transport adapters (CLI, Python, MCP, optional HTTP) do not determine domain semantics.

### 2.2 Identity, rights and policy

- **Instance Owner** is a super-administrative human authority for their instance: full supported admin operations and visibility, including recovery pathways, while still subject to data-integrity invariants and audit. Identity must be authenticated, not caller-asserted.
- Principals: human, agent, service; separate content editing, structural organization, membership, approval, publication, purge and administrative capabilities. **Full CRUD never implicitly grants purge, publication or membership management**.
- Capabilities form a granular, partially ordered set of resource/action/condition permissions, not a simple role ladder. Policies bind to **individual clusters**; avoid a globally fixed Stable permission ladder.
- Authorization is enforced by Core on **every ingress**, including direct calls and reads through search/graph/history. Resource existence is not disclosed to unauthorized agents: not names, counts, paths, hidden edges or search hit counts; unauthorized direct access looks like `NOT_FOUND` where appropriate. Optional `access.request` can ask for broader scope without discovering protected resources; grants are separate privileged decisions, possibly time/scope/session limited.
- Process/OS permissions matter: an agent with raw vault access can bypass application ACL. Do not claim vault-based multi-agent isolation without OS sandbox/account separation or scoped projections.

### 2.3 Knowledge structure

- **Node** = logical knowledge unit with stable ID, Markdown body, flat Obsidian-friendly YAML Properties, registered extensible node type, provenance, revisions, lifecycle and optional validity dates. Instance-defined type schemas may add metadata constraints. Avoid deep nested YAML as the default editing format.
- **Cluster** = policy/ownership/knowledge scope, **not** a filesystem folder. Shared is an explicit publication/governance mode, **not a synonym for multi-cluster membership**.
- **Membership** = an authorized assignment of Node to Cluster; a Node may appear in multiple clusters. A normal agent may neither mutate/retire a multi-cluster protected Node nor mutate an already published Shared Node even if they can read it. Higher authority can perform governed actions. Publishing/forking offers alternate paths; no privilege escalation via detach.
- **Membership Orchestrator** = one logical membership-changing authority per instance, plus authorized human administrative authority. It need not be a constantly running process or an AI agent. Core Membership Service verifies and commits membership operations.
- **Collection** = possibly nested private organization **inside exactly one cluster**; not a policy boundary, not cross-cluster shared. Structural rights separate from content rights. A collection may retain a local reference to a Node that becomes shared/protected without making the collection shared.
- **Relation** = first-class, independently Git-versioned typed directed edge with stable ID, provenance and **one owner cluster**, pointing to Node endpoints that can belong to other clusters. Its mutation does **not** increment Node revision. Relation creation requires permitted access to endpoints, reading requires access to relation and both endpoints, and links never grant access. Instance-extensible predicate registry with minimal built-ins and rules; no mandatory comprehensive ontology. Graph index is derived.
- **Asset** = managed attachment with stable ID, media type, checksum, provenance, policy and references from Nodes; multiple Nodes can use one Asset; Node deletion does not blindly delete Assets. Initial **only provider is Git** with configurable size/budget limits, enforced before commit. Keep a narrow future storage-provider interface, not a full plugin ecosystem.
- **External Reference** = passive locator to material outside the managed store, distinct from an Asset, with optional checksum/last-check metadata; scheduled fetching, monitoring, extraction and caching are external services.
- **Revision** = immutable historical content state, distinct from a lifecycle flag and temporal validity. Stable/shared cluster policies may point to specific approved immutable revisions while separate candidates evolve. History access (`node.history.read`) is a distinct capability; current `node.read` does not imply historical access.

### 2.4 Mutation and knowledge lifecycle

- Node creation: **hybrid** — directly into an authorized target cluster (creation-specific membership admission) or into an isolated, owned staging scope for later authorized allocation; no ownerless/ACL-less orphan nodes. Clarify how admission-on-create coexists with exclusive membership-management authority.
- Node update: **cluster-policy-driven** direct versioned CAS update or proposal/review/approval/promotion. Every committed content change yields a revision; approved immutable revisions remain addressable.
- `node.archive`: hide from regular active results but preserve in its current cluster, still accessible through explicit archival queries.
- `node.delete`: agent can relinquish an editable owned Node without `purge`; route it to **pending disposal**, after which an external Cleanup Service decides what belongs in **System Trash** vs **private Global Archive**, potentially by producing an authorized archival copy. The service is not allowed to widen disclosure just by copying; source and destination policies must both permit it.
- System Trash: isolated system storage for recoverable deletion with original ownership/membership metadata, retention, restore, scheduled expiry and policy-scoped `trash.expire`; not just another accessible shared cluster. Cleanup cron cannot arbitrarily `node.purge`; no purge until routing/required preservation is durable. Recover under **current** policy, never resurrect expired rights.
- Private **Global Archive**: a long-term, non-shared cluster for potentially valuable discarded knowledge, awaiting human/service curation and optional later publication; distinct from `node.archive`, System Trash and Shared Knowledge. Ordinary agents have no automatic access.
- `node.purge` requires an **independent privileged capability** even when content CRUD is unrestricted. Distinguish physical deletion from Git historical retention/backup/privacy erasure; never promise irrevocable deletion without an explicit retention/Git-history policy.
- Shared or multi-cluster protected Nodes cannot be deleted or archived by an ordinary agent. Removing a Collection entry, detaching membership and deleting a Node are separate operations.
- Private → Shared publication is policy-governed and may create an immutable **publication snapshot** rather than remove/edit the originating private Node. Shared → private `copy` or `fork` yields distinct ID and provenance. Plain prompt transmission may occur externally, but does not establish structured provenance.
- Source disclosure AND destination admission must be authorized; **publication policy is per destination cluster**, potentially direct for trusted services or governed for sensitive clusters.
- `Proposal` specifies an exact intended operation, its target, parameters and expected revisions; `Review` is a typed conclusion (`freshness`, `publication`, `quality`, `disposal`, etc.) tied to immutable target revision; `Approval` authorizes **one specific Proposal**, not content in the abstract. Review ≠ Approval. Approval immutable in history but revocable with privileged `approval.revoke`; revocation effects are cluster-policy-specific. Revalidate all guards at commit.
- Direct operations do **not** require Proposal by default. Governed operations use `Proposal → Review (optional) → Approval → Validate → Commit`.
- Optional Node validity metadata: `valid_from`, `valid_until`; `supersedes`/`superseded_by` should be modeled as a typed Relation, **not duplicated frontmatter truth**. Freshness is checked by external scheduled service; it may emit independent Review Records without revising a Node that remains current.
- Batch domain operations in one instance should be atomic: all-or-none, with CAS, idempotency semantics, crash/restart recovery and documented limitations on Obsidian's concurrent raw file edits. No cross-instance distributed transactions or transactions with external services.
- Cross-instance movement is explicitly `export snapshot → validate/remap/review → import as new local IDs with provenance`. No implicit sharing by symlink/junction; external references are not membership.

### 2.5 Obsidian is a first-class authoring interface

- Humans can create/edit Markdown and Properties **directly in Obsidian**, including while Core is offline. On startup/file change, reconcile modified filesystem content through Core validation; **do not silently discard invalid human edits**.
- Obsidian must be genuinely useful for browsing, search, internal links, backlinks, graph, properties, collections and reviewing knowledge — not merely a read-only projection.
- Separate Relations YAML may not appear in native Obsidian Graph View, which is built from note links. Treat this as a **critical design risk**; evaluate link-authority rules or a narrow adapter/projection, not two unsynchronized canonical graphs.
- Collections are logical; a Node cannot physically live in multiple directories simultaneously. Test whether Obsidian-native folders/Bases or a small adapter offers a usable experience.
- Human raw vault editing is **trusted/unmanaged input** until validated/committed; file-system writes cannot magically become atomic governed transactions. Describe policy for protected files and offline edits.

## 3. Required glossary (`docs/domain/glossary.md`)

Create precise definitions with identity, authority, persisted source and distinction from adjacent terms. Include at least:

- Brain Instance / Workspace / Knowledge Vault / Principal / Instance Owner / Agent / Service
- Capability / Grant / Policy / Capability Profile / Ownership / Authority / Scope
- Cluster / Membership / Membership Orchestrator / Collection
- Node / Node Type / Revision / Candidate Revision / Approved Revision / Publication Snapshot / Shared Node / Multi-cluster Node
- Relation / Predicate Type / Asset / External Reference / Source / Provenance
- Lifecycle / Archive State / Pending Disposal / Trash / Global Archive / Retention / Purge / Restore
- Proposal / Review / Approval / Revocation / Direct Operation / Governed Operation
- Query / Retrieval Adapter / Derived Index / Agent Harness / Context Bundle (explicitly **outside Core**)
- Transaction / Idempotency Key / Event / Outbox / Snapshot / Export Bundle / Import Mapping / Reconciliation.

Normalize aliases (workspace vs instance, archive meanings, delete vs trash, relation vs wikilink). Mark uncertain definitions as **OPEN**, not invented final decisions.

## 4. Required domain-operation inventory

Build an operation catalogue organized by aggregate and without inventing a generic workflow language. For each operation specify:

`name | actor/capability | resource scope | direct/governed policy | request/result outline | validation/invariants | expected revision/CAS | emitted events | errors/idempotency | audit | Obsidian impact`

Cover at minimum:

- Node: create, read, list/search, update, propose_revision, archive/unarchive, delete/request_disposal, restore, privileged purge, copy, fork, publish, revision/history reads.
- Cluster: create/configure/list/read, policy changes, ownership and closure; clarify protections around existing revisions.
- Membership: attach/detach, admission-on-create, approved revision selection/promotion (Membership Service as commit authority).
- Collection: create/rename/reparent/remove, add/remove Node reference; hierarchical permissions without redefining membership.
- Relation: create/read/update/retire/query/traverse, dangling-link handling, predicate registration.
- Asset: add/read/reference/unreference, policy-scoped garbage collection, size checks.
- ExternalReference: create/read/update/check-result intake, no automatic network side effects.
- Governance: grant/revoke/list effective permissions, `access.request`, Proposal, Review, Approval, revoke, publication.
- Disposal: route, preserve by authorized copy, trash expiry, restore, purge and retention policy.
- Cross-instance: export/import with ID remapping, provenance and explicit snapshot scope.
- Maintenance: reconciliation, rebuild derived indexes, publish domain events, ingest externally produced freshness checks.
- Atomic batch submission: prevalidation/commit/recovery; ensure nested operations and approval references are coherent.

Distinguish **confirmed business rules**, **proposed defaults**, **open questions**, **non-goals**. Do not conflate capabilities to read a Node with capabilities to enumerate its entire cluster or history.

## 5. Reuse / build-vs-buy assessment

Research and inspect **current upstream docs, licenses, releases, dependency boundaries, source implementations and relevant open issues**; date and link citations in the report. Do not mark a feature supported based solely on marketing or README wording. Candidates to assess:

| Candidate | Why it matters | Questions to investigate |
|---|---|---|
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | Markdown-first knowledge graph, file watcher, MCP, indexing, Obsidian workflow | Native wikilinks/provenance, schema support, search, revisions, one-vault-vs-many security, extensibility, license **AGPL-3.0**, embeddability vs standalone service |
| [Cognee](https://github.com/topoteretes/cognee) | Graph ingestion/retrieval, ACL/datasets | Actual authorization of all retrieval paths, storage authority, ingestion side effects, operational cost and API suitability |
| [Graphiti](https://github.com/getzep/graphiti) | Temporal semantic graph and provenance | Can it remain **derived** from our canonical Node/Relation graph? Deployment/database costs, update semantics |
| [Mem0](https://github.com/mem0ai/mem0) | Agent memory | Does it offer anything required beyond optional memory/retrieval adapters? |
| [Letta](https://github.com/letta-ai/letta) | Stateful agent memory | Is it intrinsically an agent runtime, violating passive Core separation? |
| [Casbin](https://github.com/casbin/casbin) and Python ecosystem | Authorization evaluator | ABAC/conditions, deny-by-default, cluster-scoped grants, visibility filtering, multi-resource predicates, policy-test ergonomics |
| [OpenFGA](https://github.com/openfga/openfga) | Relationship-based authorization | Is a separate auth service and relationship-store justified for local-first monorepo? |
| [Obsidian](https://obsidian.md/) + [Obsidian Git](https://github.com/Vinzent03/obsidian-git), [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api), official Properties/Bases | Authoring, history, structured views, integrations | Native support boundaries; security implications; avoid implementing redundant editor/Git/MCP features |
| [SilverBullet](https://github.com/silverbulletmd/silverbullet) | Programmable Markdown alternative | Better/worse fit than Obsidian for typed relations and external APIs; vendor/platform trade-offs |

Feel free to add genuinely relevant projects: e.g. search/FTS engines, Markdown parsers/frontmatter validators, transaction/outbox libraries, Git libraries, Obsidian graph plugins, SQLite virtual tables. Only add candidates that might replace a **specific planned responsibility**.

For every serious candidate deliver **evidence-based scores**, with `verified / partially verified / unsupported / unknown` and links or source-file pointers for:

1. Feature coverage vs our domain operations; 2. canonical data ownership and portability; 3. Obsidian authoring compatibility; 4. ACL/security isolation; 5. integration surface, maintenance and developer effort; 6. resource/runtime footprint; 7. license and redistribution risk (flag for legal review, do not issue definitive legal conclusions); 8. project health/version stability; 9. interoperability/lock-in; 10. **estimated code avoided vs adapter complexity**.

Do not assume a product replaces governance because it exposes tags, user roles or MCP. Do not assume its security correctness without an actual threat-model-aware test.

## 6. Explicit architecture alternatives to compare

Evaluate at least these three against the same traceable use-case set:

- **Option A — Custom Markdown/Git Knowledge Foundation + custom governance**, reusing libraries for FTS, policy evaluation and Obsidian adapters.
- **Option B — Basic Memory as a separately bounded knowledge/indexing component + custom governance**. Identify whether its native writes can safely be constrained, and how to prevent a second source of truth. No assumption that AGPL is compatible without analysis.
- **Option C — Obsidian-first Markdown vault + minimum Core governance and derived indexes**. No mandatory Basic Memory. Reuse native links/Properties/Bases and implement only hard invariants.

Option D (Cognee/Graphiti as sole canonical store) may be considered, but only with evidence overcoming our Git/Markdown/Obsidian requirements.

For each option describe precisely: ownership of canonical files; write entry points; reconciliation when offline; protected/shared revision representation; separate Relation support; ACL enforcement; ability to restore derived indexes; failure/recovery; dependencies; migration path between options.

**Do not predetermine the winner**. A recommendation must show the trade-offs and which assumptions must be tested.

## 7. Obsidian design review — mandatory independent deliverable

Write a dedicated report answering, using concrete note/file examples:

- What can be authored natively using Markdown, YAML Properties, wikilinks, backlinks, Graph View, Bases, folders, templates, Obsidian Git?
- How can standalone typed Relations be **visible and editable** without duplicating canonical truth? Consider: generated wikilink projections, links in Markdown, syntax conventions, virtual views, sidebar/plugin, and revised Relation authority. Examine reverse sync/conflicts.
- How do logical nested Collections interact with physical folder paths and multi-cluster Nodes?
- What does a human see/edit for `draft → proposal → approved shared revision → revoked`? Avoid a custom UI for trivial edits.
- How can protected Shared Nodes be visible but not silently mutated by Obsidian/other plugins? What *cannot* be guaranteed without filesystem isolation?
- What happens when Obsidian changes a file while Core is offline, or while a batch commit/reconciliation is running? How are invalid edits preserved for human resolution?
- Is an **Obsidian-native vault architecture** preferable to a **knowledge platform with Obsidian projection**? State the technical threshold that would justify changing our design.

Include a clear **Obsidian Experience Gap** table: native, configurable plugin, requires bespoke integration, incompatible/undetermined.

## 8. Testable, narrow PoC proposals (do not build in this phase)

Define reproducible acceptance criteria, fixtures, commands, bounded implementation effort and stop/go criteria for:

1. **Basic Memory + Obsidian:** AI creates/updates, human edits offline, changes reindexed, graph/search consistent, source of truth unequivocal.
2. **Typed Relations:** private-owned Relation points to Shared Node; Obsidian shows usable navigation; permissions and non-duplication hold.
3. **ACL and non-discovery:** two agent identities and one shared cluster; deny hidden node through direct read, enumeration, search, hit counts, relation traversals and raw FS access model.
4. **Governed revisions + batch crash:** Obsidian edit → candidate → review/approval → approved snapshot, revocation, CAS conflicts, restart/recovery and all-or-nothing commit.

Add an optional minimal temporal-review experiment only if specific backend choice would otherwise be risky. Distinguish prototype hacks from production solutions.

## 9. Deliverables / proposed file layout

Create or propose these Markdown artifacts (respect existing repository conventions; adjust exact paths if warranted):

- `docs/domain/glossary.md` — normative terminology and distinctions.
- `docs/domain/domain-model.md` — aggregates, authority, lifecycle, relationships and invariants.
- `docs/domain/operations-catalog.md` — systematic operations/capabilities and pre/postconditions.
- `docs/research/reuse-assessment.md` — market/OSS evidence table, build-vs-buy scores and references with research date.
- `docs/research/obsidian-integration-assessment.md` — practical authoring scenarios, contradictions and recommendations.
- `docs/research/architecture-options.md` — at least three competing options and recommendation with assumptions.
- `docs/research/poc-plan.md` — minimal falsifiable experiments with success criteria.
- `docs/architecture/reconciliation-register.md` — mapping old docs/ADRs/schema assumptions → confirmed changes/open issues/migrations.
- `docs/domain/open-decisions.md` — **only material unresolved questions** with recommended default, risk, blocking milestone, evidence needed.
- One concise **executive summary** pointing to the above and proposing Phase 2 implementation sequencing. Use a README or `docs/research/README.md`.

It is acceptable to split a long catalogue if navigation improves. Cross-link consistently and avoid duplication. Preserve existing specs/ADRs as historical sources; any directly revised ADR must explain supersession rather than silently overwrite history.

## 10. Acceptance / review gates

The phase is complete only if:

- Each agreed decision in §2 maps to glossary/domain-contract content or a clearly identified unresolved design question.
- Major conflicts with old repository contracts are enumerated with exact references and recommended resolution, including embedded Relations and Core Context responsibilities.
- Core vs harness, owner vs ordinary agent, Shared vs multi-cluster, archive vs Global Archive vs Trash, Review vs Approval, Node vs Asset vs External Reference are unambiguously distinct.
- Every permission-sensitive operation has an identified authority and denial semantics; no raw-file or graph-search security hand-waving.
- Obsidian is assessed through **real user workflows**, not just the statement “Markdown compatible”.
- Candidate tools have dated source links, licenses, capabilities **and gaps**, not just names/stars.
- At least one non-custom foundation architecture is compared fairly against building our own.
- No production runtime/schema implementation is mixed into this assessment phase.
- CI and existing examples/tests remain passing; Markdown-only changes should not destabilize the toolchain.

## 11. Execution instructions for Codex

1. Inspect repository files and identify existing assumptions before writing deliverables.
2. Verify third-party capabilities via current upstream source/documentation; when network access is unavailable, mark evidence **not verified**, provide exact URLs and a verification checklist, and avoid pretending live evaluation occurred.
3. Write the documentation, keep a **decision provenance register** (confirmed by owner vs proposed by analyst vs tool-evidenced), and identify implementation risks and competing architectures.
4. Treat this document as **problem-domain constraints**, not proof our current technical solution is optimal. Challenge assumptions where demonstrable reuse or Obsidian friction justifies it, but do not silently override confirmed user requirements.
5. Conclude with a sharply prioritized: **reuse now / prototype first / custom build / defer / drop** recommendation.
6. Do not create runtime scaffolding, empty packages, dependency locks, new plugin frameworks, or claim tests not run.

**Primary optimization target:** reduce bespoke code and maintenance while preserving trustworthy cluster-scoped governance, human-friendly Obsidian authoring, Git/Markdown ownership, auditability and reversible architecture choices.
