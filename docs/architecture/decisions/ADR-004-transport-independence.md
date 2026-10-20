# ADR-004: Transport-independent application boundary

Status: task-mandated principle; Python/CLI-first exposure proposed. Date: 2026-10-20.

## Context

Local scripts, agents and optional remote clients need the same knowledge and policy semantics. Putting authorization in an HTTP controller would permit local adapters to bypass it.

## Decision

Use explicit typed application methods and verified context with stable operation IDs. Validate and authorize in the application boundary for every adapter. Define behavior in ordinary documentation plus conformance tests, not a new operation DSL. Python and CLI are MVP adapters; MCP stdio follows a concrete consumer; remote bindings are optional. Outbound ports remain narrow and typed.

## Alternatives

HTTP-first forces local callers through a server. MCP-first couples all use cases to agent tooling. A universal adapter/translator promises coverage without preserving business meaning. Adapter-specific domain logic duplicates behavior and bypass risks.

## Consequences

Adapter code handles framing/authentication/error mapping, while domain errors, CAS, idempotency and effects remain stable. Interfaces and documentation need explicit conformance tests because no custom generator keeps them synchronized. Same-user hostile code remains an OS isolation concern (Q07).

## Reversibility

An adapter can be replaced without changing domain contracts. Operation semantics change through versioned contracts. Exposure of control-plane administration over remote/agent adapters needs a new reviewed decision.
