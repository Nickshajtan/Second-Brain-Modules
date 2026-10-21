# Obsidian as a first-class authoring environment

Research: 2026-10-21–22. This is a source-backed workflow/design assessment with concrete proposed fixtures, **not a live Obsidian usability test or visual audit**. No screenshots, plugin installation or vault changes were performed. [P02/P04](poc-plan.md) must validate interaction quality. Confirmed constraints: [I06–I09/I18–I19](../domain/domain-model.md). Representation choices remain D03/D04/D07.

## Native authoring baseline

Obsidian supports atomic Properties types and property search/templates, but nested Properties lack native editing support. Keep author-editable metadata flat; do not put nested Relations, approval objects or provenance chains in the note. [Official Properties documentation](https://obsidian.md/help/properties).

Bases supplies local file/Property views; it does not become an independent database. This makes it suitable for an active-note table and authoring dashboard, but a Base filter is not a policy boundary or relational membership service. [Official Bases documentation](https://obsidian.md/help/bases).

Graph View connects notes through internal links; it does not import arbitrary standalone Relation YAML. Native graph navigation can remain useful without claiming it displays the approved typed domain graph. [Official Graph View documentation](https://obsidian.md/help/plugins/graph).

Proposed human-facing working note (illustrative aliases, not approved production fields):

```markdown
---
id: n-a
node_type: claim
title: Retry budgets
valid_until: "2027-01-01"
tags: [reliability]
---
Bound retries and keep an explicit retry budget.
See [[Notes/Failure handling]] for background.
```

Human edits body/title/tags/validity using normal Obsidian tools. Core validates registered type/metadata, provenance and current policy before committing a Revision. ID, revision and publication state are not writable authority merely because YAML contains them. Native wikilinks are human navigation; they do not automatically assert typed domain Relations, source disclosure, membership or supersession.

## Standalone Relations: visible, editable, one authority

Compare these designs using private `n-a`, Shared `n-s`, and Relation `r-a` owned only by private Cluster `c-a`:

| Representation | What human sees/edits | Authority and reverse-sync/conflict behavior | Assessment |
|---|---|---|---|
| Standalone YAML only | Source-mode record, no native graph edge | One authoritative edge; little native discoverability | Technically simple but does not satisfy useful navigation alone |
| Standalone Markdown Relation note with flat Properties | Named assertion note, editable predicate; links to both endpoints; backlinks lead to assertion | IDs/predicate/owner in one record; body endpoint labels generated from IDs, never another authoritative endpoint set | Recommended first experiment, not final acceptance; native graph is two-hop/reified |
| Generated wikilink section in each endpoint | Direct-looking native links/backlinks | Derive from Relation records; never infer changes back automatically. Editing generated section creates conflict requiring explicit Relation operation. Regeneration must not increment Node semantic revision or overwrite body edits | High risk: Node revision/hash boundaries and hidden private-edge disclosure; defer until simpler approach fails |
| Authoritative typed links in ordinary Node Markdown | Natural single-file editing | Making inline links canonical would change confirmed standalone ownership/revision semantics; extracting edges requires stable IDs, provenance, owner and transactional sync | Requires explicit Owner revision of requirements; cannot quietly adopt Basic Memory's model |
| Narrow sidebar/virtual graph | Selected Node's typed edges, predicate editing through operations | Read current authorized graph; editor commits exactly one Relation, no reverse sync from display | Bespoke but contained; justified if reified notes fail P02 |
| Syntax convention plus parser | Human edits an explicit edge declaration in the Relation note | One canonical declaration only; parser resolves stable IDs, reports ambiguous renamed titles; normal wikilinks remain navigation | Possible refinement; avoid inventing a language before fixtures prove need |

Proposed Relation-note fixture:

```markdown
---
id: r-a
record_type: relation
owner_cluster_id: c-a
source_id: n-a
predicate: supports
target_id: n-s
---
[[Notes/Retry budgets]] → supports → [[Shared/Failure handling]]
```

The Properties hold canonical endpoint IDs and predicate; the body line is display-only. Editing its target label must not silently redirect the assertion. Reconcile changed Properties through `relation.update`, validate endpoint permissions, preserve conflicting body edits, then offer explicit regeneration. Changing predicate revises only `r-a`. Renaming/moving an endpoint updates a derived ID→path map/display; it does not change logical identity or edge Revision. If projection bytes share the same file as canonical metadata, define separate hash/revision boundaries before production (D07).

Native Graph shows `n-a—r-a—n-s`, with the Relation title conveying predicate; it does **not** show a direct typed `n-a→n-s` edge. A native Graph screenshot and timed navigation task must establish whether that is acceptable. Standalone Markdown is allowed by independent Git versioning but its exact file encoding is proposed.

Never project the private Relation backlink into the Shared Node's globally distributed file. Human Owner's complete trusted vault may display both. An agent who reads only Shared must receive neither the private Relation note nor its inferred degree, backlinks, title or path. Scoped projections must be generated from that principal's authorized result set, not filtered cosmetically in Obsidian.

## Collections and physical layout

Keep one physical file per Node ID. A folder is a storage convenience, not a Cluster or Collection. `Collections/Reading.md` can contain links to Nodes in the same Cluster; `Collections/Reading/Queues.md` can be a child Collection note with a parent ID. This demonstrates logical hierarchy without duplicating Node files. A Node may appear in several Collection notes while its file stays in `Notes/`.

A protected Node reference may remain in a private Collection after publication/multi-membership; removing that reference requires structural permission only and cannot delete the Node. Adding/removing Node membership must invoke Membership Service, never follow folder moves or Base property edits. If Collection records are plain Markdown link lists, ingestion must resolve stable IDs and verify same-Cluster eligibility; if manifests are canonical, list notes are generated views and need explicit edit actions. That representation remains a P02 choice.

Bases can filter permitted human-facing metadata and help browse records. A generated list of Collection IDs on every Node duplicates organizational authority unless explicitly read-only derived metadata. Do not promise Bases performs arbitrary joins against external YAML manifests. Folders cannot express multi-Cluster membership without copies; symlinks/junctions undermine isolation and are excluded.

## Draft → Proposal → approved Shared → revoked

1. Human edits `Drafts/Retry budgets.md` offline. On reconciliation, valid directly editable changes commit normally; protected destination changes become separately permitted candidates. Invalid YAML/body/type changes are retained in a restricted conflict artifact with exact raw bytes and a plain-language diagnostic.
2. Human selects “submit candidate” through a thin operation command/CLI. An ordinary Markdown review note can explain the change, but the committed Proposal binds exact operation/parameters/base/candidate hashes. No custom editor is required for prose.
3. Reviewer reads the exact candidate diff and records a typed Review. Approver performs a separate explicit action on that Proposal. Editing the review note cannot forge Approval identity. Commit rechecks permissions, policy, candidate/selection CAS and revocation.
4. Proposed publication creates `Shared/Retry budgets.md` with a distinct snapshot ID and provenance to the source Revision. Author continues editing private draft; Shared consumers receive only selected approved bytes. Approved-revision materialization is derived from retained Git objects; current draft bytes are never substituted on failure.
5. Privileged revocation leaves historical Approval intact and updates a visible authorized status. Under proposed fail-closed default, Core stops serving that selection until a policy-valid replacement is selected. An offline human vault may still display stale materialized bytes; the system must label snapshot generation/last validation and cannot claim instant remote revocation of previously delivered files.

Human should see a clear “candidate / selected approved revision / pending reconciliation / conflict / revoked” distinction. These are functional requirements for P04, not claims about existing rendered UI. Use native notes/diffs/Bases for routine work; a small approval/status action is justified by authenticated intent, not by a desire to replace Obsidian.

## Protected files, offline writes and concurrent commits

Obsidian read-only mode, CSS, excluded paths, plugin command guards and Git hooks do not enforce Core invariants against arbitrary filesystem writers. Official documentation says plugins inherit Obsidian's access and cannot be reliably permission-restricted. [Plugin security](https://obsidian.md/help/Extending%2BObsidian/Plugin%2Bsecurity).

Two valid deployment patterns require different promises:

* Trusted Owner edits a complete vault; all changes are unmanaged until reconciled. Core detects and preserves unauthorized/protected edits, keeps approved selections immutable, and refuses to serve raw candidates. This protects **Core consumption**, not the on-disk view against tampering.
* Untrusted agents use separate OS identities/sandboxed authenticated interfaces or scoped projections without full `.git`, policy, cache or token access. If approved display must be physically protected, mount separate read-only materializations and keep editable drafts elsewhere. Same-user writable “protected” files cannot support that guarantee.

At startup, scan against last committed generation before serving. Watcher events are hints; rescan handles missed/coalesced events. Capture base bytes/hash, raw edit bytes/hash, actor attribution confidence and validation outcome. Human authentication of submission does not imply every raw write was performed by that human; record ingestion provenance accurately.

During batch preparation, Core readers stay on old generation; check external hashes again before publication. A simultaneous edit creates a conflict, preserves both versions and blocks unsafe replacement. Native Obsidian can observe partial multi-file publication; either materialize a stable view separately or accept documented transient display inconsistency. A plugin lock cannot make unrelated editors cooperate. Recovery must run before new commits; no auto-Git-reset resolution.

Obsidian Git can provide familiar human diffs/history. Its source instantiates Git managers and automatic commit machinery, so auto-commit/pull must be disabled on the managed branch or explicitly coordinated with the Core writer. Git backup is distinct from approval. Native human Git history may contain everything; never expose it to a scoped agent. [Plugin source](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts).

Local REST API already has broad vault/MCP integration; rebuilding a generic editor REST server would duplicate it. Its bearer-key gate and direct vault operations do not implement our cluster-specific governance. Do not give an agent its broad token against the authoritative vault. Optional use is trusted local editor automation or an independently scoped projection; Core operations remain the write authority. [Request handler](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/src/requestHandler.ts), [vault operations](https://github.com/coddingtonbear/obsidian-local-rest-api/blob/7c603fbc42918bd9ec6f34ab5b46300bac0d0eaa/src/vaultOperations.ts).

## Obsidian Experience Gap

| User task | Classification | Gap / severity / next test |
|---|---|---|
| Edit body, flat Properties, templates, ordinary links/backlinks, search | Native | Validate constrained YAML subset; no new editor needed |
| Browse filtered file/Property tables | Native Bases | Logical manifests/ACL not automatically enforced; P02 Collection fixture |
| Git diff/history for trusted human | Configurable plugin | Disable competing automatic writers; P04 conflict/recovery check |
| Typed standalone Relation navigation | Native two-hop display; direct typed view requires bespoke integration | Major proposed workflow risk: test reified notes before sidebar |
| Edit canonical typed Relation with permissions/CAS | Requires bespoke integration or explicit Core command | Native Properties are unmanaged input; P02 exact commit behavior |
| Nested logical private Collections | Native link notes plus reconciliation, or narrow adapter | Major unresolved representation; no multi-folder Node copies |
| Exact Proposal submission/authenticated approval/revoke | Requires bespoke operation integration | Critical trust requirement; use small command, native prose/diff |
| Always show selected approved Revision while private draft evolves | Requires derived materialization/status integration | Critical selection correctness; P04 stale/missing-byte fixtures |
| Enforce ACL against same-user plugins/raw filesystem access | Incompatible without deployment isolation | Critical; P03 OS deny test; UI hiding is insufficient |
| Offline editing with preserved invalid/conflicting input | Native editing + bespoke reconciliation | Critical no-data-loss requirement; P04 |
| Atomic view of multi-file raw writes to unrelated editor | Incompatible with ordinary filesystem model | Define committed Core views and documented transient human view; D02 |
| Offline revocation of already delivered bytes | Incompatible as immediate erasure | Labels/expiry and restricted distribution; no false guarantee |

## Architecture threshold and confidence

Prefer Obsidian-native authoring plus minimum Core governance provisionally: human writes standard files, Core validates/commits, derived indexes remain disposable. A platform-owned store with Obsidian projection becomes preferable only if P02 cannot give usable Relation/Collection editing without competing truth, or P04 cannot meet recovery/protected-selection needs with files as authority, **and** a platform proves bidirectional offline authoring without lossy conversion or bypass. That change would require explicit Owner review of Git/Markdown authority; richer graph demos alone are insufficient.

Confidence: 70% for documented native boundaries and source-level integration risks; low for actual interaction quality. No rendered UI, screenshots, timed tasks or user testing were inspected. P02/P04 can overturn the proposed experience design.
