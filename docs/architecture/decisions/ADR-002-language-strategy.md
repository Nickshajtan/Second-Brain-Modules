# ADR-002: Python core with TypeScript integration support

Status: task-mandated language direction; proposed packaging details. Date: 2026-10-20.

## Context

Phase 1 tooling is Python. Obsidian/client integration benefits from TypeScript. The platform must remain independent of a provider, harness and plugin.

## Decision

Implement domain/application/storage processing in Python, with generated Pydantic models and Python 3.12+ as proposed core baseline. Provide generated TS declarations and Ajv runtime validators for integrations. TS plugins/clients call application operations and do not implement a competing policy or knowledge engine. Keep contracts installable without importing core/adapters. Use ordinary Python/npm packages in one portable repository; no mandatory monorepo framework.

## Alternatives

All-TypeScript would reduce language count but discard useful Python processing conventions. All-Python would leave TS consumers untyped or handwritten. Duplicating domain rules in both creates inconsistent authorization. Separate repositories immediately would increase release coordination before a real implementation exists.

## Consequences

Cross-language wire semantics and fixtures matter more than identical in-memory classes. Missing/null, timestamps, safe integers and unknown properties need explicit tests. Illustrative generated artifacts and locked development tooling now exist; production package publication remains future work. Current inventory scripts remain untouched and independently runnable. Logical modules need not be separate published packages; ADR-008 defines the whole repository as the submodule boundary.

## Reversibility

Core language can change behind stable contracts and conformance tests. Adapters may be added in any language. Public generated-package compatibility still requires normal releases; consumers must not depend on internal Python file paths.
