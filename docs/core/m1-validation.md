# M1 implementation and validation record

Date: 2026-10-22. Baseline: freshly fetched `origin/main` at `d2affe0`.
The prior principal-review fixes were present as uncommitted workspace changes,
not on that remote commit, and were retained. The user-provided M1 `task.md`
was read as the implementation aim and left untouched.

## Delivered implementation

| Module | Responsibility |
| --- | --- |
| `packages/python/second_brain_core/application.py` | Instance composition, strategy dispatch and the atomic transaction boundary |
| `packages/python/second_brain_core/boundary.py` | Trusted instance/principal bindings, canonical ingress/output and structured errors |
| `packages/python/second_brain_core/access.py` | Deny-by-default resource selection and aggregate expectations |
| `packages/python/second_brain_core/domain.py` | Registered metadata/predicate rules and dedicated record integrity validators |
| `packages/python/second_brain_core/operations.py` | Node/Relation creation and read strategies; resource-specific replay and receipt verification |
| `packages/python/second_brain_core/receipts.py` | Durable receipts, request binding, key scopes and authorized replay |
| `packages/python/second_brain_core/repository.py` | Canonical record encoding and pinned, validated committed snapshots |
| `packages/python/second_brain_core/bootstrap.py` | Explicit trusted fixture initialization |
| `packages/python/second_brain_core/git_store.py` | Explicit-path Git plumbing, isolated candidate tree/commit construction and conditional publication |
| `packages/python/second_brain_core/locking.py` | Windows/POSIX file-lock strategies and lock lifecycle |
| `packages/python/second_brain_core/codec.py` | Strict UTF-8 JSON-subset YAML metadata and lossless Markdown body encoding |
| `tests/test_core_m1.py` | Real disposable repositories, application-boundary conformance and recovery checks, independent Ajv output validation |

Generated contracts used: `Node`, `NodeRevision`, `NodeTypeDefinition`, `Cluster`,
`Membership`, `Relation`, `RelationTypeDefinition`, `NodeCreate`, `RelationCreate`,
`NodeRead`, `RelationRead`, `BatchRequest`, `OperationResult`, `CommittedReceipt`,
`ReadResult`, `DomainError` and their generated reference/value types.
`ContractValidator` supplies offline Draft202012Validator/FormatChecker validation,
generated root parsing and canonical output serialization. Local registered metadata
uses the same independent Python JSON Schema engine; actual successful receipt/read
outputs are additionally passed through the existing independent Node Ajv adapter.

One managed ref is the decision boundary. The complete supported after-state,
receipt and validated request are written into an isolated candidate commit before
one expected-old ref update. Exact authorized retry recovers the original receipt;
changed payloads, stale generations and reused constituent keys do not partially
execute. Unpublished objects are ignored; corrupt/missing committed state fails closed.
See [usage and guarantees](m1.md) for the supported subset and precise key/digest scope.

## Executed validation

| Command/check | Actual local result |
| --- | --- |
| `python -m pytest -q --tb=short` | 260 passed in 206.23 seconds, including 38 M1 cases |
| Final cross-Cluster regression | 1 passed, 38 deselected in 9.12 seconds |
| Final retry regression, expanded with a separate isolated Python interpreter | 1 passed, 38 deselected in 8.69 seconds |
| `python -m tools.generate_contracts --check` | 24 artifacts match; no extras |
| `python -m tools.validate_contracts` | 8 schemas, 717 offline references, 133 fixtures/round-trips passed |
| `npm run typecheck` | Passed |
| `npm run parity` | Passed, 24 shared illustrative cases |
| `python -m tools.validate_examples` | Passed, including 276 portable document links |
| Fresh contract bundle build and integrity check at `.cache/m1-contracts` | Passed, 37 payload files |
| Ruff lint and format checks | Passed |
| Diff whitespace check excluding untouched user task | Passed |

The complete run used the final production implementation. The last cross-Cluster
test and the expanded subprocess-restart assertion were then added and run separately;
the final M1 file contains 39 collected cases. No production code changed afterward.
The complete run also retains existing clean generation, source-only/dist-free build,
isolated distribution consumer and independent jsonschema/Ajv parity checks.

An initial documentation check found the not-yet-written report link; the completed
documentation check passed after this report was added. The unfiltered whitespace
check reports four pre-existing Markdown hard-break spaces in the user-provided
`task.md`; that file was not modified by this implementation. No manual testing or
hosted CI execution is claimed. These checks establish their exercised cases, not
exhaustive correctness or filesystem durability.

## Strategy refactor validation

The subsequent refactor reduced `application.py` from 764 to 178 lines by composing
the collaborators listed above. Fixed Node/Relation strategy maps replace operation
condition chains; the same creation strategies own receipt verification and replay
authorization. Dedicated record validators replace the domain kind chain. Windows
and POSIX locking use separate strategies, and the Git adapter separates binary
command I/O, tree construction, commit creation and ref publication. Public package
imports, canonical contracts and persisted formats are unchanged.

The final complete suite passed **264 tests in 235.03 seconds**, including 42 M1
cases. Three added regressions exercise valid-but-unsupported operation rejection,
explicit Node revision/Cluster selection, and binary blob preservation without ref
publication. Generation still matches all 24 artifacts; production validation still
passes 8 schemas, 717 references and 133 fixtures/round-trips. TypeScript, Ruff lint,
formatting, documentation links and the scoped whitespace check also passed.
No hosted multi-OS execution is claimed.

## Limits and next slice

Only private active Clusters, one Membership per Node, initial create revisions and
current committed reads are supported. Runtime grant snapshots come from a trusted
host/bootstrap; there is no transport identity provider or policy administration.
General YAML/frontmatter import, human-file synchronization, full governance,
history enumeration, indexing, MCP and editor integration remain absent.

Full-tree/receipt scans trade throughput for simple M1 correctness. Git hashes
and conditional ref updates do not certify power-loss durability, physical deployment
isolation or authenticity against a trusted repository administrator. Receipts and
validated requests are retained indefinitely for this development scope, pending O3.
Windows tests do not prove the POSIX lock branch; the existing three-OS CI matrix
will run the same tests when hosted CI executes.

No canonical contract changes, manually edited generated artifacts, added dependency
or new Owner policy decision was necessary. O1–O4 remain unresolved and unsupported
paths are restricted accordingly. Recommended next slice: authorized Node update
with immutable historical content and revision CAS, then explicit reconciliation
after O1's synchronization/handoff requirements are settled.
