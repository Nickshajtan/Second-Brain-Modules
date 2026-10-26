# M1.2 reconciliation and validation record

Baseline: local clean checkout before this milestone, 2026-10-26. This record
describes the implemented diff, not a release, deployment certification or claim
that the full intended domain is executable.

## Inventory and authority

The [accepted decision record](../domain/accepted-decisions.md) preserves all 135
Section 3 bullets from the supplied Owner reconciliation brief: 130 CONFIRMED,
four OPEN requirement entries and one PROPOSED handoff recommendation. The four
OPEN entries include two references to O4; they are not four new decisions.
No unavailable earlier conversation was inspected. O1–O4 remain
`OWNER_DECISION_REQUIRED` in the [current register](../domain/open-decisions.md).

The [coverage matrix](contract-coverage-matrix.md) audits 99 capabilities, including
85 slash-expanded catalogue names, the now 36 structural operation discriminators
and additional history/admin/host boundaries, with overlaps counted once.
There are 39 partial rows and 60 intentionally deferred rows; zero rows claim
complete end-to-end support. No top-level row uses the missing category: absent
request/result/type structures are identified separately in the relevant cells.
Deferral is not evidence of structural completeness.

The [invariant register](../domain/invariant-register.md),
[state transitions](../domain/state-machines.md), API conventions and per-capability
deferrals separate semantic authority from schemas, generated types and runtime.
Historical ADR/research content remains accessible with current supersession
links. No new ADR, schema DSL, dependency, workflow engine or Harness enforcement
was introduced.

## Confirmed discrepancies and bounded corrections

| Finding | Correction / remaining boundary |
|---|---|
| Request identity doubled as Node identity | Optional explicit `NodeCreate.payload.node_id`; legacy omission retains its original allocation and persisted request digest |
| NodeRevision metadata did not contain historical content | Optional exact NodeContent snapshot; new M1 creations populate and validate it, legacy records remain accepted |
| Relation head/receipt reference lacked a canonical immutable snapshot record | New RelationRevision structure with full Relation snapshot; runtime persistence remains an M2 prerequisite |
| Ordinary read shape was not a historical-access API | Typed Node/Relation revision references and two explicit revision-read requests; M1 still rejects both handlers |
| P2 found by independent review: duplicate IDs disclosed inaccessible resource conflicts | Existing Node/Relation disclosure is authorized before reporting a conflict; hidden collisions return NOT_FOUND, visible ones retain REVISION_CONFLICT; fresh creation gains no implicit read requirement |
| Publication preservation had inconsistent decision strength | Confirmed preferred direction is recorded consistently; exact copy/selection representation remains subject to M6 review |
| Creation receipts compare immutable effects to current heads/admission | Retained as correct only for create-only M1; no integrity check removed. M2 must resolve immutable original effects before enabling mutation |

Canonical changes are confined to common.schema.json, knowledge.schema.json and
operations.schema.json. Existing generators regenerated derivative Python/TS and
source/artifact manifests. The registry still lists the same eight resource
families; it did not require another family or root import.

This is an explicitly documented amendment to the **unreleased 1.0.0** bundle.
New readers retain old request/metadata acceptance, but old closed readers reject
new fields/variants. Pin code, schemas and generated artifacts together; rolling
back an amended producer's persisted records is not implicitly supported.
See the directional [compatibility analysis](compatibility.md).

## Execution and evidence

Native configured `implementer` was invoked as `/root/m12_implementation` for the
bounded implementation and one correction. Native configured `reviewer` was
invoked separately as `/root/m12_review` after handoff and for one recheck.
The conversation contains explicit agent_type spawn calls, returned identifiers,
completion messages and the correction/recheck handoffs. Separate numeric trace
IDs and per-agent token counters were not exposed. The reviewer found the P2
collision defect, then returned **PASS WITH WARNINGS**, with no remaining confirmed
P0/P1/P2 findings. No automatic correction budget remains.

The initial review used disposable Git reproduction state and reported no
repository edits; the recheck used inspection only, without writes. Reviewer
instructions do not establish filesystem isolation. The coordinator independently
ran deterministic validation and inspected mappings; agent reports alone do not
establish test outcomes or deployment guarantees.

After review, the full suite exposed missing diagnostic metadata on seven new
negative fixtures (299 passed, seven KeyErrors). The coordinator completed only
their expected keyword/path fields; no production schema, generated output,
runtime behavior or valid/invalid expectation changed. All 145 corpus cases plus
independent Ajv parity then passed (146 tests). This mechanical test-data repair
did not start another production review/fix cycle; final full verification was
restarted afterward.

| Check | Actual result |
|---|---|
| Focused corrected regressions, implementer execution | 14 passed; explicit/legacy identity, restart/replay/current authorization, snapshots/legacy/tampering, unsupported history handlers, Node/Relation collision visibility and batch atomicity |
| Final unified `python -m tools.check full` | All gates completed; 306 tests passed in 344.69 seconds, then fresh distribution build and integrity verification passed for 37 payload files |
| Canonical production validation | 8 schemas, 749 offline references, 145 fixtures/round-trips passed |
| Exact generation drift | 24 generated artifacts match, no extras |
| Quality gates | Ruff lint/format, Pyright (zero errors/warnings), ESLint, strict TypeScript consumer checking and Python compilation passed |
| Previous-HEAD directional probes | Five amended producer shapes rejected by the previous canonical bundle; original metadata-only NodeRevision accepted; sampled jsonschema checks, not universal compatibility proof |
| Independent invariant reference inspection | All 71 shorthand canonical definition references resolve |
| Matrix evidence reference inspection | All seven cited test-function/file names exist |
| Final documentation / whitespace checks | 602 portable links passed; scoped and full git diff --check passed |

An early full-check attempt reached a link to the not-yet-written state-machine
document and failed; it was rerun after handoff. The pre-correction full run and a
redundant Core-only run were interrupted and are not reported as passing. Final
validation covered the corrected code, repaired fixture metadata and completed
documents. Existing generator Black/isort deprecation warnings remain; no generator
upgrade was mixed into this milestone.

PowerShell's redirected-stderr wrapper returned status 1 even though the full plan
reached its successful final integrity check. A minimal stderr-printing Python
probe reproduced wrapper status 1, while explicitly returning its native
`$LASTEXITCODE` produced 0. The table reports the observed successful individual
gates, not a clean outer-shell status. For PowerShell automation, explicitly
propagate the native exit code after redirected commands; no global shell settings
were changed.

## Completeness and next slice

| Dimension | What is established |
|---|---|
| Domain contract | All supplied rules are recorded with provenance and authority; unresolved O1–O4 stay explicit |
| Structural contract | Eight canonical families; selected M2-blocking primitives/snapshots/requests corrected; missing API shapes remain classified |
| Operation API | 36 structural request variants plus BatchRequest; no generated-union claim of domain-wide API coverage |
| Runtime implementation | Four bounded Node/Relation create/read operations, atomic batch submission and trusted bootstrap/generation entry points; no new mutation/history handler |
| Runtime conformance | Named automated cases only; 306 full-suite cases passed, including contracts/distribution and bounded Core tests, not 306 runtime operations |
| Deployment verification | No real MCP deployment, OS isolation, power-loss/fsync, hosted OS matrix or backup/erasure guarantee verified |

The [roadmap](../architecture/implementation-roadmap.md) targets M2 immutable
revisions, M3 human reconciliation (O1), M4 authorization/MCP and isolation (O4
before multi-membership serving), M5 authorized query/Collections/graph, M6
governance/publication (O2 and selected-revocation O3), M7 disposal/expiry (O3), and
M8 portability/external services. Each incomplete capability has an activation
profile and explicit prerequisite.

First M2 slice: persist immutable original Node/Relation snapshots and admission
effects, provide explicit recoverable legacy backfill from original committed
trees, then switch receipt verification to that immutable evidence while retaining
current replay authorization. Only afterward enable bounded Node updates/history
with CAS, later-revision replay, restart and non-discovery regressions. Relation
mutation follows with independent CAS; neither O2 graph approval nor O4 policy
composition is selected implicitly.
