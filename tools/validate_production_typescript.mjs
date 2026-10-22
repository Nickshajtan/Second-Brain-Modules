// Independent Ajv oracle. No generated types or Python verdicts used to validate.
import {loadContracts} from '../packages/typescript/validation.mjs';
import Ajv2020 from 'ajv/dist/2020.js';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = async file => JSON.parse(await readFile(path.join(root, file), 'utf8'));
export async function productionVerdicts(cases) {
  const {validators} = await loadContracts(root);
  return cases.map(item => {
    const before = JSON.stringify(item.instance);
    const valid = validators[item.schema](item.instance);
    if (JSON.stringify(item.instance) !== before) throw Error(`${item.name}: mutated input`);
    if (valid !== item.valid) throw Error(`${item.name}: unexpected Ajv verdict`);
    return {name: item.name, valid};
  });
}
export async function compatibilityVerdicts() {
  const suite = await read('tests/fixtures/contracts/compatibility.json');
  const ajv = new Ajv2020({strict: true, coerceTypes: false, useDefaults: false, removeAdditional: false});
  return suite.cases.map(item => ({name: item.name, valid: ajv.validate(suite.schemas[item.schema], item.instance)}));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.stdout.write(JSON.stringify(process.argv.includes('--compatibility') ? await compatibilityVerdicts() :
    await productionVerdicts(await read('tests/fixtures/contracts/v1.json'))) + '\n');
}
