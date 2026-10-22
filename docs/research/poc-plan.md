# Narrow falsification plan

**Superseded as a required experimental phase by the Owner's Phase 1.1 task.** See [lean assessment](phase-1-1/architecture-decision.md). P01–P04 remain historical proposals, not prerequisites or authorization to deploy platforms/run broad tests. Phase 1.1 performs zero spikes.

Status: proposals only, 2026-10-22. **None of these experiments was built or run in this phase.** Commands below define a proposed disposable experiment harness, not existing repository commands. Do not invoke them until a later implementation task creates and reviews that harness. No production-data, dependency installation or plugin work is authorized by this document.

## Shared reproducible envelope

Create a separate disposable repository outside the real vault in the later task. Use fixed fabricated IDs (expanded into valid UUIDs if a chosen backend demands them), deterministic clock and checked-in fixtures. Record OS/filesystem, Python/Node/Obsidian versions, plugin versions/settings, exact upstream commit/package version, dependency lock, locale and test seed. No production credentials, no network egress unless explicitly part of a named test. Capture file SHA-256, Git tree/commit, authorized result manifests, sanitized events/audit/receipts and screenshots of human workflows. Hash raw invalid input before and after each run.

| Fixture | Contents |
|---|---|
| Principals | human Owner `h`, agents `a`/`b`, membership service authority `m`, Cleanup `s`; authenticated bindings distinct from JSON claims |
| Clusters | private `c-a` and `c-b`, destination `c-shared`, owned staging, private Global Archive; separate isolated Trash records |
| Nodes | `n-a` only c-a, `n-b` only c-b, approved Shared `n-s`, multi-cluster protected `n-m`; candidate and selected immutable revisions with distinguishable sentinel strings |
| Edges | private c-a-owned `r-a: n-a supports n-s`; c-b-owned hidden edge; retired/dangling fixtures; exact independent revisions |
| Organization/files | parent/child Collections in c-a, one Node linked twice; Unicode names, case-only rename, ambiguous title, duplicate YAML keys, invalid type/validity, raw deleted file |
| Assets | one shared-by-reference Git attachment, unreferenced attachment, over-budget file; Asset with stricter policy than referring Node |
| Governance | exact Proposal, typed Review, Approval, revoked/expired Approval, stale digest, changed policy and destination admission fixtures |
| Disposal | pending request, routing receipt missing, preservation receipt durable, retention hold, expired grant and restore destination |

Suggested future harness interface:

```text
python -m phase1_poc fixtures --seed 42 --output ./scratch
python -m phase1_poc run P01 --fixture ./scratch --report ./reports/P01.json
python -m phase1_poc run P02 --fixture ./scratch --report ./reports/P02.json
python -m phase1_poc run P03 --fixture ./scratch --report ./reports/P03.json
python -m phase1_poc run P04 --fixture ./scratch --report ./reports/P04.json
python -m phase1_poc verify --reports ./reports --expected ./fixtures/expected
```

Each experiment must finish with a short evidence report: PASS/FAIL/INCONCLUSIVE per assertion, actual commands/versions, hashes, observed failures, elapsed effort, production gaps and decision. A UI demonstration alone cannot pass policy or crash gates. Effort caps below are analyst timeboxes for one experienced implementer, not delivery promises.

## P01 — Basic Memory + Obsidian / bounded indexing reuse

**Decision:** D08, Option B versus focused FTS in C. Cap: 3 working days, including source/release reconciliation. First pin a release and compare required APIs to the inspected current-branch commit; do not assume v0.23.2 contains current accepted-content/scoped-search/wiki code.

**Setup:** two disposable authoring notes and standalone Relation; install pinned BM only inside experiment environment, point it at a disposable mirror. Prepare a minimal operation stub that validates and commits fixture writes with identity/revision receipts; explicitly mark it non-production. Initial pass tests BM standalone on sacrificial copies to observe rewrite/coercion behavior. Intended integration pass gives BM read access to committed mirror and no canonical write permission. Projection-generation writes, if needed, go elsewhere.

**Steps:** AI fixture client creates n-a through stub; human opens note in Obsidian, edits title/body/flat number/list/date/boolean Properties, closes Core, edits again, renames file and creates a broken link. Restart reconciler; adopt valid edit, preserve invalid edit. Refresh mirror, index, compare search and relation-derived navigation against expected ID/revision manifest. Remove index DB/cache and rebuild. Attempt BM native write/delete/move against canonical root, both by public tool and internal service path.

**Acceptance:**

1. Exact body/Properties round-trip without coercion loss or unauthorized extra writes. Every adopted change maps stable ID and source Revision; filename/permalink changes do not become new canonical identity.
2. Valid offline edit indexed at the recorded generation; invalid YAML preserved byte-for-byte and excluded from accepted Core results. Measured index lag reported, with no invented latency target.
3. Graph/search results trace to committed Node/Relation revisions. BM note-derived edges remain derived; no second editable authoritative graph. Rebuild produces identical normalized authorized IDs/revisions, not necessarily identical internal DB IDs/vector rankings.
4. All native BM mutation paths fail to alter canonical bytes under actual OS permissions. BM MCP/API not reachable with broad credentials by scoped agents. Accepted-content terminology is mapped explicitly, never treated as Approval.
5. Count parser/watch/index/query code avoided and list all adapter responsibilities/patches. Compare actual effort to a minimal FTS baseline over the same fixture set; no unsupported LOC estimate.

**Stop/go:** proceed with B only if mapping and isolation hold without maintaining a deep upstream fork, required release surface is stable enough to pin, dependency/runtime costs are acceptable and license review is cleared. Stop B if BM must own canonical writes, silently normalize domain values, or re-create most query/Relation logic in adapter. Keep C as fallback. This experiment does not prove full ACL or recovery; P03/P04 remain mandatory.

## P02 — Typed Relations and logical Collections in Obsidian

**Decision:** D03/D07; cap 2 working days before any custom sidebar. Use Owner's trusted test vault and a separately generated a-only view. Begin with reified standalone Markdown Relation notes and Collection link notes described in [workflow assessment](obsidian-integration-assessment.md).

**Steps:** navigate n-a→r-a→n-s, inspect backlinks/local Graph, change predicate in Properties, move/rename endpoint and Relation note, edit derived display target to conflict with canonical endpoint ID, create concurrent predicate edit, retire edge. Add n-a to two nested c-a Collections, remove one reference, then make n-a multi-cluster/protected. Inspect Shared-only view and attempt a hidden-target traversal. Compare optional generated endpoint-link section only on sacrificial copies if reified navigation fails.

**Acceptance:**

1. Predicate/endpoint edits result in one independent Relation Revision; endpoint Node content/revision hashes do not change for logical edge mutation. Display regeneration cannot masquerade as a Node revision.
2. Rebuild recovers identical edge ID/owner/predicate/endpoint/revision manifest. Body display edits never silently reverse-sync to canonical IDs; conflicts retain exact human bytes and offer explicit resolution.
3. In a-only view, private r-a can lead to permitted Shared n-s. Shared-only view has no r-a note, backlink, inferred hidden count or path; no inaccessible endpoint stubs.
4. One physical Node file appears in two logical Collections. Reparent rejects cross-Cluster parent/cycle; reference removal never deletes Node or membership. Protected Node remains linked in private Collection.
5. Human performs find outgoing assertion, inspect predicate/evidence, navigate target, edit edge and remove Collection reference. Record clicks, time, screenshot and correctness. Proposed go threshold: all five tasks completed without source-mode YAML for routine changes and no confusion between predicate/normal link; Owner evaluates usability. Native two-hop Graph limitation is explicitly accepted or rejected.

**Stop/go:** if workflow is understandable, retain native notes. If ordinary tasks require editing multiple canonical locations or fail permission/rename checks, stop that representation; permit at most one further day to sketch/test a narrow sidebar using existing operations. If typed direct Graph is essential and cannot be derived without revision churn/leaks, bring D07 to Owner; do not silently move edge authority into Nodes.

**Prototype boundary:** short IDs, manual schema validation and hardcoded display templates may accelerate testing but do not constitute production codecs, author identity, ACL, migration or synchronization guarantees.

## P03 — ACL, non-discovery and raw filesystem boundary

**Decision:** D01/D10 and policy evaluator fit; cap 3 working days. Implement the smallest fixture-only operation boundary and compare hand-specified policy outcomes to PyCasbin evaluation; keep authentication/OS isolation and query filtering outside the evaluator. Include which Cluster policies apply to each selected read and which ancestor permissions apply to Collection reparenting. No need to run both PyCasbin and OpenFGA unless a specific relationship requirement fails.

**Commands to add to the future harness:**

```text
python -m phase1_poc run P03 --actor a --matrix all-ingress
python -m phase1_poc run P03 --actor b --matrix all-ingress
python -m phase1_poc run P03 --matrix os-isolation --as-agent-account
```

**Assertions:** each a/b identity receives its private scope plus explicitly permitted Shared selection, without the other private scope. Exercise direct callable, CLI and whichever single agent adapter is actually proposed. Spoofing principal ID in payload fails authentication binding. Test direct known/guessed ID, list, search sentinel/prefix/empty query, total hits/facets/pagination/cursors, snippets/ranking, graph degree/backlinks/paths, selected/historical revisions, Assets, provenance, Proposal/Review/Approval, Trash, event subscription, diagnostics and idempotency replay. Add expired/session-bound grant, revocation after cache lookup, multi-resource Relation predicate, destination-denied publication, detach-then-edit batch and hidden-resource access.request.

**Acceptance:**

1. Hidden and nonexistent direct targets produce the same stable external error category and no distinguishing message/details. Compare normalized error envelopes; timing is measured for anomalies, not asserted constant-time without evidence.
2. Adding/removing hidden fixtures changes none of the authorized IDs, counts, snippets, visible rank order or pagination behavior at a fixed authorized snapshot. Cursor is unusable by another principal or after policy change without revalidation.
3. Relation returns only when relation/source/target all readable; candidate/current/history separation holds; old Approval/grant cannot restore access. No source/sink policy bypass via copy, export or archive preservation.
4. Ordinary actor cannot mutate/archive/delete Shared/multi-cluster Node, grant rights, change membership, approve, publish or purge through CRUD or nested operations. Owner recovery succeeds with audit while integrity guards still reject corruption.
5. Same-user full-vault test deliberately demonstrates bypass and is recorded as an unsupported isolation configuration. Actual proposed deployment must deny raw reads/writes of hidden files, `.git` objects, control DB/manifests, credentials, cache, backup and plugin tokens under separate agent identity/sandbox. Check junction/symlink/case escape. A readonly full-vault mount fails confidentiality.

**Stop/go:** any hidden byte/count/path leak or working raw-FS bypass in the claimed deployment blocks real agent access. Fix boundary before expanding features. A failure in PyCasbin model semantics justifies comparing another evaluator; a failure in application filtering does not justify buying a different authorization server.

## P04 — Governed revisions, batch crashes and editor races

**Decision:** D02–D06; cap 5 working days. This is the critical architecture falsifier. Build a disposable journal/committed-generation prototype with minimal Node/Relation/Membership/control/receipt/outbox records, not business services or a workflow engine. Use Windows target filesystem first; later supported OS need equivalent evidence.

**Steps:** edit private draft in Obsidian while Core offline; reconcile candidate; record Review and exact Proposal/Approval; atomically publish snapshot/select approved Revision together with Relation snapshot and Asset reference. Continue drafting without changing approved bytes. Revoke Approval; change grant/policy during prepare; send stale approval and CAS; replay identical/different payload keys. Submit nested batch with one invalid op and one approval referenced twice. Add disposal routing and durable preservation before expiry. Inject process termination at each persistence boundary.

```text
python -m phase1_poc run P04 --crash-matrix intent,stage,files,git,control,decision,receipt,outbox,index
python -m phase1_poc run P04 --editor-races before-prepare,before-publish,during-publish,after-decision
python -m phase1_poc run P04 --recover-until-stable --repeat 3
```

These phase labels are experimental hooks to be bound to the actual chosen protocol; they must not imply a particular unsafe write ordering. Include disk-full, locked file, failed Git commit/hook and missing retained object failures as well as process kills. Abrupt power-loss durability requires additional flush/storage evidence; process-kill success alone does not certify it.

**Acceptance:**

1. Core readers see old or new **entire** committed batch, never mixed Node/membership/approval/outbox/receipt state. Zero effects on failed prevalidation. Retry returns same committed receipt or safely concealed result after rights revoked; different payload conflicts. Nested operations have no independent partial commit.
2. At every crash point restart either returns exactly old state, completes exactly durable new decision, or blocks in documented repair-required mode with bytes preserved. No success receipt without durable effects; no missing mandatory audit/event/approval consumption; duplicate outbox delivery is detectable by event ID.
3. Approved content stays hash-identical while candidates evolve; Relation changes do not revise Nodes; graph selection includes explicit edge/endpoint revisions. Missing approved bytes fails closed. Review is never executable authority; stale/expired/revoked Approval cannot commit.
4. Concurrent human edits preserve exact raw/base/staged bytes with restricted conflict metadata, never silent reset. Native Obsidian partial-file visibility is documented and visually checked; Core atomicity is tested independently. Invalid YAML preserved after restart and after repeated recovery.
5. Restore after grant expiry uses current rights. Expiry without durable routing/preservation proof fails. Removing a Node reference never GC-deletes an Asset still referenced by retained approved revision. Git-history/backup bytes remaining after physical purge are reported accurately.
6. Delete derived indexes only, rebuild and compare authorized Node/Relation/revision manifest. Separately restore coherent Git/control/runtime backup and verify receipts, revocations and pending outbox survive. Repeat recovery three times without extra domain effects.

**Stop/go:** unresolved data loss, approval reuse, mixed Core committed state, lost revocation or unsafe editor overwrite blocks storage design and production contracts. Narrow raw-edit support or change authority only with an explicit Owner decision. Do not disguise a failed atomicity proof as “eventual consistency.”

## Sequencing and optional work

Run P02 early to discover authoring incompatibility; P03 establishes trust before real agents; P04 establishes durable authority before runtime implementation. P01 compares reuse in parallel conceptually but has no authority to bypass P03/P04. No temporal backend experiment is currently necessary: Graphiti/Cognee are deferred adapters, not selected dependencies. Add a temporal experiment only when a concrete derived retrieval requirement justifies backend cost and test ID/revision provenance, invalidation and rebuild determinism then.
