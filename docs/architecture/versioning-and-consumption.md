# Versioning and consumption

The entire repository is the reusable boundary. A Git submodule pins a repository
commit; directories inside it cannot be independently pinned gitlinks. No second
contract repository/submodule is required. Logical modules may later become ordinary
installable packages without splitting Git repositories.

```text
second-brain-personal/              # consumer repository
  knowledge/                       # consumer canonical Markdown/YAML + knowledge history
  config/                          # consumer workspace/policy/adapter configuration
  .brain/                          # consumer runtime DB, caches, audit, session artifacts
  vendor/
    second-brain-modules/           # one pinned Git submodule; reusable code only
```

Consumer command, run from the consumer root:

```text
git submodule add https://github.com/Nickshajtan/Second-Brain-Modules.git vendor/second-brain-modules
git submodule update --init --recursive
```

Commit the selected gitlink revision in the consumer. No checkout hook or installation
step may write knowledge/config/runtime data. Secret references may be in config;
secret values stay in host credential stores outside Git. Ignore sensitive host config
and `.brain/` as appropriate. Never put private state inside the submodule. Local
development commands below operate on fabricated examples only.

| Version | Meaning | Compatibility obligation |
|---|---|---|
| Repository release/tag | Whole shared code/tooling snapshot, proposed SemVer; 0.x may break | Tag alone does not prove two arbitrary schemas/instances interoperate; review exact manifest/contract support |
| Schema `$id` + schema_version | Immutable structural/semantic data contract resource | Exact registered IDs and tested producer/consumer directions; no silent network upgrade |
| Generated source | Projection of schema + locked generator/config | Source hashes and byte/file-set drift; Python/TS outputs from same snapshot |
| Application/runtime version | Future implementation of operations/state/recovery | Separately declares supported schema/operation/config versions; no runtime exists in this foundation |
| Entity revision | Consumer-owned object content revision | Never reset by code checkout; independent of code/schema version |
| HTTP/MCP binding version | Transport contract | Must preserve selected application behavior; does not replace domain schema version |

Each consumer can pin a different commit and upgrade independently without forks
or source edits. Before upgrade: inspect release notes and schema compatibility matrix,
back up coherent knowledge/control/runtime state, dry-run explicit migrations, then
activate matching code/config/schema set. The shared repository supplies migration
tools later; the consumer owns execution, backups and scheduling. No read-time migration
or install-time write. Rolling back code after new incompatible writes is insufficient:
restore a coherent snapshot or run a tested reverse migration.

Closed object schemas make optional new output fields potentially breaking for old
readers. Enum expansion, new defaults/nulls, constraint changes and behavior changes
require directional fixture and semantic review. A namespaced extension slot only
helps if already defined and safe in the older contract. Unknown security conditions
must reject, never be ignored. Versions of unrelated resources cannot be compared
numerically to establish compatibility.

Proposed deprecation policy remains current plus two supported minor releases (Q09),
with published removal dates and explicit migration guidance. Runtime support and
schema compatibility are not established by this illustrative 0.1.0 example. Production
schema namespace remains Q01 even though repository identity and MIT license now exist.

## Development without global dependencies

Use Python **3.12** and Node **22.19+** (CI uses 22.19.0). From this repository root:

```text
python -m venv .venv
```

Activate `.venv` using your shell (`.venv\Scripts\Activate.ps1` in PowerShell,
`source .venv/bin/activate` on macOS/Linux), then:

```text
python -m pip install --require-hashes -r requirements-dev.lock
npm ci --ignore-scripts --no-audit --no-fund
python -m tools.validate_examples
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
npm run typecheck
python -m tools.generate_contracts --check
```

Regenerate deliberately with `python -m tools.generate_contracts`; never edit generated
files. The checker stages results outside the source tree and compares bytes and the
full generated file set, including extra/untracked files; it ignores interpreter cache
files only. `npm run parity` prints the TS fixture verdicts; pytest compares them to
Python. Commands use Python/Node path APIs, not shell-specific separators or globs.

To update Python locks in a disposable environment with pip-tools 7.5.1:

```text
pip-compile --cache-dir .cache/pip-tools --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --output-file requirements-dev.lock requirements-dev.in
```

Review the full dependency diff and rerun generation/parity/drift. npm installs from
`package-lock.json`; use a deliberate `npm install --ignore-scripts` only when updating
it. No globally installed generator, provider SDK or production server is needed.
