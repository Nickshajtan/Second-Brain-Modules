# Engineering rules

- Before changing behavior, read the [domain baseline](docs/domain/domain-model.md),
  [current Core scope](docs/core/m1.md) and relevant [ADRs](docs/architecture/decisions/README.md).
- Canonical JSON Schema 2020-12 is the structural authority. Validate untrusted
  ingress and outgoing records canonically; generated types alone are insufficient.
- Never hand-edit generated Python/TS models or their manifests. Reuse generated
  types instead of handwritten domain DTOs; regenerate through the existing tools.
- Keep domain semantics independent of storage/transports. Preserve fail-closed
  authorization, instance isolation and conditional transaction publication.
- Do not invent Owner policy decisions or implement unsupported operations.
- Type new exported APIs and narrow infrastructure interfaces. Use Ruff alone for
  handwritten Python formatting. See [standards](docs/engineering/standards.md).
- Add focused regressions for confirmed defects; preserve existing fixtures and
  independent validators. Do not add dependencies/abstractions without a concrete need.
- Run relevant [quality commands](docs/engineering/standards.md) and report actual
  results, remaining risks and unverified platforms/durability claims.
- Preserve user changes. Do not remove uncertain/user-authored material, rewrite
  history, force-push or perform destructive cleanup. Historical evidence stays
  accessible; generated submodule-consumer artifacts remain tracked.

## Mandatory Delegation Protocol

For every nontrivial production-code change, the coordinator MUST use the configured `implementer` and `reviewer` subagents.
This M1.1 protocol covers behavior, authorization, persistence, contracts,
generation, distribution and compatibility changes. The coordinator owns
integration and deterministic verification. Exceptions are defined below;
explicit user requests for delegation still apply.
Do not replace independent review with the implementer's self-review. Subagents must not delegate.

### Execution sequence

1. **Delegate implementation.**
   - Invoke the `implementer` subagent.
   - Provide the task scope, relevant contracts and acceptance criteria.
   - The coordinator must not silently replace this step by implementing everything itself.

2. **Delegate independent review.**
   - After implementation, invoke the `reviewer` subagent.
   - Provide the completed diff and original requirements.
   - The reviewer must inspect the actual changes, not only the implementer's summary.
   - The reviewer must not edit any files.

3. **Resolve findings.**
   - P0/P1 findings block completion.
   - Confirmed P2 findings require a fix or explicit documented acceptance.
   - Delegate corrections to the implementer.
   - Allow at most three automatic correction/recheck cycles. Each cycle consists
     of one implementer correction followed by one independent reviewer recheck.
   - Escalate unresolved P0/P1 findings and confirmed P2 findings without explicit
     user acceptance; stop rather than looping.
   - Any substantive post-review change requires review of the final diff. If
     the automatic cycle is exhausted, report `DELEGATION_BLOCKED` and seek user direction.
   - A completed review with no remaining blocking findings allows normal task
     completion once applicable quality gates pass; no extra review cycle is required.

4. **Verify quality gates.**
   - Run applicable lint, typecheck, contract and test commands.
   - Report actual results.
   - CI remains the authoritative deterministic quality gate and does not trust
     agent self-reporting.

### Required execution evidence

The final report MUST include:

- Implementer: invoked / unavailable / skipped.
- Reviewer: invoked / unavailable / skipped.
- Actual configured role names, task scopes and completion status for both
  delegations, plus agent/session IDs and tool/trace references where available.
- Reviewer verdict and findings.
- Corrections performed.
- Quality-gate results.
- Any bypassed steps and reasons.
- Remaining risks and verification limits.

Never claim that a subagent ran unless an actual delegation occurred.
A task label or final-message claim alone is not execution evidence.

### Failure policy

- Report `DELEGATION_UNAVAILABLE` when a configured role cannot be discovered or
  invoked, or its execution fails. Disclose the exact failure and incomplete step;
  preserve completed work and seek user direction if required delegation cannot finish.
- Report `EVIDENCE_INCOMPLETE` when the available evidence cannot establish that
  the required delegation or review completed. Identify what is verified and what
  is missing; do not mark an unverified review as completed.
- Missing optional trace/session IDs alone must not block otherwise verified
  invocation and completion. State that limitation and complete normally if the
  review has no blocking findings and applicable quality gates pass.
- Never substitute self-review and describe it as independent. Reserve
  `DELEGATION_BLOCKED` for unresolved blocking findings or an exhausted correction
  budget; escalate those blockers to the user.

Instructions do not guarantee delegation or reviewer filesystem isolation.
See [configuration and evidence](docs/engineering/codex-workflow.md) for the
native configuration, smoke-test limitations and proposed enforcement gate.

### Exceptions

Trivial spelling, mechanical formatting, documentation-only or pure
generated-artifact updates may skip delegation if the reason is recorded.
The generated-artifact exception applies only to mechanical regeneration with
no contract, generator, runtime behavior, distribution or compatibility change.

The coordinator must not classify a production behavior change as trivial merely to avoid delegation.
