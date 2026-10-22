import type {ValidateFunction} from 'ajv';
import type {DomainError} from './generated/v1/common.js';
import type {KnowledgeRecord} from './generated/v1/knowledge.js';
import type {GovernanceRecord} from './generated/v1/governance.js';
import type {ControlRecord} from './generated/v1/control.js';
import type {SnapshotRecord} from './generated/v1/snapshots.js';
import type {AuthoringInput} from './generated/v1/authoring.js';
import type {OperationRequest} from './generated/v1/operations.js';
import type {TransactionRecord} from './generated/v1/transaction.js';

export interface ContractFamilies {
  common: DomainError;
  knowledge: KnowledgeRecord;
  governance: GovernanceRecord;
  control: ControlRecord;
  snapshots: SnapshotRecord;
  authoring: AuthoringInput;
  operations: OperationRequest;
  transaction: TransactionRecord;
}
export interface ContractValidators {
  version: '1.0.0';
  validators: {[K in keyof ContractFamilies]: ValidateFunction<ContractFamilies[K]>};
  validate<K extends keyof ContractFamilies>(family: K, payload: unknown): ContractFamilies[K];
}
export function loadContracts(root: string, version?: string): Promise<ContractValidators>;
