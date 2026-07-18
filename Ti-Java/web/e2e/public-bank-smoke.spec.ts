import { expect, test } from '@playwright/test';

test.describe('公开题库只读迁移', () => {
  test('桌面端保留论坛式广场、筛选、追加加载和只读详情边界', async ({ page }) => {
    const requestedPaths: string[] = [];
    page.on('request', (request) => {
      const url = new URL(request.url());
      if (url.pathname.startsWith('/api/')) requestedPaths.push(url.pathname);
    });

    await page.goto('/public/banks');

    await expect(page.getByRole('link', { name: 'SAK 题库广场' })).toBeVisible();
    await expect(page.locator('#public-bank-list')).toBeVisible();
    await expect(page.locator('#public-bank-list > li')).toHaveCount(10);
    await expect(page.getByText('当前仅开放公共题库浏览')).toBeVisible();
    await expect(page.getByRole('tab', { name: '最新' })).toHaveAttribute('aria-selected', 'true');

    await page.getByRole('button', { name: '加载更多' }).click();
    await expect(page.locator('#public-bank-list > li')).toHaveCount(12);

    await page.getByRole('searchbox', { name: '搜索题库' }).fill('算法');
    await page.getByRole('searchbox', { name: '搜索题库' }).press('Enter');
    await expect(page).toHaveURL(/keyword=%E7%AE%97%E6%B3%95/u);
    await expect(page.getByText(/搜索 “算法”/u)).toBeVisible();

    await page.getByRole('button', { name: '清空关键词' }).click();
    await page.locator('#public-bank-list a.forum-post-card').first().click();
    await expect(page).toHaveURL(/\/public\/banks\/card\/(system|user)\/\d+$/u);
    await expect(page.locator('#public-bank-detail')).toBeVisible();
    await expect(page.getByRole('button', { name: /加入题库/u })).toBeDisabled();
    await expect(page.getByRole('button', { name: /开始练习/u })).toBeDisabled();
    await expect(page.getByText('当前只开放题库浏览；加入和练习功能正在迁移')).toBeVisible();

    expect(requestedPaths).toEqual(expect.arrayContaining([
      '/api/public/banks/list',
      '/api/public/banks/boards',
      '/api/public/banks/hot',
      '/api/public/banks/summary',
    ]));
    expect(requestedPaths.some((path) =>
      /^\/api\/public\/banks\/card\/(system|user_public)\/101$/u.test(path),
    )).toBe(true);
    expect(requestedPaths.some((path) => path.includes('user-counts'))).toBe(false);
  });

  test('主题风格沿用旧持久化键，错误态显示 Request ID', async ({ page }) => {
    await page.goto('/public/banks');
    await page.getByText('外观与风格').click();
    await page.getByRole('button', { name: '深色', exact: true }).click();
    await page.getByRole('button', { name: /松林/u }).click();

    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expect(page.locator('html')).toHaveAttribute('data-theme-style', 'pine');
    expect(await page.evaluate(() => ({
      theme: localStorage.getItem('theme'),
      style: localStorage.getItem('app_theme_style_v1'),
    }))).toEqual({ theme: 'dark', style: 'pine' });

    await page.getByRole('searchbox', { name: '搜索题库' }).fill('error');
    await page.getByRole('searchbox', { name: '搜索题库' }).press('Enter');
    await expect(page.getByRole('heading', { name: '暂时无法读取内容' })).toBeVisible();
    await expect(page.locator('.forum-main .request-id-inline')).toContainText('请求 ID：');
    await expect(
      page.getByRole('complementary', { name: '题库筛选与概览' }).locator('.sidebar-slice-error'),
    ).toHaveCount(3);
    await expect(page.getByRole('button', { name: '重新加载' })).toBeVisible();
  });
});

test.describe('移动端原有双层抽屉模式', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('应用导航与题库侧栏保持独立抽屉', async ({ page }) => {
    await page.goto('/public/banks');

    await page.getByRole('button', { name: '打开侧边栏' }).click();
    await expect(page.locator('.app-shell')).toHaveClass(/sidebar-open/u);
    await expect(page.getByRole('complementary', { name: '侧边栏导航' })).toBeVisible();
    await page.getByRole('button', { name: '关闭侧边栏' }).click();

    await page.getByRole('button', { name: '打开题库侧栏' }).click();
    await expect(page.getByRole('complementary', { name: '题库侧栏抽屉' })).toHaveClass(/open/u);
    const plazaDrawer = page.getByRole('complementary', { name: '题库侧栏抽屉' });
    await expect(plazaDrawer.getByRole('heading', { name: '题库板块' })).toBeVisible();
    await page.getByRole('button', { name: '关闭题库侧栏' }).click();
    await expect(page.getByRole('complementary', { name: '题库侧栏抽屉' })).not.toHaveClass(/open/u);
  });
});
