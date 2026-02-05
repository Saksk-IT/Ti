import { api } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';
type AccountSubKey = 'profile' | 'security' | 'bindings';

function navTo(key: SettingsNavKey): string {
  if (key === 'practice') return '/pages/settings-practice-v2/settings-practice-v2';
  if (key === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-account-security-v2/settings-account-security-v2';
}

function accTo(key: AccountSubKey): string {
  if (key === 'profile') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'bindings') return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
  return '/pages/settings-account-security-v2/settings-account-security-v2';
}

function isStrongPassword(pwd: string): boolean {
  const v = String(pwd || '');
  if (v.length < 8) return false;
  return /[a-zA-Z]/.test(v) && /\d/.test(v);
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'account' as SettingsNavKey,
    accTab: 'security' as AccountSubKey,

    loading: false,
    submitting: false,
    errorMsg: '',
    msg: '',

    hasPasswordSet: false,
    pwdChip: '-',
    pwdSub: '用于修改或设置登录密码。',
    submitText: '提交',

    currentPassword: '',
    newPassword: '',
    confirmPassword: '',

    showCurrent: false,
    showNew: false,
    showConfirm: false
  },

  onLoad() {
    wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=account&accTab=security' });
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

  onPullDownRefresh() {
    Promise.resolve()
      .then(async () => {
        await this.loadProfile(true);
      })
      .finally(() => {
        wx.stopPullDownRefresh();
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
    this.setData(themeManager.getPageData() as any);
    this.setData({ drawerOpen: false });
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

  onSettingsNavTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as SettingsNavKey;
    if (!key) return;
    const url = navTo(key);
    if (url === '/pages/settings-account-security-v2/settings-account-security-v2') return;
    wx.redirectTo({ url });
  },

  onAccountSubTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as AccountSubKey;
    if (!key) return;
    const url = accTo(key);
    if (url === '/pages/settings-account-security-v2/settings-account-security-v2') return;
    wx.redirectTo({ url });
  },

  onToggleShow(e: any) {
    const target = String(e?.currentTarget?.dataset?.target || '');
    if (target === 'current') this.setData({ showCurrent: !this.data.showCurrent });
    if (target === 'new') this.setData({ showNew: !this.data.showNew });
    if (target === 'confirm') this.setData({ showConfirm: !this.data.showConfirm });
  },

  onCurrentInput(e: any) {
    this.setData({ currentPassword: String(e?.detail?.value || '') });
  },

  onNewInput(e: any) {
    this.setData({ newPassword: String(e?.detail?.value || '') });
  },

  onConfirmInput(e: any) {
    this.setData({ confirmPassword: String(e?.detail?.value || '') });
  },

  onReset() {
    if (this.data.submitting) return;
    this.setData({
      msg: '',
      errorMsg: '',
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
  },

  async onSubmit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true, msg: '', errorMsg: '' });
    try {
      const isSetPassword = !this.data.hasPasswordSet;
      const cur = String(this.data.currentPassword || '');
      const nw = String(this.data.newPassword || '');
      const c = String(this.data.confirmPassword || '');

      if (!nw || !c) throw new Error('请填写新密码');
      if (nw !== c) throw new Error('两次输入的密码不一致');
      if (!isStrongPassword(nw)) throw new Error('密码至少 8 位且包含字母和数字');
      if (isSetPassword && cur) throw new Error('设置密码不需要输入当前密码');
      if (!isSetPassword && !cur) throw new Error('修改密码需要输入当前密码');

      const res = await api.updateProfilePassword({
        current_password: cur,
        new_password: nw,
        is_set_password: isSetPassword
      });

      if (isSetPassword) {
        wx.showToast({ title: res?.message || '密码设置成功', icon: 'none' });
        this.setData({ currentPassword: '', newPassword: '', confirmPassword: '', msg: res?.message || '密码设置成功' });
        await this.loadProfile(true);
        return;
      }

      await new Promise<void>((resolve) => {
        wx.showModal({
          title: '修改成功',
          content: '为保证安全，需要重新登录。',
          showCancel: false,
          confirmText: '去登录',
          success: () => resolve()
        });
      });
      logout();
      wx.redirectTo({ url: '/pages/login/login' });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '操作失败，请稍后重试' });
    } finally {
      this.setData({ submitting: false });
    }
  },

  applyMode(hasPasswordSet: boolean) {
    const isSetPassword = !hasPasswordSet;
    this.setData({
      hasPasswordSet,
      pwdChip: hasPasswordSet ? '已设置密码' : '未设置密码',
      pwdSub: hasPasswordSet ? '修改登录密码。修改成功后需要重新登录。' : '为账号设置登录密码（首次设置无需填写当前密码）。',
      submitText: isSetPassword ? '设置密码' : '修改密码'
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
      const hasPasswordSet = !!p?.has_password_set;
      this.applyMode(hasPasswordSet);
    } catch (e: any) {
      this.applyMode(false);
      this.setData({ errorMsg: e?.message || '加载失败，请稍后重试' });
    } finally {
      this.setData({ loading: false });
    }
  }
});

