# Second Brain — Phase 1.1: Lean Architecture Validation

**Status:** Research and design validation  
**Repository:** `Nickshajtan/Second-Brain-Modules`  
**Objective:** Reduce architectural uncertainty and implementation cost before production contracts and Core development.

## 1. Context

Phase 1 produced the domain model, glossary, operations catalog, reuse assessment, Obsidian integration assessment, architecture alternatives, and four proposed PoCs (P01–P04).

The research phase is accepted as a useful baseline.

However, the proposed experimental phase is disproportionately expensive relative to the decisions we currently need to make.

We do not want to deploy multiple external systems merely to determine whether an architecture is reasonable.

**This task replaces the four-PoC plan with a narrow, evidence-first feasibility assessment.**

The goal is to make architectural decisions, not to demonstrate production readiness.

## 2. Hard constraints

1. **Do not implement production functionality.**
2. **Do not deploy Basic Memory, Cognee, Graphiti, OpenFGA or other complete platforms.**
3. **Do not require Docker, VPS, cloud infrastructure or external databases.**
4. **Do not call paid LLM APIs or use model inference as part of tests.**
5. **Do not install Obsidian plugins or modify the owner's actual vault.**
6. **Do not add dependencies unless a minimal experiment is demonstrably necessary.**
7. **Do not run broad integration, load, performance or crash-test suites.**
8. **Do not modify previously accepted business requirements without documenting the proposed change.**
9. **Do not introduce generalized frameworks, workflows or abstractions to support this research task.**
10. **Do not create an implementation backlog disguised as a research deliverable.**

Prefer existing Phase 1 evidence, official documentation, source inspection, reasoning from concrete fixtures, and small executable examples.

No new internet research is required unless an essential architectural question remains unanswered by the available evidence.

### Budget

- Target: one focused research pass.
- Maximum: one minimal local spike, only if static analysis cannot resolve a decision.
- The spike must use existing tooling wherever possible.
- No paid inference.
- No large dependency installations.
- No infrastructure deployment.

If a question cannot be resolved within these constraints, mark it **UNVERIFIED** and describe the smallest future experiment that would settle it.

Do not expand the scope to eliminate every uncertainty.

## 3. Confirmed architectural constraints

Treat the following as established requirements:

- Second Brain Core is passive and agent-independent.
- Canonical knowledge uses Git-backed Markdown/YAML.
- Obsidian is intended as a first-class human authoring environment.
- AI agents interact with Second Brain **exclusively through authenticated MCP**.
- Agent environments must not access canonical files, Git history, secrets or private indexes directly.
- Physical isolation is a deployment responsibility, using an isolated container, VM, VPS or equivalent boundary.
- Core enforces capabilities and cluster-specific policies.
- Shared and multi-cluster protection are distinct concepts.
- Relations are independent, Git-versioned domain entities.
- Context compilation and token budgeting belong to the external agent harness.
- Background processing, AI-based review, cleanup and freshness evaluation remain outside Core.
- Production contracts use the existing JSON Schema 2020-12 toolchain.
- Existing confirmed business/domain decisions remain authoritative unless the owner explicitly changes them.

Do not reinterpret MCP as a security sandbox. Evaluate the authenticated API boundary and OS/deployment isolation separately.

## 4. Required assessment

### A. Obsidian feasibility — highest priority

Determine whether the confirmed domain model can support a reasonable native Obsidian workflow without a large custom plugin.

Evaluate only these scenarios:

**A1. Human Node editing**

A person creates or edits a Markdown Node using Obsidian Properties and the Markdown editor.

Core is not necessarily running.

Determine the minimal reconciliation requirements and whether standard files remain sufficient.

**A2. Standalone Relations**

A Relation belongs to its own Cluster and has an independent revision.

Evaluate:

- Standalone Markdown Relation notes with links to endpoint Nodes.
- Native Obsidian Graph and backlink behavior.
- Editing Relations through Properties.
- Whether two-hop navigation is an acceptable initial compromise.
- Whether an Obsidian sidebar is genuinely necessary.

Do not implement a sidebar.

**A3. Logical Collections**

A Node can appear in multiple private Collections without creating physical duplicates.

Evaluate whether ordinary Markdown Collection notes containing Node links can represent this adequately.

Do not design a virtual filesystem.

**A4. Protected revisions**

Human drafts and approved Shared revisions must remain distinguishable.

Identify the smallest workable representation and the limitations of offline editing.

#### Expected result

A clear answer:

- **NATIVE:** Obsidian can handle the workflow directly.
- **THIN ADAPTER:** A small command, projection or plugin extension is needed.
- **PLATFORM GAP:** The workflow is impractical without substantially changing the architecture.

Include the reason and supporting evidence for each classification.

### B. Storage and transaction feasibility

Review the proposed Git-backed transaction architecture without implementing it.

Focus on one scenario:

> Create two Nodes and one Relation atomically; preserve the previous committed state if the operation fails.

Determine:

1. What guarantees Git already provides.
2. What guarantees Git does not provide.
3. Which responsibilities require a durable application journal or equivalent mechanism.
4. Whether canonical authority can be simplified without violating offline Obsidian editing.
5. Whether a minimal single-writer design is sufficient initially.

Distinguish:

- Atomicity of committed Core state.
- Visibility of raw working-directory files in Obsidian.
- Durability after process crash.
- Durability after OS or storage failure.

These are not equivalent guarantees.

Do not implement a crash matrix.

**Important:** If exact multi-resource atomicity creates disproportionate complexity, propose a simpler domain/storage design that preserves the required user-visible guarantees.

A reasoned architecture with known limitations is acceptable at this stage.

### C. Authorization and MCP boundary

Evaluate the simplest implementable security architecture given that agents have no direct filesystem access.

Assess:

- Authenticated MCP ingress.
- Principal binding and capability enforcement.
- Cluster-scoped policies.
- Non-discovery of inaccessible resources.
- Owner administrative access.
- External service identities.
- Container/VM/VPS isolation assumptions.

Compare only:

1. A small custom authorization implementation using existing primitives.
2. PyCasbin as an embedded policy evaluator.

Do not evaluate OpenFGA further unless the current domain model demonstrably requires it.

Do not deploy infrastructure or simulate hostile containers.

Provide a **deployment security checklist** rather than an executable penetration-test plan.

### D. Basic Memory adoption decision

Use the existing upstream evidence from Phase 1.

Determine whether Basic Memory should be:

- Adopted as a bounded indexing/search dependency.
- Retained as an optional future adapter.
- Rejected for the initial version in favor of SQLite FTS5 and existing Markdown tooling.

The primary criterion is:

**Does Basic Memory remove more necessary implementation complexity than its integration adds?**

Consider its release maturity, identity model, relation semantics, dependency/runtime footprint, licensing and read-only integration.

Do not install or run Basic Memory.

Do not repeat the full tool-market assessment.

### E. Approved graph semantics

Resolve or narrow this specific architectural question:

> Node content and Relations have independent revisions. What exactly does an approved Shared knowledge snapshot guarantee?

Compare only:

1. Approved Node revision, with Relations resolved under current authorized graph state.
2. Approved Node revision plus explicitly selected Relation revisions.
3. A larger immutable graph snapshot.

Assess consistency, complexity and expected user behavior.

Prefer the smallest semantics that satisfy our confirmed Shared/approval requirements.

Do not design an immutable snapshot engine without justification.

## 5. Architecture simplification mandate

Actively search for unnecessary complexity in the current documents.

For each proposed simplification, identify:

- The requirement it preserves.
- The abstraction or component it removes.
- The trade-off introduced.
- Whether the simplification is reversible.

Prioritize removal of unnecessary infrastructure, duplicate indexes, generalized workflows, extra API surfaces, custom Obsidian UI and premature extensibility.

Do not recommend a dependency merely because it implements a similar feature.

## 6. Optional minimal spike

A spike is permitted **only if**:

1. A critical architectural decision cannot be resolved from existing evidence.
2. The result could change the recommended design.
3. The experiment is small, deterministic and offline.
4. No external service, plugin installation or paid model is required.
5. The code remains outside production modules.

Maximum one spike.

Prefer a self-contained Python fixture demonstrating a narrow storage/transaction or Relation representation invariant.

If no such experiment is essential, perform **zero spikes**.

## 7. Deliverables

Create or update a compact set of Markdown documents:

### `docs/research/phase-1-1/architecture-decision.md`

The primary document.

Include:

- Recommended architecture.
- Justification.
- Changes relative to Phase 1.
- Accepted compromises.
- Critical remaining uncertainties.
- Clear **GO / CONDITIONAL GO / NO-GO** recommendation.

### `docs/research/phase-1-1/obsidian-fit.md`

Concise assessment of A1–A4.

Include the minimum necessary Obsidian integration surface and whether a custom plugin is needed for the initial version.

### `docs/research/phase-1-1/simplification-register.md`

A table of proposed simplifications with benefit, cost, risk and reversibility.

### `docs/research/phase-1-1/open-decisions.md`

Only owner-level architectural decisions that genuinely cannot be inferred from the confirmed requirements.

Do not repeat technical implementation choices that can safely be delegated to an engineer.

Aim for no more than five owner decisions.

## 8. Existing document reconciliation

Read the current Phase 1 artifacts and previous architecture documents.

Do not rewrite the entire specification.

If Phase 1.1 changes a recommendation, record:

- Original assumption.
- New recommendation.
- Supporting evidence.
- Affected document.
- Whether an ADR amendment is necessary.

Preserve all confirmed business decisions.

Do not silently promote an analyst recommendation into an owner-approved requirement.

## 9. Acceptance criteria

The task is complete when:

- We can choose the initial Knowledge Foundation architecture.
- We understand whether Obsidian can remain our main human editor.
- We know the minimal MCP and authorization boundary.
- We have a credible Git/Markdown consistency strategy with explicitly bounded guarantees.
- We know whether Basic Memory is worth integrating initially.
- We have a proposed interpretation of approved Node/Relation state.
- Remaining unknowns are explicitly identified without requiring full-system prototypes.
- No production code, deployment, paid inference or unnecessary dependencies were introduced.

A technically justified **UNVERIFIED** result is better than an expensive demonstration or an unsupported claim.

## 10. Final response format

Provide a short executive summary:

1. **Recommended architecture:** one paragraph.
2. **What we should reuse:** concrete components.
3. **What we must build:** genuinely custom domain responsibilities.
4. **What we should drop or defer:** unnecessary complexity.
5. **Obsidian verdict:** native editor, thin adapter or platform mismatch.
6. **Critical unresolved decisions:** maximum five.
7. **Next implementation slice:** the smallest useful vertical slice, without beginning implementation.

**Do not implement the next slice during this task.**

The objective is to make the next engineering decision cheaper and better informed — not to obtain experimental certainty about every future failure mode.