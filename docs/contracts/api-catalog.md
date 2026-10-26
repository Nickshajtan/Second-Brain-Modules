# API catalogue and consistency rules — M1.2

The [coverage matrix](contract-coverage-matrix.md) is the exact operation inventory. The [semantic catalogue](../domain/operations-catalog.md) supplies intended operation effects; [production mapping](operations.md) describes existing requests. This page defines shared conventions, not a competing list or generic operation interpreter.

| Concern | Current contract / required evolution |
|---|---|
| Identity | Stable entity UUID is separate from request UUID, path/title and Git object identity. NodeCreate accepts explicit `payload.node_id`; legacy omission intentionally allocates `request_id`. Relation creation already has independent `payload.relation.id`. New producers supply Node ID; copy/fork/import need explicit allocations/remaps before activation. |
| Versions | `schema_version` and `operation_version` are explicit 1.0.0; exact immutable IDs freeze at release. Unsupported versions never fetch/migrate. See compatibility amendment. |
| Instance | Request instance is checked against trusted host instance; cross-instance resource refs carry explicit scope. Caller JSON cannot establish trusted identity, grants or Owner. |
| Mutation ingress | Explicit operation discriminator/version, request identity, idempotency key and expectations; batch adds one expected generation and transaction identity. Standalone requests acquire the same business boundary. No nested partial commits. |
| Targets / CAS | Exact resource and logical revision references; batch generation fences registry/policy/membership too. Current authorization/CAS checked at publication. Missing expectation is not license to bypass required semantic guards. |
| Results | Mutation CommittedReceipt identifies transaction/request/result/resources/revisions and generation. ReadResult identifies generation and KnowledgeRecord list. **ReadResult cannot contain governance/control records**: those future read APIs require dedicated typed response families; listing/search/cursor/counts likewise need exact result contracts. |
| Errors | Canonical DomainError vocabulary, sanitized messages; inaccessible existence is concealed. Unknown supported-version operation fails finite dispatch. No revision/Git/path leak. |
| Read authority | Current resource permission is distinct from history/list/search; selected approved view is not blanket history. Current policy rechecked before replay/delivery; relation plus endpoints needed. |
| Transfer authority | Source disclosure plus destination admission; imported grants never trusted; provenance itself may be sensitive. |
| Transactions | One instance, all-or-none managed-ref CAS. Prepared objects invisible. Exact retry validates durable original effects and current authority; conflicting normalized request rejects. M2.1 resolves immutable original committed effects/admission; explicit legacy backfill precedes future M2.2/M2.3 updates. |
| Selection | Node head, immutable candidate, Cluster Membership approved pointer and publication snapshot are distinct. O2/O4 not decided by optional fields. |
| Evolution | Structural and behavioral compatibility assessed separately, no silent read-time migration. New frozen versions require explicit registry/bundle/persisted-record migration support. |

Host `Core.bootstrap` and `Core.generation` are trusted Python APIs, not caller-selectable wire operations. Bootstrap is provisioning-only and cannot substitute for Cluster/grant administration. No MCP/HTTP server, scheduler, event subscription runtime or external fetcher is implemented.
