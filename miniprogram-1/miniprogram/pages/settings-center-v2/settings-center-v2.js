'use strict';

const { api, resolveUploadUrl } = require('../../utils/api');
const { checkLogin, logout } = require('../../utils/auth');
const { safeNavigate } = require('../../utils/nav');
const { syncUserSettingsToServer } = require('../../utils/user-settings');
const { buildLastPracticeUrl } = require('../../utils/last-practice');
const { themeManager } = require('../../utils/theme');
const { bumpAvatarRev, decorateAvatarUrl } = require('../../utils/avatar');

function normalizeNavKey(raw) {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'practice' || v === 'theme' || v === 'about') return v;
  return 'account';
}

function normalizeAccTab(raw) {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'security' || v === 'bindings') return v;
  return 'profile';
}

function normalizeAboutTab(raw) {
  const v = String(raw || '').trim().toLowerCase();
  return v === 'legal' ? 'legal' : 'app';
}

function maskEmail(email) {
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

function clampLen(s, max) {
  const v = String(s || '');
  if (v.length <= max) return v;
  return v.slice(0, max);
}

function isStrongPassword(pwd) {
  const v = String(pwd || '');
  if (v.length < 8) return false;
  return /[a-zA-Z]/.test(v) && /\d/.test(v);
}

function validateEmail(email) {
  const v = String(email || '').trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!v) return { ok: false, msg: '请输入邮箱地址' };
  if (!emailRegex.test(v)) return { ok: false, msg: '邮箱格式不正确' };
  return { ok: true, value: v };
}

function summarizeUsername() {
  const userInfo = wx.getStorageSync('userInfo') || {};
  const name = String(userInfo.username || userInfo.name || userInfo.email || '').trim();
  return name || '已登录';
}

function bumpScrollTop(n) {
  const v = Number(n || 0) || 0;
  return v === 0 ? 1 : 0;
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'account',
    accTab: 'profile',
    aboutTab: 'app',
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
      wechatBadge: '未绑定',
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
      showConfirm: false,
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
      unbindingWechat: false,
    },

    practice: { msg: '' },
    theme: { msg: '' },

    about: {
      errorMsg: '',
      contactOpen: false,
      currentUsername: '—',

      adminUsername: '',
      adminEmail: '',
      adminWechat: '',
      chatDisabled: true,
      chatDisabledReason: '',
    },
  },

  onLoad(options) {
    const navKey = normalizeNavKey(options && (options.navKey || options.nav || options.tab));
    const accTab = normalizeAccTab(options && (options.accTab || options.acc || options.sub));
    const aboutTab = normalizeAboutTab(options && (options.aboutTab || options.about));

    const patch = { navKey, accTab, aboutTab };
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
      const edit = String((options && options.edit) || '');
      if (edit === '1' && navKey === 'account' && accTab === 'profile') {
        this.setData({ 'profile.editing': true });
      }
    } catch (e) {}
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
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

  ensureTabLoaded(force) {
    const navKey = this.data.navKey;
    if (navKey === 'account') return this.loadAccountSummary(!!force);
    if (navKey === 'about') return this.loadAboutInfo(!!force);
    if (navKey === 'theme' && !this.data.themeMounted) this.setData({ themeMounted: true });
    if (navKey === 'practice' && !this.data.practiceMounted) this.setData({ practiceMounted: true });
    return Promise.resolve();
  },

  resetScroll() {
    this.setData({ scrollTop: bumpScrollTop(this.data.scrollTop) });
  },

  onHamburgerTap() {
    this.setData({ drawerOpen: true });
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false });
  },

  onDrawerNavigate(e) {
    const url = e && e.detail && e.detail.url;
    const navType = e && e.detail && e.detail.navType;
    this.setData({ drawerOpen: false });
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e) {
    const style = (e && e.detail && e.detail.style) || 'default';
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode();
    this.setData({ ...themeManager.getPageData(), themeMode: mode });
  },

  onContinueLast() {
    const url = buildLastPracticeUrl();
    if (!url) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }
    wx.navigateTo({ url });
  },

  onSettingsNavTap(e) {
    const key = normalizeNavKey(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.key);
    if (!key || key === this.data.navKey) return;

    const patch = { navKey: key };
    if (key === 'practice') patch.practiceMounted = true;
    if (key === 'theme') patch.themeMounted = true;
    if (key === 'about') patch.aboutMounted = true;
    if (key === 'account') {
      const acc = this.data.accTab;
      if (acc === 'profile') patch.profileMounted = true;
      if (acc === 'security') patch.securityMounted = true;
      if (acc === 'bindings') patch.bindingsMounted = true;
    }

    this.setData(patch);
    this.resetScroll();
    this.ensureTabLoaded(false);
  },

  onAccountSubTap(e) {
    const key = normalizeAccTab(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.key);
    if (!key) return;
    if (this.data.navKey !== 'account') this.setData({ navKey: 'account' });
    if (key === this.data.accTab) return;

    const patch = { accTab: key };
    if (key === 'profile') patch.profileMounted = true;
    if (key === 'security') patch.securityMounted = true;
    if (key === 'bindings') patch.bindingsMounted = true;

    this.setData(patch);
    this.resetScroll();
    this.loadAccountSummary(false);
  },

  // ===== 账号：资料 =====
  onEdit() {
    this.setData({ 'profile.editing': true, 'profile.msg': '', 'profile.errorMsg': '' });
  },

  onCancel() {
    const original = this.__originalProfile || {};
    const signature = String(original.signature || '');
    this.setData({
      'profile.editing': false,
      'profile.msg': '',
      'profile.errorMsg': '',
      'profile.college': String(original.college || ''),
      'profile.contact': String(original.contact || ''),
      'profile.signature': signature,
      'profile.signatureCount': signature.length,
    });
  },

  onCollegeInput(e) {
    const v = clampLen(e && e.detail && e.detail.value, 40);
    this.setData({ 'profile.college': v });
  },

  onContactInput(e) {
    const v = clampLen(e && e.detail && e.detail.value, 60);
    this.setData({ 'profile.contact': v });
  },

  onSignatureInput(e) {
    const v = clampLen(e && e.detail && e.detail.value, 80);
    this.setData({ 'profile.signature': v, 'profile.signatureCount': v.length });
  },

  async onSave() {
    if (this.data.profile && this.data.profile.saving) return;
    this.setData({ 'profile.saving': true, 'profile.msg': '', 'profile.errorMsg': '' });
    try {
      await api.updateProfile({
        college: String((this.data.profile && this.data.profile.college) || '').trim(),
        contact: String((this.data.profile && this.data.profile.contact) || '').trim(),
        signature: String((this.data.profile && this.data.profile.signature) || '').trim(),
      });
      this.setData({ 'profile.editing': false, 'profile.msg': '已保存' });
      await this.loadAccountSummary(true);
    } catch (e) {
      this.setData({ 'profile.errorMsg': (e && e.message) || '保存失败，请稍后重试' });
    } finally {
      this.setData({ 'profile.saving': false });
    }
  },

  async onAvatarTap() {
    const p = this.data.profile || {};
    if (p.loading || p.saving) return;

    const currentUrl = String(p.avatarUrl || '').trim();
    if (currentUrl) {
      const idx = await new Promise((resolve) => {
        wx.showActionSheet({
          itemList: ['预览头像', '更换头像'],
          success: (res) => resolve(Number(res && res.tapIndex)),
          fail: () => resolve(-1),
        });
      });
      if (idx === 0) {
        wx.previewImage({ urls: [currentUrl], current: currentUrl });
        return;
      }
      if (idx !== 1) return;
    }

    const filePath = await new Promise((resolve) => {
      const pick = wx.chooseMedia ? 'chooseMedia' : 'chooseImage';
      if (pick === 'chooseMedia') {
        wx.chooseMedia({
          count: 1,
          mediaType: ['image'],
          sourceType: ['album', 'camera'],
          success: (res) => resolve(String(res && res.tempFiles && res.tempFiles[0] && res.tempFiles[0].tempFilePath) || ''),
          fail: () => resolve(''),
        });
        return;
      }

      wx.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => resolve(String(res && res.tempFilePaths && res.tempFilePaths[0]) || ''),
        fail: () => resolve(''),
      });
    });

    if (!filePath) return;

    this.setData({ 'profile.msg': '', 'profile.errorMsg': '' });
    wx.showLoading({ title: '上传中…', mask: true });
    try {
      const res = await api.uploadProfileAvatar(filePath);
      bumpAvatarRev();
      const url = decorateAvatarUrl(resolveUploadUrl(res && res.avatar_url));
      this.setData({ 'profile.avatarUrl': url, 'profile.msg': '头像已更新' });
      await this.loadAccountSummary(true);
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '上传失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onAvatarError() {
    const url = String((this.data.profile && this.data.profile.avatarUrl) || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) {
      this.setData({ 'profile.avatarUrl': '' });
      return;
    }

    if (this.__avatarDlTried) {
      this.setData({ 'profile.avatarUrl': '' });
      return;
    }
    this.__avatarDlTried = true;

    wx.downloadFile({
      url,
      timeout: 15000,
      success: (res) => {
        const tempFilePath = String(res && res.tempFilePath).trim();
        this.setData({ 'profile.avatarUrl': tempFilePath || '' });
      },
      fail: () => {
        this.setData({ 'profile.avatarUrl': '' });
      },
    });
  },

  // ===== 账号：安全 =====
  onToggleShow(e) {
    const target = String(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.target);
    const sec = this.data.security || {};
    if (target === 'current') this.setData({ 'security.showCurrent': !sec.showCurrent });
    if (target === 'new') this.setData({ 'security.showNew': !sec.showNew });
    if (target === 'confirm') this.setData({ 'security.showConfirm': !sec.showConfirm });
  },

  onCurrentInput(e) {
    this.setData({ 'security.currentPassword': String(e && e.detail && e.detail.value) || '' });
  },

  onNewInput(e) {
    this.setData({ 'security.newPassword': String(e && e.detail && e.detail.value) || '' });
  },

  onConfirmInput(e) {
    this.setData({ 'security.confirmPassword': String(e && e.detail && e.detail.value) || '' });
  },

  onReset() {
    if (this.data.security && this.data.security.submitting) return;
    this.setData({
      'security.msg': '',
      'security.errorMsg': '',
      'security.currentPassword': '',
      'security.newPassword': '',
      'security.confirmPassword': '',
    });
  },

  async onSubmit() {
    const sec = this.data.security || {};
    if (sec.submitting) return;
    this.setData({ 'security.submitting': true, 'security.msg': '', 'security.errorMsg': '' });
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
        is_set_password: isSetPassword,
      });

      if (isSetPassword) {
        wx.showToast({ title: (res && res.message) || '密码设置成功', icon: 'none' });
        this.setData({
          'security.currentPassword': '',
          'security.newPassword': '',
          'security.confirmPassword': '',
          'security.msg': (res && res.message) || '密码设置成功',
        });
        await this.loadAccountSummary(true);
        return;
      }

      await new Promise((resolve) => {
        wx.showModal({
          title: '修改成功',
          content: '为保证安全，需要重新登录。',
          showCancel: false,
          confirmText: '去登录',
          success: () => resolve(),
        });
      });
      logout();
      wx.redirectTo({ url: '/pages/login/login' });
    } catch (e) {
      this.setData({ 'security.errorMsg': (e && e.message) || '操作失败，请稍后重试' });
    } finally {
      this.setData({ 'security.submitting': false });
    }
  },

  // ===== 账号：绑定 =====
  onEmailActionTap() {
    if (this.data.bindings && this.data.bindings.loading) return;
    this.setData({ 'bindings.msg': '', 'bindings.errorMsg': '', 'bindings.emailFormOpen': true });
  },

  onCloseEmailFormTap() {
    if (this.data.bindings && this.data.bindings.bindingEmail) return;
    this.clearCountdown();
    this.setData({ 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '' });
  },

  onBindEmailInput(e) {
    this.setData({ 'bindings.bindEmail': String(e && e.detail && e.detail.value) || '' });
  },

  onBindCodeInput(e) {
    this.setData({ 'bindings.bindCode': String(e && e.detail && e.detail.value) || '' });
  },

  getSendCodeText() {
    const b = this.data.bindings || {};
    if (b.sendingCode) return '发送中…';
    if (b.countdown > 0) return `重发(${b.countdown}s)`;
    return '发送验证码';
  },

  refreshSendCodeUi() {
    const b = this.data.bindings || {};
    this.setData({
      'bindings.sendCodeText': this.getSendCodeText(),
      'bindings.sendCodeDisabled': !!b.sendingCode || Number(b.countdown || 0) > 0,
    });
  },

  clearCountdown() {
    if (this.__countdownTimer) {
      clearTimeout(this.__countdownTimer);
      this.__countdownTimer = null;
    }
    this.setData({ 'bindings.countdown': 0, 'bindings.sendingCode': false });
    this.refreshSendCodeUi();
  },

  tickCountdown() {
    const next = Math.max(0, Number((this.data.bindings && this.data.bindings.countdown) || 0) - 1);
    this.setData({ 'bindings.countdown': next });
    this.refreshSendCodeUi();
    if (next <= 0) {
      this.__countdownTimer = null;
      return;
    }
    this.__countdownTimer = setTimeout(() => this.tickCountdown(), 1000);
  },

  async onSendCodeTap() {
    const b = this.data.bindings || {};
    if (b.sendingCode || b.countdown > 0) return;

    const v = validateEmail(b.bindEmail);
    if (!v.ok) {
      this.setData({ 'bindings.errorMsg': v.msg || '邮箱格式不正确' });
      return;
    }

    this.setData({ 'bindings.sendingCode': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
    this.refreshSendCodeUi();
    try {
      const res = await api.sendEmailBindCode(v.value);
      const tip = String((res && res.message) || '验证码已发送');
      wx.showToast({ title: tip, icon: 'none' });
      this.setData({ 'bindings.msg': tip, 'bindings.countdown': 60 });
      this.refreshSendCodeUi();
      this.tickCountdown();
    } catch (e) {
      this.setData({ 'bindings.errorMsg': (e && e.message) || '发送失败，请稍后重试' });
      this.clearCountdown();
    } finally {
      this.setData({ 'bindings.sendingCode': false });
      this.refreshSendCodeUi();
    }
  },

  async onBindEmailTap() {
    const b = this.data.bindings || {};
    if (b.bindingEmail) return;

    const v = validateEmail(b.bindEmail);
    if (!v.ok) {
      this.setData({ 'bindings.errorMsg': v.msg || '邮箱格式不正确' });
      return;
    }

    const code = String(b.bindCode || '').trim();
    if (!code || code.length !== 6) {
      this.setData({ 'bindings.errorMsg': '请输入 6 位验证码' });
      return;
    }

    this.setData({ 'bindings.bindingEmail': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
    try {
      await api.bindEmail(v.value, code);
      wx.showToast({ title: '邮箱绑定成功', icon: 'none' });
      this.clearCountdown();
      this.setData({ 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '', 'bindings.msg': '邮箱绑定成功' });
      await this.loadAccountSummary(true);
    } catch (e) {
      this.setData({ 'bindings.errorMsg': (e && e.message) || '绑定失败，请稍后重试' });
    } finally {
      this.setData({ 'bindings.bindingEmail': false });
    }
  },

  async onWechatBindTap() {
    const b = this.data.bindings || {};
    if (b.bindingWechat) return;
    this.setData({ 'bindings.bindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
    try {
      const code = await new Promise((resolve) => {
        wx.login({
          success: (res) => resolve(String(res && res.code) || ''),
          fail: () => resolve(''),
        });
      });
      if (!code) throw new Error('获取微信登录 code 失败');

      const res = await api.miniWechatBind(code);
      if (res && res.token) wx.setStorageSync('token', res.token);
      if (res && res.user_info) wx.setStorageSync('userInfo', res.user_info);

      wx.showToast({ title: '绑定成功', icon: 'none' });
      this.setData({ 'bindings.msg': '绑定成功' });
      await this.loadAccountSummary(true);
    } catch (e) {
      this.setData({ 'bindings.errorMsg': (e && e.message) || '绑定失败，请稍后重试' });
    } finally {
      this.setData({ 'bindings.bindingWechat': false });
    }
  },

  async onWechatUnbindTap() {
    const b = this.data.bindings || {};
    if (b.unbindingWechat) return;

    const ok = await new Promise((resolve) => {
      wx.showModal({
        title: '确认解绑微信',
        content: '解绑后将无法使用微信一键登录。为保证安全，需要重新登录。',
        confirmText: '解绑',
        cancelText: '取消',
        success: (res) => resolve(!!(res && res.confirm)),
        fail: () => resolve(false),
      });
    });
    if (!ok) return;

    this.setData({ 'bindings.unbindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
    try {
      await api.wechatUnbind();
      await new Promise((resolve) => {
        wx.showModal({
          title: '解绑成功',
          content: '需要重新登录。',
          showCancel: false,
          confirmText: '去登录',
          success: () => resolve(),
        });
      });
      logout();
      wx.redirectTo({ url: '/pages/login/login' });
    } catch (e) {
      this.setData({ 'bindings.errorMsg': (e && e.message) || '解绑失败，请稍后重试' });
    } finally {
      this.setData({ 'bindings.unbindingWechat': false });
    }
  },

  // ===== 主题 =====
  onModeTap(e) {
    const mode = String(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.mode) || 'system';
    if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
    themeManager.setMode(mode);
    this.setData(themeManager.getPageData());
    const label = mode === 'light' ? '浅色' : mode === 'dark' ? '深色' : '跟随系统';
    this.setData({ 'theme.msg': `已切换到「${label}」` });
  },

  async onStyleTap(e) {
    const style = String(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.style) || 'default';
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    await syncUserSettingsToServer();
    this.setData({ 'theme.msg': '已应用并尝试同步到云端' });
  },

  // ===== 关于 =====
  onAboutTabTap(e) {
    const tab = String(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.tab).toLowerCase();
    const next = tab === 'legal' ? 'legal' : 'app';
    if (next === this.data.aboutTab) return;
    this.setData({ aboutTab: next });
    this.resetScroll();
  },

  onToggleContact() {
    const open = !!(this.data.about && this.data.about.contactOpen);
    this.setData({ 'about.contactOpen': !open });
  },

  onGoProfile() {
    this.setData({ navKey: 'account', accTab: 'profile', profileMounted: true });
    this.resetScroll();
    this.loadAccountSummary(false);
  },

  onContactChat() {
    const a = this.data.about || {};
    if (a.chatDisabled) {
      wx.showToast({ title: a.chatDisabledReason || '暂不可用', icon: 'none' });
      return;
    }
    wx.showToast({ title: '小程序暂不支持站内聊天，请在 Web 端打开 /contact_admin', icon: 'none' });
  },

  onCopy(e) {
    const v = String(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.value).trim();
    if (!v) return;
    wx.setClipboardData({
      data: v,
      success: () => wx.showToast({ title: '已复制', icon: 'none' }),
      fail: () => wx.showToast({ title: '复制失败', icon: 'none' }),
    });
  },

  onOpenTerms() {
    wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /terms', icon: 'none' });
  },

  onOpenPrivacy() {
    wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /privacy', icon: 'none' });
  },

  async loadAboutInfo(force) {
    const now = Date.now();
    const lastAt = Number(this.__aboutLastLoadedAt || 0) || 0;
    if (!force && lastAt && now - lastAt < 8000) {
      this.setData({ 'about.currentUsername': summarizeUsername() });
      return;
    }
    this.__aboutLastLoadedAt = now;

    this.setData({ 'about.errorMsg': '', 'about.currentUsername': summarizeUsername() });
    try {
      const res = await api.getSettingsAbout();
      this.setData({
        'about.adminUsername': String((res && res.admin_username) || ''),
        'about.adminEmail': String((res && res.admin_email) || ''),
        'about.adminWechat': String((res && res.admin_wechat) || ''),
        'about.chatDisabled': !!(res && res.chat_disabled),
        'about.chatDisabledReason': String((res && res.chatDisabledReason) || (res && res.chat_disabled_reason) || ''),
      });
    } catch (e) {
      this.setData({ 'about.errorMsg': (e && e.message) || '加载失败，请稍后重试' });
    }
  },

  buildSecurityMode(hasPasswordSet) {
    const isSetPassword = !hasPasswordSet;
    return {
      hasPasswordSet,
      pwdChip: hasPasswordSet ? '已设置密码' : '未设置密码',
      pwdSub: hasPasswordSet ? '修改登录密码。修改成功后需要重新登录。' : '为账号设置登录密码（首次设置无需填写当前密码）。',
      submitText: isSetPassword ? '设置密码' : '修改密码',
    };
  },

  buildBindingsProfile(p) {
    const email = String((p && p.email) || '').trim();
    const verified = !!(p && p.email_verified);
    const emailChip = email ? (verified ? '已绑定' : '已绑定(未验证)') : '未绑定';
    const emailDesc = email ? `当前邮箱：${email}${verified ? '' : '（未验证）'}` : '绑定邮箱用于接收验证码与找回账号。';
    const emailActionText = email ? '更换' : '绑定';

    const wechatBound = !!(p && p.wechat_bound);
    const wechatChip = wechatBound ? '已绑定' : '未绑定';
    const wechatDesc = wechatBound ? '已绑定微信，可使用微信一键登录。' : '绑定微信后可使用微信一键登录。';

    return { wechatBound, emailChip, emailDesc, emailActionText, wechatChip, wechatDesc };
  },

  async loadAccountSummary(force) {
    const now = Date.now();
    const lastAt = Number(this.__accountLastLoadedAt || 0) || 0;
    if (!force && lastAt && now - lastAt < 8000) return;
    this.__accountLastLoadedAt = now;

    if (!this.data.profileMounted) this.setData({ profileMounted: true });
    if (this.data.navKey === 'account') {
      if (this.data.accTab === 'security' && !this.data.securityMounted) this.setData({ securityMounted: true });
      if (this.data.accTab === 'bindings' && !this.data.bindingsMounted) this.setData({ bindingsMounted: true });
    }

    this.setData({
      'profile.loading': true,
      'security.loading': true,
      'bindings.loading': true,
      'profile.errorMsg': '',
      'security.errorMsg': '',
      'bindings.errorMsg': '',
    });
    try {
      const p = await api.getProfile();

      const username = String((p && p.username) || '用户');
      const avatar = decorateAvatarUrl(resolveUploadUrl(p && p.avatar));
      const isAdmin = !!(p && p.is_admin);
      const createdAtText = p && p.created_at ? `注册时间 ${String(p.created_at)}` : '—';
      const college = String((p && p.college) || '');
      const contact = String((p && p.contact) || '');
      const signature = String((p && p.signature) || '');

      const emailMasked = maskEmail(p && p.email);
      const emailVerified = !!(p && p.email_verified);
      const hasPasswordSet = !!(p && p.has_password_set);
      const wechatBound = !!(p && p.wechat_bound);

      const emailBadge = (p && p.email) ? (emailVerified ? '已验证' : '未验证') : '未绑定';
      const passwordBadge = hasPasswordSet ? '已设置' : '未设置';
      const wechatBadge = wechatBound ? '已绑定' : '未绑定';

      this.setData({
        profile: {
          ...this.data.profile,
          username,
          avatarUrl: avatar,
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
          wechatBadge,
        },
        security: {
          ...this.data.security,
          ...this.buildSecurityMode(hasPasswordSet),
        },
        bindings: {
          ...this.data.bindings,
          ...this.buildBindingsProfile(p),
        },
      });

      this.__originalProfile = { college, contact, signature };
      this.refreshSendCodeUi();
    } catch (e) {
      const err = (e && e.message) || '加载失败，请稍后重试';
      this.setData({
        'profile.errorMsg': err,
        'security.errorMsg': err,
        'bindings.errorMsg': err,
        security: { ...this.data.security, ...this.buildSecurityMode(false) },
        bindings: { ...this.data.bindings, ...this.buildBindingsProfile({}) },
      });
      this.refreshSendCodeUi();
    } finally {
      this.setData({ 'profile.loading': false, 'security.loading': false, 'bindings.loading': false });
    }
  },
});

