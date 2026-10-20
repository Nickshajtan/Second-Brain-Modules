# Contract toolchain specification

Status: illustrative toolchain implemented during repository hardening. Exact locks, generated artifacts, unit tests and Python/Ajv parity now exist. Production schema approval and all-OS CI confirmation remain gates. See [hardening report](hardening-report.md) for executed results.

## 1. Sources and candidate versions

Canonical JSON Schema is authoritative. Generated Pydantic classes are ergonomic application types, TS declarations are static types, and neither replaces JSON Schema runtime validation. No reverse generation from Pydantic/OpenAPI into authoritative schemas. Generated files MUST NOT be edited manually.

| Purpose | Proposed dependency/profile | Why / known limit |
|---|---|---|
| Python baseline | CPython 3.12+; generation environment 3.12.x, exact patch recorded in M2 | Matches modern generators; Phase 1 scripts remain independently usable on their current Python |
| Python schema validation | `jsonschema[format]>=4.26,<5`, explicit Draft202012Validator + FormatChecker; `referencing>=0.36,<1` constrained by lock | Independent structural oracle; registry preloaded locally, retrieval disabled. Format checking must be enabled. [Validation docs](https://python-jsonschema.readthedocs.io/en/stable/validate/) |
| Python models | `datamodel-code-generator==0.86.0`, output `pydantic_v2.BaseModel`; `pydantic>=2.10,<3` | Mature generator; selected dated release, not current main presets. Full 2020-12 equivalence is not assumed. [Repository](https://github.com/datamodel-code-generator/datamodel-code-generator), [release](https://github.com/datamodel-code-generator/datamodel-code-generator/releases/tag/0.86.0) |
| TS static declarations | `json-schema-to-typescript==16.0.0` | Established CLI; oneOf static output is a union rather than exclusive validation; do not depend on unreleased main features such as newer unevaluated handling. [Repository](https://github.com/bcherny/json-schema-to-typescript) |
| TS runtime validation | `ajv>=8.17,<9`, `ajv-formats>=3,<4`, import `ajv/dist/2020.js` | Draft-specific validator; no draft-07 mix in same instance. Formats separate. [Dialect docs](https://ajv.js.org/json-schema.html), [formats](https://ajv.js.org/guide/formats.html) |
| JS/TS baseline | Node 22.19+ in 22.x for initial generation, npm 10.9.2+, TypeScript `>=5.7,<6` | Single pinned CI generation runtime; later Node versions need parity smoke test. `strict`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess` |
| HTTP lint/docs, when binding added | `@redocly/cli>=2,<3`, locked exact | Lint + offline bundle + build-docs. Resolving refs is not proof a client generator preserves all schema semantics. [Repository/commands](https://github.com/Redocly/redocly-cli) |
| HTTP compatibility, when binding added | `oasdiff` 1.x, exact binary version/checksum pinned by CI | HTTP breaking-change checks only, not arbitrary JSON Schema inclusion or business semantics. [Repository](https://github.com/oasdiff/oasdiff) |

Actual development dependencies are fully pinned in root `requirements-dev.lock`
(hashes, pip-tools 7.5.1) and `package-lock.json`. Pydantic resolves to 2.14.1;
jsonschema 4.26.0, datamodel-code-generator 0.86.0, json-schema-to-typescript
16.0.0, Ajv 8.17.1, ajv-formats 3.0.1 and TypeScript 5.9.3 are exercised.
Ruff 0.14.1/pytest 8.4.2 and openapi-spec-validator 0.7.2 are dev-only.
Black/isort are locked transitive generator dependencies. OpenAPI semantic validation
uses its standard SchemaPath accessor with a preloaded referencing registry and no retrieval callback; no
custom bundler or translator. Redocly/oasdiff remain optional future HTTP tooling.
Dependencies are local, with no globally installed generators. Full commands are in
[versioning and consumption](versioning-and-consumption.md).

## 2. Supported schema authoring profile

Draft 2020-12 remains the validator language. The initial **generation profile** is intentionally narrower so model generation remains predictable: named object roots; `$defs`; ordinary local `$ref`; strings/booleans/bounded numbers/arrays; required properties; explicit closed objects; string enums/const; tagged `oneOf` alternatives. No `$dynamicRef`, custom vocabularies, recursive composition tricks, executable extensions, or conditional business logic in initial generated models. This is a documented usage policy, not a new schema dialect or DSL.

| Feature | Required behavior and proof |
|---|---|
| `$ref` | Stable resource IDs mapped to local files; relative references resolve against resource base. Preload transitive closure; any unresolved or network-only ref fails. Generator file refs must be tested with `$id`, not merely filesystem coincidence |
| Recursive structures | Prefer ID-based graph references. Ordinary recursive `$ref` supported only after a dedicated generator/validator fixture passes; cyclic object instances are not JSON. `$dynamicRef` deferred |
| Missing vs null | Omission is separate from explicit null. Use nullable type union only when null has domain meaning. Generated Pydantic may default an omitted optional property to None; validate canonical JSON first and serialize using `exclude_unset=True`, preserving explicitly supplied null |
| Discriminated unions | `oneOf` branches use required literal discriminator field and disjoint tags. Pydantic discriminator behavior tested; Ajv validates ordinary oneOf, no custom discriminator required. TS union does not prove exclusivity |
| Enums/extensibility | Closed lifecycle/security enums; unknown values rejected. Extensions explicitly namespaced and bounded. Adding enum members can break old consumers and exhaustive TS switches |
| Extra/unevaluated fields | `additionalProperties:false` on plain objects initially. Avoid closure through complex allOf; `unevaluatedProperties:false` valid in canonical schemas but cannot enter generation profile before parity proof. Never silently strip unknown fields |
| Formats | Explicit validators in Python and Ajv + ajv-formats. UTC timestamp profile additionally restricts spelling/range. Unknown asserted format fails configuration. Keep format outputs as JSON strings, not automatic TS Date |
| Defaults | JSON Schema defaults are annotations, not writes. Ajv `useDefaults:false`, `coerceTypes:false`, `removeAdditional:false`. No validation-side mutation; application defaulting is explicit, versioned and precedes output validation |
| Python semantics | Pydantic can coerce and serialize dates/enums differently. Canonical schema validation comes before model construction; strict parsing where supported and canonical output validation after serialization. [Strict-mode docs](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/) |
| TS/JSON numeric semantics | Integer ≠ any JS number; revision bounded to safe integer. Reject NaN/Infinity, booleans as ints in Python. Decimal/large integer domains use explicitly defined strings, never lossy coercion |
| Patterns / Unicode | Portable regex subset; no Python-only constructs. Restrict identifiers to ASCII where possible; Unicode bodies round-trip untouched. Length counts and normalization tested with non-BMP characters |
| Constraints/types | TS types cannot represent all numeric bounds/pattern/uniqueItems assertions. Pydantic may approximate constraints. Runtime canonical validators remain final authority |
| Determinism | Fixed tool versions/config/input ordering/LF/UTF-8; no timestamp headers/absolute paths; run twice in clean trees, compare bytes across all target OS |

A model accepting an invalid fixture is not automatically a wire-contract failure if the canonical ingress validator rejects it first; document that approximation. A model rejecting a valid wire fixture, dropping supplied properties, or changing its canonical meaning is a release blocker. Never narrow canonical semantics merely because a chosen generator is inconvenient.

## 3. Concrete generation proposal

The current spike uses the two schemas in `docs/architecture/examples/` without
promoting them into production schemas. Run from the repository root with the locked
environment active:

```text
python -m tools.generate_contracts
python -m tools.generate_contracts --check
python -m pytest -q
npm run typecheck
npm run parity
```

`tools/generate_contracts.py` invokes the established Python generator with explicit
flags and locked Black/isort, and `generate_typescript.mjs` invokes compileFromFile
with HTTP resolution disabled. No custom templates. Outputs are in
`packages/python/generated/` and `packages/typescript/generated/`; their source/lock/
configuration hashes are recorded alongside Python output. Drift detection regenerates
in a clean temporary directory and compares the full file set, including untracked extras.
The shared 24-case corpus is `tests/fixtures/parity.json`. Python validates with
jsonschema and compares verdicts to Ajv2020 with formats, strict mode and all input
mutation/coercion disabled. Valid cases round-trip through generated Pydantic models.

Observed limitation: Python renames JSON `class` to `class_`; callers MUST dump using
`by_alias=True`, `mode="json"` and `exclude_unset=True` to preserve wire names and
missing-versus-null. Generated optional fields can accept None more broadly than the
canonical schema, and format-aware fields become Python UUID/datetime values. Numeric
coercion/pattern fidelity and TS bounds are not canonical guarantees. Validate before
model construction and validate serialized output. Duplicate shared generated helper
types are acceptable derived output. No generated file was hand-edited.

The remaining pipeline below is the target release gate: local Windows execution is
not proof of macOS/Linux or hosted Actions success. Production package publication,
advanced recursion/unions and production schema migration remain outside this spike.

Optional HTTP milestone commands after its dev tools are locked:

```text
npm exec -- redocly lint bindings/http/openapi.yaml
npm exec -- redocly bundle bindings/http/openapi.yaml -o dist/openapi.yaml
npm exec -- redocly build-docs bindings/http/openapi.yaml -o dist/http-reference.html
oasdiff breaking previous-release/openapi.yaml dist/openapi.yaml
```

Bundle schemas using tool-supported resolution; preserve canonical IDs and semantic assertions. Validate bundled and unbundled fixtures identically. Static HTML docs are build artifacts, not a new authoritative schema. Initially Markdown tables and schema descriptions suffice; no documentation platform dependency is required.

## 4. Fixture layout, parity and compatibility gates

Proposed fixture structure: `tests/fixtures/<family>/<version>/valid/*.json`, `invalid/*.json`, and `semantic/*.json` with human-readable expected rule/error in adjacent test metadata. Valid/invalid here means structural verdict, not permission to commit a record. Only fabricated examples belong in the reusable repository. Never copy Phase 1 private records into public CI.

Minimum shared corpus: absent/explicit-null; unknown field; extension object; valid/invalid refs; discriminator ambiguity; recursive refs; emoji/non-ASCII; safe integer bounds and numeric strings; duplicate object keys; RFC3339 offset/leap-second edge; empty arrays; enum expansion; YAML quoted/unquoted scalars. Negative cases must fail for the intended reason; schema loader failure is not a valid negative verdict. Test payload size/depth limits independently. Key-duplicate tests are raw text tests because ordinary JSON objects cannot preserve duplicate keys.

M2 pipeline:

1. Parse schemas with duplicate-key detection, validate their metaschemas and all refs offline. Fail on unsupported formats or keywords in generation profile.
2. Run the exact same valid/invalid JSON corpus through Python jsonschema and Ajv2020; require identical verdicts. Compare semantic error categories where normalized, not vendor-specific message text.
3. Generate Pydantic and TS outputs from a clean tree twice. Import/typecheck them. Feed all valid fixtures through models, serialize preserving omissions, and validate canonical outputs. Assert no lost fields/changed meanings. TS compile-time negative tests supplement runtime tests.
4. Run operation conformance tests for applicable Bxx rules with fake storage/policy ports; no real model/network required.
5. Regenerate committed outputs and fail on `git diff --exit-code` **and untracked generated files**. Check file lists and source-schema hashes; plain diff alone misses new files. Generator upgrades run separately from schema changes.
6. Test old producer/new consumer and new producer/old consumer for supported negotiated combinations. Evaluate request and response directions separately. Use oasdiff for HTTP only. No chosen generic tool proves full JSON Schema 2020-12 set inclusion; manual semantic review plus corpus is required. This is a concrete tooling limitation, not grounds for a custom compatibility engine.
7. Run on Windows/macOS/Linux and compare artifact hashes from the same locked generation environment. Publish only after those pass; store schema/generator/lock hashes with package metadata.

## 5. Ownership and release

**Commit generated source** under the package directories, with generator banner and source hash manifest. This makes submodule checkout inspectable, permits consumers to build without a generator environment, and exposes drift in review. Generate only in maintainer CI/development, never automatically at consumer install time. Keep generation dependencies development-only; runtime validators and Pydantic are explicit package runtime dependencies when packages exist.

Release Python and TS packages together against the same contract release and include canonical schemas as package data. A consumer pins a submodule commit or package version; mixing generated models from a different schema release must fail a version/hash check. Publish neither private data nor project-specific policy. Human-authored domain validators live outside generated directories. Migration tools are separately reviewed and versioned. CI does not need Nx/Turborepo, a universal adapter generator, or a package publishing service at this stage.
