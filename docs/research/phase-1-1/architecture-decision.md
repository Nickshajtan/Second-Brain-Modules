# Phase 1.1 — Lean architecture decision

Date: 2026-10-22. **CONDITIONAL GO** for an Obsidian-first Markdown/Git foundation with a passive Python Core, one managed writer, one rebuildable SQLite search/graph index and authenticated MCP as the exclusive agent interface. Conditions are the small set of [Owner decisions](open-decisions.md), not completion of four platform PoCs. This is an analyst recommendation; confirmed requirements come from supplied `task.md` §3 and the accepted [domain baseline](../../domain/domain-model.md).

Scope: existing Phase 1 evidence, concrete file/state reasoning and installed Git documentation. **Zero spikes, deployments, new dependencies, inference calls or new internet research.** Feasibility is reasoned; production recovery, deployment isolation and actual Obsidian usability remain **UNVERIFIED**. No next-slice implementation is authorized here.

## Recommended boundaries

Humans author ordinary Markdown and flat Properties offline. Core validates explicit human reconciliation and agent operations, enforces capabilities/current cluster policy, and serves committed revisions. Agents have no filesystem, Git, secret or index access: they call authenticated MCP across a deployment isolation boundary. Context assembly, scheduling, fetching, AI review, cleanup decisions and freshness evaluation stay in external harnesses/services.

Reuse the existing JSON Schema 2020-12/Python/TypeScript toolchain, Git and native Obsidian editing/link/Collection-note surfaces. Use SQLite FTS5 plus ordinary edge tables in one **derived** database; obtain exact bytes and policy from committed canonical state. Start with explicit custom authorization predicates over validated grants, not a new policy language. Keep PyCasbin replaceable and optional. A small human CLI/command can reconcile, submit and approve; it is not an alternate agent ingress. Internal Python methods still enforce authorization.

## A. Obsidian feasibility

All four workflows are viable with native files and a **thin reconciliation/governance adapter**, without a custom sidebar or large plugin. Node and Collection editing are native; independent Relation notes give two-hop navigation; approved copies/selections need explicit representation and status. [A1–A4](obsidian-fit.md) distinguishes native features from integration and unverified usability. Native Graph is a navigation graph, not proof of domain approval or policy.

## B. Storage: two Nodes and one Relation, one committed result

### Simplified authority proposal

Use one instance-managed Git ref as the committed generation. Its tree contains canonical Markdown/YAML Nodes, Relations and manifests. For the initial design, also place **small commit-critical** control changes, exact approval consumption, sanitized successful-effect audit, idempotency receipt and pending-event descriptions in private control records in that same tree. This is a deliberate durability proposal, not an assertion that every runtime record belongs in Markdown. Credentials, read/denial audit streams, transient attempts and delivery diagnostics remain separate; they cannot decide whether a domain effect committed. Their independent retention/backup and failures must be explicit.

The Obsidian working directory is the human editable surface: validated committed files plus uncommitted input. It is not what Core reads as accepted state. This refines Phase 1's already confirmed “unmanaged until reconciled” rule without making a database the content authority. Keep private control records outside Obsidian's materialized note set; hiding a directory is not a security boundary. No untrusted principal receives any part of the backing repository.

If future control state must live in a separate authoritative database, multi-store recovery coordination returns; do not pretend this simplification still applies. Small Git-backed receipts have growth, retention and lookup costs, but avoid distributed commit machinery at the current scale. Receipt lookup can use a derived index; loss of that index cannot lose the canonical retry outcome. Minimum audit/outbox records are not a generic workflow engine.

### Concrete transition, no executable experiment

Let `C0` be the accepted commit, with no `n-a`, `n-b` or `r-ab`. A batch creates both Nodes, their initial authorized memberships, and `r-ab: n-a supports n-b` owned by the permitted Cluster.

1. Under the per-instance writer lock, authenticate/authorize every operation, validate endpoint IDs, metadata, membership admission and expected aggregate versions against `C0`. Freeze the submitted bytes; do not stage the entire live vault or use the human's Git index.
2. Build an isolated Git tree containing the complete after-state and its transaction receipt/control effects. Create commit `C1` with parent `C0`. Creating objects alone does not publish the batch.
3. Recheck time-dependent expiry and all commit guards, then advance the **single** managed ref from expected `C0` to `C1` using Git's conditional ref update. A mismatch rejects/revalidates the entire batch; no partial Node/edge effect. All domain writes and policy activation use this same commit boundary.
4. Core readers resolve the ref once, then read only that commit tree for the request. They observe neither entity at `C0`, or all entities at `C1`. Recheck current authorization before delivery; a pinned content snapshot must not preserve revoked access.
5. Refresh the derived index and human-facing files afterward. Index lag is detectable by commit ID; use the matching generation or a committed-source fallback. Do not mix stale authorization or uncommitted filesystem bytes into results.

If validation/object creation/ref publication fails before the ref advances, `C0` remains accepted; unreachable prepared objects are not accepted domain effects. If publication succeeds but response/index refresh fails, **the batch succeeded**: restart locates the canonical receipt and retries projections. Never reset a published ref merely because a caller timed out. Keep reachable history and approved object locators; Git garbage collection is not a retention policy.

### Guarantees and limits

| Boundary | What the design provides | What it does not establish |
|---|---|---|
| Git objects + one conditional ref | Immutable content-addressed tree/commit; expected-old-ref check; one logical publication point | Schema validity, business guards, principal identity, audit completeness or safe editor synchronization |
| Committed Core state | Old or new entire batch when readers pin one ref and all commit-critical state shares its tree | Atomic observation of multiple independent refs, arbitrary DBs or external services |
| Raw files in Obsidian | Editable standard files, including offline input; later explicit reconcile/materialize | Simultaneous multi-file visibility or immediate display of every agent commit |
| Process crash | With intact repository/filesystem, receipt/ref determines published versus unpublished; indexes can rebuild | This phase did not execute restart/failure tests; corrupt/missing objects require fail-closed repair |
| OS/power/storage failure | Git exposes hardening controls; coherent backups are required | Default Git settings do not establish acknowledged-write survival. Object **and ref** persistence, OS/filesystem/device behavior remain UNVERIFIED |

Git alone is therefore insufficient, but a custom cross-Git/SQLite transaction journal is not initially necessary **if** commit-critical state is co-located. Durable equivalents still required: canonical transaction receipts/approval state, preserved human-input bytes and a resumable materialization/conflict record. Read/denial auditing must have its own durable sink; if mandatory audit is unavailable, fail the affected operation closed. Delivery receipts can be recorded separately, with at-least-once event delivery; they never redo a domain commit.

### Human edits and single writer

Single writer means one Core commit authority, not exclusive control of every Obsidian write. Compare captured working bytes with their recorded base; validate them as candidates, preserve invalid/conflicting originals in a restricted area and never serve them as committed content. Existing files with conflicting Core/human changes require resolution against both versions; a changed title/path cannot create a new identity implicitly.

Avoid an overwrite-heavy live materializer initially. New nonconflicting files can be offered for import; updates to existing editable files wait for an explicit **quiescent handoff** (editor closed/paused and no competing writer), with changed-file detection and preserved before-images. Without that operational assumption, leave the existing file untouched and present the committed change separately for resolution. A last-second hash check cannot prevent a noncooperating editor from writing immediately afterward. Unattended overwrite-safe synchronization with arbitrary concurrent editors is **UNVERIFIED**, not promised by file locks. Raw files can be stale/partial during a coordinated refresh while Core committed state stays atomic.

This is sufficient initially if O1 accepts visible pending synchronization. Obsidian Git auto-commit/pull, external checkout/reset and other ref writers must not mutate the managed ref. Human Git history/diff remains useful through explicitly coordinated read/history use. An engineer may choose a separate backing repo/ref/worktree arrangement; none changes the one-authority rule.

Evidence read locally: installed `git-commit-tree(1)` (object creation), `git-update-ref(1)` (expected-old-value publication; its docs explicitly distinguish per-ref atomicity from multi-ref reader visibility), and `git-config(1)` (`core.fsync`, `core.fsyncMethod`, shutdown-loss caveats). Distribution: `C:/Program Files/Git/mingw64/share/doc/git-doc/`. Public references for later review: [commit-tree](https://git-scm.com/docs/git-commit-tree), [update-ref](https://git-scm.com/docs/git-update-ref), [config](https://git-scm.com/docs/git-config). These links were not newly fetched; the installed manuals were read. No configuration was changed.

## C. Authorization and MCP

Bind authenticated connection credentials to a registered principal, instance and optional delegation/session. Request JSON never selects its own identity, Owner status or tenant. Prefer one supported MCP binding for the actual harness: launcher-bound stdio identity is possible across a controlled pipe; a network deployment needs authenticated transport, verified token scope/audience/expiry and encrypted transport. This phase chooses no SDK/protocol version and makes no assumption that MCP provides authentication automatically.

Core evaluates explicit resource/action/condition grants and cluster policy on every operation, including direct internal calls. Unknown actions/conditions deny. Owner is an authenticated administrative path with full supported visibility/recovery and audit, not an unchecked integrity bypass. Each external service has its own narrowed grants, with no background job execution inside Core. MCP is the exclusive **agent** ingress; services may use a trusted authenticated adapter or MCP without inheriting Owner authority.

| Choice | Necessary implementation | Recommendation |
|---|---|---|
| Small custom evaluator using existing primitives | Explicit allow/deny/expiry/session predicates over typed data; a resource-specific applicability rule; no arbitrary expressions or inferred role ladder | Initial choice: few domain conditions and straightforward tests; keep authorization in ordinary functions |
| Embedded PyCasbin | Configure matcher/effect/domain model and verified attributes, keep enforcement enabled, map policies and synchronize versions | Defer until actual policy composition becomes cumbersome. It replaces evaluation only, not identity, filtering, audit, commit guards or OS isolation |

Phase 1 [E06 evidence](../reuse-assessment.md#e06-casbin-and-python) establishes ABAC/deny examples but also source/release ambiguity and application responsibilities. No new evaluator comparison or installation is needed. Policy examples should remain concrete cases, not a generic language/framework.

For non-discovery, authorize candidates before snippets, pagination, counts, facets and graph expansion. Relation visibility requires Relation and both endpoints. Scope ranking/statistics to authorized content; hidden corpus contents must not influence visible totals/order. A small initial corpus can scan/filter authorized records before lexical ranking; do not approximate security with top-k global search followed by postfiltering. Cursors bind identity, selection and policy version. `node.read` grants neither history nor whole-Cluster enumeration. Conceal inaccessible direct targets as `NOT_FOUND`; sanitize logs, errors, discovery and event payloads. Replay receipts still require current authorization.

Multi-membership read policy applicability remains O4; ordinary-agent Shared/multi-cluster write protections remain fixed regardless. No new global sensitivity ladder or union-of-grants default is introduced.

### Deployment security checklist — design obligations, not executed tests

- Agent container/VM/VPS/equivalent has no canonical vault, Git objects, backup, private index, runtime socket, host credential or control-record mounts; no inherited broad plugin/API token. Separate directories alone are insufficient.
- Core runs in its own trusted environment; private roots and credentials are instance-specific. Only required authenticated MCP endpoint or controlled pipe crosses the boundary; no generic shell/file/Git tools or container-management socket bridges it.
- Bind principal and instance server-side; issue least-privilege, revocable credentials separately for agents, Owner and services; limit any delegation by action/scope/time/session.
- For network MCP, select and configure a supported authenticated binding, encryption, endpoint exposure, token validation and browser/Origin protections where relevant. For stdio, authenticate the trusted launcher/credential binding; a local pipe is not automatic trust.
- Core performs current-policy checks on all read/write/history/graph/search/event paths; caches and derived indexes cannot outlive revocation authority. Owner actions retain audit and integrity checks.
- Restrict and back up control/audit/receipt records with canonical content; keep secrets outside Git. Prevent an agent from editing the human vault through an alternate REST plugin, sync share or broad editor automation token.
- Document administrator/recovery access and the actual isolation boundary. Same-host administrator or compromised trusted Core is outside an agent-only sandbox guarantee. Deployment enforcement remains UNVERIFIED until deployed, not a reason to simulate containers now.

## D. Basic Memory decision

**Reject Basic Memory for the initial dependency set; retain it only as an optional future adapter.** This is a narrower recommendation than Phase 1's P01 comparison, not a claim the project lacks value. Phase 1 [E01/source ledger](../reuse-assessment.md#e01-basic-memory) already shows file watcher/parser/search reuse, but also independent identity/permalink and note-edge semantics, native mutation paths, substantial default runtime dependencies, branch-versus-release drift and AGPL review obligations.

Necessary initial work remains our ID/revision mapping, separate Relations, approved selections, authenticated policy filtering and safe reconciliation. A read-only Basic Memory mirror adds generation tracking, process/permission configuration and another index without removing those obligations. SQLite FTS5 plus the existing Markdown/YAML tooling direction is the cheaper justified starting surface. No parser package is installed or declared proven here; strict duplicate-key/type/body preservation remains ordinary codec work. Reconsider BM only for a demonstrated retrieval feature that removes more adapter/maintenance effort than it adds. No P01 deployment is required to make this initial exclusion.

## E. Approved graph semantics

| Alternative | Guarantee / user interpretation | Complexity / judgment |
|---|---|---|
| 1. Approved Node revision + current authorized graph | Exact approved Node bytes stay fixed; returned Relations/targets are separately authorized current selections and are labeled accordingly | Smallest recommendation. Approval does not certify every current incoming/outgoing assertion; external private Relations may still refer to Shared Node |
| 2. Node + explicitly selected Relation revisions | Approval of a bounded claim bundle freezes chosen edge meanings as well as Node bytes; omitted edges are not endorsed | Add only if O2 requires assertions within the approval promise. Target revision binding and dangling/revoked dependency rules also need definition |
| 3. Larger immutable graph snapshot | Fixed multi-node/edge/revision closure, subject to current authorization | Unjustified initially: closure, partial disclosure, retention and revocation dependencies add considerable machinery |

Recommend **1**, explicitly pending O2. Example: `n-s@3` approved; `r-a@1 supports n-s` independently changes to `r-a@2 contradicts n-s` under its private owner policy. Node bytes/approval remain `n-s@3`; graph output returns permitted `r-a@2` with its own revision/owner/status, never as part of the approved publication. A Shared-owned Relation may itself be governed by that Cluster; “current” does not mean unreviewed edges bypass its policy. Editing an edge never increments Node revision. Neither approval nor a link grants endpoint access.

Do not silently combine Node `@3` with target draft bytes in an “approved graph” response. Return provenance of Node selection and each Relation/endpoint selection independently. The external harness may record the exact result manifest for a particular context request, without requiring a canonical graph-snapshot engine. Use “approved Node snapshot” and “current authorized graph,” never an unqualified “approved graph snapshot.”

## Changes, compromises and next slice

[Simplification register](simplification-register.md) maps changed recommendations to affected Phase 1/older documents and ADR treatment. The four-PoC plan is superseded as a required next phase, not erased. New Owner constraints narrow agents to authenticated MCP with deployment isolation; filesystem projections offered as agent access in Phase 1 no longer apply. Analyst backend/evaluator/graph choices remain recommendations until accepted.

Recommended compromises: two-hop Relation navigation, no custom sidebar, explicit draft/approved/pending-sync views, a single writer, possible index/materialization lag and no demonstrated OS/storage-failure durability. These do not weaken committed batch atomicity, offline authoring preservation or current-policy enforcement. Operational deployments and production implementations must validate their actual guarantees when built; the old broad experiments are not prerequisite research deliverables.

Smallest next vertical slice, **not implemented**: one private Cluster, one authenticated MCP agent identity and Owner; human creates/edits a normal note offline; explicit reconciliation validates and commits it; MCP reads that committed Revision and conceals a denied ID. Include a single two-Node/one-Relation atomic operation and its canonical receipt to establish the chosen commit boundary, without live automatic vault overwrite, publication UI or platform deployment. Routine focused implementation tests belong with that slice, not a research crash matrix. Governed publication follows only after O2 is settled.

Documentation validation: existing offline schema/ref/fixture/OpenAPI/document-link validator passed (174 portable document links); 64 selected local cross-references, including section anchors, passed a separate check; `git diff --check` passed. No runtime, broad integration, crash or security suite was run. Pre-existing deletion of the old task brief and untracked `task.md` were left untouched.
