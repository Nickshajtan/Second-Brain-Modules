# Domain capability authority

The [operation catalogue](operations-catalog.md) remains the semantic operation catalogue. The [M1.2 coverage matrix](../contracts/contract-coverage-matrix.md) is its single implementation/structural inventory, including slash-expanded operations and missing dedicated APIs. There is no second competing operation definition here.

[Accepted requirements](accepted-decisions.md) define intended boundaries; [invariants](invariant-register.md) define semantic obligations; [state machines](state-machines.md) define confirmed transitions and their unresolved portions. The [API conventions](../contracts/api-catalog.md) define wire interpretation. Canonical schemas define shape only; generated types describe that shape; runtime strategies implement a finite advertised subset; tests cover only named cases; deployment remains separately verified.

Node, NodeRevision, Cluster, Membership, Collection, Relation, RelationRevision, Asset, ExternalReference, registries, Proposal, Review, Approval, grant, disposal, snapshot, authoring and transaction/event families are separately inventoried. None is complete merely because a generated union includes its record.
