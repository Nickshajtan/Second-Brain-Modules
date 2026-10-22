# Second Brain — Core M1: Knowledge Storage Foundation

**Repository:** `Nickshajtan/Second-Brain-Modules`  
**Milestone:** M1 — First executable Core vertical slice  
**Status:** Implementation specification  
**Primary language:** Python 3.12+  
**Scope:** Domain validation, managed Git storage, atomic batches, immutable revisions, committed reads.

## 1. Objective

Implement the smallest useful executable Second Brain Core foundation on top of the existing production contracts.

The implementation must prove this workflow:

```text
Typed operation
    ↓
Canonical JSON Schema validation
    ↓
Generated Python model
    ↓
Domain invariant checks
    ↓
Git transaction preparation
    ↓
Atomic committed-generation publication
    ↓
Committed read / durable receipt
```

M1 must establish reliable state ownership and demonstrate that multiple related knowledge resources can be committed as one logical operation.

**Do not implement the entire Second Brain platform.**

Success means the next milestone can add governance, reconciliation and MCP without replacing the storage foundation.

## 2. Mandatory repository inspection

Before implementation:

1. Read the latest `main` branch.
2. Review current production schemas and generated Python models.
3. Read the existing contract generation and validation APIs.
4. Review ADR-010 and the Phase 1.1 architecture decision.
5. Review the confirmed domain invariants and operations catalog.
6. Inspect the current build/distribution hardening.
7. Check whether the principal-review fixes have already been committed.

Relevant sources:

- `contracts/schemas/v1/`
- `contracts/registry/v1.json`
- `packages/python/second_brain_contracts/`
- `packages/python/generated/v1/`
- `docs/domain/domain-model.md`
- `docs/domain/operations-catalog.md`
- `docs/research/phase-1-1/architecture-decision.md`
- `docs/contracts/README.md`
- `docs/architecture/decisions/ADR-010-production-contract-baseline.md`

Use the repository's actual interfaces and field names.

Do not invent a parallel domain model when a generated contract already exists.

If a required contract is missing or structurally wrong, document and correct the canonical schema first, then regenerate artifacts through the existing toolchain.

Avoid modifying schemas merely to accommodate implementation convenience.

## 3. Strict scope

### Implement

- Instance-scoped Core composition.
- Canonical contract ingestion.
- Minimal Node and standalone Relation domain operations.
- Cluster/Membership validation necessary for safe creation.
- Git-backed canonical persistence.
- Immutable logical revisions.
- Optimistic concurrency control.
- Atomic same-instance batches.
- Durable idempotency receipts.
- Committed-state reads.
- Focused failure and recovery tests.

### Explicitly exclude

- MCP server or client adapter.
- Obsidian plugin or editor automation.
- Full human-file reconciliation.
- SQLite search/graph index.
- General authorization policy engine.
- Publication/Approval workflow.
- Trash, Global Archive and purge.
- External services or background jobs.
- Agent orchestration.
- Context compilation.
- HTTP APIs.
- General workflow or event execution engine.
- Distributed transactions.
- Dynamic module loading.

Do not create placeholder implementations for excluded subsystems.

## 4. Architectural boundaries

Implement a small modular monolith.

Suggested boundaries:

```text
Application
  ├── Operation coordination
  ├── Minimal authorization
  └── Transaction boundary
           │
           ▼
Domain
  ├── Node invariants
  ├── Relation invariants
  └── Membership invariants
           │
           ▼
Ports
  ├── Knowledge repository
  └── Commit store
           ▲
           │
Git Adapter
```

These are logical responsibilities, not mandatory separate packages.

Do not introduce a dependency injection framework.

Use constructor injection or explicit function parameters.

The domain/application code must not import subprocess Git commands directly.

Git implementation details belong behind a narrow storage boundary.

## 5. Contract-first implementation

### 5.1 Canonical input pipeline

All externally supplied operation payloads must follow:

1. Decode strict JSON when raw JSON is supplied.
2. Validate against canonical JSON Schema.
3. Construct the corresponding generated Pydantic model.
4. Apply business/domain validation.
5. Execute the operation.
6. Serialize the generated result.
7. Validate outgoing payload against the canonical schema.

Where an internal typed entry point accepts an already validated generated model, document precisely where the canonical validation occurred.

No handwritten DTO copies.

Do not use direct Pydantic model validation as a substitute for canonical structural validation.

### 5.2 Generated types

All domain objects must use the actual generated types.

Thin helpers may wrap generated models but must not redefine:

- Node fields.
- Relation fields.
- Membership fields.
- Revision references.
- Transaction envelopes.
- Structured errors.

Do not modify generated artifacts manually.

Keep generated type usage independent of the chosen deployment location.

## 6. Instance context

Create an explicit runtime instance context containing the minimum information required for M1.

At minimum:

- Instance identity.
- Canonical Git repository location.
- Managed Git ref name.
- Contract version.
- Runtime configuration.
- Trusted principal context.
- Paths for permitted M1 local runtime state, if necessary.

Never infer instance identity from directory name, current working directory or Git remote.

Avoid global mutable state.

Two independent instances must be usable in the same Python process without overlapping storage state or locks.

Do not create credentials, grants or secret material inside the reusable module repository.

## 7. Git canonical authority

### 7.1 Core principle

**The accepted state of Second Brain is a committed Git tree selected by one managed ref.**

The human-editable working directory is not automatically authoritative.

Core reads must resolve the managed ref and read only validated committed content.

Do not read uncommitted working-directory bytes as accepted knowledge.

### 7.2 Initial canonical storage

Use stable-ID-based paths for the initial managed resources.

For example:

```text
knowledge/
  nodes/
    <node-id>.md
  relations/
    <relation-id>.md
  clusters/
    <cluster-id>.yaml
  memberships/
    <cluster-id>.yaml

control/
  receipts/
    <receipt-id>.json
```

The actual layout may differ if required by current contracts.

Keep canonical knowledge in Markdown/YAML.

Commit-critical control records may be JSON if supported by existing contract definitions.

Do not use filesystem paths as domain identities.

### 7.3 Git storage adapter

The adapter must support:

- Resolve current committed generation.
- Read a record from a specified generation.
- Construct an isolated candidate tree.
- Write Git objects without publishing them.
- Create a commit with the previous committed generation as parent.
- Publish through an expected-old-value ref update.
- Recover or inspect the outcome of an uncertain operation.

Do not stage arbitrary working-directory content.

Do not invoke Git commands against a shared mutable process working directory.

Avoid global `chdir`.

Use explicit repository paths and controlled subprocess arguments.

No shell interpolation.

A lower-level Git library may be used only if it genuinely simplifies the implementation without undermining Git's conditional ref publication semantics.

## 8. Minimal domain operations

Implement only the operations required for the first vertical slice.

### 8.1 Node creation

Provide a typed `node.create` operation.

Required behavior:

- Validate the registered Node type.
- Validate required Node metadata.
- Assign or verify a stable identifier.
- Establish an initial logical revision.
- Require an explicit valid target Cluster.
- Atomically create the required initial membership.
- Record the creating principal/provenance.
- Reject collisions.
- Reject ownerless or unscoped Nodes.

Direct creation into an authorized target Cluster is sufficient for M1.

Do not implement staging workflows yet.

### 8.2 Node read

Provide committed `node.read`.

Required behavior:

- Select one committed generation.
- Resolve Node identity through that generation.
- Validate the committed record.
- Return the requested permitted selection.
- Never substitute uncommitted files.
- Never expose unrelated Cluster details.

Historical revision enumeration is deferred.

### 8.3 Relation creation

Provide typed `relation.create`.

Required behavior:

- Independent Relation identity.
- Exactly one owner Cluster.
- Explicit source and target Node IDs.
- Registered predicate and predicate version.
- Independent initial revision.
- Endpoint existence validation.
- No modification of endpoint Node revisions.
- No implicit creation of inverse Relations.

Relation endpoints may reference Nodes outside the owning Cluster, subject to the relevant access checks.

### 8.4 Relation read

Read the Relation from one committed generation.

Require that its own record and both referenced endpoints are accessible to the current principal.

No raw access to unrelated records.

### 8.5 Cluster and Membership

M1 must support enough Cluster/Membership state to guarantee valid initial Node admission.

Support explicit trusted fixture/bootstrap creation of a Cluster if full administrative operations are not yet implemented.

Membership must remain separate from Collection organization.

Do not interpret Node references or Relation links as membership grants.

## 9. Minimal authorization

M1 does not implement the full capability system.

However, it must not establish an unsafe public operation surface.

Provide explicit trusted principal binding and a minimal, deny-by-default authorization boundary sufficient for supported operations.

Required constraints:

- No caller-provided Owner impersonation.
- No mutation without an authorized principal.
- No implicit access to every Cluster.
- No unauthorized Relation endpoint reads.
- No unauthorized resource existence disclosure.
- No accidental bypass through direct application methods.

A fixture-only or bootstrap-managed grant representation is acceptable if its scope is clearly documented.

**Do not hardcode a universal allow-all policy.**

Do not introduce PyCasbin or a custom policy DSL.

If full O4 multi-cluster policy semantics are needed for an operation, limit the supported M1 case rather than silently adopting an unapproved policy-composition rule.

## 10. Atomic batch

Implement one-instance atomic domain batches using the existing generated transaction contracts.

Mandatory acceptance scenario:

```text
Batch:
  1. Create Node A
  2. Create Node B
  3. Create Relation R: A → B

Expected:
  Either all three resources and required
  memberships become committed,
  or none do.
```

The batch must support referencing newly created entities within the same batch.

Use an explicit temporary-ID/reference mapping or another documented mechanism compatible with the canonical operation contracts.

Avoid a general workflow DSL.

### Commit protocol

1. Resolve committed generation `C0`.
2. Acquire the instance writer lock.
3. Validate the complete batch against `C0`.
4. Check current capabilities, memberships, type registrations and all preconditions.
5. Construct isolated after-state bytes.
6. Create Git objects and candidate commit `C1`.
7. Include commit-critical receipt/control state in the candidate tree.
8. Publish `C1` with one conditional expected-old-ref update.
9. Return the committed result/receipt.

Creating prepared Git objects is not the same as committing a domain effect.

Core readers must see either `C0` or `C1`, never a mixed state.

Do not create independent commits for nested operations.

### Batch failures

An invalid operation must invalidate the entire batch.

A stale expected revision must reject the entire batch.

A permission denial must reject the entire batch.

There must be no independently visible partial success.

## 11. Revisions and CAS

Committed Node and Relation revisions are immutable.

Use logical revisions as defined by the generated contracts.

Do not substitute Git hashes for entity revision identifiers.

When mutation or bootstrap conditions require an expected revision, validate it against the selected committed state.

Return a typed conflict when it no longer matches.

Do not silently resolve conflicts by overwriting newer data.

In M1, only implement the revision operations actually exercised by supported create/update paths.

Do not build full historical revision browsing or approval promotion.

## 12. Idempotency and durable receipts

Mutation requests require an idempotency key and a normalized payload digest.

Store successful commit receipts durably within the chosen canonical commit boundary.

Requirements:

- Same key and same payload must not create duplicate resources.
- Same key and different payload returns an idempotency conflict.
- Restart must be able to identify whether a previously submitted operation committed.
- A timeout after ref publication must not trigger a second commit.
- Receipt access requires current authorization.
- No successful receipt may be returned for a transaction that did not commit.

Idempotency scope must include instance identity, authenticated principal and operation identity/version.

Do not silently invent a retention duration.

The initial implementation may retain receipts indefinitely within its explicitly documented test/development scope pending O3.

## 13. Failure and recovery semantics

Support process-level recovery by treating the managed Git ref as the authoritative commit decision.

At restart:

- Resolve the committed ref.
- Verify required objects and records.
- Recover the observable outcome of committed operations through durable receipts.
- Ignore prepared but unpublished Git objects as accepted state.
- Reject serving unsafe or corrupt canonical state.

Do not use Git reset as automatic conflict resolution.

Do not claim crash-safe fsync or power-loss guarantees unless actually demonstrated on the relevant filesystems.

The initial goal is logical atomicity and consistent restart behavior, not certification of storage hardware durability.

## 14. Canonical serialization and Obsidian compatibility

Use the constrained YAML/Markdown rules already defined in the contracts.

Requirements:

- Preserve Markdown body bytes/content according to the accepted codec rules.
- Reject duplicate YAML keys and unsupported tags.
- Do not permit arbitrary executable YAML objects.
- Reject invalid metadata types.
- Keep author-editable properties flat.
- Keep Relation ownership and endpoints authoritative in one record.
- Use stable IDs instead of human-readable filenames as identities.

Do not implement a live file watcher.

Do not modify a human's existing Obsidian vault.

All tests must use fabricated disposable repositories.

## 15. Testing strategy

Use focused tests that establish M1 guarantees.

### A. Contract ingestion

- Valid Node and Relation accepted.
- Invalid payload rejected by canonical validation.
- Generated Python round-trip preserved.
- Unknown fields/versions rejected.
- No direct Pydantic-only ingress bypass.

### B. Domain invariants

- Node cannot exist without valid Cluster admission.
- Relation cannot point to missing endpoints.
- Relation has exactly one owner Cluster.
- Relation mutation does not alter Node revision.
- Unauthorized resources are concealed.
- Cross-instance references are not silently accepted.

### C. Atomicity

- Two Nodes plus Relation commit successfully.
- Invalid final operation causes zero committed effects.
- Stale generation causes CAS conflict.
- Retry of same transaction returns original result.
- Retry with changed payload returns conflict.

### D. Recovery

- Prepared Git objects without ref update are invisible.
- Failure before ref publication leaves previous generation.
- Failure after ref publication can be recognized as committed.
- Missing committed object fails closed.

### E. Instance isolation

- Two instances have separate refs and state.
- Operations cannot accidentally cross instances.
- No process-global mutable current instance.
- Direct application calls enforce authorization.

### F. Serialization

- Ukrainian and Unicode content.
- YAML duplicate keys.
- Missing versus null.
- Stable IDs through path/title changes.
- Independent Relation serialization.

Prefer tests at real application boundaries over mocking Git behavior.

Do not implement a large artificial crash-test framework.

## 16. CI and quality

Retain the existing contract generation/parity tests.

Add M1 tests without modifying generated files manually.

Run:

```bash
python -m tools.generate_contracts --check
python -m tools.validate_contracts
python -m pytest -q
npm run typecheck
npm run parity
```

Also run applicable lint and formatting checks.

Preserve Windows/macOS/Linux compatibility.

If hosted CI cannot be executed, report that limitation.

Do not claim power-loss durability or production-level filesystem isolation from passing unit tests.

## 17. Deliverables

Expected output:

1. Minimal executable Python Core package/module.
2. Domain validation for Node, Relation and required Membership/Cluster state.
3. Git-backed committed-state adapter.
4. Atomic batch application service.
5. Durable receipt and idempotency handling.
6. Committed-state read API.
7. Focused conformance and recovery tests.
8. Short architecture/usage documentation.
9. Clear limitations and next-slice recommendations.

Do not implement additional feature families merely because their contracts already exist.

## 18. Acceptance criteria

M1 is complete when:

- The implemented Core imports generated contract models.
- Canonical structural validation occurs at ingress and output.
- No parallel handwritten domain DTO model exists.
- Supported operations enforce their documented invariants.
- Accepted state is identified by one managed Git ref.
- Reads never mix committed and uncommitted state.
- Two Nodes and one Relation commit atomically with memberships.
- Retry and CAS behavior are deterministic.
- Failed operations do not partially commit.
- Restart can distinguish committed and uncommitted outcomes.
- Tests use isolated, disposable Git repositories.
- Existing contract toolchain remains stable.
- No MCP, Obsidian plugin, SQLite indexing or full governance engine has been introduced.

## 19. Final implementation report

Provide:

- Implemented modules and their responsibilities.
- Exact generated types and validators used.
- Supported domain operations.
- Git commit/ref publication approach.
- Atomic batch and idempotency guarantees.
- Relevant tests and actual results.
- Known limitations.
- Any contract changes and regenerated artifacts.
- Unresolved questions requiring Owner approval.
- Recommended next vertical slice.

**Do not present implementation recommendations as completed functionality.**

The goal is to establish a small, verifiably consistent foundation upon which the rest of Second Brain can evolve.