import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type PracticeSettings = {
  autoNextOnCorrect: boolean;
  autoFavoriteOnWrong: boolean;
  vibrationFeedback: boolean;
};

const PRACTICE_SETTINGS_KEY = 'quiz_practice_settings_v1';

function readPracticeSettings(): PracticeSettings {
  try {
    const raw: any = wx.getStorageSync(PRACTICE_SETTINGS_KEY);
    if (raw && typeof raw === 'object') {
      return {
        autoNextOnCorrect: !!raw.autoNextOnCorrect,
        autoFavoriteOnWrong: !!raw.autoFavoriteOnWrong,
        vibrationFeedback: !!raw.vibrationFeedback
      };
    }
  } catch (e) {}
  return { autoNextOnCorrect: false, autoFavoriteOnWrong: false, vibrationFeedback: false };
}

function writePracticeSettings(s: PracticeSettings): void {
  try {
    wx.setStorageSync(PRACTICE_SETTINGS_KEY, s);
  } catch (e) {}
}

function getAppVersion(): string {
  try {
    const info: any = (wx as any).getAccountInfoSync ? (wx as any).getAccountInfoSync() : null;
    const v = info?.miniProgram?.version || info?.miniProgram?.envVersion;
    return v ? String(v) : '—';
  } catch (e) {
    return '—';
  }
}

function summarizeUser(userInfo: any): { name: string; meta: string } {
  const name = String(userInfo?.username || userInfo?.name || userInfo?.email || '已登录');
  const parts: string[] = [];
  if (userInfo?.email) parts.push(String(userInfo.email));
  if (userInfo?.id || userInfo?.user_id) parts.push(`ID ${userInfo.id || userInfo.user_id}`);
  if (userInfo?.is_admin) parts.push('管理员');
  if (userInfo?.is_subject_admin) parts.push('科目管理员');
  const meta = parts.length ? parts.join(' · ') : '已登录（JWT）';
  return { name, meta };
}

Page({
  data: {
    drawerOpen: false,

    userName: '—',
    userMeta: '未登录',
    appVersion: '—',

    practiceSettings: readPracticeSettings()
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    const userInfo = wx.getStorageSync('userInfo') || {};
    const u = summarizeUser(userInfo);

    this.setData({
      userName: u.name,
      userMeta: u.meta,
      appVersion: getAppVersion(),
      practiceSettings: readPracticeSettings()
    });
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
    const style = (e?.detail?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onModeTap(e: any) {
    const mode = String(e?.currentTarget?.dataset?.mode || 'system') as ThemeMode;
    if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
    themeManager.setMode(mode);
    this.setData(themeManager.getPageData());
  },

  async onStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    await syncUserSettingsToServer();
  },

  onPracticeSwitch(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '');
    const value = !!(e && e.detail && e.detail.value);
    if (!key) return;

    const next: PracticeSettings = Object.assign({}, this.data.practiceSettings);
    (next as Record<string, boolean>)[key] = value;
    this.setData({ practiceSettings: next });
    writePracticeSettings(next);
  },

  onGoSubpage(e: any) {
    const url = String(e?.currentTarget?.dataset?.url || '').trim();
    if (!url) return;
    wx.navigateTo({ url });
  },

  onGoMine() {
    wx.switchTab({ url: '/pages/mine/mine' });
  },

  onLogout() {
    try {
      wx.removeStorageSync('token');
      wx.removeStorageSync('userInfo');
    } catch (e) {}
    wx.reLaunch({ url: '/pages/login/login' });
  }
});
