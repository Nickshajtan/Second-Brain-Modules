Implement:

.codex/config.toml with a conservative two-subagent concurrency limit.

.codex/agents/implementer.toml for contract-first implementation, typed APIs, minimal scope and regression testing.

.codex/agents/reviewer.toml for independent, read-only-by-instruction code review focused on correctness, authorization, Git atomicity, domain invariants and contract compatibility.

Update root AGENTS.md with the implementer → reviewer workflow for nontrivial production changes.

Document triggering rules, escalation of blocking findings, and exceptions for trivial changes.

Verify configuration against the installed Codex version and current official documentation.

Smoke-test agent discovery and one small delegated review without introducing production changes.

Constraints:

Use native Codex subagents; no custom orchestration framework.

Do not modify global ~/.codex settings.

Do not hardcode models unless required.

Do not force expensive multi-agent execution on trivial tasks.

Reviewer must not edit code.

Reviewer instructions alone do not establish filesystem isolation.

Limit automatic review/fix iterations to avoid uncontrolled token consumption.

CI remains the authoritative deterministic quality gate.

Report the actual discovered agent roles, smoke-test results, limitations and token-cost considerations.

Integrate this into M1.1 rather than creating a separate infrastructure milestone.


Extend the repository Codex configuration with a mandatory delegation protocol.

Requirements:

1. Configure native `implementer` and `reviewer` subagents using the supported Codex version.
2. Require implementer → reviewer delegation for nontrivial production changes.
3. Add explicit delegation failure handling: `DELEGATION_BLOCKED`.
4. Require reporting actual delegation evidence, not merely claiming review occurred.
5. Validate that the configured subagents can actually be discovered and invoked.
6. Run a controlled smoke test where the coordinator must delegate a small implementation task and a subsequent independent review.
7. Inspect available session/tool traces to confirm both delegations happened.
8. Document any limitations in verifying subagent execution.
9. Do not introduce custom orchestration infrastructure in this phase.
10. Keep CI deterministic and independent of agent self-reporting.

Do not claim guaranteed delegation based solely on AGENTS.md instructions.

If native Codex does not expose a reliable enforcement mechanism, document that limitation and propose the smallest external orchestration gate without implementing it yet.