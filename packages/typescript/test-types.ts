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
