# M2.2.2 hashing and projection lifecycle design

Status: **implemented and independently reviewed, PASS WITH WARNINGS; M2.3 GO.**
Baseline: `80a24eedb0379b15e4fd9a9d5975486d04cc0558`. See
[executed validation and limits](m2-2-2-validation.md) for the full matrix,
corrections and scoped readiness decision.

## Observed baseline

The audit inspected `application.py`, `boundary.py`, `repository.py`,
`history_index.py`, `verification.py`, `projection.py`, `git_store.py`, `ports.py`,
maintenance/locking, canonical GenerationRef/Digest, and ADR-011/012/013. Git owns
knowledge and transaction publication; ADR-013 owns authenticated derived
base/delta reconstruction into private memory. This proposal preserves both.

`Core._next_generation()` selects every knowledge path/SHA256 pair, copies the
mapping, replaces changed hashes, JSON-encodes the complete sorted mapping and
hashes it. `TransitionVerifier._generation()` independently repeats that full
selection/encoding/hash for every content-changing transition. Generation-only
transitions can reuse the previous digest. Neither operation reads historical
content blobs merely to hash unchanged content. `content_digest()` hashes all
content bytes during bootstrap/full-tree verification and legacy fixture building.
`HistoryIndex.files()` materializes every file locator, but is not called by the
healthy bounded update path. `prepare_delta()` batches changed blobs, then uses a
full temporary native Git index (`read-tree`, `update-index`, `write-tree`).

Fresh disposable profiles use the existing corpus builder and `hardening_measure`
at the exact baseline. Each size includes a first create batch, two Nodes and a
Relation every twentieth generation, a hot-Node replacement at offset ten, and
generation-only commits otherwise. The measurement is one title replacement after
full verification; it is not a throughput distribution.

| Generations | Paths in each flat commitment | Encoded bytes in each commitment | Commitments per update | Submit seconds | Generation-builder seconds | Git preparation seconds |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 70 | 9,137 | 2 | 1.874051 | 0.000632 | 0.356090 |
| 1,000 | 565 | 73,847 | 2 | 2.365163 | 0.003198 | 0.352484 |
| 10,000 | 5,515 | 720,947 | 2 | 1.656328 | 0.030482 | 0.369614 |

All three profiles execute 26 Git subprocesses, including nine bounded `cat-file`
batches, and no full SQLite serialize/hash/rewrite. Total observed SHA256 input is
185,088/314,522/1,608,736 bytes respectively; this includes records, authenticated deltas and
checkpoint envelopes, not only generation commitments. CPU timer resolution cannot
attribute these small operations reliably. Raw observations, exact helper source,
runtime fingerprint and counter boundaries are preserved in the
[baseline artifact](../engineering/history-performance-m222-baseline.json).
The nested harness Git counter was bypassed by the profiling instance wrapper;
the artifact records the corrected count from its exact 26-command trace, rather
than presenting the nested zero as a measurement. The frozen M2.2.1
baseline-matched profile at 10,000 records 0.018826
seconds in generation construction; its different instrumentation must not be
reported as a direct speed comparison.

The evidence establishes growing metadata work, **not** hashing as the present
wall-clock bottleneck. Git process startup and dependency loading dominate these
profiles. Existing benchmark directory-size enumeration is instrumentation, not
runtime mutation work. The subsequently completed matrix covers large bodies,
many small records, deep revision history and high churn; its results and native
Git fanout measurement limits are in the validation report.

## Alternatives

Let N be all canonical content paths, K changed paths, B the number of paths in an
affected bucket, and F the fanout of touched Git directories. Every option retains
ordinary canonical validation, current authorization and exact CAS.

| Option | Mutation work and bytes hashed | Build/restart/recovery | Integrity and compatibility | Decision |
|---|---|---|---|---|
| A: retain flat SHA256 map | O(N) path reads, sorting/encoding and hash bytes; deduplicating candidate/verifier work only removes a constant factor | Existing build/private-base restart; lowest operational complexity | Exact old digest; existing complete private index authenticates negative lookups and Membership sets | Retain for historical verification; cannot remove the structural cost |
| B: Git-native subset root | Reuse untouched trees; touched flat directories still cost O(F); compact top-level commitment | Existing Git objects provide persistence; retained ancestry and full audit still required | Must bind exactly knowledge subtree plus metadata, exclude receipts/generation, include instance/object format. SHA256 wrapping a SHA1 tree does not provide SHA256 collision strength | Reject as canonical replacement in SHA1 repositories; still optimize native tree preparation where measured |
| C: independent authenticated map | Balanced Patricia implementation can approach O(K log N), but adds encoding/proof/storage machinery; uncompressed 256-level sparse tree needs many derived rows | Fresh tree build plus existing base/delta restart; complete replay verifies mixed historical algorithms | Can preserve SHA256 security and complete keyed sets. Not an authorization system. Requires explicit canonical version and reviewed upgrade | Select narrow fixed-depth bucket variant below, subject to independent gate |
| D: Git plus separate derived root | Git saves unchanged blob work, but keeping canonical flat digest still requires O(N); adding a derived root alone cannot remove it | Additional roots/checkpoints without replacing generation work | Existing ADR-013 already authenticates complete private lookup state; duplicating that integrity mechanism provides no demonstrated benefit | Do not add a second Merkle tree over index tables |

All options work on Windows through existing Git/stdlib SQLite; no new service or
filesystem ingress is needed. A/B have no new dependency; C could add one, but the
assessed libraries below are not a narrow fit. No design makes future Relation,
Collection or Graph authorization implicit: changed canonical records can use the
same commitment path while their domain transition validators remain separate.

## External components and inspiration

Reviewed primary sources on 2026-10-27:

- [Cursor's indexing article](https://cursor.com/blog/secure-codebase-indexing)
  motivates skipping unchanged branches. It concerns synchronization and derived
  processing, not Second Brain's transaction authority or current grants. No cloud,
  embedding reuse, cross-user proof, similarity matching or synchronization protocol
  is proposed here.
- [Git mktree](https://git-scm.com/docs/git-mktree) and
  [hash transition documentation](https://git-scm.com/docs/hash-function-transition)
  establish existing native tree construction and the separate SHA1/SHA256 object
  formats. Reusing Git avoids a custom object store but cannot silently strengthen
  a SHA1 repository's object commitment.
- [ApeWorX py-trie](https://github.com/ApeWorX/py-trie) is an active Python project
  with tests, MIT licensing and Python >=3.10. Its
  [project metadata](https://raw.githubusercontent.com/ApeWorX/py-trie/main/pyproject.toml)
  declares Ethereum-specific dependencies. Its Patricia trie supports key/value
  operations and proofs, but introduces Ethereum encoding/hash dependencies and a
  separate persistent map integration. Complete Membership ranges would still need
  aggregate encoding or range-proof design. Reject for this bounded milestone.
- [pymerkle](https://github.com/fmerg/pymerkle) exposes append-only inclusion and
  consistency proofs, GPL-3.0 licensing, a cachetools dependency and an explicit
  security-audit warning in its current README. Its append API does not directly
  solve keyed replacement/deletion/complete-set proofs. Reject; no claim that
  repository activity establishes an independent security audit.

No external package is selected. A small SHA256 bucket tree is proposed only
because A cannot remove the required work and B weakens the existing commitment
strength on supported SHA1 repositories. It is not a general cryptographic store.

## Proposed canonical commitment

Add optional `GenerationRef.commitment_scheme`, with exactly the new value
`sha256-bucket16-v1`. **Absence means the existing sorted-map algorithm**, never an
inferred current default. `Digest.algorithm` remains `sha256`; it names the hash,
not the structure. Unknown schemes and any new-to-legacy transition fail closed.

The new structure covers exactly `knowledge/*` files and `control/metadata.json`.
Receipts, requests, migration control and generation descriptors remain excluded
to avoid circularity; their existing immutable-effect verification remains required.

Exact proposed encoding (all integers unsigned big-endian):

```text
F(tag, parts) = b"second-brain.content\x00sha256-bucket16-v1\x00"
              || u16(len(tag)) || tag || u32(len(parts))
              || concat(u64(len(part)) || part for part in parts)
I = UUID(instance_id).bytes
P = UTF8(canonical_relative_path)
bucket(P) = u16_decode(SHA256(F(b"key", [I, P]))[0:2])
entry(P, raw) = F(b"entry", [P, SHA256(raw)])
leaf(bucket, entries) = SHA256(F(b"bucket", [I, u16(bucket),
                            u32(entry_count), concat(sorted(entries_by_P))]))
empty[0] = SHA256(F(b"empty", [I]))
parent(height, left, right) = SHA256(F(b"branch", [I, u16(height), left, right]))
empty[h] = parent(h, empty[h-1], empty[h-1]), h in 1..16
commitment = SHA256(F(b"root", [I, root_at_height_16]))
```

An absent bucket uses `empty[0]`, not an empty nonempty-leaf encoding. Only 17
default hashes are initialized per instance, not 65,536 bucket defaults. Fixed
height plus ordered branches gives every bucket an implicit unique position;
nonempty leaves additionally bind the numeric bucket. An individual empty file
has a present entry with SHA256(empty bytes), distinct from an absent path. Count
and framing distinguish ordering and key/value boundaries. Reject duplicate paths.
Cryptographic path collisions merely put multiple exact paths in one bucket; they
do not alias records. Git's own object format is not used as the SHA256 leaf value.

Only nonempty leaves and necessary internal nodes need derived storage; defaults
are deterministic. Candidate computation overlays bounded changes on complete
authenticated bucket rows and reuses untouched branch hashes. Transition
verification independently updates these rows from canonical changed blobs and
compares the exact root with the descriptor. An atomic batch computes one root.
The derived DML vocabulary and authenticated projection format must be amended for
the new bucket/branch rows. The canonical commitment does **not** replace ADR-013
authentication of receipts, idempotency, Membership dependency sets or endpoints.

Complexity is O(K * (B + 16)) and O(K * 16) changed branch rows before shared-branch
deduplication, not a worst-case O(log N) promise. An adversary can search UUIDs that
concentrate buckets, causing O(N) work in that bucket; correctness remains intact.
The benchmark must report bucket cardinalities and concentrated-key tests. No
public proof API is needed: internal witnesses/tests must reconstruct complete
bucket contents and all ordered sibling hashes, rejecting omitted keys, modified
leaves and invalid absence claims. Root computation has independent golden and
full-rebuild comparisons, not only self-consistency tests.

## Exact compatibility and adoption gate

This is a reviewed **unreleased 1.0.0 amendment**; it is not compatible with old
closed readers when the optional new field is emitted. Canonical schemas, registry
source fingerprints, generated Python/TS, portable fixtures and consumer checks
must be regenerated together. Existing descriptor/request/receipt bytes and IDs
are never rewritten. Historical old generations use the old algorithm indefinitely.

Existing repositories remain legacy until an explicit trusted-host upgrade:

1. Authenticate the exact known baseline schema fingerprint, old enrollment, key,
   checkpoint and complete old projection; accept no arbitrary signed fingerprint.
   The only initially recognized predecessor contract binding is
   `bbbe881202b9b3c88548ccdf37364bdf92f7af7bb0f2e06086ed738880dcfa84`,
   computed by the actual `boundary.digest(ContractValidator().schemas)` at the
   supplied baseline. All other binding fields must exactly match the instance,
   repository/common path and managed ref. Format recognition is an explicit
   predecessor allowlist; unknown formats/fingerprints and bad MACs are rejected.
2. Retain those exact old trust bytes and accepted frontier. Fully verify retained
   Git and build a fresh projection with bucket rows under the new schema binding.
3. Atomically adopt the new derived base/checkpoint while preserving the same key,
   enrollment identity and rollback fence. Interrupted upgrade must be retryable
   from retained old material, without reenrollment or accepting a younger head.
4. Explicitly publish a generation-only scheme-adoption commit, fenced to that
   accepted source, whose new root binds unchanged canonical knowledge/metadata.
   New bootstrap can begin directly with the new scheme. Ordinary reads/writes
   neither upgrade schemas nor select a new scheme silently. Legacy writes remain
   allowed with legacy O(N) generation calculation between derived-format adoption
   and explicit canonical-scheme adoption; they cannot be described as the new
   fast path. Once the canonical descriptor adopts the new scheme, every subsequent
   writer and verifier must retain it. The host should perform these two explicit
   upgrades in one maintenance window before enabling normal mutation traffic.

No canonical upgrade record family is proposed. A generation-only adoption is
distinguished by the authenticated descriptor and parent: exactly the generation
path changes, knowledge remains unchanged, and legacy -> new is one way. A later
attempt to omit the scheme is a downgrade even if content is unchanged. Mixed
histories remain replayable/auditable; historical receipts keep their exact old
GenerationRef. Derived format/source-fingerprint adoption and canonical scheme
adoption are separate crash boundaries and must each be tested.

The exact generation-only transition proves an explicit, unambiguous canonical
algorithm change, not who invoked it. Existing unsigned Git actor claims are not
authenticated credentials. The proposed verifier accepts a valid external
generation-only adoption during ordered catch-up; it rejects a first adoption
hidden inside a resource mutation, malformed roots and later downgrade. The
trusted-host API enforces its current authority when invoked locally. No new
adoption record is necessary, and no historical host-identity proof is claimed.
This preserves the existing privileged-local-state trust limitation rather than
pretending a new unsigned actor field would solve it.

All creation/generation routes must select the authenticated scheme explicitly:
bootstrap and its `HistoryBaseline.generation`, migration's destination generation
and baseline marker, mutation receipts, `KnowledgeRepository.parse_tree`,
`TransitionVerifier` and full-history audit. Existing baseline `effects_digest`
and `plan_digest` retain their own old semantics; they are not generation roots.
Legacy fixture builders remain explicit legacy producers. A new-algorithm
descriptor with an old flat digest, a hidden adoption inside a mutation, an
unrecognized schema fingerprint, a missing bucket row, or a complete-set witness
omitting a colliding path are required negative counterexamples.

ADR-014 is appropriate only after this exact canonical decision passes review.
The proposal must not be implemented merely because the document exists.

## Projection lifecycle proposal

Retain ADR-013's authenticated immutable base and bounded delta tail. Add a trusted
host maintenance interface that inspects capacity and, when explicitly invoked by
the host, compacts at half the existing limits (512 deltas or 8 MiB). These are
initial conservative operating thresholds derived from the existing 1,024/16 MiB
hard limits; actual new delta sizes/restart/compaction measurements must justify
them before finalization. No scheduler runs in Core. The host calls maintenance
between requests. Exact encoded next-delta capacity still rejects before Git CAS;
a single unusually large bounded transaction may be rejected even after maintenance.
Report count/byte reserve, so a fixed one-delta promise is never fabricated.

Before switching a compacted/rebuilt base checkpoint, atomically persist the exact
currently signed checkpoint as `checkpoint-<SHA256(exact-signed-bytes)>.json`.
The new checkpoint's `base_previous_state` names that exact immutable archive.
Retain both current and
one previous checkpoint, their referenced immutable bases and complete tails. A
crash before/after the switch always leaves the current checkpoint's files intact;
the prior checkpoint is recovery evidence, never permission to roll back Git.
Content-addressed archive names preserve the older required archive if a crash
occurs after archiving but before the current-checkpoint switch; a mutable single
previous-checkpoint slot would lose that evidence. Unreferenced archive files are
ordinary GC candidates after a successful switch.
Missing required prior evidence fails closed for GC, not as an excuse to guess
which files are safe. Pre-feature format-3 anchors have no prior bytes; their first
explicit maintenance establishes this retention slot without inventing history.

Explicit GC dry-run/apply takes the existing repository writer lock. All cold
base/delta loading and refresh must take that same lock through authentication and
private-memory adoption; writer locking alone is insufficient today. Warm readers
already hold private data and never consult retired backing rows. This prevents a
cold reader from pinning an old checkpoint and opening its files after deletion.
Implement locked internal helpers to avoid recursively acquiring the nonreentrant
OS lock. Revalidate exact current/prior checkpoint bytes and Git frontier before
apply; a changed source invalidates the plan. Only recognized regular derived base,
delta and prepared filenames within the resolved index directory are candidates.
Do not follow symlinks/reparse-point escapes or delete unknown files, keys,
enrollment, checkpoints, lock files or Git objects. Report retained reasons and
reclaimed bytes. An interrupted deletion is safely repeatable because only
unreachable derived files are removed. Windows delete failures preserve files and
produce bounded diagnostics rather than pretending reclamation succeeded.

Backups need either a lock-consistent current/prior trust/base/tail set or retained
Git plus authentic rollback/key material for explicit full rebuild. Partial derived
backups may fail closed and require rebuild; missing anchors cannot be reset.
Neither GC nor compaction modifies canonical knowledge or promises physical erasure.

## Bounded implementation and validation plan

1. Independent review of measurements, all four alternatives, precise scheme,
   old-fingerprint upgrade, reader/GC synchronization and crash boundaries.
2. Canonical schema amendment plus fixtures/regeneration; focused commitment
   implementation with deterministic roots, insertion/deletion, ordering, instance
   separation, absent/empty, duplicate and adversarial witness tests.
3. Integrate candidate/transition generation roots, explicit upgrade/adoption and
   legacy downgrade rejection. Preserve historical effect and authorization tests.
4. Profile Git preparation separately; adopt only measured narrow native-tree
   improvements. Do not claim Git's touched-directory fanout disappears.
5. Implement trusted capacity maintenance and reader-safe reachable-file GC;
   test restart, compaction interruption, concurrent load/GC, backup and lost trust.
6. Freeze runtime and execute 100/1,000/10,000 workloads, 1,000 hot revisions,
   distributed/small/large/high-churn bodies, long tail, restart/catch-up/rebuild
   and explicit audit. Preserve frozen earlier artifacts; count paths/hash bytes,
   SQL/branch rows, writes, Git work and sufficient-sample latency distributions.
7. Independent final actual-diff review and unified quality/contract/distribution
   checks. No M2.3 GO before evidence and unresolved findings are reconciled.

Remaining O(N) operations are explicit initial build, complete audit/rebuild,
checkpoint authentication on cold startup, compaction and derived GC directory
inventory. Bucket fanout and Git touched-directory fanout are separate residual
costs. No deployment-level tamper resistance or power-loss durability is claimed.
