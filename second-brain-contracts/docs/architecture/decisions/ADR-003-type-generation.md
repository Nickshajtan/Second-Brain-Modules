# ADR-003: Automated models and independent validation

Status: generation task-mandated; candidate tools and committing generated code proposed. Date: 2026-10-20.

## Context

Hand-maintained Python/TS models drift. Static types cannot encode all JSON Schema constraints, and generator support does not imply validation equivalence.

## Decision

Propose datamodel-code-generator 0.86.0 for Pydantic v2 and json-schema-to-typescript 16.0.0 for TS declarations. Validate canonical payloads with jsonschema/Ajv2020, independent of generated model parsing. Lock full development dependency graphs and formatter/runtime versions at M2. Commit generated source with source hashes; regenerate in maintainer CI and fail on changed or untracked outputs. Consumers do not run generators at install time. No custom templates, schema compiler or semantic translator.

## Alternatives

Build-time-only generation hides output changes and requires consumer generator dependencies. Handwritten models undermine the selected authority. Treating Pydantic or TS as the only validator silently loses constraints. A custom generator costs more than narrowing the initial supported authoring profile.

## Consequences

Generated code is reviewable but adds repository volume. Upgrades can change output, so tool upgrades are isolated from schema edits. Shared valid/invalid cases and round-trip checks are release gates. Exact locks and cross-platform generator verification are not delivered by this architectural iteration; Q13/M2 records that gate.

## Reversibility

Tools are replaceable if canonical fixtures, public package exports and schema IDs stay compatible. Do not patch generated code to work around a tool; change configuration/tool and regenerate through a reviewed decision.
