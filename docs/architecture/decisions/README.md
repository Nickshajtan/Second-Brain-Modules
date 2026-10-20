# Architecture decisions

Recorded 2026-10-20. “Task-mandated” records an explicit requirement from the supplied spec; “proposed detail” remains a recommendation awaiting review. None of these records asserts an implemented runtime.

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-data-contracts.md) | JSON Schema as canonical data contracts | Task-mandated; authoring/evolution profile proposed |
| [002](ADR-002-language-strategy.md) | Python core, TypeScript integration support | Task-mandated; packaging/baselines proposed |
| [003](ADR-003-type-generation.md) | Generate cross-language models, validate independently | Generation task-mandated; tools/commit policy proposed, M2 gate |
| [004](ADR-004-transport-independence.md) | Application behavior independent of adapters | Task-mandated; initial adapter order proposed |
| [005](ADR-005-openapi-binding.md) | OpenAPI describes optional HTTP binding | Task-mandated; 3.1.2 candidate proposed |
| [006](ADR-006-state-ownership.md) | Canonical knowledge separate from runtime/index state | Task-mandated; local recovery/storage choices proposed, M3 gate |
| [007](ADR-007-deployment-model.md) | Modular monolith first | Task-mandated; extraction triggers proposed |
| [008](ADR-008-monorepo-consumption.md) | Whole-repository reuse with isolated host state | Accepted direction from hardening task |

Changes supersede an ADR with a new record instead of silently editing a released decision. Review outstanding details in the [question register](../open-questions.md).
