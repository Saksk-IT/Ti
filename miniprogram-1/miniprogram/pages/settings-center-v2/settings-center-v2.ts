import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeStyle } from '../../utils/theme';
import { fontManager, FontStyle, FONT_STYLE_CONFIG } from '../../utils/font';
import { bumpAvatarRev, decorateAvatarUrl } from '../../utils/avatar';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';
type AccountSubKey = 'profile' | 'security' | 'bindings';
type AboutTab = 'app' | 'legal';

function normalizeNavKey(raw: any): SettingsNavKey {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'practice' || v === 'theme' || v === 'about') return v;
  return 'account';
}

function normalizeAccTab(raw: any): AccountSubKey {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'security' || v === 'bindings') return v;
  return 'profile';
}

function normalizeAboutTab(raw: any): AboutTab {
  const v = String(raw || '').trim().toLowerCase();
  return v === 'legal' ? 'legal' : 'app';
}

function maskEmail(email: any): string {
  const s = email == null ? '' : String(email).trim();
  if (!s || !s.includes('@')) return s || '未绑定';
  const parts = s.split('@');
  if (parts.length < 2) return s;
  const name = parts[0] || '';
  const domain = parts.slice(1).join('@') || '';
  if (!name) return `***@${domain}`;
  if (name.length === 1) return `${name}***@${domain}`;
  return `${name.slice(0, 2)}***@${domain}`;
}

function clampLen(s: any, max: number): string {
  const v = String(s || '');
  if (v.length <= max) return v;
  return v.slice(0, max);
}

function isStrongPassword(pwd: string): boolean {
  const v = String(pwd || '');
  if (v.length < 8) return false;
  return /[a-zA-Z]/.test(v) && /\d/.test(v);
}

function validateEmail(email: string): { ok: boolean; msg?: string; value?: string } {
  const v = String(email || '').trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!v) return { ok: false, msg: '请输入邮箱地址' };
  if (!emailRegex.test(v)) return { ok: false, msg: '邮箱格式不正确' };
  return { ok: true, value: v };
}

function summarizeUsername(): string {
  const userInfo = wx.getStorageSync('userInfo') || {};
  const name = String((userInfo as any)?.username || (userInfo as any)?.name || (userInfo as any)?.email || '').trim();
  return name || '已登录';
}

function bumpScrollTop(n: number): number {
  const v = Number(n || 0) || 0;
  return v === 0 ? 1 : 0;
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'account' as SettingsNavKey,
    accTab: 'profile' as AccountSubKey,
    aboutTab: 'app' as AboutTab,
    scrollTop: 0,

    profileMounted: true,
    securityMounted: false,
    bindingsMounted: false,
    practiceMounted: false,
    themeMounted: false,
    aboutMounted: false,

    profile: {
      loading: false,
      saving: false,
      editing: false,
      errorMsg: '',
      msg: '',

      username: '—',
      avatarUrl: '',
      avatarInitial: 'U',
      roleText: '普通用户',
      createdAtText: '—',

      college: '',
      signature: '',
      signatureCount: 0,
      contact: '',

      emailMasked: '未绑定',
      emailBadge: '未绑定',
      passwordBadge: '未设置',
      wechatBadge: '未绑定'
    },

    security: {
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

    bindings: {
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

    practice: { msg: '' },
    theme: { msg: '' },
    font: { msg: '' },

    // 字体样式相关
    fontStyle: 'system' as FontStyle,
    fontStyleClass: '',
    fontStyleName: '系统默认',
    fontStyleList: Object.values(FONT_STYLE_CONFIG),

    about: {
      errorMsg: '',
      contactOpen: false,
      currentUsername: '—',

      adminUsername: '',
      adminEmail: '',
      adminWechat: '',
      chatDisabled: true,
      chatDisabledReason: ''
    }
  },

  onLoad(options: any) {
    const navKey = normalizeNavKey(options?.navKey || options?.nav || options?.tab);
    const accTab = normalizeAccTab(options?.accTab || options?.acc || options?.sub);
    const aboutTab = normalizeAboutTab(options?.aboutTab || options?.about);

    const patch: any = { navKey, accTab, aboutTab };
    if (navKey === 'practice') patch.practiceMounted = true;
    if (navKey === 'theme') patch.themeMounted = true;
    if (navKey === 'about') patch.aboutMounted = true;
    if (navKey === 'account') {
      if (accTab === 'profile') patch.profileMounted = true;
      if (accTab === 'security') patch.securityMounted = true;
      if (accTab === 'bindings') patch.bindingsMounted = true;
    }

    this.setData(patch);

    try {
      const edit = String(options?.edit || '');
      if (edit === '1' && navKey === 'account' && accTab === 'profile') {
        this.setData({ 'profile.editing': true } as any);
      }
    } catch (e) {}
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData() as any);
      this.setData(fontManager.getPageData() as any);
    } catch (e) {}

    this.ensureTabLoaded(false);
  },

  onUnload() {
    this.clearCountdown();
  },

  onPullDownRefresh() {
    Promise.resolve()
      .then(async () => {
        await this.ensureTabLoaded(true);
      })
      .finally(() => {
        wx.stopPullDownRefresh();
      });
  },

  ensureTabLoaded(force = false) {
    const navKey = this.data.navKey as SettingsNavKey;
    if (navKey === 'account') return this.loadAccountSummary(force);
    if (navKey === 'about') return this.loadAboutInfo(force);

    if (navKey === 'theme' && !(this.data as any).themeMounted) this.setData({ themeMounted: true } as any);
    if (navKey === 'practice' && !(this.data as any).practiceMounted) this.setData({ practiceMounted: true } as any);
    return Promise.resolve();
  },

  resetScroll() {
    this.setData({ scrollTop: bumpScrollTop((this.data as any).scrollTop) } as any);
  },

  onHamburgerTap() {
    this.setData({ drawerOpen: true } as any);
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false } as any);
  },

  onDrawerNavigate(e: any) {
    const url = e?.detail?.url;
    const navType = e?.detail?.navType;
    this.setData({ drawerOpen: false } as any);
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e: any) {
    const style = (e?.detail?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData() as any);
    this.setData({ drawerOpen: false } as any);
    await syncUserSettingsToServer();
  },

  onToggleDarkTap() {
    themeManager.toggleDark();
    this.setData(themeManager.getPageData() as any);
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
    const key = normalizeNavKey(e?.currentTarget?.dataset?.key);
    if (!key || key === this.data.navKey) return;

    const patch: any = { navKey: key };
    if (key === 'practice') patch.practiceMounted = true;
    if (key === 'theme') patch.themeMounted = true;
    if (key === 'about') patch.aboutMounted = true;
    if (key === 'account') {
      const acc = this.data.accTab as AccountSubKey;
      if (acc === 'profile') patch.profileMounted = true;
      if (acc === 'security') patch.securityMounted = true;
      if (acc === 'bindings') patch.bindingsMounted = true;
    }

    this.setData(patch);
    this.resetScroll();
    this.ensureTabLoaded(false);
  },

  onAccountSubTap(e: any) {
    const key = normalizeAccTab(e?.currentTarget?.dataset?.key);
    if (!key) return;
    if (this.data.navKey !== 'account') this.setData({ navKey: 'account' } as any);
    if (key === this.data.accTab) return;

    const patch: any = { accTab: key };
    if (key === 'profile') patch.profileMounted = true;
    if (key === 'security') patch.securityMounted = true;
    if (key === 'bindings') patch.bindingsMounted = true;

    this.setData(patch);
    this.resetScroll();
    this.loadAccountSummary(false);
  },

  // ========== 账号：资料 ==========
  onEdit() {
    this.setData({ 'profile.editing': true, 'profile.msg': '', 'profile.errorMsg': '' } as any);
  },

  onCancel() {
    const self: any = this as any;
    const original = self.__originalProfile || {};
    const signature = String(original.signature || '');
    this.setData({
      'profile.editing': false,
      'profile.msg': '',
      'profile.errorMsg': '',
      'profile.college': String(original.college || ''),
      'profile.contact': String(original.contact || ''),
      'profile.signature': signature,
      'profile.signatureCount': signature.length
    } as any);
  },

  onCollegeInput(e: any) {
    const v = clampLen(e?.detail?.value, 40);
    this.setData({ 'profile.college': v } as any);
  },

  onContactInput(e: any) {
    const v = clampLen(e?.detail?.value, 60);
    this.setData({ 'profile.contact': v } as any);
  },

  onSignatureInput(e: any) {
    const v = clampLen(e?.detail?.value, 80);
    this.setData({ 'profile.signature': v, 'profile.signatureCount': v.length } as any);
  },

  async onSave() {
    const saving = !!(this.data as any).profile?.saving;
    if (saving) return;

    this.setData({ 'profile.saving': true, 'profile.msg': '', 'profile.errorMsg': '' } as any);
    try {
      await api.updateProfile({
        college: String((this.data as any).profile?.college || '').trim(),
        contact: String((this.data as any).profile?.contact || '').trim(),
        signature: String((this.data as any).profile?.signature || '').trim()
      });
      this.setData({ 'profile.editing': false, 'profile.msg': '已保存' } as any);
      await this.loadAccountSummary(true);
    } catch (e: any) {
      this.setData({ 'profile.errorMsg': e?.message || '保存失败，请稍后重试' } as any);
    } finally {
      this.setData({ 'profile.saving': false } as any);
    }
  },

  async onAvatarTap() {
    const p: any = (this.data as any).profile || {};
    if (p.loading || p.saving) return;

    const currentUrl = String(p.avatarUrl || '').trim();
    if (currentUrl) {
      const idx = await new Promise<number>((resolve) => {
        wx.showActionSheet({
          itemList: ['预览头像', '更换头像'],
          success: (res) => resolve(Number((res as any)?.tapIndex)),
          fail: () => resolve(-1)
        });
      });
      if (idx === 0) {
        wx.previewImage({ urls: [currentUrl], current: currentUrl });
        return;
      }
      if (idx !== 1) return;
    }

    const filePath = await new Promise<string>((resolve) => {
      const pick = (wx as any).chooseMedia ? 'chooseMedia' : 'chooseImage';
      if (pick === 'chooseMedia') {
        (wx as any).chooseMedia({
          count: 1,
          mediaType: ['image'],
          sourceType: ['album', 'camera'],
          success: (res: any) => resolve(String(res?.tempFiles?.[0]?.tempFilePath || '')),
          fail: () => resolve('')
        });
        return;
      }

      wx.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => resolve(String((res as any)?.tempFilePaths?.[0] || '')),
        fail: () => resolve('')
      });
    });

    if (!filePath) return;

    this.setData({ 'profile.msg': '', 'profile.errorMsg': '' } as any);
    wx.showLoading({ title: '上传中…', mask: true });
    try {
      const res: any = await api.uploadProfileAvatar(filePath);
      bumpAvatarRev();
      const url = decorateAvatarUrl(resolveUploadUrl(res?.avatar_url));
      this.setData({ 'profile.avatarUrl': url, 'profile.msg': '头像已更新' } as any);
      await this.loadAccountSummary(true);
    } catch (e: any) {
      wx.showToast({ title: e?.message || '上传失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onAvatarError() {
    const url = String((this.data as any).profile?.avatarUrl || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) {
      this.setData({ 'profile.avatarUrl': '' } as any);
      return;
    }

    const self: any = this as any;
    if (self.__avatarDlTried) {
      this.setData({ 'profile.avatarUrl': '' } as any);
      return;
    }
    self.__avatarDlTried = true;

    wx.downloadFile({
      url,
      timeout: 15000,
      success: (res) => {
        const tempFilePath = String((res && (res as any).tempFilePath) || '').trim();
        this.setData({ 'profile.avatarUrl': tempFilePath || '' } as any);
      },
      fail: () => {
        this.setData({ 'profile.avatarUrl': '' } as any);
      }
    });
  },

  // ========== 账号：安全 ==========
  onToggleShow(e: any) {
    const target = String(e?.currentTarget?.dataset?.target || '');
    const sec: any = (this.data as any).security || {};
    if (target === 'current') this.setData({ 'security.showCurrent': !sec.showCurrent } as any);
    if (target === 'new') this.setData({ 'security.showNew': !sec.showNew } as any);
    if (target === 'confirm') this.setData({ 'security.showConfirm': !sec.showConfirm } as any);
  },

  onCurrentInput(e: any) {
    this.setData({ 'security.currentPassword': String(e?.detail?.value || '') } as any);
  },

  onNewInput(e: any) {
    this.setData({ 'security.newPassword': String(e?.detail?.value || '') } as any);
  },

  onConfirmInput(e: any) {
    this.setData({ 'security.confirmPassword': String(e?.detail?.value || '') } as any);
  },

  onReset() {
    const submitting = !!(this.data as any).security?.submitting;
    if (submitting) return;
    this.setData({
      'security.msg': '',
      'security.errorMsg': '',
      'security.currentPassword': '',
      'security.newPassword': '',
      'security.confirmPassword': ''
    } as any);
  },

  async onSubmit() {
    const sec: any = (this.data as any).security || {};
    if (sec.submitting) return;
    this.setData({ 'security.submitting': true, 'security.msg': '', 'security.errorMsg': '' } as any);
    try {
      const isSetPassword = !sec.hasPasswordSet;
      const cur = String(sec.currentPassword || '');
      const nw = String(sec.newPassword || '');
      const c = String(sec.confirmPassword || '');

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
        wx.showToast({ title: (res as any)?.message || '密码设置成功', icon: 'none' });
        this.setData({
          'security.currentPassword': '',
          'security.newPassword': '',
          'security.confirmPassword': '',
          'security.msg': (res as any)?.message || '密码设置成功'
        } as any);
        await this.loadAccountSummary(true);
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
      this.setData({ 'security.errorMsg': e?.message || '操作失败，请稍后重试' } as any);
    } finally {
      this.setData({ 'security.submitting': false } as any);
    }
  },

  // ========== 账号：绑定 ==========
  onEmailActionTap() {
    if ((this.data as any).bindings?.loading) return;
    this.setData({ 'bindings.msg': '', 'bindings.errorMsg': '', 'bindings.emailFormOpen': true } as any);
  },

  onCloseEmailFormTap() {
    if ((this.data as any).bindings?.bindingEmail) return;
    this.clearCountdown();
    this.setData({ 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '' } as any);
  },

  onBindEmailInput(e: any) {
    this.setData({ 'bindings.bindEmail': String(e?.detail?.value || '') } as any);
  },

  onBindCodeInput(e: any) {
    this.setData({ 'bindings.bindCode': String(e?.detail?.value || '') } as any);
  },

  getSendCodeText(): string {
    const b: any = (this.data as any).bindings || {};
    if (b.sendingCode) return '发送中…';
    if (b.countdown > 0) return `重发(${b.countdown}s)`;
    return '发送验证码';
  },

  refreshSendCodeUi() {
    const b: any = (this.data as any).bindings || {};
    this.setData({
      'bindings.sendCodeText': this.getSendCodeText(),
      'bindings.sendCodeDisabled': !!b.sendingCode || Number(b.countdown || 0) > 0
    } as any);
  },

  clearCountdown() {
    const self: any = this as any;
    if (self.__countdownTimer) {
      clearTimeout(self.__countdownTimer);
      self.__countdownTimer = null;
    }
    this.setData({ 'bindings.countdown': 0, 'bindings.sendingCode': false } as any);
    this.refreshSendCodeUi();
  },

  tickCountdown() {
    const self: any = this as any;
    const next = Math.max(0, Number((this.data as any).bindings?.countdown || 0) - 1);
    this.setData({ 'bindings.countdown': next } as any);
    this.refreshSendCodeUi();
    if (next <= 0) {
      self.__countdownTimer = null;
      return;
    }
    self.__countdownTimer = setTimeout(() => this.tickCountdown(), 1000);
  },

  async onSendCodeTap() {
    const b: any = (this.data as any).bindings || {};
    if (b.sendingCode || b.countdown > 0) return;

    const v = validateEmail(b.bindEmail);
    if (!v.ok) {
      this.setData({ 'bindings.errorMsg': v.msg || '邮箱格式不正确' } as any);
      return;
    }

    this.setData({ 'bindings.sendingCode': true, 'bindings.msg': '', 'bindings.errorMsg': '' } as any);
    this.refreshSendCodeUi();
    try {
      const res: any = await api.sendEmailBindCode(v.value as string);
      const tip = String(res?.message || '验证码已发送');
      wx.showToast({ title: tip, icon: 'none' });
      this.setData({ 'bindings.msg': tip, 'bindings.countdown': 60 } as any);
      this.refreshSendCodeUi();
      this.tickCountdown();
    } catch (e: any) {
      this.setData({ 'bindings.errorMsg': e?.message || '发送失败，请稍后重试' } as any);
      this.clearCountdown();
    } finally {
      this.setData({ 'bindings.sendingCode': false } as any);
      this.refreshSendCodeUi();
    }
  },

  async onBindEmailTap() {
    const b: any = (this.data as any).bindings || {};
    if (b.bindingEmail) return;

    const v = validateEmail(b.bindEmail);
    if (!v.ok) {
      this.setData({ 'bindings.errorMsg': v.msg || '邮箱格式不正确' } as any);
      return;
    }

    const code = String(b.bindCode || '').trim();
    if (!code || code.length !== 6) {
      this.setData({ 'bindings.errorMsg': '请输入 6 位验证码' } as any);
      return;
    }

    this.setData({ 'bindings.bindingEmail': true, 'bindings.msg': '', 'bindings.errorMsg': '' } as any);
    try {
      await api.bindEmail(v.value as string, code);
      wx.showToast({ title: '邮箱绑定成功', icon: 'none' });
      this.clearCountdown();
      this.setData({ 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '', 'bindings.msg': '邮箱绑定成功' } as any);
      await this.loadAccountSummary(true);
    } catch (e: any) {
      this.setData({ 'bindings.errorMsg': e?.message || '绑定失败，请稍后重试' } as any);
    } finally {
      this.setData({ 'bindings.bindingEmail': false } as any);
    }
  },

  async onWechatBindTap() {
    const b: any = (this.data as any).bindings || {};
    if (b.bindingWechat) return;
    this.setData({ 'bindings.bindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' } as any);
    try {
      const code = await new Promise<string>((resolve) => {
        wx.login({
          success: (res) => resolve(String((res as any)?.code || '')),
          fail: () => resolve('')
        });
      });
      if (!code) throw new Error('获取微信登录 code 失败');

      const res: any = await api.miniWechatBind(code);
      if (res && res.token) wx.setStorageSync('token', res.token);
      if (res && res.user_info) wx.setStorageSync('userInfo', res.user_info);

      wx.showToast({ title: '绑定成功', icon: 'none' });
      this.setData({ 'bindings.msg': '绑定成功' } as any);
      await this.loadAccountSummary(true);
    } catch (e: any) {
      this.setData({ 'bindings.errorMsg': e?.message || '绑定失败，请稍后重试' } as any);
    } finally {
      this.setData({ 'bindings.bindingWechat': false } as any);
    }
  },

  async onWechatUnbindTap() {
    const b: any = (this.data as any).bindings || {};
    if (b.unbindingWechat) return;

    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '确认解绑微信',
        content: '解绑后将无法使用微信一键登录。为保证安全，需要重新登录。',
        confirmText: '解绑',
        cancelText: '取消',
        success: (res) => resolve(!!(res as any)?.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    this.setData({ 'bindings.unbindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' } as any);
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
      this.setData({ 'bindings.errorMsg': e?.message || '解绑失败，请稍后重试' } as any);
    } finally {
      this.setData({ 'bindings.unbindingWechat': false } as any);
    }
  },

  // ========== 主题 ==========
  async onStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData() as any);
    await syncUserSettingsToServer();
    this.setData({ 'theme.msg': '已应用并尝试同步到云端' } as any);
  },

  // ========== 字体 ==========
  onFontStyleTap(e: any) {
    const style = String(e?.currentTarget?.dataset?.style || 'system') as FontStyle;
    fontManager.setStyle(style);
    this.setData(fontManager.getPageData() as any);
    const config = FONT_STYLE_CONFIG[style];
    this.setData({ 'font.msg': `已切换到「${config.name}」字体` } as any);
  },

  // ========== 关于 ==========
  onAboutTabTap(e: any) {
    const tab = String(e?.currentTarget?.dataset?.tab || '').toLowerCase() as AboutTab;
    const next: AboutTab = tab === 'legal' ? 'legal' : 'app';
    if (next === (this.data as any).aboutTab) return;
    this.setData({ aboutTab: next } as any);
    this.resetScroll();
  },

  onToggleContact() {
    const open = !!(this.data as any).about?.contactOpen;
    this.setData({ 'about.contactOpen': !open } as any);
  },

  onGoProfile() {
    this.setData({ navKey: 'account', accTab: 'profile', profileMounted: true } as any);
    this.resetScroll();
    this.loadAccountSummary(false);
  },

  onContactChat() {
    const a: any = (this.data as any).about || {};
    if (a.chatDisabled) {
      wx.showToast({ title: a.chatDisabledReason || '暂不可用', icon: 'none' });
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
  },

  async loadAboutInfo(force = false) {
    const self: any = this as any;
    const now = Date.now();
    const lastAt = Number(self.__aboutLastLoadedAt || 0) || 0;
    if (!force && lastAt && now - lastAt < 8000) {
      this.setData({ 'about.currentUsername': summarizeUsername() } as any);
      return;
    }
    self.__aboutLastLoadedAt = now;

    this.setData({ 'about.errorMsg': '', 'about.currentUsername': summarizeUsername() } as any);
    try {
      const res: any = await api.getSettingsAbout();
      this.setData({
        'about.adminUsername': String(res?.admin_username || ''),
        'about.adminEmail': String(res?.admin_email || ''),
        'about.adminWechat': String(res?.admin_wechat || ''),
        'about.chatDisabled': !!res?.chat_disabled,
        'about.chatDisabledReason': String(res?.chat_disabled_reason || '')
      } as any);
    } catch (e: any) {
      this.setData({ 'about.errorMsg': e?.message || '加载失败，请稍后重试' } as any);
    }
  },

  buildSecurityMode(hasPasswordSet: boolean) {
    const isSetPassword = !hasPasswordSet;
    return {
      hasPasswordSet,
      pwdChip: hasPasswordSet ? '已设置密码' : '未设置密码',
      pwdSub: hasPasswordSet ? '修改登录密码。修改成功后需要重新登录。' : '为账号设置登录密码（首次设置无需填写当前密码）。',
      submitText: isSetPassword ? '设置密码' : '修改密码'
    };
  },

  buildBindingsProfile(p: any) {
    const email = String(p?.email || '').trim();
    const verified = !!p?.email_verified;
    const emailChip = email ? (verified ? '已绑定' : '已绑定(未验证)') : '未绑定';
    const emailDesc = email ? `当前邮箱：${email}${verified ? '' : '（未验证）'}` : '绑定邮箱用于接收验证码与找回账号。';
    const emailActionText = email ? '更换' : '绑定';

    const wechatBound = !!p?.wechat_bound;
    const wechatChip = wechatBound ? '已绑定' : '未绑定';
    const wechatDesc = wechatBound ? '已绑定微信，可使用微信一键登录。' : '绑定微信后可使用微信一键登录。';

    return { wechatBound, emailChip, emailDesc, emailActionText, wechatChip, wechatDesc };
  },

  async loadAccountSummary(force = false) {
    const self: any = this as any;
    const now = Date.now();
    const lastAt = Number(self.__accountLastLoadedAt || 0) || 0;
    if (!force && lastAt && now - lastAt < 8000) return;
    self.__accountLastLoadedAt = now;

    if (!(this.data as any).profileMounted) this.setData({ profileMounted: true } as any);
    if (this.data.navKey === 'account') {
      if (this.data.accTab === 'security' && !(this.data as any).securityMounted) this.setData({ securityMounted: true } as any);
      if (this.data.accTab === 'bindings' && !(this.data as any).bindingsMounted) this.setData({ bindingsMounted: true } as any);
    }

    this.setData({
      'profile.loading': true,
      'security.loading': true,
      'bindings.loading': true,
      'profile.errorMsg': '',
      'security.errorMsg': '',
      'bindings.errorMsg': ''
    } as any);
    try {
      const p: any = await api.getProfile();

      const username = String(p?.username || '用户');
      const avatar = decorateAvatarUrl(resolveUploadUrl(p?.avatar));
      const isAdmin = !!p?.is_admin;
      const createdAtText = p?.created_at ? `注册时间 ${String(p.created_at)}` : '—';
      const college = String(p?.college || '');
      const contact = String(p?.contact || '');
      const signature = String(p?.signature || '');

      const emailMasked = maskEmail(p?.email);
      const emailVerified = !!p?.email_verified;
      const hasPasswordSet = !!p?.has_password_set;
      const wechatBound = !!p?.wechat_bound;

      const emailBadge = p?.email ? (emailVerified ? '已验证' : '未验证') : '未绑定';
      const passwordBadge = hasPasswordSet ? '已设置' : '未设置';
      const wechatBadge = wechatBound ? '已绑定' : '未绑定';

      this.setData({
        profile: {
          ...(this.data as any).profile,
          username,
          avatarUrl: avatar || '/images/default-avatar.png',
          avatarInitial: (username || 'U').charAt(0).toUpperCase(),
          roleText: isAdmin ? '管理员' : '普通用户',
          createdAtText,
          college,
          contact,
          signature,
          signatureCount: signature.length,
          emailMasked: emailMasked || '未绑定',
          emailBadge,
          passwordBadge,
          wechatBadge
        },
        security: { ...(this.data as any).security, ...this.buildSecurityMode(hasPasswordSet) },
        bindings: { ...(this.data as any).bindings, ...this.buildBindingsProfile(p) }
      } as any);

      self.__originalProfile = { college, contact, signature };
      this.refreshSendCodeUi();
    } catch (e: any) {
      const err = e?.message || '加载失败，请稍后重试';
      this.setData({
        'profile.errorMsg': err,
        'security.errorMsg': err,
        'bindings.errorMsg': err,
        security: { ...(this.data as any).security, ...this.buildSecurityMode(false) },
        bindings: { ...(this.data as any).bindings, ...this.buildBindingsProfile({}) }
      } as any);
      this.refreshSendCodeUi();
    } finally {
      this.setData({ 'profile.loading': false, 'security.loading': false, 'bindings.loading': false } as any);
    }
  }
});

