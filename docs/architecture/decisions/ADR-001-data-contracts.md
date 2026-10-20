# ADR-001: Canonical JSON Schema data contracts

Status: task-mandated principle; proposed release/authoring details. Date: 2026-10-20.

## Context

Python, TypeScript and future adapters need consistent data definitions without independently authored domain models. Existing Markdown/YAML is authoritative knowledge content, but does not yet have an application contract layer.

## Decision

Use JSON Schema Draft 2020-12 as the sole structural contract source. Validate JSON-compatible frontmatter/body projections with independent runtime validators. Released resource IDs are immutable and versioned; local registries resolve them offline. Keep a narrow initial generation profile and document unsupported generator features. Business transitions, policy and cross-record integrity remain explicit application rules. Examples do not become production schemas without M1 review.

## Alternatives

Pydantic-first makes Python the schema authoring authority; Zod-first makes TypeScript authoritative. OpenAPI-first confuses HTTP binding with domain shape. Protobuf/Smithy introduce another selected IDL. Manually synchronizing models makes drift likely. These are rejected for the current task.

## Consequences

Schemas and shared fixtures are reviewed before code; formats and unknown-property rules are explicit. Generator fidelity must be tested. Closed objects make “optional field addition” potentially breaking for old readers. There is no guarantee that JSON Schema can express authorization or concurrency.

## Reversibility

Changing the canonical format is costly: preserve published schema IDs and compatibility, migrate authoring through a new ADR, and prove fixtures across old/new consumers. Namespace/license choice is still Q01; do not publish the example namespace.
