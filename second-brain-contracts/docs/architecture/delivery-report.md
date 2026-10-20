# Phase 2.1 delivery report

## Documents created

Four requested specifications: [core contracts](contracts-spec.md), [integration protocols](integration-protocols-spec.md), [toolchain](contract-toolchain-spec.md), and [implementation plan](phase-2-plan.md). Seven [ADRs](decisions/README.md), [repository assessment](repository-assessment.md), [research/evidence log](research.md), [open-question register](open-questions.md), this report, and a [validation record](validation.md) support review. Two [illustrative schemas](examples/README.md), an illustrative OpenAPI binding, fabricated valid/invalid fixtures and an offline checker make the contract proposal concrete.

## Recommended decisions

Keep JSON Schema 2020-12 as structural authority; generate Python/TS models, validate runtime payloads independently, and commit generated source with drift checks. Keep application operations independent of protocols. Start with local Python/CLI and add only needed adapters. Bound OpenAPI to optional HTTP. Keep Markdown/YAML canonical, graph/indexes derived, and execution/desired/session state separately owned. Use one local writer and prove recovery before trusting mutations. Stable membership is approval of an exact node revision; edits require renewed eligibility.

Task-mandated directions are separated from new defaults in the ADRs. UUIDs, membership gates, SQLite usage, retention windows, version support and package names are recommendations, not silently finalized requirements.

## Tools and standards

Propose datamodel-code-generator 0.86.0/Pydantic v2, json-schema-to-typescript 16.0.0, jsonschema 4.26+/Ajv8 with formats. Lock the full dependency graph during M2. OpenAPI 3.1.2/Redocly/oasdiff are optional HTTP tools. MCP requires a pinned, tested dated profile/SDK; inspected latest resolved to 2026-07-28. Defer AsyncAPI, Protobuf/gRPC, WebSocket and remote workers; reject Smithy as another canonical authoring layer for this phase. See [source-linked research](research.md) and [toolchain limits](contract-toolchain-spec.md).

## Human review and risks

Review namespace/license, managed-note adoption, relation semantics, Stable/Stack rules, identity/approval handling, same-user trust assumptions, storage recovery, provenance retention and exact tool compatibility. They have owners and milestone gates in the register.

Main overengineering risks are premature generic workflow engines, service extraction, exposing every operation over every protocol, a universal schema translator, copying private inventories into reusable contracts, or strictifying every existing note. The implementation plan explicitly defers these.

The existing repository agrees with curated Markdown and typed relations. Compatibility gaps are real: legacy notes lack managed IDs/revisions, wikilinks can be ambiguous, and the current relation script bypasses application checks. Adoption needs explicit mapping and reconciliation; no current file was migrated or refactored. The preliminary transcript migration proposal is not treated as architecture authority.

## First implementation milestone

Review Q01–Q03, then implement the smallest M1/M2 slice: approved Node/Cluster/primitives, generated Python/TS types, independent validators, shared fabricated fixtures and reproducible generation. Do not start API/runtime work before that proof. Exact locks and all-OS generation are future work, not completed by this delivery.

## Portability and preservation

Everything delivered is under the `second-brain-contracts` subfolder. No nested Git repository, commit, remote or actual submodule was configured. Move this folder's contents to a dedicated repository later; consumers pin its revision. The package has no runtime parent-vault paths, private export records or production dependency installation. Existing Phase 1 inventory and source exports remain in place and untouched. Validation scope and limitations are recorded separately.
