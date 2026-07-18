export const apiSourceManifest = {
  phase3Authentication: {
    file: 'phase3-authentication.openapi.json',
    sha256: '7b014165a027ae3dbdbf8597ca910db8ab153b0437156f6d0fdd07985f348fab',
    namespace: 'phase3Authentication',
  },
  phase4aSubjectDirectory: {
    file: 'phase4a-subject-directory.openapi.json',
    sha256: '8344f0173f523939abae203430cf92455d6240404e3d8ffe7a002507cadd2169',
    namespace: 'phase4aSubjectDirectory',
  },
  phase4aPublicBank: {
    file: 'phase4a-public-bank.openapi.json',
    sha256: '1f163574d9fb5b25d58df4a4a75ffca6b74b874dfbf66551cf46408d67110a34',
    namespace: 'phase4aPublicBank',
  },
} as const;

export const publicBankOperationIds = {
  list: 'legacy_b7e49e77a026_get',
  boards: 'legacy_db1ac691d6fb_get',
  hot: 'legacy_a473896ff467_get',
  summary: 'legacy_f3644c1474f3_get',
  detail: 'legacy_8cfb837021af_get',
} as const;
