# M1.1 native Codex delegation

Project configuration lives in `.codex/config.toml`; standalone role definitions
live in `.codex/agents/implementer.toml` and `.codex/agents/reviewer.toml`.
The two concurrently open subagent threads exclude the coordinator. No model,
provider, credentials, global settings or approval bypass is configured here.
Roles inherit the selected session model and permissions. Project configuration
requires project trust; installing these files does not establish trust.

## Protocol and limits

The root [engineering rules](../../AGENTS.md) require implementer then independent
reviewer for nontrivial production changes. Documentation-only, spelling and
mechanical formatting changes are exempt unless delegation is explicitly requested.
The coordinator supplies a bounded assignment, waits for implementation, then
supplies the final diff and requirements to a different reviewer agent. Both roles
must be invoked by configured identity, not merely by a task label.

At most one automatic correction and one recheck are allowed. Unresolved blocking
P0/P1/P2 correctness findings or missing execution evidence stop the workflow with
`DELEGATION_BLOCKED`; report the reason and seek explicit user direction. Report
agent IDs, role names, actual completion and trace references. CI remains the
authoritative deterministic gate; no CI job calls an LLM or trusts its verdict.

Reviewer read-only instructions are behavioral constraints, not filesystem
isolation. Current native agents inherit the parent's permissions; custom agent
files cannot replace them. Do not advertise a separate read-only sandbox.

No documented native setting guarantees implementer-before-reviewer execution or
forces the coordinator to delegate. AGENTS.md is a protocol, not enforcement.
If a hard gate becomes necessary, the smallest proposed external addition is a
required merge check consuming trusted harness events: verify distinct configured
implementer/reviewer IDs, ordered completion, review tied to the final diff hash,
and no unresolved blockers, alongside existing CI. Missing events fail closed.
That proposal is not implemented here and cannot prove semantic review quality.

## Verification on 2026-10-24

Installed CLI: `codex-cli 0.163.0`. Configuration follows the current official
[subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
Standalone files require name, description and developer_instructions; no models
are pinned. TOML parsing and structural assertions passed locally.
The repository virtual environment's `python -m tools.validate_examples` passed:
295 portable document links, 2 schemas, 20 schema refs, 4 fixtures, 11 rejection
probes, 3 additional valid probes and 2 OpenAPI refs. Scoped `git diff --check`
passed. The system Python lacked `jsonschema_path`; validation was rerun using the
existing `.venv` without installing dependencies. No runtime code changed, and
the production suite was not rerun for this configuration/documentation change.

The controlled smoke prompt requested only a disposable typed addition function
under `.cache/codex-smoke/`, implementer completion, then independent review.
No production changes were authorized by that prompt.

Result: **DELEGATION_BLOCKED**, not a passing smoke test.

- Initial sandbox invocation encountered TLS certificate validation errors.
- An escalated strict invocation rejected an unrelated existing global field,
  `features.remote_connections`; global configuration was left unchanged.
- A strict `exec --ignore-user-config` retry started and completed session
  `01a16d9d-0aaf-7141-b00f-745cc5de63f6` without a config parsing error.
  This does not prove project role discovery or that role instructions loaded.
- Its available native `collaboration.spawn_agent` tool exposed no `agent_type`
  selection or configured-role discovery. The session reported zero delegations;
  its local inspection command was rejected by execution policy. Neither configured
  role was observed discovered or invoked. No implementation/review agent IDs exist.
- The inspected JSONL contains thread start, coordinator messages and turn completion,
  with no subagent call/completion events. Combined with the exposed tool schema,
  this supports a blocked result, not proof of successful execution. It does not
  establish capabilities of other Codex clients or future sessions.

Local diagnostic files are ignored under `.cache/codex-smoke/`: `events.jsonl`,
`events-escalated.jsonl`, `events-clean.jsonl`, `final.txt` and `prompt.json`.
They are local evidence, not portable tracked attestations. The prompt rendering
shows root instructions, which alone is not role discovery evidence.

The completed retry reported 40,573 input tokens (24,832 cached), 290 output tokens,
and 29 reasoning output tokens. These counters cover that coordinator turn only;
no subagent token cost was measured. Failed attempts can also consume resources.
Two concurrent threads cap concurrency, not cumulative token cost. Narrow scopes,
sequential handoff, trivial-change exemptions and the bounded correction cycle
reduce cost without promising a fixed monetary limit.

To complete validation, use a trusted native client exposing configured agent
selection; repeat the same disposable task with no production edits, capture both
actual spawn/completion events and identities, inspect reviewer actions for writes,
and independently verify the scratch result. Until then, configured roles are
present on disk but runtime discovery/invocation remains unverified. Do not replace
this check with two default agents renamed implementer and reviewer.
