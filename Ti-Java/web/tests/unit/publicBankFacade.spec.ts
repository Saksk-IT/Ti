import { describe, expect, it } from 'vitest';

import {
  createPublicBankFacade,
  type PublicBankTransport,
} from '@/api/facade/publicBankFacade';
import { publicBankOperationIds } from '@/api/contracts/sourceManifest';
import { makePlazaListResponse } from '@/testing/publicBankFixtures';

const notUsed = async (): Promise<never> => {
  throw new Error('unexpected transport call');
};

function transportWithList(
  list: PublicBankTransport['list'],
): PublicBankTransport {
  return {
    boards: notUsed,
    detail: notUsed,
    hot: notUsed,
    list,
    summary: notUsed,
  };
}

describe('publicBankFacade', () => {
  it('只暴露五个已迁移的 Phase 4A 只读 operationId', () => {
    const facade = createPublicBankFacade(transportWithList(notUsed));

    expect(facade.operationIds).toEqual(publicBankOperationIds);
    expect(Object.values(facade.operationIds)).toEqual([
      'legacy_b7e49e77a026_get',
      'legacy_db1ac691d6fb_get',
      'legacy_a473896ff467_get',
      'legacy_f3644c1474f3_get',
      'legacy_8cfb837021af_get',
    ]);
  });

  it('规范化列表响应并优先保留响应头中的 Request ID', async () => {
    const response = new Response(null, {
      status: 200,
      headers: { 'X-Request-ID': 'response-request-id' },
    });
    const facade = createPublicBankFacade(transportWithList(async () => ({
      data: makePlazaListResponse(new URLSearchParams()),
      response,
    })));

    const result = await facade.list({ page: 1, perPage: 10 });

    expect(result.items).toHaveLength(10);
    expect(result.total).toBe(12);
    expect(result.requestId).toBe('response-request-id');
  });

  it('将 503 错误转换为可重试问题并保留 Request ID', async () => {
    const response = new Response(null, {
      status: 503,
      headers: { 'X-Request-ID': 'failed-request-id' },
    });
    const facade = createPublicBankFacade(transportWithList(async () => ({
      error: {
        error: { message: '服务暂时不可用' },
        meta: { request_id: 'payload-request-id' },
      },
      response,
    })));

    await expect(facade.list()).rejects.toMatchObject({
      kind: 'unavailable',
      message: '服务暂时不可用',
      requestId: 'failed-request-id',
      retryable: true,
      status: 503,
    });
  });
});
