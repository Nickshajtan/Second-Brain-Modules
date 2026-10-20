# ADR-007: Modular monolith first

Status: task-mandated initial model; future extraction triggers proposed. Date: 2026-10-20.

## Context

This is a local personal knowledge platform with existing scripts and no measured distributed workload. Logical planes need clear ownership, not independent services.

## Decision

Start with a local Python application and explicit module/port boundaries. Add TS integrations as consumers. No broker, service mesh, orchestration platform, distributed database or worker fleet. Remote access is optional after local storage, access, job and context behavior is proven. HCC/provider integrations remain replaceable adapters.

## Alternatives

Microservices add authentication, network failures and distributed consistency before useful knowledge operations. A monolithic script without boundaries is easy initially but hard to secure/test. A general workflow platform is excessive without a concrete multi-process need.

## Consequences

Deployment and recovery are simpler, but one writer bounds write concurrency. No capacity claims are made without measurement. Extract a worker/service only for demonstrated throughput/latency, security isolation or independently operated remote consumers, with explicit ownership and recovery design. Do not treat all three as the same motivation.

## Reversibility

Typed operations and outbound ports allow later extraction. Network delivery is not transparent: auth, deadlines, retries, fencing and indeterminate effects must be designed and tested before extraction. Changing deployment does not authorize redefining canonical knowledge.
