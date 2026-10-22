// Runtime adapter over Ajv2020; canonical schemas, not generated declarations, validate JSON.
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {readFile, readdir} from 'node:fs/promises';
import path from 'node:path';

export async function loadContracts(root, version = '1.0.0') {
  if (version !== '1.0.0') {
    throw Object.assign(new Error(`Unsupported contract version: ${version}`), {code: 'UNSUPPORTED_VERSION'});
  }
  const read = async file => JSON.parse(await readFile(path.join(root, file), 'utf8'));
  const registry = await read('contracts/registry/v1.json');
  if (registry.contract_version !== version) throw Error('Registry version mismatch');
  const ajv = new Ajv2020({strict: true, allErrors: true, validateFormats: true,
    coerceTypes: false, useDefaults: false, removeAdditional: false});
  addFormats(ajv);
  const ids = new Set(registry.schemas.map(e => e.id));
  const names = new Set(registry.schemas.map(e => e.name));
  if (ids.size !== registry.schemas.length || names.size !== registry.schemas.length) throw Error('Duplicate registry entry');
  const schemaRoot = path.resolve(root, 'contracts/schemas/v1');
  const actual = (await readdir(schemaRoot)).filter(n => n.endsWith('.schema.json')).sort();
  if (JSON.stringify(actual) !== JSON.stringify(registry.schemas.map(e => path.basename(e.path)).sort())) throw Error('Schema registry coverage mismatch');
  function checkRefs(value, base) {
    if (!value || typeof value !== 'object') return;
    if ('$ref' in value) {
      const target = new URL(value.$ref, base);
      target.hash = '';
      if (!ids.has(target.href)) throw Error(`Unpackaged schema reference: ${value.$ref}`);
    }
    for (const child of Object.values(value)) checkRefs(child, base);
  }
  for (const entry of registry.schemas) {
    if (path.dirname(path.resolve(root, entry.path)) !== schemaRoot) throw Error('Schema path escaped bundle');
    const schema = await read(entry.path);
    if (schema.$id !== entry.id) throw Error('Registry/schema identity mismatch');
    checkRefs(schema, schema.$id);
    ajv.addSchema(schema, entry.name);
  }
  const validators = Object.fromEntries(registry.schemas.map(e => [e.name, ajv.getSchema(e.name)]));
  return {
    version, validators,
    validate(family, payload) {
      if (payload?.schema_version !== undefined && payload.schema_version !== version) {
        throw Object.assign(new Error('Unsupported payload contract version'), {code: 'UNSUPPORTED_VERSION'});
      }
      if (!Object.hasOwn(validators, family)) throw Error(`Unknown contract family: ${family}`);
      const validator = validators[family];
      if (!validator(payload)) {
        throw Object.assign(new Error('Canonical contract validation failed'), {
          code: 'VALIDATION_FAILED', errors: validator.errors,
        });
      }
      return payload;
    },
  };
}
