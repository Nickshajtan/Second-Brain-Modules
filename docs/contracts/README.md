# Production domain contracts — 1.0.0 baseline

Status: **implemented, unreleased contract baseline**, not a running Core or a published package. Canonical JSON Schema Draft 2020-12 is under `contracts/schemas/v1`; illustrative 0.1.0 resources remain unchanged under `docs/architecture/examples`. The version labels describe distinct contracts, not an automatic migration from examples. Confirmed semantics remain in the [domain model](../domain/domain-model.md) and [catalogue](../domain/operations-catalog.md), with [Phase 1.1](../research/phase-1-1/architecture-decision.md) supersession applied.

## Canonical inventory and public surfaces

The [registry](../../contracts/registry/v1.json) maps exact logical resource IDs, paths and generated Python root types. IDs use the Owner's GitHub repository namespace plus exact `1.0.0`; they are **identifiers**, not a promise that schemas are hosted at those URLs. Validation never fetches them. Publication/tag/distribution remains separate work.

| Resource | Root / meaningful contained definitions | Generated Python module |
|---|---|---|
| [common](../../contracts/schemas/v1/common.schema.json) | DomainError; instance/entity/correlation IDs, version, revision, RevisionRef, NodeRef/ResourceRef/ClusterResourceRef, scope, principal/source/provenance refs, digest, UTC time, CAS, generation, flat Properties and bounded extensions | `generated.v1.common_schema` |
| [knowledge](../../contracts/schemas/v1/knowledge.schema.json) | KnowledgeRecord: Node, NodeRevision, NodeTypeDefinition, Cluster, Membership, Collection, Relation, RelationTypeDefinition, Asset, ExternalReference, ProvenanceRecord | `generated.v1.knowledge_schema` |
| [governance](../../contracts/schemas/v1/governance.schema.json) | GovernanceRecord: exact Proposal, typed Review, Approval, separate ApprovalRevocation, Disposal/routing, AccessRequest | `generated.v1.governance_schema` |
| [control](../../contracts/schemas/v1/control.schema.json) | ControlRecord: PrincipalRegistration, OwnerRegistration, CapabilityGrant/conditions, ClusterPolicy/rules, ResourceRestriction, AccessDecision | `generated.v1.control_schema` |
| [snapshots](../../contracts/schemas/v1/snapshots.schema.json) | SnapshotRecord: ExportManifest, ImportPlan/ID mapping, ApprovedSelection with optional bounded independent Relation revisions | `generated.v1.snapshots_schema` |
| [authoring](../../contracts/schemas/v1/authoring.schema.json) | AuthoringInput: unmanaged, candidate or conflict input; exact raw Markdown/digest/base and explicit diagnostics | `generated.v1.authoring_schema` |
| [operations](../../contracts/schemas/v1/operations.schema.json) | OperationRequest: 34 explicitly tagged request/payload alternatives; MutationOperation subset for batches | `generated.v1.operations_schema` |
| [transaction](../../contracts/schemas/v1/transaction.schema.json) | TransactionRecord: BatchRequest, OperationResult, CommittedReceipt, ErrorResponse, ReadResult, CommittedEvent, OutboxRecord | `generated.v1.transaction_schema` |

Python models are generated together by the pinned `datamodel-code-generator`, with cross-module references rather than handwritten DTO copies. Import individual models directly or use root unions through the canonical adapter. TypeScript declarations are generated per resource; duplicated helper declarations across generated files are derivative output, not competing handwritten models. Public TS type namespaces are available from [index.d.ts](../../packages/typescript/generated/v1/index.d.ts).

Development in this pinned monorepo (Python 3.12+ and the locked development environment):

```python
from generated.v1.knowledge_schema import Node
from second_brain_contracts import ContractValidator

contracts = ContractValidator()  # registry bundled with this checkout
contracts.verify_generated()    # source + generated artifact hash agreement
node: Node = Node.model_validate(contracts.validate("knowledge", node_json))
wire = contracts.dump("knowledge", node)
# Or parse any resource root union, e.g. KnowledgeRecord:
record = contracts.parse("knowledge", node_json)
```

`node_json` is caller-provided decoded JSON. Set `PYTHONPATH=packages/python` outside pytest; alternatively install a future reviewed package when publication is actually needed. No package registry/release service is introduced. The adapter's default root derives from its source location, not current working directory; callers can supply an explicit repository root. Future packaging must include schemas/registry/manifests and preserve the same import semantics; that distribution is not claimed implemented.

```typescript
import type {Node} from './packages/typescript/generated/v1/knowledge.js';
import type {OperationRequest} from './packages/typescript/generated/v1/operations.js';
import {loadContracts} from './packages/typescript/validation.mjs';

const contracts = await loadContracts(repositoryRoot, '1.0.0');
const record = contracts.validate('knowledge', nodeJson);
if (record.kind === 'node') {
  const node: Node = record;
  console.log(node.content.body);
}
```

The runtime adapter uses Ajv2020/ajv-formats and accepts parsed JSON, not arbitrary objects/host-language instances. Raw transport parsers must reject duplicate keys and non-JSON numbers; the Python `load_json` helper does so for packaged JSON. Do not substitute generated Pydantic parsing or TS static assignment for canonical validation. Known unsupported top-level contract versions raise `UNSUPPORTED_VERSION`; canonical nested version/discriminator constraints also reject invalid values. No read-time migration or network schema loading occurs.

## Serialization and structure

UTF-8/LF artifacts, no generated timestamps or absolute paths. Entity identity is UUID v4 text with no path/title meaning. Logical immutable revisions use an independent revision ID plus resource/revision number; Git hashes are not the revision ID. Digests are explicit SHA-256 algorithm/value pairs; generation references are backend-neutral IDs/digests. Bodies are Markdown wire strings, **not duplicated authoring frontmatter**. `Node.content.properties` permits bounded flat JSON scalars/lists, no nested arbitrary metadata blobs. Instance-defined metadata schema IDs require a registered local schema and semantic validation in the future Core.

Optional omission is distinct from null. Only explicitly nullable fields, such as Cluster description, accept null; serializers use `by_alias=True`, `exclude_unset=True`, `mode="json"` and canonical output revalidation. Bounded namespaced extensions contain a version and flat Properties; unknown core fields always reject. Numbers are finite and safe for JavaScript; integer revisions are bounded at 9,007,199,254,740,991. No coercion/default insertion/property removal is enabled in Ajv.

UTC times support years 0001–9999, uppercase `T`/`Z`, seconds and optional 1–6 fractional digits; reject leap seconds, invalid calendar dates, offsets, year 0000 and newline suffixes. Canonical validation uses **independent maintained format checkers**, and refuses missing checkers. Portable patterns plus standard JSON Schema `not` exclude CR/LF in identifiers. Unicode Markdown, CRLF inside body text and decomposed Unicode remain untouched. Node content binds both `node_type` and `node_type_version`; Relations bind `predicate` and `predicate_version`. Registered definitions are immutable by key/version, so later registry changes cannot reinterpret historical records. Schema IDs for metadata must resolve to the corresponding local registered version; no online retrieval is implied.

Generator approximations are explicit: TS cannot express bounds, unique identity, namespace patterns or date formats; Pydantic optional fields may accept broader nulls and some primitives may coerce when used directly. The Python timestamp mapping deliberately emits strings to preserve fractional spelling rather than converting through datetime. Standard schema `not` guards are externally enforced, not guaranteed by generated types. No canonical constraint was removed to accommodate generation. All valid shared fixtures must round-trip unchanged through generated models.

## Unresolved semantics preserved

O1: raw authoring/candidate/conflict records are separate from committed Node/Revision; no immediate synchronization promise. O2: Node Revision approval is supported; Relations have independent revision/owner; optional bounded Relation selections are expressible but **not mandatory graph approval**. O3: Approval revocation is a separate immutable record, disposal retention/holds/preservation are explicit, no erasure scope or duration is invented. O4: selected Cluster views and resource restrictions are expressible; no union/intersection algorithm or role ladder is implemented. OwnerRegistration is evidence to be verified by trusted bootstrap, never a caller boolean that grants authority.

Collection has one Cluster and independent structural revision; it does not create membership. Relation endpoints structurally require Node references, and Relation changes do not revise Nodes. Asset provider references remain generic (initial deployment Git only); policy/budget checks are semantic. External checks are passive service-produced data. Review types include registered `freshness`, `publication`, `quality`, `disposal` and versioned instance extensions; registration/meaning are semantic, not a universal ontology.

## Generation and validation

```text
python -m tools.generate_contracts
python -m tools.generate_contracts --check
python -m tools.validate_contracts
python -m tools.validate_examples
python -m pytest -q
npm run typecheck
npm run parity
```

One generation command preserves examples and emits production models/types plus [source hashes](../../packages/python/generated/source-hashes.json) and [production manifest](../../packages/python/generated/v1/manifest.json). Check mode regenerates only in temporary directories and compares exact bytes/file sets, including unexpected extras. It does not update committed artifacts. Locks/generators remain pinned and unchanged. CI retains Windows/macOS/Linux and adds production gates; local execution does not prove hosted CI success.

Validation is independent of generation: Python `jsonschema` Draft202012Validator + FormatChecker and TS Ajv2020 consume identical canonical schemas/corpus. A separate reviewer authored the corpus and adversarial probes. [Structural fixtures](../../tests/fixtures/contracts/v1.json) include intended error keywords/paths; [semantic fixtures](../../tests/fixtures/contracts/semantic.json) deliberately pass structural validation and record future rejection obligations. No dummy handlers or policy evaluator are introduced to “test” business semantics. [Compatibility](compatibility.md), [evolution](evolution.md) and [operations](operations.md) define the remaining contract obligations.

See the [executed validation and independent review report](validation-report.md) for actual counts, resolved findings and unexecuted release gates.
