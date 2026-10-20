# Validation record

Date: 2026-10-20. Scope: architectural delivery and fabricated examples only.

Result: **PASS** — 2 schemas, 20 schema refs, 4 fixtures, 11 rejection probes, 3 additional valid probes, 2 OpenAPI refs and 39 portable document links. Repeated successfully from a different working directory. Python syntax compiled successfully; Markdown code fences were balanced. All **112** baseline inventory files matched their pre-delivery SHA-256 hashes. The delivered folder contains 29 files, including 19 Markdown documents; no nested Git metadata was created.

## Executed checks

- Parsed both JSON Schemas and checked their Draft 2020-12 metaschema validity with installed `jsonschema` 4.26.0 on CPython 3.13.2 / Windows.
- Resolved all local and cross-file schema references using a preloaded `referencing.Registry`, with no network retrieval callback.
- Checked two valid and two intentionally invalid fabricated fixtures. Invalid fixtures must fail at the intended field/keyword, not merely fail to load.
- Added targeted negative probes for extra properties, unsafe/zero/string/bool revisions, unknown lifecycle, bad UUID, timestamp offsets/leap seconds, nested provenance ID and null optional list. Positive probes cover embedded relation refs and omitted/string/null description handling.
- Parsed the JSON-syntax YAML OpenAPI example; checked its declared profile/security and both external schema references. This is targeted validation, not a complete OpenAPI semantic lint.
- Checked that relative Markdown file links resolve inside the portable folder. No private files or parent paths are required by those links.
- Compared SHA-256 of the existing Phase 1 inventory files before and after delivery, excluding upstream checkout `.git` internals. No inventory artifact/tool was changed. Source export paths were never targets of a write.

The installed jsonschema lacked its optional RFC3339 format checker. The check initially failed explicitly instead of silently accepting bad dates. The example validator uses a documented fallback only for the project's narrower UTC timestamp profile, calling Python's standard `datetime` calendar parser after the profile's regex. It is not a general RFC3339 implementation. M2 still requires the standard format extra and cross-language parity fixtures.

## Validator module refactor

The original delivery counts above describe the initial package. The validator
was subsequently extracted into `tools/example_validation.py`: `ExampleValidator`
owns the root, schema registry and validators; separate methods check each group;
an immutable `ValidationReport` carries counts. `tools/validate_examples.py`
remains the CLI. Parsing and traversal helpers remain ordinary functions.
No dependencies, runtime platform components or plugin abstractions were added.

## Not executed / not claimed

No dependencies were installed. No Pydantic/TS generation, Ajv validation, Redocly lint, oasdiff run, package build, API server, migration, process runtime or Obsidian plugin was executed. No native Excel or prior spreadsheet verification was repeated. macOS/Linux behavior, Git/filesystem crash recovery and security conformance are future acceptance gates, not validated features.

The deliverable is a reviewable specification with syntactically/structurally checked examples. It is not a certified production schema release or a working Second Brain runtime. Run the portable check again using `python tools/validate_examples.py` from the module root; environment differences fail visibly.
