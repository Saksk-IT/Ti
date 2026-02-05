import { themeManager } from './theme';

export type NavType = 'switchTab' | 'navigateTo' | 'redirectTo' | 'reLaunch';

const NAV_LOCK_MS = 350;
const STACK_SOFT_LIMIT = 8;
let lastNavAt = 0;
let lastNavTarget = '';

function toRoutePath(url: string): string {
  const raw = String(url || '').trim();
  const path = raw.split('?')[0] || '';
  return path.startsWith('/') ? path.slice(1) : path;
}

function getCurrentRoutePath(): string {
  try {
    const pages = getCurrentPages();
    const cur: any = pages && pages.length ? pages[pages.length - 1] : null;
    return String(cur?.route || cur?.__route__ || '');
  } catch (e) {
    return '';
  }
}

function normalizeType(input: any): NavType {
  const t = String(input || '').trim();
  if (t === 'switchTab' || t === 'navigateTo' || t === 'redirectTo' || t === 'reLaunch') return t;
  return 'redirectTo';
}

function getPageStackLength(): number {
  try {
    const pages = getCurrentPages();
    return Array.isArray(pages) ? pages.length : 0;
  } catch (e) {
    return 0;
  }
}

function attempt(type: NavType, url: string, onFail: () => void, onSuccess?: () => void): void {
  const ok = () => {
    try {
      if (typeof onSuccess === 'function') onSuccess();
    } catch (e) {}
  };
  if (type === 'switchTab') {
    wx.switchTab({ url, success: () => ok(), fail: () => onFail() });
    return;
  }
  if (type === 'redirectTo') {
    wx.redirectTo({ url, success: () => ok(), fail: () => onFail() });
    return;
  }
  if (type === 'reLaunch') {
    wx.reLaunch({ url, success: () => ok(), fail: () => onFail() });
    return;
  }
  wx.navigateTo({ url, success: () => ok(), fail: () => onFail() });
}

/**
 * 安全跳转：优先按 navType 执行，失败时自动降级（解决页面栈过深/跳 tabBar 等导致的静默失败）
 */
export function safeNavigate(url: string, navType?: any): void {
  const targetUrl = String(url || '').trim();
  if (!targetUrl) return;

  // 防止重复触发（例如侧边栏关闭 setData 尚未渲染时连续触发导航）
  const now = Date.now();
  if (now - lastNavAt < NAV_LOCK_MS && targetUrl === lastNavTarget) return;
  lastNavAt = now;
  lastNavTarget = targetUrl;

  const current = getCurrentRoutePath();
  const targetRoute = toRoutePath(targetUrl);
  if (current && targetRoute && current === targetRoute && !targetUrl.includes('?')) return;

  const isDataCenterSubRoute =
    targetRoute === 'pages/history-v2/history-v2' ||
    targetRoute === 'pages/data-banks-v2/data-banks-v2' ||
    targetRoute === 'pages/data-trend-v2/data-trend-v2' ||
    targetRoute === 'pages/data-ai-v2/data-ai-v2' ||
    targetRoute === 'packages/data/pages/data-center-v2/data-center-v2' ||
    targetRoute === 'packages/data/pages/data-global-v2/data-global-v2' ||
    targetRoute === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
    targetRoute === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
    targetRoute === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
    targetRoute === 'packages/data/pages/data-tags-v2/data-tags-v2';

  // 数据中心五大子页（全局/题库/错题/收藏/标签）之间切换：更像「同页 tab 切换」
  // - 避免 navigateTo 堆栈不断增长
  // - 避免 reLaunch 的“先白屏再出现”观感
  const isDataCenterTabRoute =
    targetRoute === 'packages/data/pages/data-center-v2/data-center-v2' ||
    targetRoute === 'packages/data/pages/data-global-v2/data-global-v2' ||
    targetRoute === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
    targetRoute === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
    targetRoute === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
    targetRoute === 'packages/data/pages/data-tags-v2/data-tags-v2';
  const isCurrentDataCenterTabRoute =
    current === 'packages/data/pages/data-center-v2/data-center-v2' ||
    current === 'packages/data/pages/data-global-v2/data-global-v2' ||
    current === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
    current === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
    current === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
    current === 'packages/data/pages/data-tags-v2/data-tags-v2';
  const isDataCenterTabSwitch = isDataCenterTabRoute && isCurrentDataCenterTabRoute;

  const primary = normalizeType(navType);

  const stackLen = getPageStackLength();
  const stackFull = stackLen >= 10;
  const stackTight = stackLen >= STACK_SOFT_LIMIT;

  // 统一切页策略：以深色模式的“顺滑切页”为基准
  // 1) 导航前先同步原生背景色/TabBar（避免浅色/主题风格下出现“全白屏”）
  // 2) 栈不紧张时优先使用 navigateTo 触发系统自带滑动过渡；栈过深再降级 redirectTo/reLaunch
  const preferNavigateTo = !stackTight && primary !== 'switchTab' && !isDataCenterTabSwitch && !(primary === 'reLaunch' && isDataCenterSubRoute);

  const chain: NavType[] =
    primary === 'switchTab'
      ? ['switchTab', 'reLaunch', 'redirectTo', 'navigateTo']
      : primary === 'navigateTo'
        ? (stackFull ? ['redirectTo', 'reLaunch', 'navigateTo', 'switchTab'] : ['navigateTo', 'redirectTo', 'reLaunch', 'switchTab'])
        : preferNavigateTo && primary === 'reLaunch'
          ? ['navigateTo', 'reLaunch', 'redirectTo', 'switchTab']
        : preferNavigateTo
            ? ['navigateTo', 'redirectTo', 'reLaunch', 'switchTab']
        : primary === 'reLaunch'
          ? ['reLaunch', 'redirectTo', 'navigateTo', 'switchTab']
          : ['redirectTo', 'reLaunch', 'navigateTo', 'switchTab'];

  const afterSuccess = () => {
    try {
      themeManager.applySystemUI();
    } catch (e) {}
    try {
      const nextTick = (wx as any).nextTick;
      if (typeof nextTick === 'function') {
        nextTick(() => {
          try {
            themeManager.applySystemUI();
          } catch (e) {}
        });
        return;
      }
    } catch (e) {}
    setTimeout(() => {
      try {
        themeManager.applySystemUI();
      } catch (e) {}
    }, 0);
  };

  const run = (idx: number) => {
    if (idx >= chain.length) {
      wx.showToast({ title: '跳转失败', icon: 'none' });
      return;
    }
    attempt(chain[idx], targetUrl, () => run(idx + 1), afterSuccess);
  };

  const start = () => run(0);

  const scheduleStart = () => {
    // 延迟到下一帧，给 setData（如关闭抽屉）一次渲染机会，减少“跳动/闪烁”
    try {
      const nextTick = (wx as any).nextTick;
      if (typeof nextTick === 'function') {
        nextTick(start);
        return;
      }
    } catch (e) {}
    setTimeout(start, 0);
  };

  // 导航前先同步一次系统 UI（背景色/TabBar），并等待原生背景色应用（兜底），减少主题切页白屏
  const applyAsync = (themeManager as any).applySystemUIAsync;
  if (typeof applyAsync === 'function') {
    try {
      Promise.resolve(applyAsync.call(themeManager))
        .catch(() => {})
        .finally(() => scheduleStart());
      return;
    } catch (e) {}
  }

  try {
    themeManager.applySystemUI();
  } catch (e) {}
  scheduleStart();
}
