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
