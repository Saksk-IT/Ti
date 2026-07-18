import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: { name: 'public-bank-list' },
  },
  {
    path: '/public/banks',
    name: 'public-bank-list',
    component: () => import('@/features/public-bank/pages/PublicBankListPage.vue'),
    meta: { title: '题库广场' },
  },
  {
    path: '/public/banks/joined',
    redirect: { name: 'blocked-journey', params: { journey: 'personal-banks' } },
  },
  {
    path: '/public/banks/card/:sourceType(system|user)/:bankId',
    name: 'public-bank-detail',
    component: () => import('@/features/public-bank/pages/PublicBankDetailPage.vue'),
    meta: { title: '题库名片' },
  },
  {
    path: '/user/banks/:bankId/practice',
    redirect: { name: 'blocked-journey', params: { journey: 'practice' } },
  },
  {
    path: '/subjects/:pathMatch(.*)*',
    redirect: { name: 'blocked-journey', params: { journey: 'practice' } },
  },
  {
    path: '/user/banks/:pathMatch(.*)*',
    redirect: { name: 'blocked-journey', params: { journey: 'personal-banks' } },
  },
  {
    path: '/feature-boundaries',
    name: 'feature-boundaries',
    component: () => import('@/pages/FeatureBoundaryPage.vue'),
    meta: { title: '功能边界' },
  },
  {
    path: '/unavailable/:journey(join|practice|personal-banks|user-counts|write)',
    name: 'blocked-journey',
    component: () => import('@/pages/FeatureBoundaryPage.vue'),
    meta: { title: '功能尚未迁移' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFoundPage.vue'),
    meta: { title: '页面不存在' },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'SAK';
  document.title = `${title} · SAK`;
});
