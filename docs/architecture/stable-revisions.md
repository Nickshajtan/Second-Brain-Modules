# Stable revision semantics review

New recommendation, not implemented: **Stable points to an approved immutable node
revision while a new candidate may evolve independently.** This supersedes the prior
recommendation that any head edit immediately removes the node from Stable eligibility.
Q03 remains open for acceptance and precise historical relation-resolution semantics.

| Choice | Benefit | Cost / failure mode |
|---|---|---|
| Prior head-only eligibility | Simple current-file reads; no historical retrieval in Stable path | Ordinary drafting makes reviewed knowledge disappear; callers can lose useful context until reapproval |
| Approved pointer + candidate head (recommended) | Reviewed revision stays visible; promotion atomically replaces pointer; previous revision recoverable | Requires reliable immutable revision lookup, approval/revision CAS and explicit relation/sensitivity semantics |

Markdown/YAML stays authority. The candidate working file represents the current editable
revision; immutable approved bytes must be recoverable from a verified knowledge revision
locator/Git object with content hash. A membership manifest stores node ID, approved
revision, approval record and manifest revision. Do not keep an independently mutable
approved body in SQLite. Git history must retain referenced objects; garbage collection,
history rewrites and backup policy cannot discard approved revisions. Missing or invalid
approved content fails closed, rather than substituting current draft content.

Promotion validates the exact candidate revision/hash and approval, checks expected
membership revision, and commits the pointer change with approval consumption/audit
through the future journal. Editing a candidate does not update the pointer. Concurrent
promotion/drafting requires explicit expected revisions; stale approval cannot approve
a newer head. Rollback of a pointer is itself an authorized audited change, not an
untracked Git reset. Previous approved revision remains recoverable subject to retention
and privacy requirements (Q06).

Relations in the approved node are those embedded in that approved revision. Targets
must be resolved using an explicit context snapshot: prefer the target's approved
pointer when traversing Stable, never silently the latest draft. A target without an
approved pointer is omitted/redacted or handled by an explicitly authorized mixed-scope
request. Pin the selected target revisions in the context manifest. This avoids claiming
that approval of one node automatically approves all future content at its targets.
The exact policy for cross-cluster references is still Q03, before M5/M10.

Provenance retains source hashes and derivation/approval records for that revision.
Authorization and revocation are current checks, even when content is historical:
an old revision cannot bypass a new sensitivity restriction or erasure. A tightening
of node sensitivity applies to historical retrieval too. Source and target citations
remain independently authorized. Nothing here implements storage, promotion or an
ACL sandbox; it establishes review obligations for M3/M5.
