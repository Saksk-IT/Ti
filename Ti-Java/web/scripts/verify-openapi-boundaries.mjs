import { createHash } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';
import { resolve, relative } from 'node:path';

import {
  forbiddenOpenApiTokens,
  openApiSources,
  publicBankRuntimeOperations,
} from './apiSources.mjs';

const projectRoot = resolve(import.meta.dirname, '..');
const generatedRoot = resolve(projectRoot, 'src/api/generated');

function operationCatalog(spec) {
  return Object.entries(spec.paths ?? {}).flatMap(([path, pathItem]) =>
    Object.entries(pathItem ?? {})
      .filter(([, operation]) => operation && typeof operation === 'object')
      .filter(([, operation]) => typeof operation.operationId === 'string')
      .map(([method, operation]) => ({
        id: operation.operationId,
        method: method.toUpperCase(),
        migration: operation['x-ti-migration'],
        path,
      })),
  );
}

function operationKey(operation) {
  return `${operation.method} ${operation.path} ${operation.id}`;
}

function assertExactSet(actual, expected, label) {
  const actualSet = [...actual].sort();
  const expectedSet = [...expected].sort();
  if (JSON.stringify(actualSet) !== JSON.stringify(expectedSet)) {
    throw new Error(`${label} drifted:\nactual=${actualSet.join(',')}\nexpected=${expectedSet.join(',')}`);
  }
}

for (const source of openApiSources) {
  const absolutePath = resolve(projectRoot, source.input);
  const normalizedSelection = `${source.input}|${source.output}`.toLowerCase();
  if (forbiddenOpenApiTokens.some((token) => normalizedSelection.includes(token))) {
    throw new Error(`Forbidden OpenAPI source selected: ${source.input}`);
  }

  const raw = await readFile(absolutePath);
  const actualSha = createHash('sha256').update(raw).digest('hex');
  if (actualSha !== source.sha256) {
    throw new Error(`OpenAPI source drifted: ${source.input} (${actualSha})`);
  }

  const operations = operationCatalog(JSON.parse(raw.toString('utf8')));
  assertExactSet(
    operations.map(operationKey),
    source.operations.map(operationKey),
    `Operation set in ${source.input}`,
  );

  for (const operation of operations) {
    if (
      operation.migration?.status !== 'migrated' ||
      operation.migration?.productionCutover !== false
    ) {
      throw new Error(
        `Operation ${operation.id} is not migrated with production cutover disabled`,
      );
    }
  }
}

for (const operation of publicBankRuntimeOperations) {
  if (operation.method !== 'GET') {
    throw new Error(`Runtime public-bank operation is not read-only: ${operationKey(operation)}`);
  }
}

const generatedNamespaces = (await readdir(generatedRoot, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name);
assertExactSet(
  generatedNamespaces,
  openApiSources.map((source) => source.id),
  'Generated client namespaces',
);

const facadePath = resolve(projectRoot, 'src/api/facade/publicBankFacade.ts');
const facade = await readFile(facadePath, 'utf8');
const sdkImport = facade.match(
  /import\s*\{(?<symbols>[^}]*)\}\s*from\s*['"]@\/api\/generated\/phase4aPublicBank\/sdk\.gen['"]/u,
);
if (!sdkImport?.groups?.symbols) throw new Error('Public-bank facade SDK import was not found.');

const importedSdkSymbols = sdkImport.groups.symbols
  .split(',')
  .map((symbol) => symbol.trim())
  .filter(Boolean);
const expectedSdkSymbols = publicBankRuntimeOperations.map((operation) => operation.sdkExport);
assertExactSet(importedSdkSymbols, expectedSdkSymbols, 'Public-bank facade SDK imports');

for (const symbol of expectedSdkSymbols) {
  const calls = facade.match(new RegExp(`\\b${symbol}\\s*\\(`, 'gu')) ?? [];
  if (calls.length !== 1) {
    throw new Error(`Expected exactly one runtime call to ${symbol}; found ${calls.length}.`);
  }
}

const sourceManifest = await readFile(
  resolve(projectRoot, 'src/api/contracts/sourceManifest.ts'),
  'utf8',
);
assertExactSet(
  [...sourceManifest.matchAll(/legacy_[a-f0-9]+_(?:get|post|put|patch|delete)/gu)]
    .map((match) => match[0]),
  publicBankRuntimeOperations.map((operation) => operation.id),
  'Runtime operationId manifest',
);

async function sourceFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const absolutePath = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      if (absolutePath.startsWith(generatedRoot)) continue;
      files.push(...await sourceFiles(absolutePath));
    } else if (entry.isFile() && /\.(?:ts|vue)$/u.test(entry.name)) {
      files.push(absolutePath);
    }
  }
  return files;
}

for (const file of await sourceFiles(resolve(projectRoot, 'src'))) {
  const content = await readFile(file, 'utf8');
  if (
    file !== facadePath &&
    /api\/generated\/phase4aPublicBank\/sdk\.gen/u.test(content)
  ) {
    throw new Error(`Generated public-bank SDK imported outside facade: ${relative(projectRoot, file)}`);
  }
}

console.info(
  'OpenAPI boundaries verified: exact Phase 3/4A sources, five GET runtime operations, production cutover disabled.',
);
