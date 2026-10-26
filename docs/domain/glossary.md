# Domain glossary

Current authority: [M1.2 accepted decisions](accepted-decisions.md) and [coverage matrix](../contracts/contract-coverage-matrix.md). Production schemas and Core M1 now exist; the dated Phase 1 status and representation proposals below are historical.

Status: Phase 1 contract baseline; no production schemas or runtime. Authority: the owner's supplied `second-brain-phase-1-domain-and-reuse-assessment.md`, section 2. Proposed representations remain proposals. See [model](domain-model.md), [operations](operations-catalog.md), [open decisions](open-decisions.md) and [provenance](../architecture/decision-provenance.md).

## Instance and authority

| Term | Definition, identity and authority | Persisted source / distinction |
|---|---|---|
| Brain Instance | Independently identified administrative and data boundary, governed by its authenticated Owner | Instance configuration, own knowledge Git history, policy, durable runtime state, credentials and cache; shared code grants no shared data |
| Workspace | Legacy alias for Brain Instance when referring to isolation; otherwise an editor workspace must be qualified | Never infer instance identity from an Obsidian workspace or directory |
| Knowledge Vault | Files opened by a human authoring tool; may include canonical working files, unmanaged input and derived views | Filesystem layout; neither an identity nor a security boundary by itself |
| Principal | Registered authenticated human, agent or service identity | Identity registry and trusted authentication binding; not caller-supplied JSON |
| Instance Owner | Human super-administrator with supported full visibility, administration and recovery | Authenticated owner registration; integrity guards and audit still apply |
| Agent | Principal acting through a harness, with explicitly scoped grants | Principal registry; intelligence is outside Core |
| Service | Principal performing bounded operations, including external cleanup/freshness services | Principal registry; service status confers no implicit privileges |
| Capability | Versioned resource/action/condition permission meaning | Capability registry; a partially ordered set, not a role ladder |
| Grant | Assignment of capabilities to principal within scope/time/session | Durable control record; delegation cannot widen the issuer's authority |
| Policy | Cluster-specific rules governing admission, operations and disclosure, with versioned activation | Control records; current policy governs even historical content |
| Capability Profile | Convenience bundle of capabilities, resolved to explicit grants | Versioned control definition; changes must not silently enlarge grants |
| Ownership | Recorded responsibility for a resource | Resource/control record; ownership alone is not an unchecked write or purge permission |
| Authority | Legitimate power to decide or commit a particular operation | Verified grants, policy and designated commit responsibility; separate from authorship |
| Scope | Explicit instance/resource/cluster/session restriction on an operation or grant | Request/control references; directory names are not scope authority |

## Knowledge

| Term | Definition, identity and authority | Persisted source / distinction |
|---|---|---|
| Cluster | Identified ownership, policy and knowledge scope | Git-versioned manifest plus control policy; not a folder; Shared is a governance mode |
| Membership | Authorized Node assignment to one Cluster, potentially selecting an approved Revision | Membership manifest; identity is cluster + node; does not grant access by itself |
| Membership Orchestrator | One logical instance authority deciding membership changes, alongside authorized human administration | Principal/authority binding; not necessarily a daemon or AI; Core Membership Service validates and commits |
| Collection | Identified, possibly nested organization inside exactly one Cluster | Collection records with Node references; not membership, policy scope or shared cross-cluster container |
| Node | Logical managed knowledge unit with stable ID, body, flat Properties, registered type, provenance, revisions and lifecycle | Git Markdown + constrained YAML; filename/title is not identity |
| Node Type | Registered extensible classification with additional metadata constraints | Versioned instance registry/schema references; not a hardcoded universal ontology |
| Revision | Immutable historical content state of an aggregate, hash-addressable through retained Git bytes | Revision locator; distinct from mutable aggregate CAS token, lifecycle and validity |
| Candidate Revision | Committed proposed content not yet selected for governed consumption | Immutable Node Revision + candidate reference; unvalidated raw edits are not committed revisions |
| Approved Revision | Immutable Revision selected under one Cluster's policy | Membership selection + exact Proposal/Approval evidence; not a universal quality label |
| Publication Snapshot | Immutable source-revision-derived publication representation | New identity/provenance proposed; exact identity choice OPEN D04; private source remains separate |
| Shared Node | Node published under a Cluster's explicit Shared governance mode | Publication/membership records; ordinary agents cannot mutate/archive/delete it |
| Multi-cluster Node | Node with more than one authorized membership | Membership records; protected from ordinary-agent mutation even if all memberships are readable; not automatically Shared |
| Relation | First-class directed typed edge with stable ID, provenance, independent revision and exactly one owner Cluster | Independently Git-versioned record; endpoint links grant no access; not embedded Node state or a wikilink |
| Predicate Type | Registered Relation meaning and endpoint/cardinality/symmetry rules | Instance registry; minimum built-ins only; inverse traversal does not silently create another assertion |
| Asset | Managed attachment with ID, checksum, media type, provenance, policy and references | Git bytes + manifest initially; deduplication does not confer disclosure; not deleted just because one Node disappears |
| External Reference | Passive identified locator outside managed storage with optional checksum/check metadata | Git metadata record; not an Asset, membership or instruction to fetch |
| Source | Identified origin of information or bytes | Source record/locator, potentially unavailable; not necessarily managed or trusted |
| Provenance | Evidence of source, derivation, actor and exact revision relationships | Immutable records, independently authorized; prompt transmission alone does not create it |

## Lifecycle and governance

| Term | Definition and authority | Persisted source / distinction |
|---|---|---|
| Lifecycle | Managed state transitions of a resource | Versioned state/transition records; validity dates and approval are separate axes |
| Archive State | Node hidden from normal active results while remaining in its current Cluster | Node lifecycle Revision; `node.archive`, reversible through explicit archival queries |
| Pending Disposal | Relinquished editable Node awaiting durable routing/preservation | Disposal record + state; does not yet mean trash, purge or publication |
| Trash | Isolated recoverable system storage with original ownership/membership evidence and expiry rules | Durable disposal metadata/bytes; not an accessible Shared Cluster |
| Global Archive | Private, long-term Cluster for discarded knowledge awaiting curation | Authorized archival copy/membership; ordinary agents have no automatic access |
| Retention | Policy defining required preservation, expiry and backup/history treatment | Versioned policy + routing receipts; Git retention is separate from working-file deletion |
| Purge | Independently privileged destruction within an explicitly stated storage/history scope | Audited receipt/tombstone; never implies complete privacy erasure from Git/backups |
| Restore | Governed recovery into a currently authorized destination | New committed recovery record; old grants never revive automatically |
| Proposal | Immutable exact intended operation, targets, parameters, expected revisions and digest | Durable governance record; not every direct write requires one |
| Review | Typed conclusion on immutable target Revision, e.g. freshness/publication/disposal | Independent immutable record; does not authorize execution |
| Approval | Authorization of one exact Proposal by authenticated authority | Immutable durable record with privileged revocation/consumption evidence; not generic content approval |
| Revocation | Privileged withdrawal of grant/approval effect | Durable monotonic record; Approval history remains; selected-revision response is policy-specific |
| Direct Operation | Authorized operation committed without mandatory Proposal | Request + audit; all guards still apply |
| Governed Operation | Policy-gated Proposal → optional Review → Approval → validation → commit | Linked governance and transaction records; recheck guards at commit |

## Retrieval, transactions and integration

| Term | Definition, authority and persisted source | Distinction |
|---|---|---|
| Query | Explicit request over authorized committed state, including lifecycle/scope filters | Not permission to enumerate whole Clusters or history |
| Retrieval Adapter | Replaceable query/search implementation over derived data | No canonical writes or authority to relax Core policy |
| Derived Index | Rebuildable search/graph projection, tied to committed source generation | Disposable; cannot reconstruct durable audit, grants or idempotency |
| Agent Harness | External orchestration/context/model execution environment | Outside passive Core, with scoped authenticated access |
| Context Bundle | Harness-produced selection/serialization of authorized knowledge and pinned revisions | Outside Core; Core supplies authorized retrieval and snapshot references |
| Transaction | One-instance all-or-none domain commit with CAS, durable recovery and atomic Core-reader visibility | External editors cannot receive multi-file filesystem atomicity; no cross-instance/external transaction |
| Idempotency Key | Principal/instance/operation-scoped retry identity bound to normalized payload digest | Durable result receipt; different payload conflicts; retry horizon OPEN D02 |
| Event | Immutable committed-domain fact with ID, source transaction and scoped payload | At-least-once delivery is proposed; not permission or replay authority |
| Outbox | Durable pending-delivery records committed with domain effects | Not disposable indexing; exact backend OPEN D02 |
| Snapshot | Explicit immutable selection of committed resource/revision references | Not necessarily publication or filesystem backup |
| Export Bundle | Authorized explicit snapshot plus integrity/provenance manifest | No implicit grants/secrets or complete history |
| Import Mapping | Foreign IDs/revisions to new local IDs with provenance | Never grants foreign access or aliases foreign membership |
| Reconciliation | Validation/adoption/conflict handling of external filesystem changes against last committed state | Preserves invalid human bytes; watcher notification is not a commit |

Aliases: “delete” means request disposal, not purge; “archive” must be qualified as Node archive state or Global Archive; “relation” means canonical typed record, while “wikilink” means navigational Markdown syntax. “Stable” names a possible Cluster policy, never a globally fixed permission tier.
