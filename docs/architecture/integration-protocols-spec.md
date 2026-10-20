# Integration and open protocols specification

Status: proposed. This document defines adapter obligations, not running endpoints. Shared business rules B01–B13 are in [core contracts](contracts-spec.md). Version research and source links are in [research notes](research.md).

## 1. Application boundary

An application operation receives typed input and a **verified** request context, then returns typed output or a domain error. Context contains workspace, authenticated principal, delegation/session, correlation ID, deadline, and cancellation handle. Context is created by a trusted local bootstrap or authenticated adapter, never accepted as an arbitrary caller-supplied principal object. Application authorization is mandatory even for Python direct calls.

Use ordinary Python `typing.Protocol` interfaces, explicit methods and generated request/result types. Define an operation's semantics in tables and conformance cases. JSON Schema defines payloads; Markdown defines behavior; Python defines callable signatures. Do not invent a schema compiler or executable operation manifest. A simple discovery projection may list operation IDs and schema refs; it must be tested against the actual methods and is not a universal translator.

Illustrative interface only, not delivered runtime code:

```python
class KnowledgeApplication(Protocol):
    def get_node(self, request: GetNodeInput, context: VerifiedContext) -> KnowledgeNode: ...
    def replace_node(self, request: ReplaceNodeInput, context: VerifiedContext) -> KnowledgeNode: ...
```

Operation identifiers are stable names, e.g. `sb.knowledge.node.get`, with a separately negotiated contract version. A breaking operation can coexist under a new version; do not reinterpret the old ID's semantics. HTTP method names and MCP tool naming constraints may need explicit aliases; tests assert a one-to-one mapping to the documented operation/version. A `Protocol` is not generated from the documentation and therefore needs conformance review and tests.

### Operation catalog (proposed minimum and later extensions)

The following shorthand describes future canonical schema references: `X@1` means the exact `1.x.y` schema ID selected by compatibility negotiation, never a floating URL. Only the illustrative Node/Cluster schemas exist in this delivery. All operations use the common Error contract. R = synchronous request/result; J = durable job returning RunRef. All mutation keys/revisions are application payload fields, with optional transport mirrors required to match.

| Operation ID suffix after `sb.` | Input → output | Capabilities / side effects | Concurrency, idempotency, mode, timeout/cancel, audit |
|---|---|---|---|
| `system.describe` | DescribeInput → AdapterDescriptor | `sb.system.discover`; metadata read | R, bounded deadline; exposes installed support, no grant/sensitive resource names; audit remote/session establishment |
| `knowledge.node.get` | GetNodeInput `{id, revision?}` → Node | `sb.knowledge.read`; read | R, revision-specific or committed snapshot; repeatable only for pinned revision; safe cancel; audit sensitivity-dependent read |
| `knowledge.node.search` | SearchInput `{query, scope, limit, cursor?}` → NodeSummaryPage | `sb.knowledge.read`; derived read | R, opaque cursor binds snapshot + principal + policy; max 100 results proposed; authorization before pagination/count; safe cancel; audit scope |
| `knowledge.node.create` | CreateNodeInput `{idempotency_key, draft}` → Node | `sb.knowledge.write`; canonical write | R; server validates allocated ID uniqueness, starts revision 1; B06 replay; commit cannot be undone by disconnect; audit intent/result |
| `knowledge.node.replace` | ReplaceNodeInput `{id, expected_revision, content_hash, idempotency_key, replacement}` → Node | `sb.knowledge.write`; canonical write | R; complete replacement of editable fields only, B05/B06; deadline before commit aborts; committed response recoverable by key; audit change |
| `knowledge.node.transition` | TransitionInput `{id, expected_revision, to, reason, approval_ref?, key}` → Node | `sb.knowledge.transition`; lifecycle write | R; B01, CAS, exact approval; safe-point cancel only; audit transition |
| `knowledge.cluster.membership.replace` | MembershipReplaceInput `{cluster_id, expected_revision, members, key, approval_ref?}` → Membership | `sb.cluster.manage`; membership write | R; one manifest aggregate, duplicate/member eligibility checks; B02/B03/B06; audit additions/removals |
| `knowledge.promote` | PromoteInput `{node_revision, target_cluster_revision, approval_ref, key}` → Membership | `sb.knowledge.promote` + target scope; Stable membership write | R; approved active node revision + target manifest CAS. Does not mutate node or automatically remove Stack membership; consume approval with commit |
| `context.compile` | ContextInput `{cluster_ids, node_revisions?, budget, format_version}` → ContextBundle | `sb.context.read` plus each resource read; read | R initially; deterministic B13; deadline aborts before delivery, no partial authorized bundle unless explicitly requested; audit manifest without content |
| `import.preview` | ImportPreviewInput `{configured_source_id, options}` → ImportPlanRef | `sb.import.preview`; read source, write temporary plan | J later; no knowledge write, no arbitrary server-side paths from remote input; cancel discards scratch; audit source/plan hash |
| `import.apply` | ImportApplyInput `{plan_hash, expected_snapshot, approval_ref, key}` → RunRef | `sb.import.apply` + scoped writes; curated writes | J later; resumable per-item commits, no all-import atomicity claim; cancel preserves committed items; explicit report/audit |
| `run.get` / `run.cancel` | RunInput → Run / CancelReceipt | `sb.run.read` / `sb.run.cancel` with run ownership | R; cancel receipt says requested/already-terminal, never false rollback promise; cancel idempotent; audit requests |
| `control.grant.issue` / `control.grant.revoke` | GrantIssueInput / GrantRevokeInput → Grant | `sb.control.grants.manage`; access-control write | Local human administration only for MVP; CAS/key, monotonic revocation, current authority checked; mandatory audit |

Omitted operations are not silently exposed as generic CRUD. Hard deletion, remote arbitrary command execution, raw file write, unrestricted Git, model invocation and policy expression evaluation are unsupported through the initial public application interface. Application effects returning large content use authorized immutable artifact handles, not arbitrary paths or public URLs. Handles expire and preserve resource scope.

## 2. Protocol versus transport

Stdio, HTTP, Unix domain sockets and Windows named pipes carry bytes. JSON-RPC defines request/response envelopes and errors; MCP adds agent-facing semantics and capabilities over particular bindings. REST is an interaction style over HTTP. WebSocket is a persistent duplex messaging channel with an HTTP upgrade; it does not define Second Brain operation semantics. gRPC couples RPC semantics, a service IDL and an HTTP/2 binding.

Choose adapters for demonstrated consumers. **MVP: Python and CLI only.** MCP stdio is the first planned agent adapter after the boundary is proven. HTTP and MCP Streamable HTTP remain optional later exposure, not prerequisites for importing knowledge.

| Candidate | Suitability / tooling | Identity and authentication | Streaming / cancellation | Cost and cross-platform decision |
|---|---|---|---|---|
| Python direct | Core callers/tests, no serialization overhead | Trusted bootstrap binds principal; app enforces policy. Arbitrary same-process malicious code is outside isolation guarantee | Iteration only if explicitly contracted; cooperative token/deadline | Lowest; all 3 OS. Required MVP |
| Local CLI | Human/admin and scripts; argparse + generated payloads | Explicit configured local profile, OS account and workspace binding; no default superuser. Privileged profile requires human gate | stdout JSON result, stderr diagnostics, exit mapping; interrupt requests cooperative cancellation | Low; all 3 OS. Required MVP |
| Process stdio without protocol | One-shot JSON-in/JSON-out CLI for batch scripts | Launcher profile and environment secret references; never principal from payload | One document per invocation; no multiplexing/progress on stdout; process kill can leave committed effect | Low; useful CLI mode. Do not invent persistent framing |
| JSON-RPC 2.0 over stdio | Bidirectional request correlation when a consumer specifically requires it | Same launcher identity; explicit limits | Standard request IDs; base JSON-RPC has no built-in streaming/cancellation semantics | Moderate; all 3 OS. Defer standalone adapter; MCP already covers likely agent consumer |
| MCP over stdio | Standard agent tool integration; maintained Python/TS SDKs | Launcher-scoped identity/grants; limited inherited environment; local ≠ unrestricted | Protocol-version-specific cancellation/progress, mapped to safe-point app behavior | Moderate; all 3 OS. Planned, not mandatory for every harness |
| MCP over Streamable HTTP | Remote agent clients, potentially request-scoped SSE | Follow selected MCP HTTP authorization profile; validated audience/issuer, TLS, server policy | SDK/protocol-version-defined streaming and termination; transport loss does not cancel a durable job | Higher; all 3 OS. Optional after remote security gate |
| HTTP/REST + OpenAPI | General web/TS clients and external services | TLS + scoped short-lived credential, explicit server identity; CSRF/Origin protection where cookies/browser access apply | R endpoints; later J polling, optional SSE. HTTP disconnect ≠ job cancel | Moderate; all 3 OS. Optional later |
| WebSocket | Interactive duplex UI only if polling/SSE proven inadequate | Authenticate upgrade and connection, authorize each operation; refresh/revoke long-lived sessions | Bidirectional frames; flow control/resume and cancel protocol require design | Higher; all 3 OS. Defer; no MVP need |
| gRPC | Typed service integrations, efficient streaming | TLS/mTLS or validated tokens with per-RPC policy | Deadlines, stream flow control and cancellation available, still best effort for effects | Higher, extra Protobuf authority and generators; all 3 OS. Defer |
| Unix sockets / Windows named pipes | Local daemon IPC if process startup becomes costly | OS peer identity/ACLs plus app principal binding; test named-pipe ACLs explicitly | Framing/protocol must be chosen, e.g. JSON-RPC; neither endpoint defines an RPC protocol | Separate platform adapters/tests. Optional transport under proven daemon requirement |

JSON-RPC base notifications lack responses; mutating operations must use requests with correlation IDs. JSON-RPC's standard errors describe envelope/parser failures; application errors map to a documented server-error code with the domain envelope in `data`. Do not conflate domain `not_found` with method-not-found. [JSON-RPC specification](https://www.jsonrpc.org/specification).

MCP research resolved `latest` to **2026-07-28**, which changes parts of earlier initialization/cancellation behavior. The adapter must pin an SDK and a tested dated profile, not assume the 2025 lifecycle applies. This document selects no SDK or backwards-compatibility shim yet (Q10). The standard still separates [stdio and Streamable HTTP bindings](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports); HTTP [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) and local launcher authentication are different responsibilities.

## 3. Outbound ports

| Category / adapter | Boundary and owned behavior | Constraints |
|---|---|---|
| Data source: ChatGPT inventory | Read Phase 1 JSONL and source locators through configured source root; produce candidates/provenance, not trusted nodes | Original IDs/hash/branch evidence retained; stream bounded records; unresolved refs preserved; preliminary labels not authoritative. No parser rewrite now |
| Data source: other stores | Read/export using store-specific ports; map to candidate records and evidence | Never directly dual-write canonical knowledge; source license/retention/access retained |
| Storage: filesystem | Safe Markdown/YAML codec, atomic staging, path/hash checks, lock and recovery helpers | Resolve under configured root, reject traversal, symlink/junction escape and case-collision ambiguity; allowlist extensions; no code execution |
| Version history: Git | Managed commit/lookup/history port, exact repo/branch/expected tree | No arbitrary shell input, no force push, no auto-fetch/push by default. Hooks are executable trust boundary; disable or explicitly approve managed hooks |
| Human interface: Obsidian | Reads standard files; optional TS plugin invokes application operations | Plugin not canonical store or policy authority. Human direct edits reconciled as B09; no mandatory plugin |
| Execution: external harnesses incl. HCC | Invoke explicit approved process/context ports or consume inbound interfaces | No provider/harness identity in core types; delegated capability/session scope; harness cannot bypass approval or storage boundaries |
| Execution: optional remote workers | Submit bounded job definition/artifact handles, get effect receipts/checkpoints | Defer until measured need. Grant attenuation, worker identity, idempotency/fencing and unknown outcome reconciliation required |
| Outbound communication: model providers | Optional model invocation port returns suggestions + provider/model/version/provenance/cost evidence | Explicit egress authorization and redaction; no network by default; never auto-promote provider output |
| Outbound communication: remote APIs | Endpoint-specific typed requests through allowlisted config | Secrets outside files/context; explicit send/side-effect policy, bounded retries, no arbitrary URL dereference |

Adapters do not share a generic “execute anything” port. Ports are narrow and typed. Registration is explicit at startup; dynamic third-party code loading and a plugin marketplace are deferred.

## 4. Standards selection

These are recommendations based on official sources, not a promise that generators preserve every keyword. Python and TypeScript both have mature ecosystems for the adopted tools; runtime parity must be demonstrated by M2.

| Standard | Role, strengths, language/tooling cost | Decision / source-of-truth impact |
|---|---|---|
| JSON Schema Draft 2020-12 | Structural data contracts; independent validators; expressive refs/unions; not authorization/state transitions | Adopt now, mandated. Sole data authority. [Specification](https://json-schema.org/draft/2020-12) |
| OpenAPI 3.1.2 | HTTP operations/status/auth/parameters, broad client/doc ecosystem; Schema Object aligned with 2020-12 dialect | Optional binding; adopt only when HTTP chosen. Handwritten binding metadata, external schema refs; never independently maintained copies of Node. [Specification](https://spec.openapis.org/oas/v3.1.2.html) |
| MCP dated profile | Agent-facing tools/resources, discovery and standard bindings; SDK/client version interoperability needs testing | Plan stdio after M5/M10; remote optional. Tool input/output must reference or use derived canonical schema, not new models. [Current inspected specification](https://modelcontextprotocol.io/specification/2026-07-28) |
| JSON-RPC 2.0 | Simple language-neutral request/error envelope; no auth or standard business cancellation by itself | Use as part of chosen MCP profile; standalone adapter deferred. No new data authority. [Specification](https://www.jsonrpc.org/specification) |
| AsyncAPI 3.0 | Describes message channels/bindings; Python/TS event tooling available; extra operational/documentation burden | Defer until external event broker/channel exists. Internal events do not require it. Event payloads would reference schemas. [Specification](https://www.asyncapi.com/docs/reference/specification/v3.0.0) |
| gRPC / Protocol Buffers | Strong RPC codegen for Python/TS, binary streaming; another IDL and semantic conversion cost | Defer; reject as canonical contract now. A future bounded service may own a separate Protobuf boundary with explicit mapping tests. [gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/) |
| Smithy 2.0 | Service/resource modeling and codegen ecosystem; useful for broad service SDK programs, extra build/model layer | Reject for current phase: competes with selected canonical schemas/operation docs without demonstrated benefit. Reconsider only for a measured SDK requirement. [Specification](https://smithy.io/2.0/index.html) |

OpenAPI `$ref` resolution must work offline from a release bundle, including external schema IDs and relative files. A stock HTTP generator may flatten or ignore 2020-12 features; reject that result rather than changing schema semantics to accommodate it. Optional clients may use binding-generated transport types while importing shared domain types; actual generator choice waits for the HTTP fixture spike. The [example](examples/openapi-example.yaml) deliberately has one GET and external Node ref; it is not a universal application catalog. An HTTP binding can expose a subset of operations and must preserve application error, auth, CAS and idempotency semantics.

## 5. Discovery and negotiation

Minimal response: adapter ID/implementation version; binding protocol/transport and supported dated versions; operation ID + exact accepted input/output/error schema IDs + contract version; optional features; authentication scheme names; request-size/deadline limits; streaming/cancellation flags and semantics; compatibility/deprecation metadata. No secret values, grant details, private cluster names, or raw filesystem paths.

Discovery answers **what is installed**, filtered to avoid sensitive implementation details. Authorization answers **what this principal can do now**. A declared capability or cached discovery response never grants invocation. Client and adapter choose a supported protocol and operation/schema combination by intersection; no intersection returns unsupported-version with safe metadata. Unknown required features fail; optional unknown features are ignored. Recheck per-operation authorization and revocation regardless of session negotiation. Cache discovery by adapter release/config hash, not indefinitely.

## 6. Trust boundaries and enforcement

1. Inbound adapters authenticate and normalize input, enforce size/depth/rate limits and attach verified identity. The application independently enforces scope/policy and validates canonical payloads. Adapter-only checks are insufficient.
2. Principal delegation records both actor and subject. A service cannot substitute a caller-selected principal. Bind session memory and context attachments to the verified session, and check expiry/revocation at delivery/commit.
3. Local CLI/Python uses explicit workspace profiles and scoped grants. A same-user process with raw filesystem access can still edit files; application policy is not an OS sandbox. Isolate untrusted agents with OS accounts/container permissions or read-only materialized context if hostile-code resistance is required (Q07).
4. External text, Markdown, chat exports and attachments are untrusted data. Do not execute code, evaluate YAML tags, follow instructions found in content, fetch embedded URLs, or expose secrets in compiled context. Limit archive expansion and attachment handling separately when import is built.
5. Resolve secret references just in time through deployment credential providers. Never log tokens, serialize them into contract fixtures, Git, run checkpoints, error details, or model requests.
6. Remote exposure defaults disabled. Require explicit bind configuration, TLS, validated audience/issuer/expiry, narrow capabilities, endpoint allowlists, request limits, audit and revocation tests. Loopback binding is not sufficient authentication. Handle browser Origin and DNS rebinding; no permissive CORS by default.
7. Filter retrieval before counts, relationship expansion, snippets and context construction. Cross-context disclosure is a separate authorized action. Audit resource handles, reasons and policy versions without raw private content.
8. The client disconnect/transport cancellation boundary must not fabricate rollback. Durable run cancellation invokes `run.cancel`; uncertain outbound effects require reconciliation. No unlimited automatic retries.

## 7. Capability-to-adapter matrix

Statuses: **R** Required for MVP, **P** Planned, **O** Optional, **U** Unsupported by this exposure policy, **?** Undecided pending consumer requirement. “Optional” is not a commitment to build. IPC means JSON-RPC over Unix socket/named pipe if a local daemon is later justified; WS and gRPC remain deferred even where `?` appears.

| Core capability | Python | CLI / one-shot stdio | MCP stdio | HTTP REST | MCP HTTP | Standalone JSON-RPC / IPC | WebSocket | gRPC |
|---|---|---|---|---|---|---|---|---|
| Describe/read/search | R | R | P | O | O | ? | ? | ? |
| Create/replace/transition | R | R | P | O | O | ? | ? | ? |
| Membership/promote (approval required) | R | R | P | O | O | ? | ? | ? |
| Context compile | R | R | P | O | O | ? | ? | ? |
| Import preview/apply | P | P | O | O | O | ? | U | ? |
| Run read/cancel | P | P | P | O | O | ? | ? | ? |
| Grant/approval administration | R | R | U | U | U | U | U | U |
| Policy/config activation | R | R | U | U | U | U | U | U |
| Raw file/shell/Git execution | U | U | U | U | U | U | U | U |
| Event subscription | ? | U | O | O (SSE) | O | ? | ? | ? |

Admin capabilities are restricted to human-controlled local paths in MVP to avoid ambient agent privilege; this is a product exposure decision, not a claim that HTTP cannot be secured. No event subscription schema is promised until a consumer exists. Import is excluded from WS to avoid adding large-artifact upload/resume semantics merely to duplicate the job API. Raw filesystem/Git operations are internal outbound ports, never exposed wholesale. One-shot CLI can poll a run but cannot provide a persistent event subscription. Unsupported exposure can change only through a reviewed binding/security decision.
