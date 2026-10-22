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
