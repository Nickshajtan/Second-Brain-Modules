import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {productionVerdicts, compatibilityVerdicts} from './validate_production_typescript.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = async name => JSON.parse(await readFile(path.join(root, name), 'utf8'));
const ajv = new Ajv2020({strict: true, allErrors: true, validateFormats: true,
  coerceTypes: false, useDefaults: false, removeAdditional: false});
addFormats(ajv);
const validators = {};
for (const name of ['node', 'cluster']) {
  const schema = await read(`docs/architecture/examples/${name}.schema.json`);
  ajv.addSchema(schema, name);
}
for (const name of ['node', 'cluster']) validators[name] = ajv.getSchema(name);
const cases = await read('tests/fixtures/parity.json');
const results = [];
for (const item of cases) {
  const before = JSON.stringify(item.instance);
  const valid = validators[item.schema](item.instance);
  if (valid !== item.valid) throw new Error(`${item.name}: unexpected Ajv verdict`);
  if (JSON.stringify(item.instance) !== before) throw new Error(`${item.name}: mutated input`);
  results.push({name: item.name, valid});
}
const production = await productionVerdicts(await read('tests/fixtures/contracts/v1.json'));
const compatibility = await compatibilityVerdicts();
const expectedCompatibility = (await read('tests/fixtures/contracts/compatibility.json')).cases;
if (compatibility.some((r, i) => r.valid !== expectedCompatibility[i].valid)) throw Error('Compatibility verdict mismatch');
process.stdout.write(JSON.stringify(process.argv.includes('--production') ? production : results) + '\n');
