# Domain contract baseline

Current implementation pointers: [production structural contracts](../contracts/README.md)
and [Core M1 supported subset](../core/m1.md). The original assessment status below
is historical; the invariant register remains the semantic baseline.

Status: reconciled by the current [M1.2 accepted decisions](accepted-decisions.md), [invariant register](invariant-register.md) and [API coverage](../contracts/contract-coverage-matrix.md). Production schemas and the bounded M1 runtime exist. Dated proposals below are historical where superseded. [Glossary](glossary.md) defines terms; [catalogue](operations-catalog.md) defines operations; [provenance](../architecture/decision-provenance.md) separates authority levels.

Phase 1.1 precedence: the Owner now requires agents to use **authenticated MCP exclusively**, with physical deployment isolation and no access to canonical files, Git history, secrets or private indexes. Scoped filesystem projections are no longer an allowed agent interface. The [lean assessment](../research/phase-1-1/architecture-decision.md) replaces the four-PoC gate and proposes a simpler committed-state strategy; its storage/approval defaults are analyst recommendations, not changes to the invariants below.

## Boundary and authorities

Core is a passive deterministic authorized store. It owns knowledge/state operations, search/query/graph access, governance enforcement and committed events. Harnesses own planning, context compilation, token budgets, summarization, evaluation, network fetching and scheduled refresh. Cleanup/freshness schedulers invoke bounded Core operations as authenticated services. No LLM, generic workflow engine, universal loader, microservices or mandatory HTTP dependency belongs in the baseline.

One pinned modular-monolith codebase serves independent Brain Instances. Each instance has its own identity, Git history, knowledge roots, policy/control records, runtime durability, credentials and cache. A copied checkout is not a grant or a new instance identity. No symlink/junction sharing of canonical data. Cross-instance transfer is export/validate/remap/review/import, with new local IDs.

| Aggregate / identity | Authority and source | Consistency boundary |
|---|---|---|
| Node / stable local ID | Markdown body + flat safe YAML; Core commits valid edits | Content/lifecycle changes create immutable Revision; path rename alone need not alter logical content |
| Cluster / stable ID | Cluster manifest; versioned policy and authenticated administration | Policy/owner changes revalidate protected selection and active authority |
| Membership / cluster + node | Membership Service commits; designated Orchestrator or human admin authorizes | Manifest CAS; admission-on-create and approved selection included |
| Collection / stable ID + exactly one cluster | Git record; structural capability | Parent must share Cluster; cycle checks; Node references do not confer membership |
| Relation / stable ID + exactly one owner cluster | Standalone Git record with source/target/predicate/provenance | Independent CAS/revision; changes never increment endpoint Node revisions |
| Asset / stable ID | Git bytes and metadata initially | Check checksum/media type/budget before commit; reference accounting separate from ownership |
| External Reference / stable ID | Passive locator and metadata | No network execution; external check intake verifies source/time/target version |
| Registries / type or predicate key + version | Instance desired configuration referencing structural schemas | Reject unregistered required meaning; do not change existing record semantics in place |
| Proposal, Review, Approval / stable record IDs | Durable control/governance records; immutable content | Exact operation digest + revision binding; separate revocation/consumption records |
| Disposal / stable request ID | Durable routing, preservation and restore receipts | Preservation precedes irreversible expiry; no unprivileged purge path |
| Transaction/outbox/audit/idempotency / scoped IDs | Durable coordination authority, backend OPEN D02 | Never rebuild from disposable indexes; effects and receipts recover together |

Canonical knowledge is Git-versioned Markdown/constrained YAML; registries/manifests are Git-versioned proposals where representation is not specified. Governance/audit/journal durability is **not settled** merely by choosing Markdown. See [D02](open-decisions.md). JSON Schema 2020-12 describes structure; generated Python/Pydantic and TS remain derived. Preserve independent validation and fixture parity. Transport names do not decide semantics.

## Invariant register

| ID | Confirmed rule / required enforcement |
|---|---|
| I01 | Authenticate principal and instance at every ingress, including direct Python calls; Owner has supported super-administration/recovery and visibility, still bound by integrity and audit |
| I02 | Evaluate resource/action/condition capabilities and current per-cluster policy; content CRUD never implies structural, membership, approval, publication or purge authority |
| I03 | Unauthorized existence-sensitive access returns indistinguishable `NOT_FOUND`; filter before search counts, pagination, graph expansion and history; no hidden path/name/edge disclosure |
| I04 | Node creation atomically admits to authorized target or owned isolated staging; never ownerless/ACL-less. Proposed admission delegation only creates initial membership, never later attach/detach |
| I05 | Ordinary agents cannot mutate/archive/delete Shared or multi-cluster protected Nodes. Detach cannot remove protection as a privilege escalation. Recheck full memberships at commit |
| I06 | Collection is within one Cluster; hierarchy is acyclic; structural grants are distinct from content editing; a local reference may survive Node protection |
| I07 | Relation has one owner Cluster, independent revision and endpoints that may cross clusters. Create requires endpoint access; read requires Relation AND both endpoints; links never grant rights |
| I08 | Node/Relation/type/predicate identities are stable; committed content revisions immutable; current read does not imply `node.history.read`; validity and lifecycle are independent |
| I09 | Approved Node Revision can remain selected while candidates evolve. Missing historic bytes fail closed. Relation approval/snapshot selection is separately OPEN D03 |
| I10 | Publication requires source disclosure AND destination admission under destination policy; copy/fork uses new IDs and provenance; a snapshot may preserve private original |
| I11 | Review is typed evidence about a Revision; Approval authorizes one exact Proposal. Changed targets/parameters invalidate authorization; recheck policy, identity, CAS, approval and revocation at commit |
| I12 | Node archive preserves current membership and hides active results; delete relinquishes editable owned content into pending disposal; neither grants purge |
| I13 | Cleanup routing is externally decided and Core-authorized. Global Archive copy requires both source disclosure and destination admission; Trash is isolated with original metadata and retention |
| I14 | No purge until required routing/preservation is durable. `trash.expire` is policy-scoped expiry, not arbitrary `node.purge`; restore checks current rights; physical/Git/backup erasure are distinct |
| I15 | Asset references are many-to-many; deleting Node does not delete shared bytes. Initial Git provider enforces configurable per-file/aggregate budgets before commit; interface remains narrow |
| I16 | External References/check results are passive; external services own fetching, extraction, caching and schedules; independent freshness Review does not revise a still-current Node |
| I17 | Atomic batches are one-instance all-or-none with CAS, retry receipts and crash recovery. External services/editors are outside the atomicity boundary; no nested partial commits |
| I18 | Human offline edits are trusted unmanaged input pending validation. Preserve invalid/conflicting bytes without silent discard or promotion; protected raw edits cannot silently change approved state |
| I19 | Raw filesystem/Git access bypasses Core ACL; agents use authenticated MCP exclusively and physical isolation, never filesystem projections. Obsidian exclusions and MCP itself are not authorization/sandboxing |
| I20 | Derived graph/search indexes are rebuildable from committed source; stale indexes never widen disclosure. Domain events are durable scoped facts; context assembly belongs exclusively to harness |
| I21 | Cross-instance exports have explicit authorized snapshot scope; imports allocate new local IDs and remap all references with provenance; no distributed atomicity or inherited grants |

## Independent state axes and transitions

Content head/candidate → Proposal → optional typed Review → exact Approval → revalidate → selected approved Revision. Direct content commits skip governance records when cluster policy permits. Revocation records remain immutable history; whether selected content becomes unavailable or reverts to a prior approved selection is OPEN D05, with fail-closed serving proposed until resolved.

Active ↔ archived-in-current-cluster is separate from content approval and validity. Editable owned active/archived content → pending disposal → authorized Trash routing and/or private Global Archive copy → policy expiry; restore uses current destination policy. Purge is an independently authorized terminal action over a stated retention scope. Protected Nodes reject ordinary-agent lifecycle mutation. Collection reference removal changes organization only.

Validity uses optional `valid_from`/`valid_until`; reject inverted interval. Supersession is a typed Relation, not duplicated frontmatter. Temporal review is external evidence; “valid” does not mean approved or accessible.

## Historical transaction/reconciliation proposal (superseded backend direction)

Current authority: [M1.2 decisions](accepted-decisions.md) and [Core M1](../core/m1.md) use one managed Git ref with commit-critical records co-located. A separate Git/SQLite transaction journal and four-PoC gate are not current requirements. The paragraph below preserves the earlier proposal; it is not a runtime guarantee.

All Core readers observe a committed generation. A per-instance writer validates full operation set, current permissions and aggregate CAS, hashes external working files, stages before/after bytes, and records durable transaction intent. Journal must coordinate Git tree/commit, control changes, audit, approval consumption, idempotency receipt and outbox. Publish committed generation only after durable decision; rebuild indexes afterward. Failure before a durable decision yields no visible domain effects; after it, restart completes that exact decision. Divergent human bytes are preserved in a restricted conflict area before repair; never overwrite them from stale staged bytes.

Filesystem rename is not a multi-file transaction, and a Git commit alone cannot atomically commit SQLite audit. The existing staged-journal idea is an experiment, not a guarantee. P04 must demonstrate restart at every boundary on Windows. Recovery blocks normal serving if neither verified roll-forward nor rollback can preserve evidence. No “exactly once” external delivery promise; proposed outbox delivery uses event IDs and duplicate-tolerant consumers.

Safe YAML forbids duplicate keys, executable tags, anchors/aliases and implicit type surprises; validate against JSON-compatible types and registered metadata constraints. Preserve Markdown body bytes. Flat Properties avoid deep provenance/Relation objects; store their canonical records separately. Obsidian edits to IDs/revisions/control fields are reconciliation conflicts, not authority to forge revisions or grants.

## Section 2 coverage

| Brief section | Contract coverage |
|---|---|
| 2.1 passive Core, isolation, Git, schemas, transports | Boundary/authority table; I01, I17, I20–I21; D02 |
| 2.2 Owner, granular grants, per-cluster policy, non-discovery, OS isolation | I01–I03, I19; governance catalogue; D01 |
| 2.3 Nodes/types, Clusters/Membership/Collections, standalone Relations, Assets/references/revisions | Aggregate table; I04–I09, I15–I16; D03 |
| 2.4 creation, CAS, archive/disposal/trash/purge, publication/governance, validity, batch/import | I04–I18, I21; state axes; D02–D06 |
| 2.5 native offline authoring, graph/Collections, protected files | I06–I07, I18–I19; [Obsidian workflows](../research/obsidian-integration-assessment.md); D01/D07 |
