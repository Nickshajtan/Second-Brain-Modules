# Compatibility contract

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
| New RelationRevision union alternative | Old Relation head records accepted | Rejects new kind | Structural full snapshot only; M1 still rejects unsupported persisted kind; no on-read conversion |
| Common RelationRef / NodeRevisionRef / RelationRevisionRef | Existing references unchanged | No promise of newly exported names | Typed refs separate logical revision/resource/Git identity; semantic equality and retention checks remain required |
| NodeRevisionRead / RelationRevisionRead requests | Existing current-read requests accepted | Rejects new discriminator | M1 finite dispatch rejects both; M2 must implement historical authority/resolution and exact retained revision response |

Actual directional probes used the previous HEAD canonical eight-resource bundle with independent jsonschema validation: it rejects the five new producer shapes above (explicit Node ID, Node snapshot, RelationRevision, two historical reads) and accepts the original metadata-only NodeRevision. The amended corpus accepts original shapes plus the new valid fixtures and rejects null/missing snapshots/wrong endpoint kinds. These are sampled directional acceptance checks, not a proof of universal schema inclusion or behavioral compatibility.

No runtime mutation/history handler is enabled. The current-head creation-receipt verification must not be reused after updates. M2 must persist/resolve immutable original Node/Relation snapshots and original admission effects, validate exact digest/resource/revision correspondence and current replay permissions, and explicitly migrate old retained original commit effects before activation. No integrity check is removed. Physical Git retention and backup/durability policy remain separately verified.
