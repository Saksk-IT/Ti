import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';

function navTo(key: SettingsNavKey): string {
  if (key === 'account') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'practice') return '/pages/settings-practice-v2/settings-practice-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-theme-v2/settings-theme-v2';
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'theme' as SettingsNavKey,
    msg: ''
  },

  onLoad() {
    wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=theme' });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}
  },

  onHamburgerTap() {
    this.setData({ drawerOpen: true });
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false });
  },

  onDrawerNavigate(e: any) {
    const url = e?.detail?.url;
    const navType = e?.detail?.navType;
    this.setData({ drawerOpen: false });
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e: any) {
    const style = String(e?.detail?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData() as any);
    this.setData({ drawerOpen: false, msg: '已应用并尝试同步到云端' });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData() as any), themeMode: mode });
  },

  onContinueLast() {
    const url = buildLastPracticeUrl();
    if (!url) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }
    wx.navigateTo({ url });
  },

  onModeTap(e: any) {
    const mode = String(e?.currentTarget?.dataset?.mode || 'system') as ThemeMode;
    if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
    themeManager.setMode(mode);
    this.setData(themeManager.getPageData() as any);
    const label = mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟随系统';
    this.setData({ msg: `已切换到「${label}」` });
  },

  async onStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData() as any);
    await syncUserSettingsToServer();
    this.setData({ msg: '已应用并尝试同步到云端' });
  },

  onSettingsNavTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as SettingsNavKey;
    if (!key) return;
    const url = navTo(key);
    if (url === '/pages/settings-theme-v2/settings-theme-v2') return;
    wx.redirectTo({ url });
  }
});
