# Obsidian fit — four bounded workflows

2026-10-22. Verdict: **native editor with a THIN ADAPTER**, no initial custom plugin/sidebar. Evidence reused from [Phase 1 workflow/source review](../obsidian-integration-assessment.md); no app/plugin installed, no real vault modified, no screenshots or live usability test. Feasibility is reasoned; version-specific behavior and user comfort are **UNVERIFIED**.

| Scenario | Classification | Minimum workable workflow / evidence |
|---|---|---|
| A1 Human Node editing | **NATIVE** authoring; **THIN ADAPTER** adoption | Ordinary Markdown body + flat text/list/date/number Properties. Native Properties/editor/templates suffice; Core validates only on explicit reconciliation or later file scan, including while previously offline |
| A2 Independent Relations | **THIN ADAPTER**, native two-hop navigation | One Markdown Relation note, independent Git revision and owner Cluster; Properties edit predicate/endpoints; endpoint links give native backlink/Graph navigation. Validation and display consistency require reconciliation, not a sidebar |
| A3 Logical Collections | **NATIVE** organization; **THIN ADAPTER** validation | Two Collection notes can link to the same Node file. Optional parent/Cluster Properties supply hierarchy. Core enforces one-Cluster membership/acyclic parent and structural permissions; no virtual filesystem or duplicate Nodes |
| A4 Protected revisions | **THIN ADAPTER** | Editable private draft and separately named approved materialization from exact retained Revision; submit/approve/revoke through a small trusted command. Raw file edits never directly change selected approved state |

No identified **PLATFORM GAP** for these four initial scenarios under the stated compromises. A requirement for native direct typed edges, immediate offline revocation of delivered files or perfectly synchronized concurrent multi-file editing would exceed what is established here; none should be silently promised.

## Concrete fixtures and minimal reconciliation

These are descriptive examples, not schemas or files created in a vault. Use stable ID-based filenames to reduce rename ambiguity; titles remain author-friendly Properties.

**A1:** `Nodes/n-a.md` has ID `n-a`, type `claim`, title `Retry budget`, ordinary body text. Human changes title/body offline. Reconciliation compares recorded base with captured bytes, safely parses constrained YAML, verifies ID/type/provenance/current policy and either commits a new Revision, retains a candidate, or preserves invalid/conflicting bytes with a diagnostic. No watcher daemon is required for correctness: startup/explicit scan suffices. Timestamp/mtime alone cannot be the CAS token. Human submission identity must not falsely attribute every raw filesystem edit to that human.

**A2:** `Relations/r-a.md` Properties contain `id: r-a`, `owner_cluster_id: c-a`, `source_id: n-a`, `predicate: supports`, `target_id: n-s`. Its body provides `[[Nodes/n-a]]` and `[[Shared/n-s]]` navigation. Canonical endpoints are the Properties; body links are a display projection. Editing predicate/endpoint Properties is ordinary native editing followed by `relation.update` validation. A mismatched display link is a visible reconciliation conflict; do not silently treat it as an endpoint change. A small explicit refresh command can regenerate the Relation note's links after confirmed changes. Do not write inverse links into either endpoint Node.

Native Graph/backlinks see links between notes: `n-a — r-a — n-s`, not a direct typed edge. Predicate is visible in Relation title/Properties. Two-hop navigation is a reasonable **initial recommendation**, not a tested Owner preference. It preserves separate edge identity/revision and keeps private assertions out of the Shared Node file. Generic prose wikilinks remain navigation, not canonical typed assertions. No sidebar is justified for these tasks yet.

**A3:** `Collections/Reading.md` and `Collections/Current.md` both contain `[[Nodes/n-a]]`; `Collections/Queues.md` has a parent reference to Reading and same Cluster ID. This is one Node file and several private organizational references. Link-list entries are the Collection's canonical references after validation, not generated Node membership Properties. Removal changes only the Collection; Node deletion, Cluster membership and publication remain separate. Ordinary folder organization or optional Bases views can aid browsing, but neither enforces domain policy.

**A4:** `Drafts/n-a.md` remains editable; `Approved/n-p--r3.md` displays a publication/selection derived from exact approved bytes, with provenance identifying the source Revision and the last materialized generation. Publication identity remains the recommended distinct-ID snapshot from Phase 1. Approval is an authenticated exact Proposal action, never a manually typed `approved: true` Property. Approval status can be a separate generated notice/index so it is not confused with the immutable Node bytes.

A changed approved display file is preserved as conflicting input or an explicitly authorized new candidate; Core still serves only the approved selection. Offline Obsidian can show stale approval/revocation information. Current Core rights govern delivery after reconnection; neither revocation nor a read-only label erases previously delivered bytes. Physical read-only materialization is useful only if the OS account arrangement enforces it; same-user plugins can otherwise modify files.

## Minimum integration surface

One small human command/CLI surface is sufficient initially: reconcile with conflict report; refresh selected displays during coordinated handoff; submit exact Proposal; record authorized review/approval/revocation. Standard files handle prose, Properties, links, Collections and review explanations. No generalized synchronization framework, custom graph renderer, virtual folders, extra editor REST endpoint or plugin installation is required.

The main limitation is synchronization, not note editing. Core serves committed Git state; the open human vault may contain older committed files and newer unmanaged edits. Avoid automatic replacement of actively edited files. At a quiescent handoff, compare bases and preserve conflicts before refreshing; otherwise leave files alone and present pending changes. See [storage guarantees](architecture-decision.md#b-storage-two-nodes-and-one-relation-one-committed-result) and Owner decision O1. Unattended race-free overwrite preservation remains UNVERIFIED; a plugin lock does not control arbitrary external writers.

Evidence: Phase 1 inspected official [Properties](https://obsidian.md/help/properties), [Graph View](https://obsidian.md/help/plugins/graph), [Bases](https://obsidian.md/help/bases) and [plugin security](https://obsidian.md/help/Extending%2BObsidian/Plugin%2Bsecurity) documentation. These establish native feature boundaries, not tested interaction quality. No new research or custom UI is needed to choose the initial representation.
