import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';
type AboutTab = 'app' | 'legal';

function navTo(key: SettingsNavKey): string {
  if (key === 'account') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'practice') return '/pages/settings-practice-v2/settings-practice-v2';
  if (key === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  return '/pages/settings-about-v2/settings-about-v2';
}

function summarizeUsername(): string {
  const userInfo = wx.getStorageSync('userInfo') || {};
  const name = String(userInfo?.username || userInfo?.name || userInfo?.email || '').trim();
  return name || '已登录';
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'about' as SettingsNavKey,
    aboutTab: 'app' as AboutTab,
    contactOpen: false,

    currentUsername: '—',

    adminUsername: '',
    adminEmail: '',
    adminWechat: '',
    chatDisabled: true,
    chatDisabledReason: '',

    errorMsg: ''
  },

  onLoad() {
    wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=about' });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    this.setData({ currentUsername: summarizeUsername() });
    this.loadAboutInfo();
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

  onContinueLast() {
    const url = buildLastPracticeUrl();
    if (!url) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }
    wx.navigateTo({ url });
  },

  onSettingsNavTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as SettingsNavKey;
    if (!key) return;
    const url = navTo(key);
    if (url === '/pages/settings-about-v2/settings-about-v2') return;
    wx.redirectTo({ url });
  },

  onAboutTabTap(e: any) {
    const tab = String(e?.currentTarget?.dataset?.tab || '').toLowerCase() as AboutTab;
    const next: AboutTab = tab === 'legal' ? 'legal' : 'app';
    if (next === this.data.aboutTab) return;
    this.setData({ aboutTab: next });
  },

  onToggleContact() {
    this.setData({ contactOpen: !this.data.contactOpen });
  },

  async loadAboutInfo() {
    this.setData({ errorMsg: '' });
    try {
      const res: any = await api.getSettingsAbout();
      this.setData({
        adminUsername: String(res?.admin_username || ''),
        adminEmail: String(res?.admin_email || ''),
        adminWechat: String(res?.admin_wechat || ''),
        chatDisabled: !!res?.chat_disabled,
        chatDisabledReason: String(res?.chat_disabled_reason || '')
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后重试' });
    }
  },

  onGoProfile() {
    wx.redirectTo({ url: '/pages/settings-account-profile-v2/settings-account-profile-v2' });
  },

  onContactChat() {
    if (this.data.chatDisabled) {
      wx.showToast({ title: this.data.chatDisabledReason || '暂不可用', icon: 'none' });
      return;
    }
    wx.showToast({ title: '小程序暂不支持站内聊天，请在 Web 端打开 /contact_admin', icon: 'none' });
  },

  onCopy(e: any) {
    const v = String(e?.currentTarget?.dataset?.value || '').trim();
    if (!v) return;
    wx.setClipboardData({
      data: v,
      success: () => wx.showToast({ title: '已复制', icon: 'none' }),
      fail: () => wx.showToast({ title: '复制失败', icon: 'none' })
    });
  },

  onOpenTerms() {
    wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /terms', icon: 'none' });
  },

  onOpenPrivacy() {
    wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /privacy', icon: 'none' });
  }
});
