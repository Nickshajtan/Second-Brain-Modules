# Production operation contracts

All operations below are version **1.0.0**. This is a supported structural baseline, not implemented handlers. [Full domain catalogue](../domain/operations-catalog.md) remains authoritative for semantics; [invariant IDs](../domain/domain-model.md) are traceable below.

## Common obligations

Every request binds an instance and request ID; actor identity comes from authenticated context, never caller JSON. No implicit Owner boolean, role ladder or transport-specific SDK type exists. Read results pin committed generation; current policy rechecks apply before delivery. Missing/hidden existence-sensitive targets return NOT_FOUND. Other common errors: VALIDATION_FAILED, UNAUTHENTICATED, FORBIDDEN for visible action denials, REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, POLICY_CHANGED, APPROVAL_REQUIRED, APPROVAL_REVOKED, INVALID_TRANSITION, INTEGRITY_FAILED, UNSUPPORTED_VERSION, DEADLINE_EXCEEDED, BUDGET_EXCEEDED, RETENTION_HOLD, REPAIR_REQUIRED, INTERNAL. [Canonical error vocabulary](../../contracts/schemas/v1/common.schema.json) is structural; diagnostic messages are sanitized, not machine-parsed.

Each mutation requires idempotency_key and expectations; the expectations array describes every existing touched aggregate under semantic rules, not a schema guarantee that clients supplied all guards. Revalidate authority, current policy, clock conditions, CAS, expected digest and exact Approval at commit. Same key+digest replays one receipt under current read permission; same key/different digest conflicts. Successful effects, approval consumption, audit/receipt and scoped events share the later backend transaction boundary. A timeout is not rollback; event delivery may repeat. Historical contract-only scope: no handlers/coordinator/journal/authorization evaluator is implemented.

Mode P means direct or governed by target Cluster policy; it does not force every mutation through Proposal. Mode G applies to actual selection/promotion when approval is required by its governing policy; the table leaves destination-specific policies unchosen. Read mode R has no mutation key. Review never authorizes execution. Proposal carries operation identifier/version, exact subject, scope, payload digest and CAS expectations; registry membership and equality with another record are semantic.

Every mutation returns [CommittedReceipt](../../contracts/schemas/v1/transaction.schema.json#/$defs/CommittedReceipt) with request-correlated OperationResult handles/revisions; reads return [ReadResult](../../contracts/schemas/v1/transaction.schema.json#/$defs/ReadResult). Errors return [ErrorResponse](../../contracts/schemas/v1/transaction.schema.json#/$defs/ErrorResponse). This avoids a separate response DTO per trivial operation; the runtime must correlate operation/resources/result and enforce disclosure. NodeRevision IDs, exact Proposal bindings, current membership and graph authorization cannot be established by closed-object shape alone.

## Request and behavior mapping

| Operation / request definition | Capability / authority | Scope | Mode | Preconditions | Postconditions | Invariants | Success event |
|---|---|---|---|---|---|---|---|
| [node.create](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeCreate) | node.create + delegated membership.admit_on_create | Target Cluster or owned staging | P | Admitted target, registered type, owner/provenance | New Node Revision and initial membership, no orphan | I04 | node.created |
| [node.read](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeRead) | node.read; history separately if requested | Node and selected Cluster view | R | Current permission and exact approved/current selection | Authorized committed bytes only | I03 I09 | none |
| [node.update](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeUpdate) | node.update | Node and full protection/membership set | P | Editable owned scope; protected ordinary agents denied | New immutable content Revision, approved selection unchanged | I05 I08 | node.revised |
| [node.archive](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeArchive) | node.archive | Node and memberships | P | Permitted lifecycle transition; protected actor check | Archive in place, preserve membership | I05 I12 | node.archived |
| [node.unarchive](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeUnarchive) | node.unarchive | Node and memberships | P | Authorized archival access and transition | Return to active selection under policy | I05 I12 | node.unarchived |
| [node.delete](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeDelete) | node.request_disposal | Editable owned Node | P | Protection/ownership check; no purge grant inferred | Pending disposal request, not physical erasure | I05 I12 | disposal.requested |
| [node.restore](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeRestore) | node.restore + destination admission | Disposal source and destination | P | Retained bytes and current rights, no old grants revived | Restored authorized content/membership with lineage | I14 | node.restored |
| [node.copy](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeCopy) | node.copy + source disclosure + destination create | Exact source Revision and destination | P | Both disclosure and admission; reference policies | New local ID and provenance, no inherited grants | I10 | node.copied |
| [node.fork](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeFork) | node.fork + source disclosure + destination create | Exact source Revision and destination | P | Same disclosure/admission guards as copy | New ID and derivation provenance | I10 | node.forked |
| [node.publish](../../contracts/schemas/v1/operations.schema.json#/$defs/NodePublish) | node.publish + source disclosure + destination admission | Exact source Revision and Shared target | P | Destination policy and exact Proposal/Approval when governed | Publication/selected snapshot, no implicit private draft change | I10 I11 | node.published |
| [node.propose_revision](../../contracts/schemas/v1/operations.schema.json#/$defs/NodeProposeRevision) | node.propose_revision | Base Revision and permitted candidate scope | D | Candidate creation allowed independently of protected selection | Candidate Revision and exact Proposal; no approval implied | I05 I11 | node.candidate_created |
| [cluster.configure](../../contracts/schemas/v1/operations.schema.json#/$defs/ClusterConfigure) | cluster.configure plus policy/ownership authority for changed fields | Cluster | P | Privileged configuration; existing selection impacts reviewed | New manifest/config version; historic bytes preserved | I01 I02 | cluster.configured |
| [membership.attach](../../contracts/schemas/v1/operations.schema.json#/$defs/MembershipAttach) | membership.attach; designated Orchestrator or authorized human admin | Node and Cluster | P | Membership Service validates admission and full protection set | Attach without granting implicit read/publication | I04 I05 | membership.attached |
| [membership.detach](../../contracts/schemas/v1/operations.schema.json#/$defs/MembershipDetach) | membership.detach; designated Orchestrator or authorized human admin | Node and Cluster | P | No detach-to-edit escalation or ownerless orphan | Detach membership only; route last membership safely | I04 I05 | membership.detached |
| [membership.select_revision](../../contracts/schemas/v1/operations.schema.json#/$defs/MembershipSelectRevision) | membership.select_revision + required approval authority | Node Revision and Cluster selection | G when policy requires | Exact Proposal, current approval, candidate and manifest CAS | Select approved immutable Revision; independent optional edges | I09 I11 | membership.revision_selected |
| [collection.create](../../contracts/schemas/v1/operations.schema.json#/$defs/CollectionCreate) | collection.create | One Cluster and optional parent | P | Structural permission, same Cluster, acyclic hierarchy | Create organization; no membership/content effects | I06 | collection.created |
| [collection.update](../../contracts/schemas/v1/operations.schema.json#/$defs/CollectionUpdate) | Changed structural actions: collection.rename/reparent/node.add/node.remove | Collection, old/new parent, references | P | Authorize each changed action; same Cluster/cycles/reference eligibility | Replace organization only; protected references may remain | I06 | collection.changed |
| [collection.remove](../../contracts/schemas/v1/operations.schema.json#/$defs/CollectionRemove) | collection.remove | Collection and descendants | P | Explicit nonempty/reparent policy, no implicit Node deletion | Remove organization only | I06 | collection.removed |
| [relation.create](../../contracts/schemas/v1/operations.schema.json#/$defs/RelationCreate) | relation.create + both endpoint read | One owner Cluster and two Node endpoints | P | Registered predicate, same instance, endpoint rules/provenance | New independent Relation Revision; no Node revision change | I07 | relation.created |
| [relation.update](../../contracts/schemas/v1/operations.schema.json#/$defs/RelationUpdate) | relation.update + endpoint read | Relation owner and endpoints | P | Owner policy, predicate rules, independent CAS | Revise edge only; approval scope stays independent | I07 I09 | relation.revised |
| [relation.delete](../../contracts/schemas/v1/operations.schema.json#/$defs/RelationDelete) | relation.retire | Relation owner Cluster | P | Authorized retirement and retained-selection dependencies | Retire edge, never physically purge Node or edge history | I07 | relation.retired |
| [relation.read](../../contracts/schemas/v1/operations.schema.json#/$defs/RelationRead) | relation.read + source/target node.read | Relation and both endpoints | R | All three resources readable at current policy | No hidden edge/stub/degree disclosure | I03 I07 | none |
| [asset.register](../../contracts/schemas/v1/operations.schema.json#/$defs/AssetRegister) | asset.add + target admission | Asset policy scope | P | Git initially; checksum/media type and size/budget before commit | Register managed bytes/reference, no disclosure by dedup | I15 | asset.added |
| [asset.reference](../../contracts/schemas/v1/operations.schema.json#/$defs/AssetReference) | asset.reference or asset.unreference + node.update | Asset and referencing Node | P | Both policies, protected Node rules, retained references | Reference change; unreference never deletes Asset | I05 I15 | asset.reference_changed |
| [knowledge.search](../../contracts/schemas/v1/operations.schema.json#/$defs/KnowledgeSearch) | node.search or scoped node.list plus result reads | Explicit authorized scope | R | Filter before counts/snippets/rank/pagination; independent history access | Authorized summaries/records and opaque scoped cursor | I03 I20 | none |
| [proposal.create](../../contracts/schemas/v1/operations.schema.json#/$defs/ProposalRecord) | proposal.create | Caller-known authorized targets | D | Exact registered intended operation/payload digest and expected revisions | Immutable exact Proposal; no target effect | I11 | proposal.created |
| [review.record](../../contracts/schemas/v1/operations.schema.json#/$defs/ReviewRecord) | review.record | Exact immutable subject Revision | D | Authenticated reviewer and registered review type/evidence | Independent Review, no Approval or Node revision | I11 I16 | review.recorded |
| [approval.issue](../../contracts/schemas/v1/operations.schema.json#/$defs/ApprovalRecord) | approval.issue | One exact Proposal | P | Current approver authority and required review/separation rules | Immutable decision bound to operation digest | I11 | approval.issued |
| [approval.revoke](../../contracts/schemas/v1/operations.schema.json#/$defs/ApprovalRevoke) | approval.revoke independently privileged | Approval and affected selection | P | Current revoker authority; policy-specific serving effects | Separate revocation record, old Approval unchanged | I11 | approval.revoked |
| [access.request](../../contracts/schemas/v1/operations.schema.json#/$defs/AccessRequestSubmit) | access.request | Caller-described intended scope | D | No protected-resource lookup/discovery oracle | Request record only, never implicit grant | I03 | access.requested |
| [disposal.route](../../contracts/schemas/v1/operations.schema.json#/$defs/DisposalRoute) | disposal.route; scoped external Cleanup identity | Pending source and authorized destinations | P | Source/destination policy, preservation/retention evidence | Durable routing record; no arbitrary purge | I13 I14 | disposal.routed |
| [disposal.preserve_copy](../../contracts/schemas/v1/operations.schema.json#/$defs/DisposalPreserve) | disposal.preserve_copy + source disclosure + Archive admission | Source Revision and private Global Archive | P | Both policies and retained Asset/provenance checks | New authorized archival ID and durable preservation proof | I13 I14 | disposal.preserved |
| [snapshot.export](../../contracts/schemas/v1/operations.schema.json#/$defs/SnapshotExport) | snapshot.export + each source disclosure/history permission | Explicit revision set | P | Authorized closure and current delivery permission; exclude secrets/grants | Exact manifest/digest; no implicit live sharing | I21 | snapshot.exported |
| [snapshot.import](../../contracts/schemas/v1/operations.schema.json#/$defs/SnapshotImport) | snapshot.import + destination creation/admission | One destination instance | P | Validate mapping/plan/digest, new local IDs, no rights inheritance | Remapped local resources/provenance atomically within chosen batch | I21 | snapshot.imported |

## Batches, events and exact structural boundaries

[BatchRequest](../../contracts/schemas/v1/transaction.schema.json#/$defs/BatchRequest) submits 1-100 flat tagged MutationOperation entries, one instance/transaction ID, expected committed generation and idempotency identity. No nested batch, external service transaction or distributed commit is promised. Semantic I17 requires all-or-none results, unique coherent request/approval references, instance matching and revalidated CAS. Fail one entry and commit no effects; after a durable success, recover the same receipt instead of repeating domain effects.

[CommittedEvent](../../contracts/schemas/v1/transaction.schema.json#/$defs/CommittedEvent) and [OutboxRecord](../../contracts/schemas/v1/transaction.schema.json#/$defs/OutboxRecord) contain typed resource/revision handles and delivery metadata, not arbitrary executable payloads. Events describe committed facts only. Event type registration, result/request correlation, delivered_at consistency and approval consumption are semantic obligations. No graph snapshot approval is required by these records.

The [semantic conformance corpus](../../tests/fixtures/contracts/semantic.json) intentionally passes structural validators while recording required runtime rejections, including inverted validity, Proposal/Approval mismatch, cross-instance batch, bad Collection hierarchy, missing preservation and batch instance mismatch. No test handler pretends to enforce these rules yet.

## Vocabulary reconciliation

The release profile uses knowledge.search as a typed query envelope for node.search/list semantics; it does not grant whole-Cluster enumeration. asset.register implements asset.add metadata intake. relation.delete means domain retirement, not purge. collection.update groups structural replacement fields; each actual rename/reparent/reference change still needs its separate authority. This is explicit aliasing/shape reuse, not a generic CRUD privilege. Existing catalogue operation names outside this baseline are not silently exposed.

No final retention duration, policy composition algorithm, immediate Obsidian synchronization or whole-graph approval is frozen. See [Owner decisions O1-O4](../research/phase-1-1/open-decisions.md) and [evolution](evolution.md).

## M1.2 exact historical-read requests

`operations#/$defs/NodeRevisionRead` (`node.revision.read`) requires `payload.revision: common#/$defs/NodeRevisionRef`; `RelationRevisionRead` (`relation.revision.read`) uses `RelationRevisionRef`. Both carry explicit schema/operation versions, instance and request IDs, and no mutation key. They are separate from current selection reads, require independent history authority plus current resource disclosure, and must return exact immutable KnowledgeRecord revision snapshots in `transaction#/$defs/ReadResult`. Cross-instance/equality/digest/retention checks are semantic. The original M1 dispatch rejects both. M2.2's bounded Node implementation and verification status are recorded below; Relation history and range/history-list pagination remain deferred.

## M2.2 Node replacement and exact history

The [independently reviewed design](../core/m2-2-node-mutation.md) activates existing
request definitions, not new aliases or patch shapes. Actual implementation/test
status is in the [M2.2 validation report](../core/m2-2-validation.md).

`NodeUpdate` replaces the entire `NodeContent`; omitted optional content fields
are removed. Require exactly one target Node CAS expectation using the existing
resource/expected_revision and optional expected_digest. Batch expected_generation
also fences current membership, registry and policy. Fresh accepted replacement,
including identical content, creates one new logical revision under the catalogue's
existing replacement-to-new-revision effect; exact idempotent retry creates none.
Preserve Node identity, creation metadata, lifecycle, Membership and independent
Relations. Only a private active sole-membership Node with explicit `node.update`
is supported. One Node cannot be mutated twice in a batch; distinct-Node mixed
create/update batches remain flat and atomic. No governed or selected update is
implicitly supported.

`NodeRevisionRead` carries its exact Node identity/instance in revision.resource;
it has no selected_cluster_id field. Require current `node.read` AND
`node.history.read` in the actual sole scope before probing historical evidence.
Return one canonical immutable `NodeRevision`, including its exact snapshot, in
`ReadResult.records` at the current pinned generation. Never substitute current
Node content. Validated legacy supplements may supply outgoing snapshot content
without rewriting the stored old revision. Current Node read does not grant history.

Mutation replay requires the original operation's current capability:
create/admit for Node creation, `node.update` for Node update. History permission
is not required merely to return the original receipt's handles; replay never
returns old content or restores an old head. Exact immutable original effects
remain independently verified after later mutations.

Current handler inventory is [Core M1](../core/m1.md) and the [coverage matrix](contract-coverage-matrix.md); dated statements that this contract milestone has no handlers are not current repository status.
