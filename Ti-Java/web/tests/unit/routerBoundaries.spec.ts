import { describe, expect, it } from 'vitest';

import { router } from '@/router';

describe('router migration boundaries', () => {
  it('只晋级公共题库只读路由，并为未迁移旅程提供显式阻断页', () => {
    expect(router.resolve({ name: 'public-bank-list' }).href).toBe('/public/banks');
    expect(router.resolve({
      name: 'public-bank-detail',
      params: { sourceType: 'user', bankId: '42' },
    }).href).toBe('/public/banks/card/user/42');

    for (const journey of ['join', 'practice', 'personal-banks', 'user-counts', 'write']) {
      expect(router.resolve({ name: 'blocked-journey', params: { journey } }).href)
        .toBe(`/unavailable/${journey}`);
    }

    expect(router.resolve('/public/banks/joined').matched[0]?.redirect).toEqual({
      name: 'blocked-journey',
      params: { journey: 'personal-banks' },
    });
    expect(router.resolve('/user/banks/42/practice').matched[0]?.redirect).toEqual({
      name: 'blocked-journey',
      params: { journey: 'practice' },
    });
  });
});
