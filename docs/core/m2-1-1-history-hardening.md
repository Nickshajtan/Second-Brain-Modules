# M2.1.1 history hardening design

Status: implementation present; Phase A design independently reviewed
PASS WITH WARNINGS and all 21 bounded baseline rows recorded before production
changes. Final full validation, benchmark matrix and independent completed-diff
review determine the M2.2 readiness gate; no completion is claimed here.
Baseline: `d00fb9b6be83a9a83d6f15c26062df0530c2b192`.

## Baseline audit

`KnowledgeRepository.snapshot()` resolves the ref, reads every current blob,
parses every record and request/receipt, then calls `HistoricalEffects.validate()`.
That method materializes every retained tree, checks immutable retention, resolves
each receipt's original generation by scanning those trees, and repeatedly parses
original trees through `origin()` and `recovered()`. `Core.read`, `generation`,
replay and create all enter this same path. `ReceiptStore.check_unused` additionally
scans all prior requests. `GitStore.read` launches one `cat-file` process per blob.
Legacy inspection loads ancestry once itself and again through validation.

The existing authority remains ADR-011: exact original generation, receipt/request,
parent generation, original admission and immutable revision correspondence.
Generation digest excludes receipts/requests/history marker; checking it alone
cannot establish their retention. Current DomainRules rejects unsupported states,
checks all Memberships (not merely active ones), unique registry key/version,
revision identity/sequence and content digests. No authorization verdict may be
retained in an index. Existing M2.1 future-head simulations are not update handlers.

## Trust boundary

Git stays canonical. A SQLite file outside its committed tree is a disposable
locator projection. A separate local checkpoint and randomly provisioned key live
under the trusted backing repository's Git common directory, never in Git records.
The checkpoint authenticates exact instance ID, resolved repository/common path,
managed ref, index format, canonical schema fingerprint, accepted commit/generation
and SHA256 of a fully closed SQLite file. HMAC authenticates the checkpoint; SQLite
`verified=true` has no independent meaning. The key is an OS-protected local secret,
not a new domain authority or authorization credential.

Restart checks HMAC, binding and complete SQLite byte hash before querying the
projection, then checks canonical generation bytes at the accepted commit and the
current managed ref. This costs O(index bytes), not O(history blobs). Local key
permissions use available platform mechanisms; Python mode bits alone cannot
prove a restrictive Windows ACL. Deployment must isolate trusted state from agents.
An actor able to replace Git, key and checkpoint defeats this local integrity
boundary; there is no independent remote or hardware anchor.

The exact bytes whose SHA256 matches the authenticated checkpoint are passed to
stdlib SQLite Connection.deserialize into a private in-memory connection. There
is no hash-then-reopen disk race. All runtime lookups and carried-forward metadata
use this authenticated immutable in-process database, never a mutable disk query
or fallback. Complete Membership dependency sets and idempotency absence are
therefore authenticated together with the projection. Canonical records are still
loaded from pinned Git paths/OIDs and canonically parsed before delivery.

An external disk mutation, including restored size/mtime and deleted lookup rows,
cannot change this authenticated in-memory set. Restart rejects its hash mismatch.
Before publication or derived advancement, check disk/checkpoint coherence again;
never sign metadata read from an unauthenticated changed disk database. A failed
coherence check reports corruption or rebuilds explicitly from the retained signed
anchor. Tests must cover omitted deny Memberships, removed batch/per-operation and
transaction identity rows, and corruption followed by an unrelated create. There
is no stat-only trust or per-row signing oracle. This design requires O(index bytes)
startup work and private memory, which must be measured rather than described as
constant memory. Warm replay queries remain indexed without a full database hash
on every request.

Targeted blob loading recomputes the Git blob object hash (including its header,
using the repository's SHA1/SHA256 format) before trusting a path/OID locator.
Well-shaped bytes under a corrupt object filename are not accepted merely because
JSON Schema accepts them. Previously verified, unrequested historical objects are
not continuously re-read on the warm path; retained-object availability is an
operational assumption checked by explicit audit and when evidence is requested.
The frontier is not a claim that every retained byte was re-read on each delivery.

Checkpoint/key absence when prior enrollment exists is an explicit recovery
condition, never silent enrollment or acceptance of a replacement history.
An already existing empty enrollment directory is evidence of lost/ambiguous local
trust, not a pristine instance. Audit, rebuild and enrollment reject it with
`VERIFICATION_FAILED` without minting keys or changing canonical refs. Removal or
replacement of the entire directory by a privileged actor remains outside the
declared local-anchor boundary; no independent remote trust anchor is implied.
Initial enrollment needs an explicit durable incomplete/complete state; interruption
must not cause the runtime to silently mint a new trust anchor. Trusted recovery
must disclose loss of the rollback anchor rather than pretend continuity. Fresh
trusted bootstrap may enroll atomically under its existing host capability. An
existing unenrolled Git repository requires explicit trusted rebuild enrollment;
ordinary untrusted requests cannot authorize its first historical trust decision.
Legacy test provisioning must finish before enrollment, rather than bypassing the
rollback anchor to replace a live enrolled root.

## Projection and reads

Small tables hold verified commit/generation bindings, current paths/blob OIDs,
resource dependencies, revision identity/resource/logical sequence/digest/location,
original transaction/receipt location, principal-scoped batch idempotency,
principal-scoped operation/version/key and transaction uniqueness. No secret request
or content bodies are stored. Registry key/version uniqueness remains global.
An isolated database has exact instance/ref/schema identity, not an inferred path
identity. Copying all files does not create an independent Brain Instance.

Warm reads pin one verified commit and load only resource, metadata/type or
predicate definitions, ALL relevant Memberships, Cluster and Relation endpoints,
and required revision records. The supported private/active/single-membership
restrictions remain unchanged. Current principal grants are evaluated on each
delivery. Missing or corrupt index state never falls back to stale results.

Before loading private resource/receipt/effect bytes, denial-only screens consult
authenticated scope/lifecycle metadata and the caller's current grants. A hidden
resource with unavailable bytes therefore remains `NOT_FOUND`, like an unknown
resource. These screens cannot grant delivery or execution: canonical parsing,
domain checks and the existing full AccessControl checks still run on every
positive path. Original receipt effect locators select current scopes before
loading a private receipt/request or origin. Node creation replay requires
`node.create` plus `membership.admit`, without inventing `node.read`; Relation
creation replay retains owner creation and endpoint read requirements. Mutations
screen target/collision/endpoint/expectation scopes before dependency loading.
Earlier resources in the same atomic batch have transient scope facts only after
their admission checks; these are neither persisted grants nor executable evidence.

Git gains narrow batch blob reading, exact path/OID lookup and ordered descendant
transition enumeration. No full-tree or ancestry fallback belongs in warm reads.
Writes may still construct a full Git tree; they must not revalidate all historical
transactions. Receipt replay locates its exact original committed effects through
the projection and checks canonical bindings plus current admission capabilities.
Candidate construction uses an existing parent tree plus bounded changed blobs,
not one `hash-object` invocation per unchanged canonical file. The projection keeps
raw SHA256 per knowledge/config path so the existing generation content digest can
be reproduced exactly from verified metadata plus changed bytes. Enumerating that
metadata for commit construction is distinct from re-reading historical blobs.

## Verification and publication

First explicit build verifies complete linear retained history and EVERY generation
transition, including unrelated commits. M2.1 receipt/effect/admission validation is
preserved. Every immutable receipt/request/revision/supplement establishes a retained
path/OID obligation. Removing an entire transaction therefore fails even when no
current row or receipt remains. Baseline marker retention is separately mandatory.
Full build/audit streams ordered transition deltas and batches unique blob reads;
it must not call the old materialize-all-trees/per-receipt ancestry algorithm.

Catch-up requires the signed accepted frontier A to occur in B's full nonshallow
linear ancestry, visits every intervening commit in order, validates changed
canonical records and affected dependency closure and checks every changed/deleted
immutable path against prior obligations. New receipts establish unique original
generation and exact original parent/effects. Generation uniqueness spans all
commits. Rollback, unrelated replacement, merge, shallow history, unavailable object
or ambiguous generation fails closed. B's validity never follows from an index row.

Prepared Git objects have no domain effect. Publish Git using existing writer lock
and conditional ref CAS first. Then construct/close an isolated SQLite replacement,
recheck the managed ref and atomically replace projection, then atomically publish
its authenticated checkpoint. A reader pins a matching checkpoint/database pair;
it may not combine an old open handle with a new checkpoint. Maintenance uses the
same writer lock. Crash after Git publication leaves a lagging frontier; catch-up
revalidates published transitions. Crash between database swap and checkpoint
leaves the OLD signed frontier intact, rejects the mismatched database and rebuilds
from that anchor. A failed CAS never advances derived metadata. No database update
is a canonical domain transaction.

Explicit rebuild verifies the pinned current Git state into an isolated replacement,
preserves the known-good file until successful replacement and fences source ref
and generation before checkpoint publication. Even with SQLite absent, the signed
frontier constrains rebuild: target must descend it. No reset, checkout, force push
or canonical repair occurs. Audit is a trusted-host maintenance interface, not an
operation discriminator, and reports index/canonical/ancestry/migration categories
without private paths in ordinary DomainError responses. Full audit compares the
projection to canonical Git; rebuilding requires separately explicit authorization.

## Scope and compatibility

No canonical schema amendment is presently justified. Generated files stay unchanged.
Only stdlib SQLite/HMAC/hash facilities are used. No search tables, plugins,
update/history handlers, background workers or general migration engine are added.
Future M2.2 updates must extend transition validation while retaining old immutable
obligations; existing receipts keep their original meaning. Full retained ancestry
and original objects are required for audit/rebuild. SQLite backup is optional;
Git refs/objects plus trusted anchor recovery policy are not optional. Physical
power-loss durability, backup guarantees and privileged tamper resistance remain
unproven by CAS or benchmarks.

## Performance evidence and acceptance

The disposable [benchmark harness](../../tools/benchmark_history.py) records actual
Git processes, blob reads, trees, traversed commits, canonical parse calls and
receipt pair validations, with elapsed time secondary. An explicit Git-process
budget censors unaffordable M2.1 operations and reports `budget_exhausted`; those
rows are lower bounds, not successful timings or extrapolated measurements.
Workloads contain supported two-Node/Relation batches, varied bodies and fixture
unrelated generations. They do not pretend to implement Node mutation.

Concrete structural budgets and all censored baseline observations are recorded in
[performance evidence](../engineering/history-performance.md). Cold verification/rebuild may scale with
history; warm Node/Relation/replay must traverse zero complete ancestry, validate
bounded dependency records and never scan every receipt. Cross-process restart,
index tampering, rollback, whole-transaction deletion, publication crash and hidden
membership denial require regression cases, not merely fast benchmark results.

## Implemented boundaries

| Module | Responsibility |
|---|---|
| `history_index.py` | Minimal SQLite locators, authenticated enrollment/checkpoint, exact-byte private deserialize, read-only live connection, target dependencies, catch-up/rebuild/audit coordination |
| `verification.py` | Ordered per-commit canonical/domain checks, retained immutable obligations, exact original creation/effect locators, legacy migration binding; temporary unique-blob cache only during verification |
| `git_store.py` / `ports.py` | Binary batch blobs with object rehash, safe exact locators, linear complete transition enumeration, parent-tree delta preparation and existing CAS publication |
| `application.py` / `operations.py` | Fixed four-operation dispatch, per-strategy dependencies, bounded current authorization, indexed exact replay and original evidence checks |
| `repository.py` / `migration.py` | Explicit full current-state/migration views pinned to the accepted frontier; migration reuses the held writer lock and cannot re-enroll a replaced history |
| `maintenance.py` | Trusted explicit audit/rebuild, safe stable diagnostics; no public operation discriminator |

Canonical schemas/generated files and original receipt/revision identities remain
unchanged. New host capabilities extend the existing coverage catalogue rather
than introduce a second authority. Generation lookup validates the exact current
descriptor and its canonical tree, not every unrequested historical blob. Targeted
read/replay and full audit retain their respective object-availability obligations.
The private SQLite connection is thread-bound; use separate Core instances across
threads/processes. No shared-thread Core guarantee or deployment ACL verification
is established here. The interprocess writer lock remains the publication boundary.
