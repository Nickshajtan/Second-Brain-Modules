# ADR-009: Phase 1 domain baseline and historical scope correction

Status: records Owner-confirmed brief constraints; storage/UI/architecture-option choices remain proposed. Date: 2026-10-21.

## Context

The supplied `second-brain-phase-1-domain-and-reuse-assessment.md` supersedes several earlier design assumptions. Existing contracts/examples remain useful historical and toolchain evidence, not production authority. Exact conflicts are [registered](../reconciliation-register.md).

## Decision

Use [domain terminology and invariants](../../domain/domain-model.md) and [operation semantics](../../domain/operations-catalog.md) for the confirmed brief constraints. Relations are standalone owner-Cluster aggregates and independently Git-versioned; their changes do not revise Nodes. Context compilation and agent/process/workflow orchestration belong outside passive Core. Per-Cluster policy replaces any universal Stable permission ladder. Membership, organization, publication, history, approval, disposal and purge are distinct authorities. Native offline human authoring remains required; raw vault access is not an ACL sandbox.

This **partially supersedes ADR-006's embedded-Relation decision** and narrows Context/Execution scope in the historical contract/module/phase-plan documents. It does not supersede state separation, JSON Schema, independent generators/validators, transport independence, modular monolith or whole-repository instance reuse.

## Consequences and alternatives

Do not rewrite old ADRs, regenerate illustrative embedded-edge models as if they were production, or silently reinterpret old grants. New schemas and migration need separate review. Keeping embedded edges would contradict explicit independent edge identity/revision ownership; keeping Core context/workflow execution would contradict the confirmed passive boundary. Different Obsidian display options and reusable index implementations remain legitimate alternatives.

## Open and reversible choices

No durable backend, Relation-note representation, publication snapshot identity or reuse option is accepted by this ADR. D01–D10 and the four [PoCs](../../research/poc-plan.md) gate implementation. Markdown artifacts do not authorize runtime scaffolding.
