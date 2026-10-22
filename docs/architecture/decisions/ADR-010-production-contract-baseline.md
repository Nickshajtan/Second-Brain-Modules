# ADR-010: Production contract-first baseline

Status: implemented unreleased structural baseline under the Owner's Phase 2 task. Date: 2026-10-22.

## Decision

Keep JSON Schema Draft 2020-12 authoritative. Add eight [production resources](../../../contracts/registry/v1.json), generated Python modules/TS declarations, exact registry/source hashes and independent Python jsonschema/Ajv validation. Existing illustrative 0.1.0 resources/fixtures remain unchanged and independently checked. Domain operations use explicit discriminators and reusable typed payloads; no handwritten DTO copy, custom schema language, runtime handlers or universal execution engine.

Retain the existing pinned generators and temporary-tree check mode, extended to production. The baseline version 1.0.0 is unreleased; logical schema IDs do not imply a hosted endpoint, package publication, existing supported predecessor or frozen Owner policy. This implements ADR-001/002/003 and ADR-009 domain corrections, rather than silently rewriting ADR-006's old embedded-relation text.

## Consequences

Production consumers can import generated models and canonically validate decoded JSON offline. Strict input/output validation remains necessary: static TS types and Pydantic parsing approximate some constraints. Timestamp strings preserve spelling; independent external validators enforce calendar/format/newline rules and closed-object contracts. Shared fixtures, round-trips, strict TS checks, synthetic compatibility cases and full file-set regeneration are CI gates. Separate review found and fixed year-zero/trailing-newline validator disagreements; these remain regression fixtures.

O1–O4 remain explicitly unresolved in [contract documentation](../../contracts/README.md). Future Core must implement authorization, state transitions, cross-record consistency and atomicity; structural validation does not implement them. No transport server, filesystem transaction, index, policy evaluator or actual knowledge migration is delivered.

## Evolution

Released identifiers are immutable. Structural and semantic changes receive directional compatibility review and explicit versioning; no migration on read or unknown-schema network fetch. See [compatibility](../../contracts/compatibility.md) and [evolution](../../contracts/evolution.md). Hosted multi-OS execution and eventual package distribution are future release gates, not asserted by local checks.
