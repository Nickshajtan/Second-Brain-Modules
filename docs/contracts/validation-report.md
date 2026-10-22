# Phase 2 delivery and independent validation

Executed locally on Windows, 2026-10-22; CPython 3.12.6, Node 24.19.0, existing pinned generator/validator dependencies. No dependency installation or lock upgrade. This report describes executed automated checks, not manual application tests, external human certification or hosted CI results.

## Delivered

Eight [canonical Draft 2020-12 resources](../../contracts/registry/v1.json) under `contracts/schemas/v1`, with 34 explicit operation variants and knowledge/governance/control/authoring/snapshot/transaction structures. [Inventory and consumption examples](README.md), [operation obligations](operations.md), [compatibility](compatibility.md) and [evolution](evolution.md) define their public use. Version 1.0.0 remains an **unreleased** structural baseline.

Generated output: ten files under [Python v1](../../packages/python/generated/v1) (eight modules, package marker and source/artifact manifest); nine under [TypeScript v1](../../packages/typescript/generated/v1) (eight declarations plus namespace index). Together with five existing illustrative artifacts, check mode verifies **24 files**. Runtime validation adapters are [Python](../../packages/python/second_brain_contracts/validation.py) and [TypeScript](../../packages/typescript/validation.mjs); neither implements domain services or an alternate handwritten DTO model.

## Executed automated gates

| Gate | Result |
|---|---|
| `python -m pytest -q` | **204 passed**, including original tests and production conformance checks |
| `python -m tools.validate_contracts` | **8 schemas, 717 offline references, 133 structural fixtures**; valid generated-model round-trips pass |
| `npm run parity` | Original 24 cases retained; additionally checks all 133 production verdicts and 10 synthetic directional compatibility cases with Ajv |
| `npm run typecheck` | Strict TS compilation, operation discriminator narrowing, optional-field/endpoint negative static cases pass |
| `python -m tools.generate_contracts --check` | All **24 generated files** match, no extra files; temporary-tree comparison |
| Two independent clean generations | Identical bytes/file sets and equal to checked-in outputs; existing output remains unchanged |
| `python -m tools.validate_examples` | Original schemas/fixtures/OpenAPI and all portable documentation links pass |
| Ruff check / format check | Pass |
| Illustrative preservation | Original schema/fixture hashes match preserved baseline; original generated Node/Cluster Python/TS files unchanged |
| Diff whitespace check | Implementation changes pass; pre-existing user edits in `task.md` contain two Markdown trailing-space lines and were left untouched |

No operation handler is used to manufacture a semantic test result. The [nine semantic cases](../../tests/fixtures/contracts/semantic.json) deliberately validate structurally and describe rejection obligations for future Core implementations. These are not evidence that authorization, atomicity, retention or approval equality is implemented.

## Independent reviewer and findings

A separate reviewer authored the shared corpus and independently invoked maintained Python `jsonschema` Draft202012Validator/FormatChecker and TypeScript Ajv2020, rather than copying generated-model verdicts. Final structural corpus: **79 valid, 54 invalid**. All valid values round-trip unchanged, including actual Ukrainian text, emoji, decomposed Unicode, CRLF Markdown, empty/false/zero values, optional omission/explicit nullable values and fractional timestamps. Negatives check intended keywords and instance paths, not just an arbitrary exception.

The reviewer also ran additional unknown-field/nonfinite/remote-reference/unsupported-version probes and a separate targeted test run (**143 passed, one generation test excluded**), plus strict TypeScript checks. Parent full-suite/deterministic-generation results are recorded separately above. Findings resolved before completion:

- Year `0000` was accepted by Ajv but rejected by Python's format checker: canonical portable year profile now excludes it.
- A terminal newline was accepted by Python's timestamp validation but rejected by Ajv: standard `not` CR/LF guards and regression cases now align the validators. Newline-bearing capability/operation/extension names also reject.
- Historical Node types and Relation predicates needed explicit version binding: persisted content/edges now carry registered definition versions.
- Four production operation modes initially drifted from the domain catalogue: direct Proposal/Review/access-request/revision-proposal modes were restored.
- Fixture Unicode authoring through shell stdin initially lost characters: fixture construction was corrected with escaped code points and verified; no unsupported Unicode-coverage claim remains.

The review finished with **no remaining blocking findings**. Independence here means separate review and separate maintained validation implementations within this work, not certification by an outside organization.

## Limits and deferred decisions

Generated Pydantic can approximate null/coercion/negative constraints; TS declarations cannot enforce numeric/date/pattern rules. Canonical ingress/output validation is mandatory, with no custom fallback date checker. Future semantic services must enforce registry membership, cross-record identity/CAS/approval equality, endpoint authorization, current policy and transaction/disposal behavior.

O1–O4 remain visible and unchosen: synchronization timing, approval breadth, retention/revocation effects and multi-Cluster read composition. Optional Relation selection does not mandate graph-snapshot approval. Dedicated purge/expiry/grant-management operation schemas and other catalogue extensions are deferred as described in [evolution](evolution.md), not claimed delivered handlers. There is no known blocked structural family among the task's minimum families.

CI configuration retains Windows/macOS/Linux and adds the production registry/round-trip gate; hosted jobs and cross-OS artifact equality were **not executed here**. No package distribution/hosting, MCP server, policy evaluator, storage/index implementation, real migration, paid inference or manual testing was introduced.
