export const forbiddenOpenApiTokens = ['phase4c', 'user-counts'];

export const openApiSources = [
  {
    id: 'phase3Authentication',
    input: '../openapi/phase3-authentication.openapi.json',
    output: 'src/api/generated/phase3Authentication',
    sha256: '7b014165a027ae3dbdbf8597ca910db8ab153b0437156f6d0fdd07985f348fab',
    operations: [
      { id: 'legacy_88d7dc05cdbb_get', method: 'GET', path: '/api/auth/login-methods' },
      { id: 'legacy_02366fc520ac_post', method: 'POST', path: '/api/login' },
    ],
  },
  {
    id: 'phase4aSubjectDirectory',
    input: '../openapi/phase4a-subject-directory.openapi.json',
    output: 'src/api/generated/phase4aSubjectDirectory',
    sha256: '8344f0173f523939abae203430cf92455d6240404e3d8ffe7a002507cadd2169',
    operations: [
      { id: 'legacy_d3cd12aaca90_get', method: 'GET', path: '/api/quiz/subjects' },
      { id: 'legacy_7fd9b0fc8111_get', method: 'GET', path: '/api/quiz/subjects/meta' },
    ],
  },
  {
    id: 'phase4aPublicBank',
    input: '../openapi/phase4a-public-bank.openapi.json',
    output: 'src/api/generated/phase4aPublicBank',
    sha256: '1f163574d9fb5b25d58df4a4a75ffca6b74b874dfbf66551cf46408d67110a34',
    operations: [
      { id: 'legacy_14642ebe7c1d_get', method: 'GET', path: '/api/public/banks' },
      {
        id: 'legacy_db1ac691d6fb_get',
        method: 'GET',
        path: '/api/public/banks/boards',
        runtime: true,
        sdkExport: 'legacyDb1Ac691D6FbGet',
      },
      {
        id: 'legacy_8cfb837021af_get',
        method: 'GET',
        path: '/api/public/banks/card/{source_type}/{bank_id}',
        runtime: true,
        sdkExport: 'legacy8Cfb837021AfGet',
      },
      {
        id: 'legacy_a473896ff467_get',
        method: 'GET',
        path: '/api/public/banks/hot',
        runtime: true,
        sdkExport: 'legacyA473896Ff467Get',
      },
      {
        id: 'legacy_b7e49e77a026_get',
        method: 'GET',
        path: '/api/public/banks/list',
        runtime: true,
        sdkExport: 'legacyB7E49E77A026Get',
      },
      {
        id: 'legacy_f3644c1474f3_get',
        method: 'GET',
        path: '/api/public/banks/summary',
        runtime: true,
        sdkExport: 'legacyF3644C1474F3Get',
      },
      { id: 'legacy_37cd782b28dc_get', method: 'GET', path: '/api/public/banks/{bank_id}' },
    ],
  },
];

export const publicBankRuntimeOperations = openApiSources
  .find((source) => source.id === 'phase4aPublicBank')
  .operations
  .filter((operation) => operation.runtime === true);
