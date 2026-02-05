import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { decorateAvatarUrl } from '../../utils/avatar';

function maskEmail(email: any): string {
  const s = (email == null) ? '' : String(email).trim();
  if (!s || !s.includes('@')) return s || '未绑定';
  const parts = s.split('@');
  if (parts.length < 2) return s;
  const name = parts[0] || '';
  const domain = parts.slice(1).join('@') || '';
  if (!name) return `***@${domain}`;
  if (name.length === 1) return `${name}***@${domain}`;
  return `${name.slice(0, 2)}***@${domain}`;
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    errorMsg: '',

    username: '—',
    avatarUrl: '',
    avatarInitial: 'U',
    roleText: '普通用户',
    createdAtText: '—',

    wechatBound: false,
    wechatBadge: '微信未绑定',

    emailRaw: '',
    emailMasked: '未绑定',
    emailBadge: '未绑定',

    collegeRaw: '',
    contactRaw: '',
    signatureRaw: '',
    collegeText: '未设置',
    contactText: '未设置',
    signatureText: '未设置',

    streakDays: 0,
    totalAnswered: 0,
    accuracyText: '0%',
    mistakesCount: 0,
    favoritesCount: 0
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}

    if (!this.data.loading) this.loadProfile(false);
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
    this.setData(themeManager.getPageData() as any);
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onPullDownRefresh() {
    Promise.resolve()
      .then(async () => {
        await this.loadProfile(true);
      })
      .finally(() => {
        wx.stopPullDownRefresh();
      });
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData() as any), themeMode: mode });
  },

  onEditProfile() {
    wx.navigateTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=account&accTab=profile&edit=1' });
  },

   onLogoutTap() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#FF3B30',
      success: (res) => {
        if (!res.confirm) return;
        logout();
        wx.reLaunch({ url: '/pages/login/login' });
      }
    });
  },

  onAvatarTap() {
    const url = String((this.data as any).avatarUrl || '').trim();
    if (url) {
      wx.previewImage({ urls: [url], current: url });
      return;
    }
    this.onEditProfile();
  },

  onAvatarError() {
    const url = String((this.data as any).avatarUrl || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) {
      this.setData({ avatarUrl: '' });
      return;
    }

    const self: any = this as any;
    if (self.__avatarDlTried) {
      this.setData({ avatarUrl: '' });
      return;
    }
    self.__avatarDlTried = true;

    wx.downloadFile({
      url,
      timeout: 15000,
      success: (res) => {
        const tempFilePath = String((res && (res as any).tempFilePath) || '').trim();
        this.setData({ avatarUrl: tempFilePath || '' });
      },
      fail: () => {
        this.setData({ avatarUrl: '' });
      }
    });
  },

  onGoHistory() {
    wx.navigateTo({ url: '/packages/data/pages/data-center-v2/data-center-v2' });
  },

  onGoMistakes() {
    wx.navigateTo({ url: '/pages/mistakes-v2/mistakes-v2' });
  },

  onGoFavorites() {
    wx.navigateTo({ url: '/pages/favorites-v2/favorites-v2' });
  },

  onCopy(e: any) {
    const value = String(e?.currentTarget?.dataset?.value || '').trim();
    if (!value) {
      wx.showToast({ title: '无可复制内容', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: value,
      success: () => wx.showToast({ title: '已复制', icon: 'none' }),
      fail: () => wx.showToast({ title: '复制失败', icon: 'none' })
    });
  },

  async loadProfile(force = false) {
    if (this.data.loading) return;

    const self: any = this as any;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 8000) return;
    self.__lastLoadedAt = now;

    this.setData({ loading: true, errorMsg: '' });
    try {
      const p: any = await api.getProfile();
      const username = String(p?.username || '用户');
      const avatar = decorateAvatarUrl(resolveUploadUrl(p?.avatar));
      const isAdmin = !!p?.is_admin;
      const createdAtText = p?.created_at ? `加入 ${String(p.created_at)}` : '加入时间 —';

      const college = String(p?.college || '');
      const contact = String(p?.contact || '');
      const signature = String(p?.signature || '');

      const streakDays = Number(p?.streak_days || 0) || 0;
      const totalAnswered = Number(p?.total_answered || 0) || 0;
      const accuracy = Number(p?.accuracy || 0) || 0;
      const mistakesCount = Number(p?.mistakes_count || 0) || 0;
      const favoritesCount = Number(p?.favorites_count || 0) || 0;

      const emailRaw = String(p?.email || '').trim();
      const emailMasked = maskEmail(emailRaw);
      const emailVerified = !!p?.email_verified;
      const emailBadge = emailRaw ? (emailVerified ? '已验证' : '未验证') : '未绑定';

      const wechatBound = !!p?.wechat_bound;
      const wechatBadge = wechatBound ? '微信已绑定' : '微信未绑定';

      this.setData({
        username,
        avatarUrl: avatar || '/images/default-avatar.png',
        avatarInitial: (username || 'U').charAt(0).toUpperCase(),
        roleText: isAdmin ? '管理员' : '普通用户',
        createdAtText,
        wechatBound,
        wechatBadge,
        emailRaw,
        emailMasked: emailMasked || '未绑定',
        emailBadge,
        collegeRaw: college,
        contactRaw: contact,
        signatureRaw: signature,
        collegeText: college ? college : '未设置',
        contactText: contact ? contact : '未设置',
        signatureText: signature ? signature : '未设置',
        streakDays,
        totalAnswered,
        accuracyText: `${accuracy}%`,
        mistakesCount,
        favoritesCount
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后重试' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
