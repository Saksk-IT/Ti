import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { bumpAvatarRev, decorateAvatarUrl } from '../../utils/avatar';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';
type AccountSubKey = 'profile' | 'security' | 'bindings';

function navTo(key: SettingsNavKey): string {
  if (key === 'practice') return '/pages/settings-practice-v2/settings-practice-v2';
  if (key === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-account-profile-v2/settings-account-profile-v2';
}

function accTo(key: AccountSubKey): string {
  if (key === 'security') return '/pages/settings-account-security-v2/settings-account-security-v2';
  if (key === 'bindings') return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
  return '/pages/settings-account-profile-v2/settings-account-profile-v2';
}

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

function clampLen(s: any, max: number): string {
  const v = String(s || '');
  if (v.length <= max) return v;
  return v.slice(0, max);
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'account' as SettingsNavKey,
    accTab: 'profile' as AccountSubKey,
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

  onLoad(options: any) {
    const qs: string[] = ['navKey=account', 'accTab=profile'];
    try {
      const edit = String(options?.edit || '');
      if (edit === '1') qs.push('edit=1');
    } catch (e) {}

    wx.redirectTo({ url: `/pages/settings-center-v2/settings-center-v2?${qs.join('&')}` });
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
    if (url === '/pages/settings-account-profile-v2/settings-account-profile-v2') return;
    wx.redirectTo({ url });
  },

  onAccountSubTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as AccountSubKey;
    if (!key) return;
    const url = accTo(key);
    if (url === '/pages/settings-account-profile-v2/settings-account-profile-v2') return;
    wx.redirectTo({ url });
  },

  onEdit() {
    this.setData({ editing: true, msg: '', errorMsg: '' });
  },

  onCancel() {
    const self: any = this as any;
    const original = self.__originalProfile || {};
    this.setData({
      editing: false,
      msg: '',
      errorMsg: '',
      college: String(original.college || ''),
      contact: String(original.contact || ''),
      signature: String(original.signature || ''),
      signatureCount: String(original.signature || '').length
    });
  },

  onCollegeInput(e: any) {
    const v = clampLen(e?.detail?.value, 40);
    this.setData({ college: v });
  },

  onContactInput(e: any) {
    const v = clampLen(e?.detail?.value, 60);
    this.setData({ contact: v });
  },

  onSignatureInput(e: any) {
    const v = clampLen(e?.detail?.value, 80);
    this.setData({ signature: v, signatureCount: v.length });
  },

  async onSave() {
    if (this.data.saving) return;
    this.setData({ saving: true, msg: '', errorMsg: '' });
    try {
      await api.updateProfile({
        college: String(this.data.college || '').trim(),
        contact: String(this.data.contact || '').trim(),
        signature: String(this.data.signature || '').trim()
      });
      this.setData({ editing: false, msg: '已保存' });
      await this.loadProfile(true);
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '保存失败，请稍后重试' });
    } finally {
      this.setData({ saving: false });
    }
  },

  async onAvatarTap() {
    if (this.data.loading || this.data.saving) return;

    const currentUrl = String(this.data.avatarUrl || '').trim();
    if (currentUrl) {
      const idx = await new Promise<number>((resolve) => {
        wx.showActionSheet({
          itemList: ['预览头像', '更换头像', '使用微信头像'],
          success: (res) => resolve(Number(res?.tapIndex)),
          fail: () => resolve(-1)
        });
      });
      if (idx === 0) {
        wx.previewImage({ urls: [currentUrl], current: currentUrl });
        return;
      }
      if (idx === 2) {
        await this.useWechatAvatar();
        return;
      }
      if (idx !== 1) return;
    } else {
      // 没有头像时，显示选择菜单
      const idx = await new Promise<number>((resolve) => {
        wx.showActionSheet({
          itemList: ['从相册/相机选择', '使用微信头像'],
          success: (res) => resolve(Number(res?.tapIndex)),
          fail: () => resolve(-1)
        });
      });
      if (idx === 1) {
        await this.useWechatAvatar();
        return;
      }
      if (idx !== 0) return;
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
        success: (res) => resolve(String(res?.tempFilePaths?.[0] || '')),
        fail: () => resolve('')
      });
    });

    if (!filePath) return;

    this.setData({ msg: '', errorMsg: '' });
    wx.showLoading({ title: '上传中…', mask: true });
    try {
      const res = await api.uploadProfileAvatar(filePath);
      bumpAvatarRev();
      const url = decorateAvatarUrl(resolveUploadUrl(res?.avatar_url));
      this.setData({ avatarUrl: url, msg: '头像已更新' });
      await this.loadProfile(true);
    } catch (e: any) {
      wx.showToast({ title: e?.message || '上传失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  // 使用微信头像
  async useWechatAvatar() {
    // 先尝试从缓存获取
    let avatarUrl = '';
    const cachedInfo = wx.getStorageSync('wechatUserInfo');
    if (cachedInfo && cachedInfo.avatarUrl) {
      avatarUrl = cachedInfo.avatarUrl;
    }

    // 如果缓存没有，尝试调用 getUserProfile 获取
    if (!avatarUrl) {
      avatarUrl = await new Promise<string>((resolve) => {
        (wx as any).getUserProfile?.({
          desc: '用于设置账号头像',
          success: (res: any) => {
            const info = res?.userInfo || {};
            if (info.avatarUrl) {
              // 缓存微信用户信息
              wx.setStorageSync('wechatUserInfo', {
                nickName: info.nickName,
                avatarUrl: info.avatarUrl
              });
            }
            resolve(info.avatarUrl || '');
          },
          fail: () => resolve('')
        }) || resolve('');
      });
    }

    if (!avatarUrl) {
      wx.showToast({ title: '无法获取微信头像', icon: 'none' });
      return;
    }

    // 下载微信头像并上传
    this.setData({ msg: '', errorMsg: '' });
    wx.showLoading({ title: '设置中…', mask: true });
    try {
      // 下载微信头像到本地
      const tempFilePath = await new Promise<string>((resolve, reject) => {
        wx.downloadFile({
          url: avatarUrl,
          success: (res) => {
            if (res.statusCode === 200 && res.tempFilePath) {
              resolve(res.tempFilePath);
            } else {
              reject(new Error('下载失败'));
            }
          },
          fail: () => reject(new Error('下载失败'))
        });
      });

      // 上传到服务器
      const res = await api.uploadProfileAvatar(tempFilePath);
      bumpAvatarRev();
      const url = decorateAvatarUrl(resolveUploadUrl(res?.avatar_url));
      this.setData({ avatarUrl: url, msg: '头像已更新' });
      await this.loadProfile(true);
    } catch (e: any) {
      wx.showToast({ title: e?.message || '设置失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
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
      });

      self.__originalProfile = { college, contact, signature };
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后重试' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
