# Codex Task — Contract Generation & Distribution Hardening

## Context

Repository: `Nickshajtan/Second-Brain-Modules`

Phase 2 introduced canonical JSON Schema Draft 2020-12 contracts, generated Python/Pydantic and TypeScript artifacts, offline validators, deterministic generation, source manifests and CI drift checks.

We want to improve the separation between **source contracts**, **generated artifacts**, and **distribution**, while preserving the current Git-submodule consumption model.

Our architectural preference is:

> Generated artifacts should eventually be excluded from source Git and produced through a reproducible build/release process.

However, do not introduce package publishing infrastructure prematurely.

## Objectives

1. Establish an explicit Source → Build → Distribution lifecycle.
2. Keep JSON Schema as the single canonical structural authority.
3. Ensure generated Python/TypeScript artifacts can be rebuilt reproducibly.
4. Prepare for a future `dist-free Git` model.
5. Preserve current consumer compatibility.
6. Keep initialization independent of code generation.

## Scope

### 1. Define artifact ownership

Classify existing files as:

- **Source:** Canonical schemas, registry, generator configuration, tests, fixtures and documentation.
- **Generated:** Python/Pydantic models, TypeScript declarations and generation manifests.
- **Runtime support:** Handwritten validation adapters that consume canonical schemas/generated types.
- **Distribution:** Future installable or bundled packages containing validated contracts.

Do not classify handwritten runtime validators as disposable generated files.

### 2. Define lifecycle commands

Reuse the existing tooling.

Support these conceptual operations:

```bash
python -m tools.generate_contracts
python -m tools.generate_contracts --check
python -m tools.validate_contracts
```

Add a lightweight `build` or `package` command only if necessary to prepare an isolated, self-contained distribution directory.

Do not duplicate generation logic.

A build must:

- Use the existing pinned toolchain.
- Include canonical schemas and the registry.
- Include generated Python/TypeScript artifacts.
- Include required runtime validation code.
- Verify source/artifact consistency.
- Fail on missing, stale or unexpected artifacts.
- Avoid network access after dependencies are installed.

### 3. Keep initialization lightweight

A future Second Brain instance `init` must not require contract generation.

Its responsibilities should be limited to:

- Selecting the compatible contract version.
- Validating the availability and integrity of contract artifacts.
- Initializing instance-specific state when that functionality exists.

Do not implement instance initialization during this task.

### 4. Prepare for dist-free Git

Document two supported delivery models.

**Current model:**

```text
Git submodule
  ├── canonical schemas
  ├── generated Python
  └── generated TypeScript
```

**Target model:**

```text
Source Git
    │
    ▼
Reproducible build
    │
    ▼
Versioned contract distribution
    ├── canonical schemas
    ├── Python artifacts
    └── TypeScript artifacts
```

Design the tooling so that future consumers can switch between these models without changing domain schemas or public type semantics.

Do not implement PyPI/npm publishing.

Do not introduce an artifact server or registry.

### 5. Prevent accidental coupling

Check that:

- Handwritten code imports generated models through documented public import paths.
- Generated outputs are never manually edited.
- Generation scripts do not depend on the consumer instance's working directory.
- Generated output locations are configurable where practical.
- Runtime code does not rely on developer-only absolute paths.
- A clean source checkout can reproduce the distribution using the documented pinned dependencies.

Avoid widespread refactoring for hypothetical packaging requirements.

### 6. Strengthen validation gates

Verify:

- Generation is deterministic.
- Canonical schema references resolve offline.
- Python and TypeScript parity remains intact.
- Generated files match source hashes.
- No unexpected generated artifacts appear.
- Build outputs are reproducible in clean temporary directories.
- Existing tests and cross-platform CI remain functional.

If a build command is introduced, test that a distribution contains all required resources and does not depend on undeclared source-tree paths.

Do not run unrelated runtime or infrastructure tests.

## Important constraint

**Do not remove generated artifacts from Git in this task.**

Instead, make their future removal possible without redesigning the generator or contract interfaces.

Treat the current tracked generated files as a temporary distribution mechanism.

If analysis shows that removing generated artifacts now is safe and significantly simpler, document the alternative and its exact migration steps, but do not silently change the consumption model.

## Deliverables

1. Minimal tooling/configuration changes, only where justified.
2. A documented contract build/distribution lifecycle.
3. A clear distinction between source, generated and runtime-support files.
4. A future migration procedure for dist-free Git.
5. Relevant tests or CI hardening.
6. No changes to canonical domain semantics.

## Acceptance criteria

- Existing generation/parity/test workflows still pass.
- A clean checkout can reproduce all generated artifacts.
- Runtime consumers have documented, stable import surfaces.
- The eventual removal of generated files from Git is a distribution change, not a domain-contract migration.
- No new framework, publishing service or heavyweight dependency is introduced.
- No runtime Core/MCP/Obsidian implementation is added.

Report any technical obstacle that would prevent a future dist-free repository.

Prefer a small, focused change set.

**The goal is to strengthen the contract build boundary, not create a packaging platform.**