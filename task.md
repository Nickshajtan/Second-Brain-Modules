# Second Brain — M1.1: Engineering Quality & Repository Hygiene

**Repository:** `Nickshajtan/Second-Brain-Modules`  
**Baseline:** Latest `main`, following Core M1 implementation  
**Status:** Implementation task  
**Scope:** Code quality, static analysis, engineering standards, CI hardening and evidence-based repository cleanup.

## 1. Objective

Establish a consistent, enforceable engineering quality baseline before continuing Second Brain Core development.

The repository now contains:

- Canonical JSON Schema 2020-12 contracts.
- Generated Python/Pydantic and TypeScript artifacts.
- Contract validators and generation/build tools.
- Python Core M1.
- Git-backed atomic transaction storage.
- Tests, architectural documentation and historical research artifacts.

The next development phases will introduce mutable revisions, reconciliation, governance and MCP.

Before expanding the codebase, improve its maintainability and remove demonstrably unnecessary repository artifacts.

**This task is primarily hardening and cleanup, not feature development.**

## 2. Non-negotiable constraints

1. Do not change accepted domain semantics.
2. Do not implement M2 or new domain operations.
3. Do not change persisted record formats without an explicit compatibility justification.
4. Do not manually edit generated artifacts.
5. Do not replace the existing contract toolchain.
6. Do not introduce a second formatter or overlapping linting framework without justification.
7. Do not introduce heavyweight architectural abstractions.
8. Do not delete files merely because they are old.
9. Do not rewrite Git history or force-push.
10. Do not delete untracked or user-authored files without establishing their purpose and obtaining explicit approval when uncertain.
11. Do not suppress lint/typecheck findings globally merely to produce a green build.
12. Do not perform broad mechanical refactors unrelated to confirmed quality issues.

Prefer minimal changes with measurable quality improvements.

## 3. Initial repository audit

Before modifying the repository, inspect:

- Current Git status and tracked files.
- Existing CI workflow.
- Dependency lockfiles.
- Python/TypeScript package structure.
- Canonical schemas and generated outputs.
- Build/distribution workflow.
- Existing documentation hierarchy.
- Development tooling.
- Ignore rules.
- Test fixtures and temporary artifacts.
- Relevant ADRs and supersession notices.

Establish the difference between:

- Tracked source files.
- Tracked generated distribution artifacts.
- Ignored build outputs.
- Untracked working files.
- Historical architectural records.
- Active production contracts.
- Obsolete documentation.
- Redundant or unused implementation code.

Do not assume that an unused file is safe to remove.

### Required audit output

Produce a repository hygiene inventory:

| Path | Classification | Evidence | Recommended action | Risk |
|---|---|---|---|---|
| Example | Source/generated/historical/temp | Actual references and consumers | Keep/move/remove/ignore | Low/medium/high |

Use actual paths and evidence.

Avoid listing every legitimate source file. Concentrate on cleanup candidates and inconsistencies.

## 4. Safe cleanup

### 4.1 Automatically eligible cleanup

Files may be removed or ignored when their purpose and disposal safety are demonstrated.

Examples:

- Accidentally tracked Python caches.
- Temporary test output.
- Reproducible build caches.
- Redundant local reports.
- Accidentally committed virtual environments.
- Orphaned temporary development files.
- Obsolete generated duplicates not required by the current distribution model.
- Stale build output unintentionally tracked outside the intended distribution policy.

Before removal, confirm they are not referenced by tests, scripts, documentation or consumers.

### 4.2 Cleanup requiring architectural review

Do not automatically delete:

- Historical ADRs.
- Contract migration/evolution documentation.
- Earlier schema examples used by parity tests.
- Domain glossary and operation catalogue.
- Research and evidence ledgers.
- User-authored notes or specifications.
- Current generated models required by Git-submodule consumers.
- Existing fixtures or snapshots without proving redundancy.
- Source compatibility adapters.

For these, recommend consolidation, relocation, archival or supersession markers where appropriate.

### 4.3 Documentation cleanup

Identify:

- Duplicate README content.
- Broken relative links.
- Contradictory active guidance.
- Superseded development instructions.
- Outdated implementation status.
- Repeated command documentation.
- Historical proposals presented as current decisions.

Create or update a concise documentation entry point.

Suggested structure:

```text
README.md
docs/
  architecture/
  contracts/
  core/
  domain/
  engineering/
  research/
```

Adapt to the existing structure.

Do not reorganize for aesthetics alone.

Preserve historical decision provenance.

Prefer adding a current-document pointer to rewriting previous ADRs.

### 4.4 Git hygiene

Review `.gitignore` for:

- Python caches.
- Virtual environments.
- Test/coverage output.
- Typechecker caches.
- Node dependencies.
- Build/distribution output.
- Editor-specific temporary files.
- Local secrets/configuration.
- Temporary Git repositories used in tests.
- Local research caches.

Ensure ignore rules do not conceal canonical schemas, test fixtures or source code.

Do not indiscriminately ignore all generated code while Git-submodule compatibility still depends on tracked artifacts.

## 5. Python quality standard

Use Ruff as the primary linter and formatter.

Retain the current Python baseline and line-length conventions unless a concrete issue requires change.

### 5.1 Ruff

Review the existing profile and gradually enable useful rule families.

Recommended candidates:

- `E4`, `E7`, `E9`
- `F`
- `I`
- `UP`
- `B`
- `SIM`
- `C4`
- `PIE`
- `RET`
- Selected `RUF` rules.

Do not enable every rule blindly.

Inspect violations before applying fixes.

Use narrow per-file exceptions only with documented reasons.

Avoid global ignores that hide defects.

### 5.2 Formatting

Use Ruff format as the sole handwritten Python formatter.

Exclude generator-owned Python output from handwritten formatting enforcement.

Do not run multiple competing formatters over the same files.

Generated output reproducibility is controlled by generation checks.

### 5.3 Static typing

Introduce **Pyright** for handwritten production Python.

Targets:

- `second_brain_core`
- `second_brain_contracts`
- Relevant handwritten tooling where practical.

Generated Python models may be imported as dependencies but should not be manually rewritten to satisfy handwritten typing rules.

Adopt a strictness policy that is realistic for the current codebase.

Suggested direction:

- New public production APIs: fully typed.
- Internal boundary interfaces: typed.
- Domain operation input/output: generated contract types.
- Infrastructure ports: narrow typed interfaces or Protocols where useful.
- Existing dynamic internals: progressively improved.

Avoid introducing handwritten DTO copies of generated domain contracts.

Do not introduce `Any`, `cast`, `type: ignore` or blanket diagnostic suppression without a concrete justification.

If full strict Pyright would cause excessive unrelated refactoring, establish an explicit transitional baseline with documented diagnostics.

### 5.4 Error handling

Review broad exception handling in security- and storage-sensitive paths.

Distinguish:

- Invalid caller input.
- Authorization denial.
- Revision/CAS conflicts.
- Corrupt committed state.
- Storage failures.
- Programmer defects.

Maintain sanitized external error envelopes.

Preserve useful internal diagnostics without leaking sensitive content.

Do not expose Git stderr or private paths to untrusted callers.

Do not add a generic exception framework.

## 6. Contract runtime boundary

Inspect dependencies between Core and `second_brain_contracts`.

Eliminate inappropriate imports of private implementation helpers.

In particular, review strict JSON encoding/decoding helpers currently imported by Core from private functions in the validation module.

Prefer one documented public strict JSON API with predictable semantics.

Do not duplicate parsers and validation logic across packages.

Preserve:

- Duplicate-key rejection.
- Non-finite number rejection.
- Canonical input/output validation.
- Unicode round-tripping.
- Existing generated-model behavior.

Add focused regression tests for any changed boundary.

## 7. Git and receipt correctness review

Perform a limited correctness review of existing M1 code.

Focus on:

- Conditional Git ref publication.
- Path safety.
- Subprocess invocation and environment isolation.
- Canonical snapshot validation.
- Instance identity.
- CAS behavior.
- Idempotency replay.
- Receipt integrity.
- Corruption handling.
- Process restart.

Do not redesign the storage backend.

### 7.1 Historical receipt compatibility

Before implementing future mutable revisions, review whether receipt validation assumes that a historical operation result must still match the current resource head.

Identify the exact coupling.

If the current M1 implementation is correct only because all supported resources are create-only, document this limitation.

Prefer a small forward-compatible correction only if it can be implemented without changing existing domain semantics or persisted formats.

Do not implement Node update in this task.

### 7.2 Snapshot complexity

Current committed reads may validate the entire Git tree.

Treat this as an accepted M1 performance trade-off.

Do not introduce SQLite indexing or caching solely to optimize the current tiny corpus.

Document the performance characteristics and the future immutable-snapshot caching boundary.

Do not relax authorization checks when introducing future caching.

## 8. TypeScript and JavaScript quality

Inspect handwritten TypeScript/JavaScript files, particularly:

- Runtime contract validation.
- Contract generation tooling.
- Build tooling.
- Tests and TypeScript consumer fixtures.

Introduce a small ESLint configuration only if it offers meaningful coverage not already supplied by TypeScript and existing tests.

Prefer:

- Correctness-focused rules.
- Import hygiene.
- Explicit handling of unchecked runtime inputs.
- No unnecessary `any`.
- No accidental use of Node-specific globals in portable consumers.

Do not introduce Prettier unless a concrete formatting need cannot be met by the existing workflow.

Do not lint generated `.d.ts` artifacts as handwritten source.

Keep ESLint dependencies and configuration minimal.

## 9. Generated code policy

Establish clear file ownership boundaries.

| Category | Source of truth | Required checks |
|---|---|---|
| Canonical schemas | Handwritten JSON Schema | Schema validation, offline refs, compatibility |
| Python generated models | Canonical schemas + generator | Deterministic generation, import/round-trip tests |
| TypeScript generated types | Canonical schemas + generator | Deterministic generation, TS consumer typecheck |
| Python runtime adapters | Handwritten source | Ruff, Pyright, tests |
| JS/TS runtime adapters | Handwritten source | Typecheck/lint/tests |
| Build/distribution output | Reproducible build | Integrity, reproducibility, packaging checks |

Do not format generated models after generation.

Do not patch generated declarations manually.

Respect the current distribution policy and future dist-free transition.

Make build artifacts disposable while preserving the current documented consumption model.

## 10. Engineering standards

Introduce a concise root `AGENTS.md`.

It must guide Codex and other coding agents without becoming an oversized architectural document.

Required rules:

1. Read current domain contracts and ADRs before changing behavior.
2. Use canonical JSON Schema as the structural authority.
3. Never hand-edit generated artifacts.
4. Reuse generated Python/TS models rather than defining duplicate DTOs.
5. Keep domain semantics independent of storage and transports.
6. Require canonical validation at untrusted boundaries.
7. Write regression tests for confirmed defects.
8. Type new public APIs.
9. Use Ruff formatting for handwritten Python.
10. Preserve fail-closed authorization behavior.
11. Do not invent Owner policy decisions.
12. Do not add dependencies or abstractions without a concrete need.
13. Run relevant tests and quality checks.
14. Report what was actually tested and what remains unverified.
15. Preserve existing user changes and avoid destructive repository operations.

Put detailed standards under `docs/engineering/` only where useful.

Link to existing contract, architecture and testing documentation rather than duplicating it.

## 11. Unified local quality command

Provide a convenient, documented developer-facing entry point.

For example:

```bash
python -m tools.check
```

The exact command may differ if the repository already has a better convention.

Support a reasonable separation between:

- Fast source quality checks.
- Contract generation/validation checks.
- Core tests.
- Full verification.

Avoid creating a task-runner framework.

The local workflow and CI must use the same underlying commands.

Do not duplicate lint/test logic in multiple scripts.

## 12. CI hardening

Preserve the existing Windows/macOS/Linux CI matrix.

Organize checks conceptually into:

### Quality Gate

- Python Ruff lint.
- Python Ruff formatting.
- Pyright.
- TypeScript/JavaScript lint, if adopted.
- Syntax/import checks.

### Contract Gate

- Canonical schema validation.
- Reference resolution.
- Generated artifact drift.
- Python/Ajv parity.
- Distribution integrity.
- Cross-language consumer compatibility.

### Core Gate

- M1 functional tests.
- Domain invariant tests.
- Git atomicity.
- CAS/idempotency.
- Recovery.
- Instance isolation.

These may remain steps in the same workflow.

Avoid multiplying CI jobs without measurable benefit.

Pin new tools in the existing dependency-locking mechanism.

Do not weaken existing gates merely to make the build pass.

## 13. Test and coverage policy

Keep existing tests and fixtures.

Add targeted tests only where changes introduce new failure risks.

Introduce coverage reporting if useful, preferably through the existing pytest ecosystem.

Coverage should help locate untested critical code rather than serve as an arbitrary percentage target.

Prioritize:

- Authorization-denial paths.
- Transaction failure boundaries.
- Corrupt committed state.
- Retry and receipt replay.
- Contract validation.
- Error sanitization.
- Serialization.

Do not require 100% coverage.

Do not create test-only abstractions without concrete reuse.

## 14. Scope control and execution order

Perform the task in this order:

1. Audit repository and classify cleanup candidates.
2. Record current quality baseline.
3. Fix verified contract/Core boundary defects.
4. Introduce incremental lint/typecheck standards.
5. Make only necessary focused refactors.
6. Add or adjust regression tests.
7. Harden CI and local commands.
8. Perform safe repository cleanup.
9. Update current documentation and agent instructions.
10. Run complete relevant validation.
11. Report findings and remaining risks.

Use separate commits for quality tooling and cleanup if practical.

Do not mix unrelated cosmetic changes into correctness fixes.

## 15. Deliverables

Produce:

- Updated Ruff configuration.
- Pyright configuration and documented strictness baseline.
- Minimal ESLint setup, if justified.
- Root `AGENTS.md`.
- Updated CI/local quality workflow.
- Contract runtime boundary hardening.
- Focused M1 correctness fixes, only when substantiated.
- Repository hygiene inventory.
- Safe removal or ignore-rule updates.
- Updated engineering documentation.
- Relevant regression tests.
- Final validation report.

Suggested document paths:

```text
docs/engineering/
  standards.md
  repository-hygiene.md
  quality-validation.md
```

Adapt to existing conventions.

## 16. Acceptance criteria

The task is complete when:

- Handwritten production Python has an enforceable lint/format standard.
- Static typing is checked with a documented baseline.
- Generated artifacts are not treated as handwritten source.
- The contract-runtime boundary has no inappropriate private API dependencies.
- Local checks and CI agree.
- Existing Core and contract functionality remains unchanged.
- The repository has been audited for obsolete, duplicate and temporary content.
- Only demonstrably safe cleanup has been applied.
- Historical architecture and contract evidence remains accessible.
- No unnecessary dependency/framework proliferation was introduced.
- Relevant tests pass.
- The final report clearly distinguishes actual verification from assumptions.

Do not declare cleanup complete merely because the working tree is clean.

## 17. Final report

Report:

1. Initial quality findings and severity.
2. Tooling/configuration changes.
3. Confirmed defects fixed.
4. Refactors performed and justification.
5. Files removed, moved or ignored, with reasons.
6. Cleanup candidates intentionally retained.
7. Updated CI gates.
8. Executed commands and actual results.
9. Remaining quality risks.
10. Recommended next development milestone.

Include a short before/after repository inventory summary.

**The goal is a clean, consistently maintained engineering foundation — not maximum lint-rule coverage or the smallest possible file count.**