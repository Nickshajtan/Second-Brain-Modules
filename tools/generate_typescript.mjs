import {compileFromFile} from 'json-schema-to-typescript';
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const destination = path.resolve(process.argv[2] ?? path.join(root, 'packages/typescript/generated'));
await mkdir(destination, {recursive: true});
for (const name of ['node', 'cluster']) {
  const input = path.join(root, 'docs/architecture/examples', `${name}.schema.json`);
  const output = await compileFromFile(input, {
    cwd: path.dirname(input),
    $refOptions: {resolve: {http: false}},
    style: {singleQuote: true},
  });
  await writeFile(path.join(destination, `${name}.d.ts`), output.replaceAll('\r\n', '\n'));
}
const registry = JSON.parse(await readFile(path.join(root, 'contracts/registry/v1.json'), 'utf8'));
await mkdir(path.join(destination, 'v1'), {recursive: true});
for (const entry of registry.schemas) {
  const input = path.join(root, entry.path);
  const output = await compileFromFile(input, {
    cwd: path.dirname(input), $refOptions: {resolve: {http: false}},
    style: {singleQuote: true}, unknownAny: true,
  });
  await writeFile(path.join(destination, 'v1', `${entry.name}.d.ts`), output.replaceAll('\r\n', '\n'));
}
await writeFile(path.join(destination, 'v1', 'index.d.ts'),
  registry.schemas.map(e => `export type * as ${e.name} from './${e.name}.js';`).join('\n') + '\n');
