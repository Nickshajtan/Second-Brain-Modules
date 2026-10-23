# M1.1 repository hygiene audit

Inspected 2026-10-23 at `ed356827de35bba5ea5cc97bb04577aafdb0f5bd`:
HEAD equals freshly fetched `origin/main`. Initial working changes: only the
user's replacement `task.md`; no nonignored untracked files. No tracked bytecode,
virtual environments, dependency installs or disposable build output were found.

| Path | Classification | Evidence | Action | Risk |
| --- | --- | --- | --- | --- |
| `packages/python/generated/`, `packages/typescript/generated/` | Tracked generated artifacts | Generator's exact 24-file inventory; current Git/submodule consumers and distribution tests | Keep tracked; generation alone owns changes | High if removed |
| `docs/architecture/examples/`, illustrative generated models | Historical contracts still consumed | ExampleValidator, parity corpus, generator and TS consumer fixtures use them | Keep; distinguish from production v1 | High if removed |
| `docs/architecture/decisions/`, `docs/research/` | Historical decision/evidence records | Linked ADR index, domain provenance and supersession register | Keep; add current implementation pointers to indexes | High if rewritten/deleted |
| `docs/domain/domain-model.md`, `operations-catalog.md` | Confirmed semantic baseline with historical status text | ADR-009/010 and Core M1 refer to these invariants | Keep; point to current implementation without changing semantics | High |
| `docs/contracts/README.md`, `distribution.md` | Active structural authority and delivery guidance | Runtime registry, isolated bundle and dist-free tests | Keep; document public strict JSON API | High |
| `README.md`, CI command lists | Current entry point with repeated development commands | Existing workflow runs independent lint/type/test commands | Link one engineering guide and shared local command | Low |
| `task.md` | User-authored active specification | Only initial Git modification; M1.1 task | Preserve unchanged | High if edited/deleted |
| `.cache/` | Ignored reproducible builds and development scratch | Existing ignore rule; previous local refactor scripts and bundle checks | Leave ignored; no deletion needed | Medium for unknown scratch |
| `.local/` | Ignored local user material | Not tracked; purpose not established by this task | Retain untouched | High if deleted |
| `.venv/`, `node_modules/`, `dist/` | Ignored provisioned environments/builds | Existing ignore rules and documented reproducible provisioning | Retain local copies; keep ignored | Low |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Ignored test/tool caches | Existing rules; no tracked instances | Keep ignored | Low |
| `.mypy_cache/`, `.pyright/`, `.coverage.*`, `*.tsbuildinfo`, swap files | Potential local outputs | Missing explicit ignore coverage before M1.1 | Add narrow patterns; do not ignore source/generated trees | Low |
| `.env*`, `config/`, `.brain/`, `knowledge/` | Instance/private local state | Existing root rules and module/instance boundary | Retain rules and `.env.example` exception | High if exposed |

Before/after: 141 baseline tracked files plus 9 intentional new first-party files
(150 tracked-plus-new working files); no files removed or relocated. No deletion of old reports, fixtures,
research, user notes or generated consumers is justified. New engineering source
and documentation are intentional additions, not cleanup targets. Ignore additions
cover local outputs only; canonical schemas, test fixtures and generated models
remain visible/tracked. Future dist-free Git requires the existing delivery policy
and migration gates; this task does not remove generated artifacts.

Initial quality baseline: existing Ruff lint/format checks pass (26 handwritten
Python files); probing B/SIM/C4/PIE/RET/RUF reports three loop-closure warnings and
20 `dict()` style findings. The closures are invoked immediately, so this is a
maintainability finding, not a reproduced late-binding runtime failure. No existing
Pyright or JS lint gate exists. The preceding M1 report records 264 passing tests;
M1.1 reruns the complete final suite rather than assuming that historical result.
