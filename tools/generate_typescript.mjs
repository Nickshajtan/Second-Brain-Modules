import {compileFromFile} from 'json-schema-to-typescript';
import {mkdir, writeFile} from 'node:fs/promises';
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
