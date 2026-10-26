# Reusable modular monolith and instance isolation

Current semantic/API authority: [M1.2 decisions](../domain/accepted-decisions.md) and [roadmap](implementation-roadmap.md). Context construction belongs to external harnesses; historical Context component placement below is superseded. No agent filesystem ingress is permitted.

Status: repository strategy adopted by the hardening task. Runtime interfaces below
are design obligations, not implemented services. The implementation here consists
of validation, tests, generated illustrative models and CI only.

## Code boundary

`Second-Brain-Modules` is one reusable repository, consumed as one pinned submodule
or future release. Modules are cohesive internal units; they do not each require
a package, repository, service or plugin registration protocol. The previous
`second-brain-contracts/` wrapper has been flattened into this root. Schemas remain
under `docs/architecture/examples/` until production contract review; generated
Python/TS artifacts are under `packages/`. No empty runtime modules are created.

| Logical module | Responsibility / future public interface | Allowed dependencies | Forbidden dependencies | State ownership / extraction |
|---|---|---|---|---|
| Contracts | Versioned data schemas, generated types, independent validation | Standard libraries and selected validation libraries | Core runtime, adapters, provider/agent SDKs | No installation state; already independently usable as files/types; future package optional |
| Knowledge | Node/revision/embedded relation invariants; typed application operations | Contracts, policy and repository ports | HTTP/MCP, concrete Git/database clients, agent SDKs | Canonical aggregate ownership; extract only behind versioned operations |
| Storage | Markdown/YAML codecs, filesystem/Git ports and implementations, commit recovery | Contracts and narrow repository ports | Agent SDKs, provider clients, inbound transports | Consumer-owned canonical files/Git journal; not a second knowledge authority |
| Graph | Query/index projections over committed knowledge | Contracts, read-only knowledge port | Canonical writes, provider SDKs, transports | Per-instance derived index, rebuildable; query boundary can be extracted later |
| Clusters | Scope/membership and approved revision pointers | Contracts, policy and knowledge read ports | Transport implementations or direct unguarded file mutation | Membership manifests; can remain with knowledge in one cohesive package |
| Policies | Principals, grants, approvals and deterministic decisions | Contracts, control repository/clock ports | Inbound adapter auth as sole enforcement, model output as authority | Instance desired policy/grant records; always enforced at application boundary |
| State | Runs, attempts, checkpoints and idempotency coordination | Contracts, durable state port | Knowledge-content authority, transport-specific sessions as global state | Consumer runtime DB, separately durable from derived caches |
| Execution | Explicit application/process coordination, cancellation/fencing | Contracts, policy, state and operation ports | Arbitrary SDK import in domain, universal workflow DSL | Runs via State; extraction only with measured need and effect/recovery protocol |
| Context | Authorized deterministic snapshot assembly | Contracts, policy, cluster/knowledge read ports | Model-specific ranking as deterministic core; direct secret reads | Per-instance disposable caches and session-scoped attachments |
| Integration | Inbound adapters and outbound provider/source/storage bindings | Application interfaces, adapter-specific SDKs in optional dependency groups | Redefining domain semantics or bypassing policy | Consumer endpoint/credential references; no secrets in descriptors |
| Observability | Audit/diagnostic port contracts and adapters | Contracts, sanitized event/clock interfaces | Raw private content or credentials in logs, mutation authority | Instance audit/log destinations; durable audit distinct from disposable metrics |

These responsibilities may be grouped as contracts, core and adapters when actual
code warrants it. Current `tools/` is development tooling, not a production module
loader. No DI framework is needed: constructors receive explicit ports/context.

Dependency direction is inbound adapters → application interfaces → domain rules
and ports ← outbound implementations. Contracts sit below all. When production
modules exist, add import-linter contracts or AST import tests for these layers,
and conformance tests proving direct Python calls enforce policy too. Until then,
there is no value in tests against empty directories. Contract consumption/generation
already imports no knowledge runtime, model, MCP, Obsidian, database or agent SDK.

## Workspace context (proposed runtime contract)

Each operation will receive an immutable, explicitly supplied workspace context:
workspace UUID; validated absolute knowledge/source/artifact roots; knowledge Git
working directory/branch; control config version; state DB path; per-instance cache
root; credential-provider namespace/reference; and installed code/contract compatibility
metadata. Verified principal/session context is separate and bound to that workspace.
This is configuration plus explicit handles, not a mutable universal Global State.

Host configuration resolves relative paths against the host config file location,
never current working directory or shared-code location. Resolve and validate roots
once; reject overlapping private state/credential roots for independently configured
installations unless an explicit shared-storage design is approved. Symlinks/junctions,
case collisions and lock behavior require storage implementation tests. Never infer
workspace identity from a folder title, process environment mutation or Git remote.

All repositories, connections, locks, caches, idempotency keys and session attachments
are scoped by explicit workspace identity. No process-wide mutable “active workspace.”
One process can later hold two independent workspace service instances. A single
writer lock is per workspace; installations can run concurrently without global
`chdir`, environment switching or shared SQLite connection singletons. Sharing a
read-only code checkout is possible with separate environments/state, although normal
submodule consumers get independently pinned checkouts. Ordinary checkout runs no
hooks, generators or consumer-data writes.

Credentials are host-owned references resolved by namespace and principal; never
files committed under this repository. Per-instance caches include schema/code/config
and source snapshot hashes. Cache deletion cannot remove durable run/audit state.
Git history for knowledge is the consumer's history, distinct from reusable code history.

Backup/restore retains workspace ID and coherent canonical/control/runtime snapshots,
including compatible code/contract versions. A fork allocates a new workspace ID,
records lineage and explicitly reissues grants/credentials; copying a DB does not
authorize the new instance. Cross-workspace entity references remain explicit. Instances
upgrade independently; compatibility checks/migrations run before serving writes.

## Trust levels

Trusted local code is part of the application process and can access its configured
ports; it must follow application contracts. Policy-compliant agents use authenticated,
scoped interfaces and have no need for raw vault write access. Untrusted execution
with the human user's filesystem privileges can edit canonical files, secrets and
policy outside those interfaces. Application ACLs cannot stop that attacker. OS-account
separation, a sandbox or read-only materialized context would be needed; none is
implemented here. Q07 stays open for each deployment threat model.

See [consumption/versioning](versioning-and-consumption.md), [Stable revision review](stable-revisions.md)
and [ADR-008](decisions/ADR-008-monorepo-consumption.md).
