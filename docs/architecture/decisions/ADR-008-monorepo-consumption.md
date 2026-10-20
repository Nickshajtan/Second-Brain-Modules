# ADR-008: Whole-repository reuse across isolated installations

Status: accepted direction from the repository-hardening task. Date: 2026-10-20.

## Context

The initial delivery was a portable contract folder intended for extraction. The
user has now established Second-Brain-Modules as the reusable core repository, with
MIT license. Independent projects need their own data/configuration/state and pinned
code version without separate repositories for each logical domain.

## Decision

Use one modular-monolith repository and one root Git submodule boundary. Promote
docs/tools to the root; keep illustrative contracts in their established relative
location until production review. No nested gitlinks or second contract submodule.
Modules may be independently importable without being separately published. Supply
workspace-specific context explicitly; no mutable process-global active workspace.
Host installations own knowledge, Git history, policy, runtime stores and secrets.

## Alternatives

Keep the old wrapper: lower immediate diff, but misleading root and consumption
instructions. One repository per module: independent Git pinning but unnecessary
release/deployment overhead. Universal module loader or microservices: not justified.

## Consequences

Consumers pin the complete repository commit and upgrade independently. Code updates
must not mutate host knowledge during checkout. Contract validation/generation can run
without future runtime/provider dependencies. Internal dependency rules are documented
now and tested as actual production modules appear. No empty domain scaffolding.

## Reversibility

Future package publication or measured worker/service extraction is possible behind
stable interfaces, through a new ADR. It does not require repository-per-module now.
This supersedes extraction guidance in the original delivery report and README;
unrelated schema namespace, trust and storage questions remain open.
