import { defineConfig } from '@hey-api/openapi-ts';

import { openApiSources } from './scripts/apiSources.mjs';

const plugins = [
  '@hey-api/typescript',
  '@hey-api/client-fetch',
  {
    name: '@hey-api/sdk',
    operations: {
      strategy: 'flat',
    },
  },
] as const;

export default defineConfig(openApiSources.map(({ input, output }) => ({
  input,
  output,
  plugins,
})));
