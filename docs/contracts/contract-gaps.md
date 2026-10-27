# Contract gaps and explicit deferrals

This register classifies domain/API gaps, not a request to implement every handler. [Coverage](contract-coverage-matrix.md) is the operation inventory. Each deferred row below references an explicit profile supplying its technical prerequisites, activation criteria, planned conformance tests and compatibility risk. Owner decisions remain [open](../domain/open-decisions.md).

## Confirmed M1.2 structural corrections

1. `NodeCreate.payload.node_id` separates stable resource identity from request identity. It is optional only for unreleased M1 compatibility; omission preserves the exact original allocation rule and persisted request hashes. Runtime honors explicit identity; request identity remains durable operation evidence. No copy/fork/import handler is implied.
2. `knowledge#/$defs/RelationRevision` records immutable identity, logical revision, full exact Relation snapshot (including predicate version/endpoints/lifecycle), digest and recorder. Shape cannot prove digest equality, relation identity equality, previous-revision linkage or immutability. M2.1 now persists and validates these records; mutation/history delivery remain absent.
3. Historical receipt validation in M1.2 depended on current heads/admission. M2.1 resolves original committed effects and exact admission, separately authorizes replay, and provides explicit legacy migration. This foundation is implemented; mutation and authorized history delivery are separate M2.2/M2.3 prerequisites. Never weaken current integrity checks. Before enabling updates, persist immutable full Node/Relation effect bytes and original admission under logical RevisionRefs; verify receipt against those effects, then separately authorize replay under current policy. Migrate old committed create effects explicitly from their original committed trees; missing bytes fail closed.
4. NodeRevision now permits an immutable exact `snapshot: NodeContent`; new M1 creations populate and digest-check it. Legacy metadata-only records lack historical body. Git retention is not a public historical read contract. M2 must pin complete old content and type/schema versions, CAS heads independently, preserve original receipt effects and test retry after two later revisions/revocation/restart.
5. Membership currently distinguishes Node head from optional Cluster `approved_revision`/`approval_id`; candidate NodeRevision and Proposal are separate records. Publication snapshot has separate manifest. Cross-record equality/exact selection is semantic; O2 Relation breadth/O4 read composition remain open. There is no ambiguous claim that mutable Node head equals an approved selection.

6. Two confirmed exact-history requests exist: NodeRevisionRead/RelationRevisionRead require typed resource-specific logical RevisionRefs, not mutable head selectors. Original M1 explicitly rejects them. M2.2 activates the bounded exact Node subset; Relation history and range/history listing remain deferred. See [M2.2 verification status](../core/m2-2-validation.md).

## Naming discrepancies

Catalogue `node.search` versus wire `knowledge.search`; catalogue `relation.retire` versus wire `relation.delete`; Collection rename/reparent/reference actions versus wire `collection.update`; preserve/copy/export/import spellings are mapped as distinct rows. Generated class `ProposalRecord` has wire discriminator `proposal.create`; `ApprovalRecord` is `approval.issue`; `AccessRequestSubmit` is `access.request`. Class names are not additional wire aliases. No automatic alias or rename is adopted. Before implementing each family, pick its public name by explicit compatibility review and versioned conversion. Likewise trusted `membership.admit` is not silently renamed to catalogue `membership.admit_on_create`.

## Family assessment

| Family | Meaning/lifecycle | Structure | Protocol | Authorization / transaction | Runtime / tests |
|---|---|---|---|---|---|
| Common | stable scoped identity/version/error meaning | primitives and typed immutable revision refs | no standalone operation; reused everywhere | no authentication/authorization or transactions implied | independent validators/type fixtures only |
| Operations | explicit per-operation protocol, not a generic interpreter | 36 tagged request variants | exact revision-read requests; dedicated query/admin gaps remain | current capabilities and CAS remain business obligations | M1 four create/read handlers plus M2.2 Node update/exact history; [actual gates](../core/m2-2-validation.md) |
| Knowledge | confirmed boundaries; O4/O2 selections open | Node/Revision/Membership/Collection/Relation/Asset/ExternalReference; RelationRevision | bounded Node history; Relation history/admin absent | cross-record obligations not schema-enforced | M1 Node/Relation create/read plus M2.2 Node replacement/history subset; deployment unverified |
| Governance | exact immutable evidence/disposal; O2/O3 effects open | Proposal/Review/Approval/revocation/disposal records | existing record/revoke/route wrappers partial | execution/revocation/consumption/retention not implemented | absent; structural/parity corpus only |
| Control | granular principal/grant/scope semantics confirmed | principal/grant/audit/access records | grant administration missing | authenticated policy engine not implemented | trusted M1 host bindings only |
| Snapshots | independent identity/remap/provenance | manifests / mappings | export/import requests partial | closure/disclosure/admission semantic | absent; shape fixtures |
| Authoring | raw bytes unmanaged; O1 open | authoring inputs/conflicts | scan/commit missing | preserve all bytes, underlying rights | absent; shape fixtures |
| Transaction | one-instance atomic/ref boundary | batch/receipt/event/read envelopes | status/recovery/events absent | CAS/current policy/replay M1 bounded | real disposable Git CAS/recovery tests; physical durability unverified |

## DF-M2

**Immutable revisions; first target M2.** M2.2 supplies bounded private Node replacement
and exact historical delivery. Relation mutation/history, range enumeration and
broader protected selections remain deferred; structural shapes alone are not
executable semantics. [Validation](../core/m2-2-validation.md) records actual gates.

Prerequisites: M2.1 immutable snapshots, original admission/receipt resolution and
explicit backfill, followed by M2.1.1 authenticated frontier. Node activation uses
M2.2 target CAS/current-policy history guards and explicit projection upgrade;
M2.3 must provide independent Relation transition evidence and endpoint authority.
Migrate incomplete legacy history before mutation; no read-time backfill.

Owner decision: none for basic immutable history; O2/O4 only if approved graphs or multi-membership are included.

Activation / planned conformance: Mutation/restart/retry after a later revision passes exact receipt and negative history authorization tests.

Compatibility/migration risk: Existing mutable head and closed request consumers require explicit migration; never rewrite on read.

## DF-M3

**Human reconciliation; first target M3.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: M2 plus Owner O1 timing/handoff decision and preserved raw-byte conflict protocol.

Owner decision: O1.

Activation / planned conformance: Offline valid edits reconcile under underlying capabilities; invalid/conflicting bytes survive restart.

Compatibility/migration risk: Raw vault bytes cannot overwrite committed/approved state; versioned reconciliation plan needed.

## DF-M4

**Authorization and ingress; first target M4.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: Registered principal/grant lifecycle, current-policy scopes and physical deployment isolation; O4 before multi-membership serving.

Owner decision: O4 for multi-membership composition.

Activation / planned conformance: Direct calls and authenticated MCP pass resource/condition/non-discovery/revocation truth tables.

Compatibility/migration risk: Existing trusted bootstrap grants are not transport credentials; no assumed permission inheritance.

## DF-M5

**Queries and organization; first target M5.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: M2 independent revisions, M4 disclosure filtering, pinned generation and rebuildable indexing; explicit hierarchy structural policy.

Owner decision: O4 for multi-membership query views.

Activation / planned conformance: Cycles/cross-Cluster parents rejected; filtering precedes ranking/count/cursor/expansion; rebuild reproduces authorized answers.

Compatibility/migration risk: Query/cursor and hierarchy protocols require explicit new contracts; no folder ACL inference.

## DF-M6

**Governance and publication; first target M6.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: M2 exact revision selection, M4 current authority, exact Proposal/Review/Approval; O2 for Relation assertion approval.

Owner decision: O2 for Relation approvals; O3 for revoked selections.

Activation / planned conformance: Modified parameters/revisions/revocations reject at commit; exact approved Node bytes are preserved. Publication follows the confirmed preferred direction of preserving private source; the exact identity/selection representation must receive M6 compatibility review rather than silently adopting historical D04 snapshot identity.

Compatibility/migration risk: Naming mismatch wrappers need explicit version conversion; no generalized graph snapshots.

## DF-M7

**Lifecycle and disposal; first target M7.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: M4 authorization, durable preservation, M6 governed publication; Owner O3 retention/revocation/expiry choice.

Owner decision: O3.

Activation / planned conformance: Restore uses current admission; purge/expiry remain separate; preservation survives crash before destructive expiry.

Compatibility/migration risk: Tombstone never promises Git/backup erasure; erasure scope/retention migration must be reviewed.

## DF-M8

**Portability and services; first target M8.** Reason: runtime outside create/read M1 safe subset; structural shapes are not executable semantics.

Prerequisites: Stable export/import manifests, explicit ID remap and source/destination checks; scoped committed events/maintenance boundary.

Owner decision: none for identity remap; policy prerequisites still apply.

Activation / planned conformance: No imported grants or foreign aliases; offline closure and restart-safe delivery/status fixtures pass.

Compatibility/migration risk: Cross-instance bundles remap IDs explicitly; at-least-once delivery never reexecutes domain effects.

## Per-capability deferrals

Each row is an explicit deferral. Its linked profile is part of the row and supplies all fields above; runtime remains absent unless labelled M1-partial.

| Capability ID | Operation | Current status | Reason / prerequisite / acceptance / test / risk profile | First target |
|---|---|---|---|---|
| CAP-001 | `access.request` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-002 | `approval.issue` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-003 | `approval.read` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-004 | `approval.revoke` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-005 | `asset.add` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-006 | `asset.gc` | absent runtime | [DF-M8](#df-m8) plus [DF-M7](#df-m7); Owner O3 retention, live/historical/publication reference closure, preservation-before-GC tests and irreversible-history risk must be satisfied | M8 |
| CAP-007 | `asset.read` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-008 | `asset.reference` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-009 | `asset.register` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-010 | `asset.unreference` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-011 | `batch.recover` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-012 | `batch.status` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-013 | `batch.submit` | M1 partial; broadened semantics not implemented | [DF-M2](#df-m2); retain existing Core tests and add profile conformance before activation | M2 |
| CAP-014 | `cluster.close` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-015 | `cluster.configure` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-016 | `cluster.create` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-017 | `cluster.list` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-018 | `cluster.ownership.transfer` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-019 | `cluster.policy.change` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-020 | `cluster.policy.read` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-021 | `cluster.read` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-022 | `collection.create` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-023 | `collection.list` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-024 | `collection.node.add` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-025 | `collection.node.remove` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-026 | `collection.read` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-027 | `collection.remove` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-028 | `collection.rename` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-029 | `collection.reparent` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-030 | `collection.update` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-031 | `core.bootstrap` | M1 partial; broadened semantics not implemented | [DF-M4](#df-m4); retain existing Core tests and add profile conformance before activation | M4 |
| CAP-032 | `core.generation` | M1 partial; broadened semantics not implemented | [DF-M4](#df-m4); retain existing Core tests and add profile conformance before activation | M4 |
| CAP-033 | `disposal.preserve_copy` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-034 | `disposal.route` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-035 | `event.delivery.status` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-036 | `event.publish_pending` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-037 | `event.read` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-038 | `external_reference.check_result.ingest` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-039 | `external_reference.create` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-040 | `external_reference.read` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-041 | `external_reference.update` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-042 | `freshness.review.ingest` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-043 | `grant.issue` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-044 | `grant.revoke` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-045 | `index.rebuild` | bounded trusted-host history projection; public/search API absent | M2.1.1 authenticated frontier/full audit; SearchIndex/FTS and external authorization/protocol remain [DF-M5](#df-m5) / DF-M8 | M2.1.1 host; M5/M8 broader scope |
| CAP-046 | `knowledge.search` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-047 | `membership.admit_on_create` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-048 | `membership.attach` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-049 | `membership.detach` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-050 | `membership.promote` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-051 | `membership.select_revision` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-052 | `node.archive` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-053 | `node.copy` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-054 | `node.create` | M1 partial; broadened semantics not implemented | [DF-M2](#df-m2); retain existing Core tests and add profile conformance before activation | M2 |
| CAP-055 | `node.delete` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-056 | `node.fork` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-057 | `node.history.read` | range/list API absent; exact-revision grant used by CAP-065 | [DF-M2](#df-m2); define versioned pagination/cursor/disclosure protocol and pass current-policy history conformance after exact-read foundation | M2 follow-on |
| CAP-058 | `node.list` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-059 | `node.propose_revision` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-060 | `node.publish` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-061 | `node.purge` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-062 | `node.read` | M1 partial; broadened semantics not implemented | [DF-M2](#df-m2); retain existing Core tests and add profile conformance before activation | M2 |
| CAP-063 | `node.request_disposal` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-064 | `node.restore` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-065 | `node.revision.read` | bounded exact Node subset; [actual validation](../core/m2-2-validation.md) | [DF-M2](#df-m2); independent history/current disclosure; range and protected scopes still require exact protocol/policy | M2.2 subset; M4 broader scope |
| CAP-066 | `node.search` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-067 | `node.unarchive` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-068 | `node.update` | bounded private sole-membership replacement; [actual validation](../core/m2-2-validation.md) | [DF-M2](#df-m2); mandatory CAS, immutable new revision, current update authority; governed/protected scope requires M4/M6 | M2.2 subset; M4/M6 broader scope |
| CAP-069 | `node_type.read` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-070 | `node_type.register` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-071 | `node_type.revise` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-072 | `permission.effective.list` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-073 | `predicate.read` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-074 | `predicate.register` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-075 | `predicate.revise` | absent runtime | [DF-M4](#df-m4); operation-specific rights and exact requested effect must pass profile conformance | M4 |
| CAP-076 | `proposal.commit` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-077 | `proposal.create` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-078 | `proposal.read` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-079 | `reconciliation.commit` | absent runtime | [DF-M3](#df-m3); operation-specific rights and exact requested effect must pass profile conformance | M3 |
| CAP-080 | `reconciliation.scan` | absent runtime | [DF-M3](#df-m3); operation-specific rights and exact requested effect must pass profile conformance | M3 |
| CAP-081 | `relation.create` | M1 partial; broadened semantics not implemented | [DF-M2](#df-m2); retain existing Core tests and add profile conformance before activation | M2 |
| CAP-082 | `relation.delete` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-083 | `relation.history.read` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-084 | `relation.integrity.check` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-085 | `relation.query` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-086 | `relation.read` | M1 partial; broadened semantics not implemented | [DF-M2](#df-m2); retain existing Core tests and add profile conformance before activation | M2 |
| CAP-087 | `relation.retire` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-088 | `relation.revision.read` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-089 | `relation.traverse` | absent runtime | [DF-M5](#df-m5); operation-specific rights and exact requested effect must pass profile conformance | M5 |
| CAP-090 | `relation.update` | absent runtime | [DF-M2](#df-m2); operation-specific rights and exact requested effect must pass profile conformance | M2 |
| CAP-091 | `review.read` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-092 | `review.record` | absent runtime | [DF-M6](#df-m6); operation-specific rights and exact requested effect must pass profile conformance | M6 |
| CAP-093 | `snapshot.export` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-094 | `snapshot.import` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-095 | `snapshot.import.commit` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-096 | `snapshot.import.preview` | absent runtime | [DF-M8](#df-m8); operation-specific rights and exact requested effect must pass profile conformance | M8 |
| CAP-097 | `trash.expire` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-098 | `trash.list` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |
| CAP-099 | `trash.read` | absent runtime | [DF-M7](#df-m7); operation-specific rights and exact requested effect must pass profile conformance | M7 |

## M2.1 trusted maintenance coverage

`inspect_history` and `apply_history_migration` are trusted-host Python functions,
not wire OperationRequest alternatives. Their canonical durable result is
`transaction.schema.json#/$defs/HistoryBaseline` (generated Python
`generated.v1.transaction_schema.HistoryBaseline`, TS `transaction.js:HistoryBaseline`).
They require the existing trusted bootstrap binding, deterministic dry-run/source
fence, retained original history and exact plan validation. See
[M2.1](../core/m2-1-immutable-history.md); no agent migration ingress is defined.

| CAP-100 | `history.inspect`; trusted-host inventory | implemented bounded host API | No public operation; any future agent/service exposure needs M4 authenticated maintenance authority and a separate reviewed protocol | M2.1 host; M8 external |
| CAP-101 | `history.migrate`; trusted-host backfill | implemented bounded host API | No public operation; any future agent/service exposure needs M4 authority, source fence, exact plan and retained ancestry conformance | M2.1 host; M8 external |


## M2.1.1 history operations

The [derived history index](../core/m2-1-1-history-hardening.md) is disposable,
authenticated locator metadata, not another canonical authority. CAP-045 now has
the trusted `rebuild_history_index` subset; its external/public/SearchIndex contract
remains deferred. CAP-102 adds trusted `audit_history` full verification and safe
structured diagnostics. These are Python host functions under bootstrap/recovery
authority, not new public operation discriminators or generated protocol models.
No FTS5, graph search, update or historical-read handler is implied. The
[M2.1.1 validation gates and readiness limits](../core/m2-1-1-validation.md) are
recorded as complete for the bounded foundation; M2.2 remains a separate slice.

| CAP-102 | `history.audit`; trusted-host full verification | bounded host API | Public maintenance requires M4 authenticated scopes and M8 versioned protocol; activation must retain diagnostic non-disclosure and canonical/index separation | M2.1.1 host; M4/M8 external |
