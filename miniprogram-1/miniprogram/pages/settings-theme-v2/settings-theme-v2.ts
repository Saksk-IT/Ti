import { checkLogin } from '../../utils/auth';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { fontManager, FontStyle, FONT_STYLE_CONFIG } from '../../utils/font';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';

function navTo(key: SettingsNavKey): string {
  if (key === 'account') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'practice') return '/pages/settings-practice-v2/settings-practice-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-theme-v2/settings-theme-v2';
}

Page({
  data: {
    navKey: 'theme' as SettingsNavKey,
    msg: '',
    fontMsg: '',
    fontStyle: 'system' as FontStyle,
    fontStyleClass: '',
    fontStyleName: '系统默认',
    fontStyleList: Object.values(FONT_STYLE_CONFIG)
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData());
      this.setData(fontManager.getPageData());
    } catch (e) {}
  },
  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
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
    this.setData(themeManager.getPageData());
    const label = mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟随系统';
    this.setData({ msg: `已切换到「${label}」` });
  },

  async onStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    await syncUserSettingsToServer();
    this.setData({ msg: '已应用并尝试同步到云端' });
  },

  onFontStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'system') as FontStyle;
    fontManager.setStyle(style);
    this.setData(fontManager.getPageData());
    const config = FONT_STYLE_CONFIG[style] || FONT_STYLE_CONFIG.system;
    this.setData({ fontMsg: `已切换到「${config.name}」字体` });
  },

  onSettingsNavTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as SettingsNavKey;
    if (!key) return;
    const url = navTo(key);
    if (url === '/pages/settings-theme-v2/settings-theme-v2') return;
    wx.redirectTo({ url });
  }
});
