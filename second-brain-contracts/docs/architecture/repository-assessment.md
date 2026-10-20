# Repository assessment

## Observed evidence

Inspection was read-only, on 2026-10-20, of the parent Second Brain vault and the Phase 1 workspace. This document records structural facts; it intentionally excludes personal titles, source filenames, message excerpts, and account identifiers. The paths below describe the inspected checkout, not portable runtime dependencies.

| Evidence in inspected checkout | Finding | Architectural consequence |
|---|---|---|
| `00 System/Brain.md` | Markdown notes and explicit relations are authoritative; raw conversations are not the brain | Curated knowledge is the target; transcript import is optional provenance |
| `00 System/Rules/Knowledge Shape.md` | Properties are lightweight and optional; separate notes need meaningful identity/lifecycle | Strict managed records must coexist with ordinary notes |
| `00 System/Rules/Relation Vocabulary.md`; `00 System/Relations/relations.json` | Existing small typed vocabulary, including `part-of`, `supports`, `contradicts`, `supersedes`; catalog version `0.1` | Reuse names after semantic review; do not invent an unrelated edge taxonomy |
| `00 System/Templates/Typed Relation Example.md` | Embedded `relations` with `type` and wikilink `target` | Managed node relations remain embedded; graph index is derived |
| `tools/add_relation.py` | Directly edits frontmatter using regex and validates relation names against the catalog | Legacy human tool; no revision, identity, or authorization boundary. Do not route agents through it |
| `00 System/Routing/Access Router.md` | Contextual least privilege; public/internal/personal/sensitive/secret | Align policy vocabulary; agent access never means vault-wide access |
| `00 System/Memory.md` | DROP / ARCHIVE / EXTRACT / PROMOTE triage | Import disposition is distinct from a managed node's lifecycle |
| `.gpt/inventory/README.md`, `statistics.json`, scripts | 861 source files; 1,012 conversations/groups; 34,267 messages; 35,276 graph nodes; 134 branch points | Keep original IDs and branches in provenance, not as canonical knowledge IDs |
| Phase 1 references and classifications | 2,764 file-token occurrences, 1,066 unresolved; classifications are keyword evidence | Unresolved is not proof of missing files; labels are untrusted curation suggestions |
| `build_inventory.py`, `write_reports.py`, `export_tables.py` | Offline inventory, JSONL outputs, normalized CSV/XLSX review; reviewed upstream utility dependency | Reuse adapter inputs; do not refactor the tools in this iteration |
| `inventory/obsidian-proposal.md` | Suggested archive/transcript projection | Preliminary proposal only; no requirement to retain every transcript in the curated vault |
| Parent checkout | Existing Obsidian workspace/graph changes and a deleted welcome note; untracked vault tooling and workspace | Existing user changes are outside this delivery; no Git cleanup or staging |

Inventory row shapes and source-preserving script behavior were inspected. No semantic reclassification, attachment extraction, transcript migration, or export execution was performed here. No established Python/TypeScript application package, service runtime, or production schemas were found in the inspected `tools`, `00 System`, and `.gpt` locations. This is a scoped observation, not a claim about other projects or external harness repositories.

## Assumptions and reconciliation

**User-stated:** Markdown/YAML, Git, Python core, TypeScript integration support, Draft 2020-12, modular monolith, independent transports, Windows/macOS/Linux, and an eventual reusable submodule. HCC is optional.

**Proposed:** a project-owned workspace root; stable UUID entity IDs; embedded node relations; revision history in Git with a transactional local commit journal; SQLite for disposable indexes and durable run/audit coordination in separate stores. Storage details must pass M3 crash tests before being accepted for production.

**Compatibility gaps requiring review:** existing notes lack required IDs/revisions and may have ambiguous wikilinks. Existing direct-edit tooling bypasses application controls. Catalog meanings such as “symmetric-ish” need precise rules before machine reasoning. There is no evidence that the vault already defines Stable/Stack membership or a managed schema namespace. These are new recommendations, not discovered conventions.

Adoption must be explicit and incremental: an unmanaged note is readable as user-authored source material, but cannot silently become a trusted managed node. Do not rewrite current notes or claim policy isolation from another program running as the same OS user. See Q02, Q03, Q04, and Q07 in the [question register](open-questions.md).
