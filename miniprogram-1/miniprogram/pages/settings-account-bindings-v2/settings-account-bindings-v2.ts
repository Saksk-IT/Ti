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
  return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
}

function accTo(key: AccountSubKey): string {
  if (key === 'profile') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'security') return '/pages/settings-account-security-v2/settings-account-security-v2';
  return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
}

function validateEmail(email: string): { ok: boolean; msg?: string; value?: string } {
  const v = String(email || '').trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!v) return { ok: false, msg: '请输入邮箱地址' };
  if (!emailRegex.test(v)) return { ok: false, msg: '邮箱格式不正确' };
  return { ok: true, value: v };
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'account' as SettingsNavKey,
    accTab: 'bindings' as AccountSubKey,

    loading: false,
    errorMsg: '',
    msg: '',

    emailChip: '-',
    emailDesc: '加载中…',
    emailActionText: '绑定',
    emailFormOpen: false,
    bindEmail: '',
    bindCode: '',
    sendingCode: false,
    countdown: 0,
    sendCodeText: '发送验证码',
    sendCodeDisabled: false,
    bindingEmail: false,

    wechatBound: false,
    wechatChip: '-',
    wechatDesc: '加载中…',
    bindingWechat: false,
    unbindingWechat: false
  },

  onLoad() {
    wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=account&accTab=bindings' });
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

  onUnload() {
    this.clearCountdown();
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
    if (url === '/pages/settings-account-bindings-v2/settings-account-bindings-v2') return;
    wx.redirectTo({ url });
  },

  onAccountSubTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as AccountSubKey;
    if (!key) return;
    const url = accTo(key);
    if (url === '/pages/settings-account-bindings-v2/settings-account-bindings-v2') return;
    wx.redirectTo({ url });
  },

  onEmailActionTap() {
    if (this.data.loading) return;
    this.setData({
      msg: '',
      errorMsg: '',
      emailFormOpen: true
    });
  },

  onCloseEmailFormTap() {
    if (this.data.bindingEmail) return;
    this.clearCountdown();
    this.setData({
      emailFormOpen: false,
      bindEmail: '',
      bindCode: ''
    });
  },

  onBindEmailInput(e: any) {
    this.setData({ bindEmail: String(e?.detail?.value || '') });
  },

  onBindCodeInput(e: any) {
    this.setData({ bindCode: String(e?.detail?.value || '') });
  },

  getSendCodeText(): string {
    if (this.data.sendingCode) return '发送中…';
    if (this.data.countdown > 0) return `重发(${this.data.countdown}s)`;
    return '发送验证码';
  },

  refreshSendCodeUi() {
    this.setData({
      sendCodeText: this.getSendCodeText(),
      sendCodeDisabled: this.data.sendingCode || this.data.countdown > 0
    });
  },

  clearCountdown() {
    const self: any = this as any;
    if (self.__countdownTimer) {
      clearTimeout(self.__countdownTimer);
      self.__countdownTimer = null;
    }
    this.setData({ countdown: 0, sendingCode: false });
    this.refreshSendCodeUi();
  },

  tickCountdown() {
    const self: any = this as any;
    const next = Math.max(0, Number(this.data.countdown || 0) - 1);
    this.setData({ countdown: next });
    this.refreshSendCodeUi();
    if (next <= 0) {
      self.__countdownTimer = null;
      return;
    }
    self.__countdownTimer = setTimeout(() => this.tickCountdown(), 1000);
  },

  async onSendCodeTap() {
    if (this.data.sendingCode || this.data.countdown > 0) return;
    const v = validateEmail(this.data.bindEmail);
    if (!v.ok) {
      this.setData({ errorMsg: v.msg || '邮箱格式不正确' });
      return;
    }

    this.setData({ sendingCode: true, msg: '', errorMsg: '' });
    this.refreshSendCodeUi();
    try {
      const res: any = await api.sendEmailBindCode(v.value as string);
      const tip = String(res?.message || '验证码已发送');
      wx.showToast({ title: tip, icon: 'none' });
      this.setData({ msg: tip, countdown: 60 });
      this.refreshSendCodeUi();
      this.tickCountdown();
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '发送失败，请稍后重试' });
      this.clearCountdown();
    } finally {
      this.setData({ sendingCode: false });
      this.refreshSendCodeUi();
    }
  },

  async onBindEmailTap() {
    if (this.data.bindingEmail) return;
    const v = validateEmail(this.data.bindEmail);
    if (!v.ok) {
      this.setData({ errorMsg: v.msg || '邮箱格式不正确' });
      return;
    }
    const code = String(this.data.bindCode || '').trim();
    if (!code || code.length !== 6) {
      this.setData({ errorMsg: '请输入 6 位验证码' });
      return;
    }

    this.setData({ bindingEmail: true, msg: '', errorMsg: '' });
    try {
      await api.bindEmail(v.value as string, code);
      wx.showToast({ title: '邮箱绑定成功', icon: 'none' });
      this.clearCountdown();
      this.setData({ emailFormOpen: false, bindEmail: '', bindCode: '', msg: '邮箱绑定成功' });
      await this.loadProfile(true);
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '绑定失败，请稍后重试' });
    } finally {
      this.setData({ bindingEmail: false });
    }
  },

  async onWechatBindTap() {
    if (this.data.bindingWechat) return;
    this.setData({ bindingWechat: true, msg: '', errorMsg: '' });
    try {
      const code = await new Promise<string>((resolve) => {
        wx.login({
          success: (res) => resolve(String(res?.code || '')),
          fail: () => resolve('')
        });
      });
      if (!code) throw new Error('获取微信登录 code 失败');

      const res: any = await api.miniWechatBind(code);
      if (res && res.token) wx.setStorageSync('token', res.token);
      if (res && res.user_info) wx.setStorageSync('userInfo', res.user_info);

      wx.showToast({ title: '绑定成功', icon: 'none' });
      this.setData({ msg: '绑定成功' });
      await this.loadProfile(true);
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '绑定失败，请稍后重试' });
    } finally {
      this.setData({ bindingWechat: false });
    }
  },

  async onWechatUnbindTap() {
    if (this.data.unbindingWechat) return;

    // 检查是否已绑定邮箱，防止账号悬空
    const emailChip = this.data.emailChip || '';
    const hasEmail = emailChip.includes('已绑定');
    if (!hasEmail) {
      wx.showModal({
        title: '无法解绑',
        content: '请先绑定邮箱后再解绑微信，否则账号将无法登录。',
        showCancel: false,
        confirmText: '去绑定邮箱'
      });
      return;
    }

    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '确认解绑微信',
        content: '解绑后将无法使用微信一键登录。为保证安全，需要重新登录。',
        confirmText: '解绑',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    this.setData({ unbindingWechat: true, msg: '', errorMsg: '' });
    try {
      await api.wechatUnbind();
      await new Promise<void>((resolve) => {
        wx.showModal({
          title: '解绑成功',
          content: '需要重新登录。',
          showCancel: false,
          confirmText: '去登录',
          success: () => resolve()
        });
      });
      logout();
      wx.redirectTo({ url: '/pages/login/login' });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '解绑失败，请稍后重试' });
    } finally {
      this.setData({ unbindingWechat: false });
    }
  },

  applyProfile(p: any) {
    const email = String(p?.email || '').trim();
    const verified = !!p?.email_verified;

    const emailChip = email ? (verified ? '已绑定' : '已绑定(未验证)') : '未绑定';
    const emailDesc = email ? `当前邮箱：${email}${verified ? '' : '（未验证）'}` : '绑定邮箱用于接收验证码与找回账号。';
    const emailActionText = email ? '更换' : '绑定';

    const wechatBound = !!p?.wechat_bound;
    const wechatChip = wechatBound ? '已绑定' : '未绑定';
    const wechatDesc = wechatBound ? '已绑定微信，可使用微信一键登录。' : '绑定微信后可使用微信一键登录。';

    this.setData({
      wechatBound,
      emailChip,
      emailDesc,
      emailActionText,
      wechatChip,
      wechatDesc
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
      this.applyProfile(p);
      this.refreshSendCodeUi();
    } catch (e: any) {
      this.applyProfile({});
      this.setData({ errorMsg: e?.message || '加载失败，请稍后重试' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
