# M2.1 immutable history and receipt foundation

Historical implementation record: [M2.1.1](m2-1-1-history-hardening.md) supersedes
the ordinary full-ancestry read strategy with an authenticated derived frontier.
The immutable evidence/receipt/migration semantics below remain authoritative;
full retained verification is now explicit audit/rebuild or incremental catch-up.

Status: implemented; Stage A and final independent recheck both PASS WITH WARNINGS.
Executed checks and limitations are in the validation record. Authority: the Owner's M2.1 implementation specification against
`524d954ea1c6e26efc8a81d83052bc5ebf0e46a5`. This extends the
[accepted decisions](../domain/accepted-decisions.md) and
[invariant register](../domain/invariant-register.md), not their policy scope.
No Node/Relation mutation or historical-read handler is authorized here.

## Preliminary contract and persistence audit

The audit inspected application, operation strategies, receipt store, repository,
domain rules, access control, bootstrap, Git adapter and its CommitStore port;
the relevant canonical knowledge/common/transaction/operation definitions; and
the required M1.2 decision, transition, API, gap, compatibility and roadmap documents.

| Question | Baseline finding and consequence |
|---|---|
| 1. Is NodeRevision.snapshot sufficient? | Yes for exact NodeContent: body, title, properties, explicit type/version, provenance, optional metadata-schema identity, validity and extensions. It is not a complete Node head (lifecycle/timestamps/reference), nor admission evidence. New M1.2 creates include it; earlier records may omit it. Metadata schema/type definitions remain retained versioned dependencies. |
| 2. Is RelationRevision complete? | Its snapshot is the complete closed Relation: stable ID, numeric revision, owner Cluster, explicit scoped endpoints, predicate/version, lifecycle, provenance and optional validity. Endpoints identify resources rather than implicitly pinning their changing content. This is exact original Relation meaning, not an approved graph or endpoint snapshot. Baseline runtime rejects RelationRevision records and never persists them. |
| 3. Where is admission? | A canonical Membership stores independent ID, Node/Cluster, admitting principal/time, admission provenance, lifecycle and numeric revision. OperationResult contains Node and Membership refs in order. The current record is mutable in the intended domain; its original committed bytes are the immutable admission evidence. Relation owner/endpoints occur in its original complete record. |
| 4. Which facts are in receipts? | Transaction/key, normalized request digest, actor, generation, commit time, ordered request IDs/operation IDs, resource refs and revision refs. Original BatchRequest is retained separately. Node revision ID is also in the head; original Relation revision ID currently exists only in the receipt. Membership identity is in the result. No receipt contains the entire effect or a Git commit locator. |
| 5. What do hashes bind? | Request digest binds normalized original envelopes, operation order, parameters and expectations. Generation digest binds knowledge/config paths and bytes, excluding descriptor, requests and receipts. Git tree/commit binds all bytes including actor and result. Existing pair validation checks request/result linkage, but head equality currently supplies effect verification. A self-consistent edited receipt is not independently authenticated by request digest alone. |
| 6. Can the source commit be found? | Receipt.generation is a noncircular logical locator: search retained managed first-parent ancestry for its exact descriptor, then require identical receipt/request bytes and verified generation digest. Existing CommitStore lacks ancestry enumeration; a narrow ancestry method is needed. Require one original publication, rejecting ambiguous repeated generations, merges, missing ancestors and unavailable objects. A commit cannot contain its own final hash. |
| 7. Can legacy data migrate safely? | Only from verified original creation trees identified above, never the present head. Complete Node snapshots are checked; missing snapshots can be recovered from the original Node's exact content and original digest. RelationRevision uses the receipt's existing revision UUID, never a replacement. Original Membership is recovered from the receipt's exact Membership ID. Missing/conflicting evidence means repair required. |
| 8. Are existing variants sufficient? | Existing NodeRevision/RelationRevision represent complete immutable content and receipts bind logical results. Existing families have no durable migration result, and enriching a legacy NodeRevision in place would change existing historical bytes. A narrow snapshot supplement plus migration result is proposed below; no new family is needed. |

## Implemented boundary

Use a focused historical-effect resolver shared by receipt validation and trusted
migration. It resolves original generation from managed ancestry, validates the
original tree's canonical records/config, generation digest, exact receipt/request
pair, ordered results and actor, then selects original effects by exact result
references. It must not recursively validate every ancestor's receipts through
the normal snapshot loader. Parse/validate a pinned tree separately from receipt
effect resolution to avoid cycles. Cache only within one resolution call if needed;
no persistent cache/index subsystem.

For a Node result check allocated ID, exact original NodeContent, logical revision
1, exact revision UUID/ref, recorder/provenance/digest, and exact original Membership
ID/Cluster/admitting actor/time. For a Relation result check complete original
Relation against request, logical revision 1, receipt UUID, snapshot digest and
recorder. New RelationRevision records are published with the Relation and receipt.
New NodeRevision snapshots remain mandatory in runtime creation.

Current retained immutable revision records must equal their original committed
records, not current heads. The resolver must also reject removal or alteration
of retained immutable history. For legacy additions, a migration record must
explain exactly which original-generation evidence was recovered.

Replay remains separate: validate historical truth first through repository
validation, then use current live membership/owner/endpoints and the existing
creation/admission grants before returning the old receipt. Historical admission
is never a grant. Preserve create-only callers without adding an implicit read
grant requirement. Fail concealed when current required scopes are inaccessible.
Changed request under the same scoped key conflicts; child operation keys cannot
partially replay an earlier batch.

## Legacy preservation and canonical amendments proposed

Do not rewrite an existing metadata-only NodeRevision even when adding a snapshot
would be semantically correct. The narrow knowledge record
`NodeRevisionSnapshot`: independent evidence ID, typed NodeRevisionRef, exact
NodeContent snapshot/digest and original GenerationRef. It supplements the existing
immutable metadata record without becoming another content revision. It is allowed
only for legacy metadata-only revisions and must match the original creation tree
and record digest. Fresh histories use NodeRevision.snapshot directly.

A canonical transaction-family `HistoryBaseline` record distinguishes fresh bootstrap
from explicit legacy migration. Fresh mode permits no migration source fields;
migrated mode requires original source commit/generation and deterministic plan
digest. Both bind actor, resulting generation, exact added paths and effects digest. The original marker's
publication is validated against retained ancestry; migrated publication must be
a direct child of the source, preserve every original byte except GenerationRef,
and add exactly the records reconstructed from original receipts. This is trusted
maintenance evidence, not a public Operation variant or a grant.

Retained original trees alone supply verification but do not materialize a complete
legacy revision snapshot for the explicit backfill/readiness gate. The supplement
provides that missing material without altering its revision's historical bytes;
its identity is evidence identity, not another Revision ID or sequence slot.
Fresh NodeRevision snapshots and RelationRevision records cannot disappear under
legacy fallback: retained marker ancestry detects downgrade/removal, and marked
repositories require every recovered record. Normal reads never write supplements.

This amends unreleased 1.0.0 explicitly; old closed readers reject new record kinds
and must upgrade pinned schema/runtime/generated artifacts together. Existing
requests and receipts are not rewritten; logical revision identities are retained.

## Explicit migration protocol

1. Trusted-host-only dry-run reads a pinned managed commit, validates legacy state
   and all original effect bindings, and returns deterministic classifications:
   complete; missing Node snapshot; missing RelationRevision; insufficient
   admission; ambiguous history; corrupt/unavailable original effects. No writes,
   timestamp allocation, UUID allocation, repair or ref update occur in dry-run.
2. Deterministic plan includes source commit/generation, exact recoverable record
   bytes and original receipt identities. Derive supplement/migration IDs from
   stable scoped plan inputs; preserve all original revision and receipt IDs.
3. Explicit apply requires trusted bootstrap/maintenance authority and the exact
   reviewed plan. Under the existing writer lock re-read source, compare source
   commit/generation/plan digest, validate all destination records, preserve all
   original bytes, add only proven missing evidence and durable migration result.
4. Publish one child commit through existing prepare/update-ref CAS. No working
   tree reset/checkout. A prepublication interruption leaves no visible effects;
   rerun recomputes the same plan. An afterpublication retry returns the durable
   matching migration result without another generation. CAS races fail without
   partial publication. Any blocking inventory item prevents the whole apply.

Ordinary reads never trigger migration. Legacy support is explicit: validated
create-only legacy repositories can remain readable while inventory reports their
missing materialized snapshots; M2 mutation activation requires successful migration.
Normal receipt validation still resolves their original committed effects and
fails closed if those effects are unavailable. No reconstruction from current
heads occurs, even when their bytes happen to match.

## Retention and readiness

Managed ancestry is required retained authority, not unreachable loose objects.
All original creation and migration commits must remain reachable through the
managed first-parent chain. No shallow-history assumption, replacement objects,
merge ambiguity, rebased/imported replacement history or garbage-collected missing
source is silently accepted. Repository administrator rewriting all trusted
history is outside cryptographic attestation: this is integrity within retained
trusted Git, not a signed external ledger. Backups must retain the ancestry too.

H01/H02/H03/H04 map to I08; H05/H06/H07 to I04/I07/I08/I17;
H08 to I01/I02/I03; H09 to I08/I09/I17; H10 to I04/I17. Tests cover
unique IDs/logical sequence, exact snapshots, original admission, restart/unrelated
commit replay, whole-batch linkage, corruption/missing origin, explicit migration,
interruption/CAS/idempotency and authorization revocation. Isolated future-head
fixtures exercise historical verification against Node revisions 2/3, independent
Relation heads and changed live Membership without relaxing production's bounded
single-membership profile. Historical permission delivery remains simulated only;
no public history handler is introduced.

Logical single-ref atomicity does not establish physical flush/power-loss durability,
backup coherence, raw Obsidian-file visibility or deployed process isolation.
O1–O4 remain open. M2.2/M2.3 require their own reviewed mutation/read authorization
work after this foundation passes.

## Trusted host invocation and implemented scope

```python
from second_brain_core import inspect_history, apply_history_migration

# core is constructed by a trusted host with bootstrap=True; never expose this
# object or maintenance function through an agent-controlled request adapter.
plan = inspect_history(core)       # deterministic, no object/ref/worktree writes
if plan["status"] == "eligible":
    result = apply_history_migration(core, plan)
```

A blocking report is sanitized and distinguishes unavailable effects, ambiguous
history, insufficient admission evidence, inconsistent history and corrupt original
state. It does not repair partial subsets. Missing legacy Node snapshots preserve
existing metadata-only NodeRevision bytes; new NodeRevisionSnapshot supplements
use deterministic instance/revision-scoped IDs. Missing RelationRevision uses its
original receipt UUID and committed actor/time. Every rerun validates the exact
original plan, including after unrelated commits, before returning the durable
HistoryBaseline without publication.

New files are `history.py` (original-effect resolution) and `migration.py` (narrow
trusted maintenance); existing strategies, domain validation, repository parser,
bootstrap and Git ancestry port are extended. No new public agent operation, update
handler, history handler, storage subsystem or dependency was added. Current normal
snapshots retain the create-only Relation profile; isolated future-head tests call
the historical verifier directly without weakening public domain validation.

Execution evidence and limitations are in [M2.1 validation](m2-1-validation.md).
