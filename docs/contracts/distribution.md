# Contract source, build and distribution

JSON Schema remains canonical. Generated artifacts stay tracked for current submodule consumers.

| Ownership | Files | Maintenance |
| --- | --- | --- |
| Source | Schemas, registry, generator scripts/configuration, locks, tests, fixtures, docs | Edit and review; regenerate after relevant changes |
| Generated | `packages/python/generated/`, `packages/typescript/generated/`, including manifests | Never edit manually |
| Runtime support | `packages/python/second_brain_contracts/`, TypeScript `validation.mjs` and `validation.d.mts` | Handwritten public adapters, retained in source Git |
| Distribution | `dist/contracts-1.0.0/` or an explicit output | Disposable ignored local bundle; no publishing infrastructure |

## Build lifecycle

Use Python 3.12 and Node 22.19–24. Install pinned dependencies from a clean checkout:
`python -m pip install --require-hashes -r requirements-dev.lock` and
`npm ci --ignore-scripts --no-audit --no-fund`. Subsequent commands run offline.

```sh
python -m tools.generate_contracts
python -m tools.generate_contracts --check
python -m tools.validate_contracts
python -m tools.build_contracts --output dist/contracts-1.0.0
python -m tools.build_contracts --check dist/contracts-1.0.0
```

Generation accepts `--output-root DIRECTORY`. From another working directory, invoke
the absolute generator or builder script path: source discovery uses the script's
checkout, never the consumer CWD. Explicit relative output paths use the caller CWD.
Build requires a fresh destination, reuses the existing generator, compares the exact
tracked generated file set and rejects missing, stale or unexpected artifacts.
It never overwrites an existing destination or modifies source outputs.

The bundle contains eight canonical schemas, registry, production generated v1 Python
and TypeScript, handwritten adapters, LICENSE, runtime dependency declarations, build
locks and `distribution.json`. Tools, tests and illustrative generated examples are
excluded. The distribution manifest hashes the exact first-party payload; the generated
production manifest binds canonical inputs to generated artifacts. Checks reject
missing/changed/unexpected payload files. Hashes detect drift, not publisher identity.
Installed `node_modules` and bytecode caches are excluded environment state.

## Runtime consumption

First-party resources are self-contained; third-party dependencies are not vendored.
Provision Python dependencies declared in `requirements-runtime.txt` and Node dependencies
in the private runtime `package.json` before offline use. Exact transitive versions are
recorded in `build-locks/requirements-dev.lock` and `build-locks/package-lock.json`.
Those full locks include build tools for provenance; runtime adapters do not import them.
Runtime declarations alone do not lock transitive versions: reproducible provisioning
must use the recorded locks or a consumer lock derived from them. For a local Node
installation use `npm install --ignore-scripts --no-audit --no-fund --package-lock=false`;
keep consumer lock files outside the bundle's first-party inventory.

Add the bundle's `packages/python` to the import path. Public imports remain
`from second_brain_contracts import ContractValidator` and
`from generated.v1.knowledge_schema import Node` (other families follow the registry).
`ContractValidator()` infers the packaged root; `verify_generated()` checks its production
manifest. Use `validate`, `parse` and `dump` for canonical validation and serialization.
Direct generated-model construction does not replace canonical validation.

TypeScript declarations remain at `packages/typescript/generated/v1/<family>.d.ts`.
Import `loadContracts` from `packages/typescript/validation.mjs` and pass the bundle root
and compatible version, e.g. `loadContracts(bundleRoot, '1.0.0')`. Preserve relative
bundle layout. Neither runtime surface imports a generator or requires a source checkout.
See the [contract guide](README.md) for complete examples.

## Current delivery and dist-free Git migration

Today a consumer pins a Git submodule commit containing schemas, generated artifacts
and adapters. This remains supported. The target is Source Git → reproducible build →
versioned distribution → consumer, with identical schemas and public type semantics.

`python -m tools.build_contracts --from-source --output DIRECTORY` generates fresh
without consulting tracked outputs, including when those directories are absent.
The normal mode continues checking tracked drift. Automated tests compare independent
clean builds, exercise a source-only checkout and run Python jsonschema and Node Ajv
consumers outside the checkout with only declared runtime dependencies available.

Migration steps:

1. Agree and implement versioned artifact delivery, dependency provisioning and a trust
   policy. Package publication and artifact servers are outside this task.
2. Release CI builds with `--from-source`, retains parity/reproducibility gates and
   delivers the complete verified bundle.
3. Consumers select a compatible bundle and validate availability/integrity before use.
4. Only then remove generated directories from tracking and ignore them. Change the
   tracked-output drift gate to compare fresh generation with delivered artifacts.
   Keep schemas, handwritten adapters and generation sources tracked.

The remaining obstacle is a delivery/provisioning policy, not schema or import coupling.
This is a distribution change, not a domain-contract migration. Future instance `init`
selects a version, verifies artifacts and initializes state; it never runs generation.
Instance initialization is deliberately not implemented.
