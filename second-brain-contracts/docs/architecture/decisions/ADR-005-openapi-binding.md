# ADR-005: OpenAPI as an optional HTTP binding

Status: bounded role task-mandated; OpenAPI 3.1.2 candidate proposed. Date: 2026-10-20.

## Context

HTTP tooling is useful, but cannot define every local, stdio or agent operation. Duplicating domain schemas in an HTTP description creates another source of truth.

## Decision

Use OpenAPI 3.1 for selected HTTP operations only, initially proposing 3.1.2. Reference canonical JSON Schemas; binding metadata owns paths/methods/status/auth/headers. Generated HTTP docs/clients are derived artifacts. Use Redocly for lint/bundle/docs when HTTP is selected and oasdiff for HTTP compatibility. Do not generate canonical contracts back from HTTP server types.

## Alternatives

OpenAPI as universal internal interface overfits HTTP. OpenAPI 3.0 requires different nullability/schema assumptions. Adopting a newer specification solely because available may outrun consumer generators. Handwritten HTTP payload copies defeat single authority.

## Consequences

External `$ref` and 2020-12 keyword behavior require a real generator/bundler spike. Lint success does not certify a generated client. The delivered GET example is illustrative and not a running API. Exact binding error/status rules are part of adapter conformance.

## Reversibility

The HTTP binding can be versioned, removed or upgraded independently while application methods remain. A newer OpenAPI version requires tooling proof, not domain schema redesign.
