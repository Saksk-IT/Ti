import { themeManager } from './theme';

const TAB_TRANSITION_CLASS = 'tab-switch-enter';
const TAB_ROUTES = [
  'pages/hub-v2/hub-v2',
  'pages/public-bank-v2/public-bank-v2',
  'pages/my-banks-v2/my-banks-v2',
  'pages/campus/campus',
  'pages/mine/mine',
];

export function restartTabPageTransition(page: WechatMiniprogram.Page.Instance<Record<string, any>, Record<string, any>>): void {
  if (!page || typeof page.setData !== 'function') return;

  syncCustomTabBar(page);

  page.setData({ tabPageTransitionClass: '' }, () => {
    setTimeout(() => {
      page.setData({ tabPageTransitionClass: TAB_TRANSITION_CLASS });
    }, 16);
  });
}

function currentTabIndex(): number {
  try {
    const pages = getCurrentPages();
    const current = pages && pages.length ? pages[pages.length - 1] : null;
    const route = String((current as any)?.route || (current as any)?.__route__ || '').trim();
    const index = TAB_ROUTES.indexOf(route);
    return index >= 0 ? index : 0;
  } catch (e) {
    return 0;
  }
}

function updateTabBar(tabBar: any, selected: number): void {
  if (!tabBar || typeof tabBar.setData !== 'function') return;
  try {
    const themeData = themeManager.getPageData();
    tabBar.setData({
      selected,
      switching: false,
      switchingIndex: -1,
      isDarkMode: themeData.isDarkMode,
      themeClass: themeData.themeClass,
      themeStyleClass: themeData.themeStyleClass,
    });
  } catch (e) {
    tabBar.setData({ selected, switching: false, switchingIndex: -1 });
  }
}

function syncCustomTabBar(page: WechatMiniprogram.Page.Instance<Record<string, any>, Record<string, any>>): void {
  const instance = page as any;
  if (typeof instance.getTabBar !== 'function') return;
  const selected = currentTabIndex();
  try {
    const maybe = instance.getTabBar((tabBar: any) => updateTabBar(tabBar, selected));
    if (maybe) updateTabBar(maybe, selected);
  } catch (e) {
    try {
      const tabBar = instance.getTabBar();
      updateTabBar(tabBar, selected);
    } catch (err) {}
  }
}
