# M2.2 Node mutation and exact historical reads

Status: implemented bounded Node mutation/history subset; independent final review, full quality gates and all 42 performance observations passed. Independent Stage A review preceded production edits. Exact evidence and operational limits are in the [validation report](m2-2-validation.md).
Baseline: `625cdf5baf6385541effc6f385aded6b39c620a2`. The Owner M2.2
implementation specification is the authority for this bounded extension. Existing
[accepted decisions](../domain/accepted-decisions.md), [invariants](../domain/invariant-register.md)
and [state machines](../domain/state-machines.md) retain authority; O1-O4 remain open.

## Preliminary audit and contract compatibility

Canonical namespace is
`https://github.com/Nickshajtan/Second-Brain-Modules/contracts/1.0.0/`.
The following are existing definitions, not proposed new request shapes.

| Exact definition | Audited meaning and implementation consequence |
|---|---|
| `operations.schema.json#/$defs/NodeUpdate` | Operation/version 1.0.0; payload requires node_id and complete knowledge NodeContent. This is replacement, never a JSON patch. Mutation identity and expectations are required; the array can structurally be empty, so semantic target CAS must reject that case. |
| `common.schema.json#/$defs/CasExpectation` | Existing resource, expected_revision and optional expected_digest provide target CAS without another field. Require exactly one expectation for the target Node; reject duplicated expectations and unsupported scope. Batch expected_generation additionally fences membership, policy and registry state. |
| `knowledge.schema.json#/$defs/NodeContent` | Complete title/body/properties/provenance and registered type/version; optional fields omitted in replacement are removed. Properties pass the registered metadata schema. |
| `knowledge.schema.json#/$defs/NodeRevision` | Exact snapshot, digest, actor/time, provenance, logical_revision and existing optional previous RevisionRef suffice. For new revisions greater than one previous becomes a runtime requirement. Legacy absence of snapshot is handled only by previously validated explicit supplements. |
| `knowledge.schema.json#/$defs/Node` | Stable id, content/head revision and revision_ref, lifecycle, created_at and updated_at. Preserve lifecycle/created_at; set updated_at to revision recorded_at. |
| `common.schema.json#/$defs/RevisionRef` | Resource/instance, revision UUID and logical number stay distinct from Git identity; require exact correspondence. NodeRevisionRef specializes the resource kind. |
| `operations.schema.json#/$defs/NodeRevisionRead` | Payload contains only exact typed revision. Node identity and instance are inside revision.resource; there is no selected_cluster_id field. Supported sole membership supplies the current scope. |
| `transaction.schema.json#/$defs/ReadResult` | KnowledgeRecord union already admits NodeRevision. Deliver one exact immutable NodeRevision, not a current Node masquerading as history. |
| `transaction.schema.json#/$defs/BatchRequest` | Flat ordered 1-100 mutations, exact expected generation, transaction/key identity. No nested scheduling or partial commit. |
| `transaction.schema.json#/$defs/CommittedReceipt` | Exact normalized request digest, actor, generation and request-correlated OperationResult resources/revisions already express update evidence. No content in replay receipt. |

Generated imports already exist under `generated.v1.operations_schema` (NodeUpdate,
NodeRevisionRead), `generated.v1.knowledge_schema` (NodeRevision) and
`generated.v1.transaction_schema` (ReadResult/CommittedReceipt). Canonical ingress
and outgoing validation remain mandatory. No schema amendment, generated edit,
dependency or version change is currently justified. Enabling previously absent
handlers is an intentional behavioral extension, not a persisted-format migration.

The [operation catalogue](../domain/operations-catalog.md) specifies
"replacement content -> new Revision"; the [production mapping](../contracts/operations.md)
specifies "New immutable content Revision" without a content-difference precondition.
Design interpretation accepted at the independent design gate: an accepted fresh request creates one
revision even when replacement equals current content. An exact idempotency retry
returns its original receipt without creating a revision. This preserves the
existing unconditional effect contract and avoids introducing an unrepresented
no-change outcome or a novel rejection condition. This interpretation follows the existing operation contract and does not decide O1-O4.

## Baseline gaps addressed by this slice

`application.py` has fixed create/read dispatch and `_create` rejects existing
record keys. Update requires explicit replacement of the one authorized Node
head, not relaxing duplicate creation checks. Replay currently screens every Node
effect as create/admit; it needs operation-specific screens derived from the
original request, never caller-selected privileges.

`verification.py:TransitionVerifier._receipt` rejects any result resource already
in the parent and infers Node history only from node.create. Its changed-record
explanation check currently covers new heads but not all existing-head mutations.
M2.2 must verify every changed Node head/body and reject unexplained mutations;
Membership/Relation changes remain unsupported. Original effect locators must
retain the publication's head bytes, rather than point at later current bytes.

`history_index.py:closure` currently loads current Node, sole memberships, current
revision and registered definitions; revision records do not recursively load
previous. `domain.py:validate` nevertheless requires the previous revision object
for every revision greater than one. Naively loading predecessors to satisfy this
would make hot reads linear in revision count. Separate exhaustive sequence
validation from bounded delivered-record validation: incremental transition checks
bind new revision to the exact prior head and authenticated revision locator;
ordinary reads validate exact snapshot/reference and current dependencies, relying
on the already verified retained chain without rewalking it. Explicit audit/rebuild
still checks each transition sequentially.

`domain.py:relation` validates predicate endpoint types against current Nodes.
A replacement that changes type can invalidate an unchanged Relation. Preserve
this invariant by loading and validating only incoming/outgoing Relations touching
the affected Node, their endpoints and predicate definitions when type changes.
Use narrow derived endpoint locators maintained from canonical Relations; do not
scan all resource JSON or load all Relations for every update. Cost depends on
actual affected edges; an invalid replacement rejects without changing Relations.

The legacy `history.py` original-effect routine assumes resources are newly
created. Explicit legacy inspection must retain its create recovery role and must
not misclassify later updates as Relation creation. Audit/rebuild's incremental
verifier is the authority for supported new transitions; compatibility tests must
exercise migration inspection on a repository containing valid later updates.

## Mutation and revision sequence

Before private evidence is loaded, denial-only authenticated scope screens require
active Node, exactly one active membership, private active Cluster and explicit
node.update. Positive authorization rechecks canonical current dependencies and
all unsupported protected/approved states fail closed. Mutation does not infer
node.read: CAS target checking needs a mutation-specific authorized selector,
rather than the existing read-only selector. Other explicitly referenced targets
retain their own current disclosure obligations.

Require exact target CAS and optional digest against the pre-operation Node.
Registered replacement content is validated before publication. New uid() UUID
and revision current+1 produce an immutable NodeRevision with previous equal to
the exact old revision_ref, digest(snapshot), authenticated actor and server UTC
time. Preserve Node id/schema_version/created_at/lifecycle; replace complete content,
revision/ref and updated_at. Preserve prior snapshots, Membership and Relations.
Reject unresolved history baseline/missing exact original bytes; never migrate on
read/update. Existing validated NodeRevisionSnapshot supplements may supply legacy
revision-one content without rewriting the original revision metadata.

One Node may be updated at most once in a batch. Reject duplicate updates and
create-plus-update of that same Node deterministically as VALIDATION_FAILED before
preparation. Distinct Nodes may update together; create/update of distinct Nodes
and interdependent Relation creation remain ordered under the existing flat batch.
No last-writer-wins or multiple unpublished logical revisions are introduced.
All errors leave canonical generation and accepted projection unchanged.

## Historical effects and current authority

For update publication, resolve exact parent Node head from prior authenticated
path/OID metadata before applying delta. Verify target/CAS, unchanged system fields,
replacement content, sequence/previous, actor/time, resulting head/ref, new unique
revision identity and exact receipt/result. Reject any other changed Node, body,
Membership or Relation not explained by a supported operation. Retained immutable
path/OID obligations remain unchanged; update may replace only its existing head
and body. Bind effects to original head/body and new revision OIDs in the existing
effects table. Parent state can be verified from original publication's parent
and immutable previous reference without adding a duplicate canonical ledger.

Creation and update receipts after later revisions verify original stored effect
locators and original generation; never require current head equality. Replay
screens every original operation under current capabilities: node.create plus
membership.admit for creation; node.update for update; relation.create plus both
endpoint reads for Relation creation. No history capability is required merely
to return resource/revision handles in a mutation receipt. No historical content
is returned there. The caller's changed request under the same batch key conflicts;
individual operation keys cannot partially replay an earlier batch.

Historical delivery requires BOTH current node.read and node.history.read in the
current sole private active scope. Screen both before probing requested revision
rows or loading historical bytes. Exact instance/resource/UUID/logical-number
mismatch, unknown revision and denied history return NOT_FOUND without identifiers.
After authorization, missing/corrupt retained expected evidence fails closed with
sanitized REPAIR_REQUIRED. Canonically validate exact revision snapshot, digest,
resource binding and its registered original type/version. Return NodeRevision in
ReadResult at the current verified generation; do not return the current content
or enumerate revision counts. For validated legacy supplement evidence, construct
the canonical outgoing revision with snapshot for delivery without persisting or
rewriting old bytes, and validate the supplement binding first.

## Index, performance and crash boundaries

Retain ADR-012 exact-byte authenticated disk-to-private-memory boundary. Existing
revision UUID and resource/logical locators already support exact historical
lookup. Add only required reverse endpoint locators and authenticated per-operation replay scope metadata (operation plus exact affected resource correlation, established by verified request/result binding). Screens must use that metadata before loading private original requests; the existing receipt-wide effect kind alone cannot distinguish create from update in a mixed batch. any derived format
change explicitly invalidates old projection format and requires trusted rebuild,
never silently reinterprets it. Git canonical records and anchor continuity remain
unchanged. For a format-1 checkpoint, normal load must return an explicit rebuild-required diagnostic. Only explicit trusted rebuild may authenticate the old HMAC/enrollment using the complete old binding (same instance/repository/common/ref/contracts, recognized format 1), enforce ancestry from that old accepted commit, build format 2 from canonical Git and publish the upgraded checkpoint/enrollment using the existing key. Unknown formats, any other binding mismatch or damaged anchors fail closed. Do not call begin/re-enroll, discard the old anchor or perform an implicit SQL migration. Upgrade publication writes the completed v2 database, then its v2 signed checkpoint, then signed enrollment v2. Normal load requires a matching v2 checkpoint/enrollment pair and database hash; an interrupted mixed-format pair is never served. Explicit rebuild may authenticate either recognized signed enrollment format independently alongside the signed checkpoint, require every stable binding to match, and retain the checkpoint commit fence. Thus a crash before checkpoint replacement uses the old fence; a crash after it uses the newer accepted fence. No mixed pair authorizes ordinary data delivery. Add old-format rebuild, rollback and interrupted-upgrade tests. No SQL row is authorization or canonical content.

Use request-scoped unique blob reuse and grouped cat-file calls where measurements
show duplicate loads. Clear caches after the operation and do not retain permission
verdicts. Pin all delivered dependencies to one verified frontier. Preserve the
public unexpected-error INTERNAL boundaries in read/submit/generation.

Candidate verification validates one new transition, then conditional Git ref
publication precedes projection replacement. Before-publication interruption leaves
no domain effects. After-publication interruption leaves a recoverable lagging
projection; catch-up verifies the one committed update exactly once. CAS loser
cannot publish or advance its projection. Rebuild/audit verify all retained
transitions, including unchanged immutable paths and original receipt bindings.
No force update, canonical repair or human worktree overwrite occurs.

## Planned evidence and completion gate

Focused tests cover revisions 1 -> 2 -> 3, unique IDs/digests/previous, original snapshots,
CAS/races, no-op fresh request versus exact retry, explicit grants, missing/duplicate
CAS, metadata/type errors, protected/multicluster rejection, and relation endpoint
type invariants. Historical tests cover exact old snapshots, wrong Node/instance,
revocation/non-disclosure, missing/corrupt evidence, and explicit legacy baseline.
Receipt tests cover create and update replay after later updates/restart/unrelated
commits, changed-key conflicts, atomic mixed batches, no partial batch replay and
tampered original effects. Recovery tests cover both publication boundaries,
external valid/invalid transitions, immutable removal and index loss/rebuild.

Structural instrumentation must forbid full ancestry/full tree reads on healthy
update/history/replay, require one new transition per update and zero unrelated
receipt checks, count unique blob loading, and show bounded parsing across many
revisions. Budgets will be measured, not invented. Projection copying/path-hash
metadata enumeration remains an acknowledged existing write cost, distinct from
historical content scanning. The coordinator-owned benchmark will retain M2.1.1
workloads and add all eight requested workloads at 100/1,000/10,000 generations,
including many revisions of one Node. No timing claim precedes actual execution.

Independent design review preceded production implementation. Completion additionally requires
focused regressions, full deterministic quality/contract/distribution gates,
independent final-diff review and actual benchmark evidence. Relation mutation,
governance, multi-cluster composition, transport/authoring integrations and O1-O4
policy choices remain excluded. M2.3 readiness is not established by this design.


## Implemented request reuse and trusted projection upgrade

The request-scoped blob map is keyed by immutable Git OID and is cleared in a
finally block after read/submit, including failures. Candidate verification can
reuse those same exact bytes; no parsed authorization verdict survives the request.
It contains only the affected dependency/effect blobs for ordinary operations;
explicit audit/rebuild retains its separate full-verification cache. This is not
a cross-request content cache or a bound on total index-copy memory.

M2.1.1 format-1 projections return INDEX_STALE/REPAIR_REQUIRED on normal access.
A trusted bootstrap-authorized host explicitly calls rebuild_history_index(core).
The old signed checkpoint and enrollment are authenticated with unchanged stable
bindings and retained key, and current Git must descend the accepted checkpoint.
Only full verification then publishes format-2 SQLite, checkpoint and enrollment.
No automatic migration or key reset occurs. Interrupted mixed-format publication
cannot serve ordinary reads; the explicit rebuild authenticates the remaining
signed checkpoint fence and retries. Unknown formats, wrong instance, bad MAC,
rollback or missing trust material require operator intervention. Canonical Git
and all original revision/receipt identities are untouched.

Developmental measurements showed the narrow reuse reduced a warm update from
37 Git subprocesses/19 blob requests (six repeated OIDs) to 31/13 (zero repeated
OIDs) on the same disposable 20-generation workload. These are development counts,
not final timings or the required large-corpus evidence. Final budgets and measured
results belong to the coordinator-owned performance/validation reports.


## Versioned interpretation protection

The independent design addendum identified that baseline external commits could
change same-version registered meaning while historical snapshots still passed
structure. I08 and M12-REV-06 require historical content not be reinterpreted.
The supported M2.2 configuration subset therefore retains existing Node/Relation
definition records byte-for-byte (including description/revision) and existing
metadata-schema ID values semantically unchanged. New definition versions with
new IDs and new metadata-schema IDs may be appended; same key/version shadowing
is rejected. Whole-record immutability is this bounded supported-profile rule,
not a universal domain rule forbidding future authorized descriptive maintenance.
No administration handler is added. Both incremental catch-up and full rebuild
apply the restriction; older histories with in-place reinterpretation fail closed
for operator review rather than being silently grandfathered or migrated.


## Independent review correction: ordered original CAS

The first completed-diff review reproduced two invalid external publications:
foreign operation instance inside a local batch, and stale additional CAS outside
the update target. Transition verification now validates every operation instance
and every declared expectation against its exact ordered pre-operation state.
An affected-resource parent OID/body lookup cache supplies initial state; a small
per-batch overlay supplies earlier operation results. Thus update A followed by
update B may require A revision 2, while B before A may require original A revision
1 and its exact digest. Newly created Nodes are likewise visible to later Relation
creation expectations. No present principal grants or final-publication heads are
substituted for that historical prestate. The shared unique-OID request/verification
cache prevents repeated canonical blob loads; no full parent tree or receipt scan
is added. Invalid incremental advancement and explicit rebuild leave the accepted
signed checkpoint unchanged.
