# Compatibility contract

## M2.2.2 unreleased generation commitment amendment

GenerationRef gains optional `commitment_scheme` with the sole value
`sha256-bucket16-v1`. Absence keeps the exact historical sorted-map SHA256 meaning;
the Digest hash algorithm remains SHA256. New readers accept old descriptors and
stored receipts; old closed readers reject emitted new fields. This is an explicit
unreleased 1.0.0 amendment, requiring source/generated consumers to pin the same
commit. No historical Git descriptor, request, receipt or revision is rewritten.
Portable positive/unknown/null fixtures and Python/Ajv/type consumers exercise this
directional boundary, without claiming universal semantic inclusion.

Derived format 4 adds content-commitment tables. Ordinary reads reject old schema
bindings. `upgrade_history_index` explicitly authenticates the known baseline
fingerprint `bbbe881202b9b3c88548ccdf37364bdf92f7af7bb0f2e06086ed738880dcfa84`,
same instance/repository/ref, exact old base/tail and protected key/enrollment;
it retains the accepted ancestry fence, fully verifies Git and adopts new derived
bytes. Interrupted new-checkpoint/old-enrollment state is recoverable only through
that explicit interface. Unknown fingerprints or missing anchors cannot reenroll.

The direct predecessor is format 3 at the supplied M2.2.1 baseline. Existing
format-1/2 instances must first use that baseline runtime's explicit authenticated
`rebuild_history_index` upgrade, then invoke M2.2.2 upgrade and adoption. Preserve
the key/checkpoint and complete canonical ancestry throughout; do not delete trust
material to make the new runtime accept an older format. This is a staged upgrade
procedure, not a claim that the new loader accepts arbitrary historic fingerprints.

This derived upgrade does not change the canonical algorithm. Legacy writes can
continue with legacy O(N) hashing until explicit `adopt_generation_commitment`.
Adoption is generation-only and one way; valid external adoption can be verified,
but no past host identity is proved by unsigned Git. After adoption every next
descriptor must retain the scheme. Fresh bootstrap starts with the new commitment.
Historical generations select their own authenticated scheme during full audit.
See [ADR-014](../architecture/decisions/ADR-014-versioned-content-commitments.md)
and [runtime evidence](../core/m2-2-2-validation.md).

## M2.2.1 derived persistence hardening

The [M2.2.1 design](../core/m2-2-1-mutation-hardening.md) changes derived
persistence only; public operation shapes, canonical revisions, original receipt
identities and current authorization semantics remain unchanged. Its format-3
upgrade must explicitly authenticate the old format-1/2 trust material and retain
the accepted Git frontier and key before full verification and adoption. Ordinary
reads must not silently migrate or reenroll. Actual implementation and validation
status is recorded in the [milestone evidence](../core/m2-2-1-validation.md).

The implemented authenticated immutable base and bounded delta tail preserve the
private-memory lookup boundary. Warm operations do not hash the whole disk base;
damage to already authenticated backing bytes is detected on restart or explicit
verification rather than necessarily at the next warm write. Those disk bytes
cannot modify the private connection or become a source of newly signed rows.
This detection-timing change is explicit, not a claim of unchanged operational
diagnostic timing or protection against privileged replacement of all trust state.

## M2.2 Node runtime and derived-format compatibility

M2.2 reuses existing `NodeUpdate`, `NodeRevisionRead`, `NodeRevision.previous`,
revision refs and shared result contracts. No canonical schema, generated model,
version/registry or old receipt identity change is planned. The finite handler
surface gains Node replacement and exact historical delivery; Relation mutation
and Relation history remain unsupported. See [operation semantics](operations.md#m22-node-replacement-and-exact-history)
and [actual validation status](../core/m2-2-validation.md).

Fresh identical replacement creates a revision under the existing catalogue
effect. This is distinct from retrying the exact original request/key, which
returns the authorized old receipt without effects. Mandatory semantic target CAS
does not narrow schema structure: an empty expectations array remains structurally
valid but is rejected by Node-update business validation.

Derived index format 2 adds incident-Relation and operation-specific replay
locators. A format-1 projection is not silently read or migrated. Explicit trusted
`rebuild_history_index` authenticates recognized old signed checkpoint/enrollment
bindings, preserves all non-format identity fields, the key and accepted-commit
rollback fence, fully verifies canonical Git and publishes a fresh format-2
projection. Interrupted mixed-format trust pairs require explicit recovery, never
implicit reenrollment. Bad MAC, wrong identity, unknown format or divergent
ancestry fail closed. Canonical historical bytes do not migrate. Opening or reading
an instance does not trigger this upgrade; the [design](../core/m2-2-node-mutation.md)
and validation report identify tested upgrade/crash behavior.

Historical interpretation also requires stable registered meanings (I08 and
M12-REV-06). The independently reviewed M2.2 subset is append-only for registered
Node/predicate definition records and existing metadata-schema ID values. Existing
records cannot be changed or removed, even for descriptive-only edits; this is a
bounded implementation restriction, not a universal domain requirement that every
future definition field is immutable. Add a new version/identity and schema ID
instead. No administration handler is introduced. Incremental catch-up and explicit
full rebuild reject historical overwrite/removal rather than silently adopting the
latest meaning. Existing histories containing such changes need operator review;
there is no automatic migration, trust reset or rewriting of canonical evidence.

## M2.1.1 operational compatibility

M2.1.1 changes no canonical schema, generated artifact, public operation variant,
receipt identity or logical RevisionRef. The existing create/read wire surface
remains finite; no update or historical-read handler is added. Stdlib SQLite is
derived locator metadata, not canonical persisted knowledge.

Existing unenrolled M2.1 repositories require explicit trusted
`rebuild_history_index(core)` enrollment after complete historical verification.
Fresh trusted bootstrap establishes its initial projection. Missing SQLite with a
valid checkpoint is rebuildable; lost/invalid key, enrollment or signed checkpoint
cannot silently establish replacement ancestry. Checkpoints bind exact schema
source hashes, index format, repository path/ref and instance. Runtime/schema
upgrades or relocation therefore need operator-reviewed verification/rebuild,
not silent adoption of older local trust files.

There is an intentional operational distinction: `Core.generation()` now checks
the exact pinned generation descriptor/tree and verified frontier, rather than
exhaustively probing every historical object's availability. Requested Node/Relation
and replay evidence still fail closed when their bytes/origin are unavailable;
explicit `audit_history` verifies all retained obligations and is required after
restore or suspected object pruning. See [recovery](../engineering/history-recovery.md)
and [M2.1.1 validation](../core/m2-1-1-validation.md). This is not a claim of
continuous full-history corruption detection on each warm lookup.

The final unreleased projection includes minimal scope/lifecycle facts for early
denial checks. Development projections created before that correction should be
explicitly rebuilt; canonical schemas, receipts and revision records do not migrate.
An existing empty enrollment directory now requires operator recovery, preserving
the distinction between missing disposable SQLite data and lost trust material.

The private authenticated SQLite connection is thread-bound. Separate Core
instances per process/thread are supported by the shared writer/CAS boundary;
sharing one Core object across threads is not a verified concurrency model.

## Structural evolution

Current production baseline is **unreleased 1.0.0**. There is no released production predecessor and no backward-compatibility claim against illustrative 0.1.0. Immutable `$id` values identify exact structural meaning; `schema_version` and `operation_version` are explicit. Runtime support is an advertised finite set, initially only 1.0.0. Unknown versions fail with typed `UNSUPPORTED_VERSION` at version selection; invalid nested version values fail canonical structural validation. They never trigger a fetch or silent migration.

| Change | Compatibility consequence for closed, versioned contracts |
|---|---|
| Description-only correction | May be patch; release still has a new immutable exact ID and source hash |
| Optional field addition | New reader may accept old producer; old closed reader rejects new producer that emits it. Not automatically backward-compatible |
| Required field addition / narrowing | Old producer may fail new reader; breaking unless version negotiation isolates it |
| Enum expansion | New reader may accept old values; old reader rejects expanded producer values, exhaustive TS switches change |
| Field removal or rename | Producer/consumer directions can both fail; requires explicit conversion/migration |
| New/changed discriminator or operation | Versioned semantic/structural change; unsupported operation envelopes reject rather than fall through |
| Nullability/default change | Affects meaning and acceptance. Defaults are annotations, never validator writes |
| Stable reference or `$id` change | New resource/version and registry bundle; no rewriting old identifiers in place |
| Same shape, changed authority/state/CAS semantics | Behavioral breaking change even if structural corpus still passes |
| Entity/revision identity change | Explicit reviewed ID/provenance mapping; not inferred from title/path or applied during read |

For producer P and consumer C, both P's possible outputs and C's intended requests need directional acceptance and unchanged interpretation. A SemVer label does not prove this inclusion. The [synthetic compatibility fixture](../../tests/fixtures/contracts/compatibility.json) exercises optional addition, closed-reader rejection, enum expansion, required addition, renaming and discriminator changes with Python jsonschema and Ajv. Its tiny schemas are clearly synthetic test inputs, not another domain model or hypothetical released contract.

Consumer startup can inspect [registry](../../contracts/registry/v1.json) and [generated manifest](../../packages/python/generated/v1/manifest.json). `ContractValidator.verify_generated()` checks canonical-source and emitted Python/TS hashes in the pinned checkout. CI additionally regenerates and compares the full generated file set; a manifest alone cannot prove generator fidelity. Types from one pin must not silently pair with schemas from another.

Future release gates: previous/current producer-consumer corpus; semantic review of changed operation obligations; all supported OS generation equality; offline transitive reference closure; exact dependency/runtime pins and actual consumer import checks. These are release requirements, not claims that hosted runs or a package publication already occurred.

## M1.2 unreleased amendment (2026-10-26)

The Owner requested M2-blocking contract completion before release. This is an explicitly reviewed **unreleased 1.0.0 amendment**, not permission to mutate released exact IDs. The registry version/status remain 1.0.0/unreleased and source/generated manifests change. Consumers must pin the amended commit and bundle together. There is no released predecessor compatibility promise; after release any such acceptance/meaning change requires a new exact schema ID/version and supported migration.

| Amendment | New reader with old producer | Old closed reader with amended producer | Persisted implications |
|---|---|---|---|
| Optional NodeCreate.payload.node_id | Accepts omission with exactly legacy request_id allocation | Rejects emitted new field | Original stored requests/digests unchanged; explicit identity used by new requests; no ID rewrite |
| Optional NodeRevision.snapshot | Accepts old metadata-only record | Rejects emitted full snapshot field | New M1 creations persist exact content and validate digest; legacy rows remain readable but require explicit original-byte backfill before M2 updates/history |
| New RelationRevision union alternative | Old Relation head records accepted | Rejects new kind | M1.2 was structure-only; M2.1 persists and validates it; no on-read conversion |
| Common RelationRef / NodeRevisionRef / RelationRevisionRef | Existing references unchanged | No promise of newly exported names | Typed refs separate logical revision/resource/Git identity; semantic equality and retention checks remain required |
| NodeRevisionRead / RelationRevisionRead requests | Existing current-read requests accepted | Rejects new discriminator | M1 finite dispatch rejects both; M2 must implement historical authority/resolution and exact retained revision response |

Actual directional probes used the previous HEAD canonical eight-resource bundle with independent jsonschema validation: it rejects the five new producer shapes above (explicit Node ID, Node snapshot, RelationRevision, two historical reads) and accepts the original metadata-only NodeRevision. The amended corpus accepts original shapes plus the new valid fixtures and rejects null/missing snapshots/wrong endpoint kinds. These are sampled directional acceptance checks, not a proof of universal schema inclusion or behavioral compatibility.

## M2.1 unreleased amendment

No mutation/history handler is enabled. Receipt verification now resolves original
managed committed generations, validates exact request/result/actor/admission and
retained immutable records, and evaluates current replay permissions separately.
New Relation creation persists the existing RelationRevision shape.

Two root variants are added within the existing eight families:
`knowledge#/$defs/NodeRevisionSnapshot` supplies exact legacy content without
modifying metadata-only historical revisions; `transaction#/$defs/HistoryBaseline`
is a closed fresh/migrated trusted-host result/profile marker. Existing producers'
records remain structurally accepted. Previous closed readers reject both new kinds;
source hashes, generated artifacts and pinned runtime must upgrade together.
Fresh persisted state uses the marker; existing legacy repositories remain
create-only readable only with verifiable original ancestry and are migrated
explicitly before future mutation activation. There is no automatic read repair.

Original receipts, requests, resource and revision IDs and existing historical bytes
remain unchanged during migration. A migration adds canonical supplements/missing
RelationRevision and one durable marker under a source-generation fence and single
managed-ref CAS. The Git ancestry must retain every original publication and marker;
missing objects, shallow history, merge ambiguity or a missing original effect fail
closed. This is no signed external attestation against a trusted administrator who
replaces all repository history. See [M2.1 design](../core/m2-1-immutable-history.md).
Physical flush, backup and deployment isolation guarantees remain unverified.
