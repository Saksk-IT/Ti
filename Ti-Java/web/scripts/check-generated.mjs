import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';
import { resolve, relative } from 'node:path';
import { promisify } from 'node:util';

import { openApiSources } from './apiSources.mjs';

const execute = promisify(execFile);
const projectRoot = resolve(import.meta.dirname, '..');

async function generatedSnapshot() {
  const snapshot = {};

  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries) {
      const absolutePath = resolve(directory, entry.name);
      if (entry.isDirectory()) await visit(absolutePath);
      else if (entry.isFile()) {
        const path = relative(projectRoot, absolutePath);
        snapshot[path] = createHash('sha256').update(await readFile(absolutePath)).digest('hex');
      }
    }
  }

  for (const source of openApiSources) await visit(resolve(projectRoot, source.output));
  return snapshot;
}

const before = await generatedSnapshot();
await execute(resolve(projectRoot, 'node_modules/.bin/openapi-ts'), [], {
  cwd: projectRoot,
  maxBuffer: 10 * 1024 * 1024,
});
const after = await generatedSnapshot();

if (JSON.stringify(before) !== JSON.stringify(after)) {
  throw new Error('Generated clients drifted; run npm run generate:api and commit the exact output.');
}

console.info('Generated clients are deterministic and current.');
