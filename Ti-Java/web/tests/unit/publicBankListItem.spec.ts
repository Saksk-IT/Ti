import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import { describe, expect, it } from 'vitest';

import PublicBankListItem from '@/features/public-bank/components/PublicBankListItem.vue';
import { publicBankCards } from '@/testing/publicBankFixtures';

describe('PublicBankListItem', () => {
  it('忽略合同中的旧 detail_url，始终构造 Vue Router 内部详情路由', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/public/banks', name: 'public-bank-list', component: { template: '<div />' } },
        {
          path: '/public/banks/card/:sourceType/:bankId',
          name: 'public-bank-detail',
          component: { template: '<div />' },
        },
      ],
    });
    await router.push('/public/banks');
    await router.isReady();

    const bank = {
      ...publicBankCards[0]!,
      detail_url: '/legacy/untrusted-detail-url',
      practice_url: '/legacy/untrusted-practice-url',
    };
    const wrapper = mount(PublicBankListItem, {
      props: { bank },
      global: { plugins: [router] },
    });
    const href = wrapper.get('a.forum-post-card').attributes('href');

    expect(href).toBe('/public/banks/card/user/101');
    expect(href).not.toBe(bank.detail_url);
    expect(href).not.toContain('/practice');
    wrapper.unmount();
  });
});
