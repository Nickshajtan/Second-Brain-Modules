import type {ExampleKnowledgeNode} from './generated/node.js';
import type {ExampleCluster} from './generated/cluster.js';

declare const node: ExampleKnowledgeNode;
const title: string = node.title;
declare const cluster: ExampleCluster;
const description: string | null | undefined = cluster.description;
// Static types supplement canonical runtime validation; numeric bounds require Ajv.
// @ts-expect-error title is required and cannot be null
const invalidTitle: ExampleKnowledgeNode['title'] = null;
// @ts-expect-error class is a closed enum
const invalidClass: ExampleCluster['class'] = 'unregistered';
void [title, description, invalidTitle, invalidClass];

import type {OperationRequest} from './generated/v1/operations.js';
import type {Node, Relation} from './generated/v1/knowledge.js';
import type {ContractValidators} from './validation.mjs';
declare const operation: OperationRequest;
if (operation.operation === 'node.create') {
  const body: string = operation.payload.content.body;
  // @ts-expect-error node.create has no relation payload
  operation.payload.relation;
  void body;
}
declare const productionNode: Node;
// @ts-expect-error independent Relations are not mutable state embedded in Node
productionNode.relations;
// @ts-expect-error optional properties cannot be explicitly undefined
const badMetadata: Node['content'] = {...productionNode.content, metadata_schema_id: undefined};
// @ts-expect-error a Relation endpoint must be a Node, never an Asset
const badEndpoint: Relation['source'] = {instance_id: 'x', id: 'y', resource_kind: 'asset'};
declare const contracts: ContractValidators;
const checked: OperationRequest = contracts.validate('operations', {});
void [badMetadata, badEndpoint, checked];

// M1.2 immutable snapshots remain canonically checked at runtime.
import type {NodeRevision, RelationRevision} from './generated/v1/knowledge.js';
declare const relationRevision: RelationRevision;
const historicalPredicate: string = relationRevision.snapshot.predicate;
declare const nodeRevision: NodeRevision;
const historicalBody: string | undefined = nodeRevision.snapshot?.body;
if (operation.operation === 'node.create') {
  const allocatedNode: string | undefined = operation.payload.node_id;
  void allocatedNode;
}
// @ts-expect-error immutable Relation snapshot must retain exact Relation fields
const missingSnapshot: RelationRevision = {kind: 'relation_revision'};
void [historicalPredicate, historicalBody, missingSnapshot];

import type {NodeRevisionSnapshot} from './generated/v1/knowledge.js';
import type {HistoryBaseline} from './generated/v1/transaction.js';
declare const supplement: NodeRevisionSnapshot;
declare const historyBaseline: HistoryBaseline;
const recoveredBody: string = supplement.snapshot.body;
const sourceCommit: string | undefined = historyBaseline.source_commit;
// @ts-expect-error a snapshot supplement cannot point at a Relation revision
const wrongHistoryKind: NodeRevisionSnapshot['revision_ref']['resource']['resource_kind'] = 'relation';
void [recoveredBody, sourceCommit, wrongHistoryKind];
