# Second Brain — Phase 2: Production Domain Contracts

**Repository:** `Nickshajtan/Second-Brain-Modules`  
**Phase:** First production contract implementation  
**Status:** Ready for implementation  
**Scope:** Canonical domain schemas, Python/TypeScript generation, contract validation and evolution.

## 1. Objective

Convert the accepted Second Brain domain design into production-ready, versioned, language-neutral contracts.

Use the existing repository architecture and contract toolchain.

The deliverable is a **contract-first foundation**, not an implementation of the Second Brain runtime.

Required outcome:

1. Canonical JSON Schema Draft 2020-12 contracts.
2. Generated Python/Pydantic v2 domain models.
3. Generated TypeScript domain types.
4. Shared runtime validation against canonical schemas.
5. Structural and behavioral contract documentation.
6. Explicit compatibility and evolution rules.
7. Deterministic code generation.
8. CI gates preventing contract drift.
9. Portable fixtures proving Python/TypeScript compatibility.

The next implementation phase must be able to consume these artifacts rather than redefine domain structures.

## 2. Existing authoritative inputs

Inspect the current repository before writing code.

Read, at minimum:

- `docs/domain/glossary.md`
- `docs/domain/domain-model.md`
- `docs/domain/operations-catalog.md`
- `docs/domain/open-decisions.md`
- `docs/architecture/contracts-spec.md`
- `docs/architecture/contract-toolchain-spec.md`
- `docs/architecture/decision-provenance.md`
- `docs/architecture/reconciliation-register.md`
- `docs/research/phase-1-1/architecture-decision.md`
- `docs/research/phase-1-1/obsidian-fit.md`
- `docs/research/phase-1-1/open-decisions.md`
- Relevant ADRs and existing schema examples/tests.

Apply the latest confirmed decisions and explicit supersession notices.

Do not treat illustrative example schemas as production contracts.

Do not silently resolve contradictions between old architecture proposals and newer accepted domain decisions.

## 3. Architectural principles

### 3.1 Canonical contract authority

JSON Schema Draft 2020-12 is authoritative for:

- Structural types.
- Required and optional fields.
- Allowed values.
- Validation constraints.
- Schema references.
- Tagged unions.
- Structural compatibility.

Markdown specifications are authoritative for:

- Business semantics.
- Authorization obligations.
- State transitions.
- Cross-aggregate invariants.
- Transaction behavior.
- Operation preconditions and postconditions.

Generated Python and TypeScript representations are derivative artifacts.

Never reverse-generate canonical schemas from Pydantic, TypeScript or OpenAPI.

### 3.2 Preserve transport independence

Domain contracts must not depend on:

- MCP SDK types.
- HTTP request/response frameworks.
- Obsidian APIs.
- Git implementation objects.
- AI provider SDKs.
- Agent harness abstractions.

MCP is the exclusive external agent ingress in the intended deployment, but domain contracts must remain independent from transport.

Do not implement an MCP server in this phase.

### 3.3 Preserve the passive Core boundary

Do not add AI-specific behavior to domain entities.

Context compilation, model inference, summarization, scheduling, fetching and automated decision-making remain external.

Represent their results as structured domain data only where required.

### 3.4 Do not create a framework

Avoid:

- Custom schema DSLs.
- A universal entity runtime.
- Dynamic plugin loaders.
- Generic workflow engines.
- Custom authorization expression languages.
- Universal transport translators.
- Manually synchronized language-specific DTOs.

Use the existing toolchain and explicit schemas.

## 4. Production contract families

Implement a coherent, production-oriented structural contract baseline covering the confirmed domain model.

Keep schemas small and composable.

### 4.1 Shared primitives

Define reusable types for:

- Brain Instance identity.
- Entity ID.
- Schema version.
- Entity revision.
- Immutable revision reference.
- UTC timestamps.
- Principal reference.
- Resource reference.
- Cluster-scoped resource reference.
- Provenance reference.
- Source reference.
- Content digest/checksum.
- Operation identifier.
- Correlation ID.
- Idempotency key.
- Structured domain error.
- Capability identifier and resource scope.

Use stable, unambiguous naming.

Avoid embedding filenames, paths or human-readable titles into identity semantics.

### 4.2 Knowledge contracts

Cover:

**Node**

- Identity and type.
- Content metadata.
- Revision reference.
- Markdown content representation.
- Lifecycle state.
- Validity interval.
- Provenance.
- Optional schema-defined typed metadata.

Use Markdown-first semantics with flat Obsidian-compatible authoring properties.

Do not duplicate canonical content in frontmatter.

**Node Revision**

- Immutable logical revision.
- Content digest.
- Schema version.
- Recorded actor/time.
- Provenance.
- Previous revision reference where applicable.

A Git commit hash is not a substitute for the logical revision ID.

**Node Type Definition**

- Registered type identity/version.
- Associated canonical metadata schema.
- Validation metadata.

Do not invent a universal ontology.

**Cluster**

- Stable identity.
- Ownership.
- Policy reference/version.
- Lifecycle and configuration metadata.

Do not hardcode a universal hierarchy of Shared/Private permissions.

**Membership**

- Cluster and Node identity.
- Admission provenance.
- Membership lifecycle.
- Applicable approved revision selection where relevant.

Membership is distinct from Node content and Collection organization.

**Collection**

- Identity.
- Exactly one owning Cluster.
- Optional parent Collection.
- Organizational references to Nodes.
- Independent structural revision.

No duplicate Node files or implicit membership changes.

**Relation**

- Independent stable identity.
- Exactly one owner Cluster.
- Source and target Node references.
- Registered predicate/type.
- Independent revision.
- Provenance and optional validity metadata.

Relation changes must not revise endpoint Nodes.

Relations must not be embedded in Node as canonical mutable state.

**Relation Type Definition**

- Registered predicate.
- Directionality/symmetry.
- Supported endpoint constraints.
- Versioned validation rules.

No full ontology engine.

### 4.3 Supporting knowledge resources

**Asset**

- Stable identity.
- Media type.
- Content checksum.
- Size and budget-relevant metadata.
- Storage-provider reference.
- Provenance.
- Access-related resource scope.

Git is the initial storage provider, but domain contracts must not be coupled to Git.

**External Reference**

- Passive locator.
- Resource identity.
- Source metadata.
- Provenance.
- Optional checksum.
- Last externally reported verification data.

No fetching or caching implementation.

**Review**

- Independent immutable record identity.
- Review type.
- Reviewed subject and exact revision.
- Reviewer identity.
- Outcome.
- Evidence/provenance references.
- Timestamp.

Types include freshness, publication, quality and disposal, with versioned extension where appropriate.

**Proposal**

- Exact proposed operation.
- Subject resource/revision.
- Target scope.
- Versioned operation payload or payload digest.
- Relevant CAS expectations.
- Proposer.
- Status/reference metadata.

**Approval**

- Exact Proposal reference.
- Approver.
- Decision.
- Approved operation digest.
- Timestamp and relevant validity conditions.

Revocation is separately recorded; do not rewrite historical Approval records.

A positive Review is not Approval.

**Disposal**

- Deletion/disposal request.
- Original ownership and location snapshot.
- Routing decision.
- Trash disposition or Global Archive preservation reference.
- Retention and preservation state.
- Restore-relevant metadata.

Do not encode `node.delete` as unconditional physical deletion.

**Access Request**

- Requesting principal.
- Requested purpose/scope.
- Status and decision metadata.
- No implicit grant.

### 4.4 Control and authorization data

Define structural records for:

- Principal registration.
- Capability grant.
- Capability scope/conditions.
- Cluster policy definition/reference.
- Policy version.
- Explicit resource restrictions.
- Approval revocation.
- Access decision/request references.

Support granular capability combinations rather than a role hierarchy.

Instance Owner is a privileged verified identity, not a caller-editable boolean granting authority.

Do not implement the policy evaluator in this phase.

### 4.5 Operations and committed effects

Define typed envelopes and reusable payload contracts for domain operations.

At minimum cover:

- Node create/read/update/archive/delete/restore/copy/fork.
- Node revision proposals and publication.
- Cluster configuration.
- Membership attach/detach.
- Collection management.
- Relation create/update/delete/read.
- Asset registration/reference.
- Knowledge query/search.
- Proposal/Review/Approval/revocation.
- Disposal routing/preservation.
- Access requests.
- Import/export snapshot metadata.
- Transaction batch submission.
- Idempotent operation result/receipt.
- Committed domain event.

Use explicit operation discriminators and versioned payloads.

Do not implement handlers.

Operation request schemas describe structure. Authorization, state transitions, multi-resource admission, CAS and atomicity remain semantic obligations outside JSON Schema validation.

Avoid generating a separate schema for every trivial operation if a smaller reusable contract family expresses the same wire semantics without losing type safety.

## 5. Schema design constraints

Follow the existing repository generation profile.

- Draft 2020-12.
- Stable `$id`.
- Explicit `$schema`.
- Reusable `$defs` and local references.
- Closed structural objects where appropriate.
- Required discriminators for tagged unions.
- Explicit omission-versus-null semantics.
- No unknown core fields.
- Versioned, bounded extension fields where required.
- Portable formats and regular expressions.
- Safe JavaScript integer bounds.
- Deterministic serialization rules.

Do not add custom schema keywords requiring proprietary runtime interpretation.

Business constraints that cannot be accurately expressed in the existing generation profile must be documented and tested as semantic contract rules, not hidden in arbitrary JSON.

Do not weaken canonical schemas to accommodate generator limitations.

## 6. Python and TypeScript generation

Reuse the currently pinned toolchain.

### Python

Generate Pydantic v2 models.

Requirements:

- Importable modules.
- Stable naming and export surface.
- Strict canonical ingress validation.
- Alias-preserving serialization.
- Round-trip preservation of meaningful optional fields.
- No silent coercion or removal of unknown fields.
- Canonical output revalidation.

Generated Pydantic validation alone is not the canonical JSON Schema validator.

### TypeScript

Generate TypeScript declarations/types using the existing generator.

Requirements:

- Strict compilation.
- Correct tagged unions.
- Exact optional-property handling.
- No unnecessary `any`.
- Stable import/export paths.
- No runtime assumptions hidden in type declarations.

Generated TypeScript types are not runtime validators.

Use the existing Ajv Draft 2020-12 validation path for runtime payload validation.

### Generated artifacts

Generated files must carry appropriate autogenerated markers.

Never hand-edit them.

Do not duplicate generated definitions in handwritten domain modules.

If a semantic wrapper is needed, it must import the generated type rather than copy its fields.

## 7. Contract-first consumption

This is a mandatory architectural outcome.

Production consumers must be able to depend on:

1. Canonical schemas for language-neutral validation.
2. Generated Python models.
3. Generated TypeScript types.
4. Stable contract IDs and versions.
5. Well-defined serialization and compatibility behavior.

Document the public import surfaces for both languages.

Distinguish source-development layout from future package publishing.

Do not introduce a package registry, release server or dynamic contract distribution mechanism without an actual consumer requirement.

The reusable monorepo remains a pinned dependency of independent Second Brain instances.

## 8. Contract evolution

Contract changes are expected and must be first-class.

Define a policy distinguishing:

- Additive backward-compatible changes.
- Potentially breaking structural changes.
- Semantic changes without schema shape changes.
- Enum expansion.
- Required-field additions.
- Field removal or renaming.
- Discriminator/operation changes.
- Schema reference and identifier changes.
- Revision and resource identity migrations.

Use explicit versioning.

Do not assume every SemVer bump is automatically safe for all existing clients.

### Compatibility guarantees

A consuming runtime must be able to identify:

- Which contract version it understands.
- Whether an incoming payload uses a supported version.
- Whether its generated models match canonical schema sources.
- Whether a persisted record needs an explicit migration.

Never silently migrate knowledge during read or validation.

No network fetch of unknown schema definitions.

Unknown versions fail predictably with typed errors.

### Compatibility testing

Create representative previous/current-version fixtures or a small synthetic compatibility baseline when no production release exists yet.

Do not claim backward compatibility with hypothetical released contracts.

Document future release gates separately from what can actually be validated now.

## 9. Deterministic generation

Extend the existing generation workflow rather than replacing it.

Requirements:

- Single reproducible generation command.
- Independent check-only mode.
- Fixed generator and dependency versions.
- Offline schema reference resolution.
- Stable ordering.
- Stable UTF-8/LF output.
- No machine-dependent absolute paths.
- No timestamps in generated output.
- No generated artifact edits during `--check`.
- No unexpected generated files.
- Explicit failure on stale output.

The expected developer workflow remains conceptually:

```bash
python -m tools.generate_contracts
python -m tools.generate_contracts --check
python -m pytest -q
npm run typecheck
npm run parity
```

Adapt commands only when necessary to preserve the existing tooling contracts.

## 10. Cross-runtime parity

Extend shared fixtures from illustrative schemas to production contracts.

Test at least:

- Valid and invalid Node.
- Valid and invalid Relation.
- Valid and invalid Membership.
- Missing versus null.
- Unknown field rejection.
- Registered versus unknown discriminator.
- Invalid enum values.
- Exact revision reference.
- Date/time format.
- Safe integer limits.
- Unicode Markdown content.
- Namespaced extensions.
- Proposal/Approval payload consistency at the structural level.
- Valid and invalid operation envelopes.
- Unsupported schema version.
- Preservation of serialized optional values.

Python JSON Schema and TypeScript Ajv must agree on structural validity.

Valid canonical payloads must survive generated Python model round-trips without semantic data loss.

Negative semantic cases belong in explicit conformance fixtures/documentation; they must not be falsely reported as schema-validation guarantees.

## 11. Behavioral contract documentation

For each operation family, document:

- Operation identifier and version.
- Required capability.
- Resource and policy scope.
- Request and response schema references.
- Precondition.
- Postcondition.
- CAS/idempotency obligation where applicable.
- Relevant invariant IDs.
- Success event.
- Stable error codes.
- Direct or governed mode.

The operations catalog remains the semantic specification until executable services exist.

Do not implement dummy operation handlers solely to satisfy documentation.

Do not create a generalized operation execution engine.

## 12. Unresolved decisions

The Phase 1.1 register contains Owner-level decisions O1–O4.

Do not silently freeze their proposed defaults.

### O1 — Obsidian synchronization

Schema contracts should distinguish committed state, unmanaged authoring input, candidate/conflict state and accepted revisions.

Do not promise immediate synchronization.

### O2 — Approval scope

Do not encode whole-graph approval as mandatory.

Node Revision approval must be supported.

Keep Relation approval/selection semantically independent, and preserve future support for bounded approved Relation sets without requiring a graph snapshot engine now.

### O3 — Retention and revocation

Provide sufficient structured data for explicit revocation, retention and disposal decisions.

Do not specify irreversible physical erasure or a final retention duration without Owner approval.

### O4 — Multi-cluster read-policy composition

Support selected Cluster view and explicit resource-level restrictions structurally.

Do not bake an unapproved global union/intersection rule into generated models.

The runtime policy algorithm remains a separately approved semantic contract.

If other unresolved questions block a schema, isolate that small family or represent only confirmed structure.

Do not resolve policy questions by inventing defaults.

## 13. Transaction contracts

Define only the data shapes needed for future atomic operations:

- Batch request.
- Typed operation entries.
- Expected revisions.
- Idempotency identity.
- Transaction ID.
- Committed-generation reference.
- Operation result.
- Durable receipt.
- Error response.
- Event/outbox record.

The intended architecture uses one managed Git commit/ref boundary with commit-critical state co-located.

This remains a backend recommendation rather than a reason to encode Git-specific internals in every domain contract.

Do not implement Git commits, locks, journal, transaction coordinator, or recovery logic now.

## 14. Recommended repository organization

Respect existing conventions.

A possible target is:

```text
contracts/
  schemas/
    v1/
      common/
      knowledge/
      governance/
      operations/
      events/
  registry/

packages/
  python/
    generated/
  typescript/
    generated/

tests/
  fixtures/
    contracts/
  contract_parity/

docs/
  contracts/
    README.md
    operations.md
    compatibility.md
    evolution.md
```

This is illustrative.

Inspect actual repository structure and adapt to it rather than creating redundant directories.

Keep previous illustrative schemas clearly separated from production contracts.

Avoid introducing a new package layout unless necessary.

## 15. Validation and CI

Extend existing contract checks to cover production schemas.

Required gates:

1. Canonical schema syntax and reference resolution.
2. No network schema dependencies.
3. Python generation succeeds.
4. TypeScript generation succeeds.
5. Generated-file drift detection.
6. Python canonical validation.
7. Ajv parity.
8. Valid payload round-trip.
9. TypeScript strict typecheck.
10. Documentation references and schema registry consistency.
11. No accidental changes to old illustrative fixtures.
12. No duplicate handwritten domain DTO definitions.

Do not introduce paid infrastructure or heavyweight application-test frameworks.

Retain Windows/macOS/Linux CI compatibility.

## 16. Implementation strategy

Implement contracts in dependency order:

**Stage A — Shared primitives and registry**

Stable identifiers, revisions, schema references, common errors, principals and resource references.

**Stage B — Knowledge aggregates**

Node, Relation, Cluster, Membership, Collection and type registries.

**Stage C — Governance/supporting records**

Assets, External References, Proposal, Review, Approval, capabilities, policy records and disposal metadata.

**Stage D — Operation envelopes and results**

Typed operations, batches, receipts, errors, events and snapshot metadata.

**Stage E — Generation, parity and evolution gates**

Finish cross-language output, tests, documentation and reproducibility.

These are internal implementation stages of one contract-focused task, not authorization to build runtime functionality.

If a proposed schema is blocked by unresolved semantics, document it and continue with independent families. Never invent the missing business rule merely to complete a checklist.

## 17. Explicit exclusions

Do not implement:

- Knowledge CRUD services.
- Storage repositories.
- Git commit protocol.
- SQLite indexing.
- Authorization evaluator.
- MCP server.
- Obsidian integration/plugin.
- Cleanup services.
- Scheduler.
- Agent memory or harness.
- Context compilation.
- Search engine.
- Semantic retrieval.
- Real migrations of existing knowledge.
- Packaging/publication infrastructure without a consumer.

Only contracts, generated artifacts, tests and supporting documentation.

## 18. Acceptance criteria

The phase is complete when:

1. Production canonical contracts are separated from examples.
2. Confirmed stable domain structures have generated Python and TypeScript representations.
3. Structural validators share the same authoritative schemas.
4. Generated artifacts are reproducible and checked into the repository following existing conventions.
5. CI detects schema/model drift.
6. Contract changes have an explicit versioning and compatibility policy.
7. Business invariants are traceable from documentation to affected contract families.
8. No runtime implementation was introduced.
9. Open Owner decisions remain visible and are not silently resolved.
10. A future Core implementation can import generated models without rewriting the same domain structures.

Do not create superficial placeholder schemas to claim coverage.

If a family cannot be safely finalized, report it as incomplete with its exact blocking decision.

## 19. Final report

Provide:

- Implemented contract families.
- Canonical schema inventory.
- Generated Python and TypeScript artifact paths.
- Public import/validation examples.
- Tests and CI results.
- Compatibility/evolution policy summary.
- Outstanding semantic decisions.
- Explicit list of deferred contract families, if any.
- Changes to existing architecture documents.
- Any generator limitations or approximations.
- Confirmation that no runtime services were implemented.

Use actual repository paths and results.

Do not describe unexecuted tests as passed.

**Success means we can confidently build Second Brain on top of these contracts without maintaining three independent models.**