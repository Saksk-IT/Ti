import { api } from '../../utils/api';
import { checkLogin, wechatLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';

type JoinMode = 'token' | 'code';

const PENDING_MINI_REDIRECT_KEY = 'pendingMiniRedirect';

function setPendingMiniRedirect(url: string): void {
  try {
    const s = String(url || '').trim();
    if (!s) return;
    wx.setStorageSync(PENDING_MINI_REDIRECT_KEY, s);
  } catch (e) {}
}

function clearPendingMiniRedirect(): void {
  try {
    wx.removeStorageSync(PENDING_MINI_REDIRECT_KEY);
  } catch (e) {}
}

function normalizeTokenFromShareLink(input: any): string {
  const s = String(input || '').trim();
  if (!s) return '';
  if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?')) return s;

  const tokenMatch = s.match(/[?&]token=([^&#]+)/i);
  if (tokenMatch && tokenMatch[1]) {
    try {
      return decodeURIComponent(tokenMatch[1]);
    } catch {
      return tokenMatch[1];
    }
  }
  return '';
}

Page({
  data: {
    mode: 'code' as JoinMode,
    token: '',
    shareCode: '',
    loading: false,
    errorMsg: ''
  },

  async onLoad(options: any) {
    const rawToken = options?.token || options?.share_token || '';
    let token = normalizeTokenFromShareLink(rawToken);
    // 兼容：扫码/二维码场景可能走 scene 参数
    if (!token) {
      const scene = String(options?.scene || '').trim();
      if (scene) {
        try {
          token = normalizeTokenFromShareLink(decodeURIComponent(scene)) || normalizeTokenFromShareLink(scene);
        } catch {
          token = normalizeTokenFromShareLink(scene);
        }
      }
    }
    const shareCode = String(options?.share_code || options?.code || '').trim().toUpperCase();

    const mode: JoinMode = token ? 'token' : 'code';
    this.setData({ mode, token, shareCode });

    // 打开分享即加入：token / share_code 都直接尝试加入，不再走“预览/确认”
    if (token) {
      await this.autoJoinByToken(token);
      return;
    }
    if (shareCode && shareCode.length === 6) {
      await this.joinByCode(shareCode);
    }
  },

  onShareCodeInput(e: any) {
    const v = String(e?.detail?.value || '').trim().toUpperCase();
    this.setData({ shareCode: v, errorMsg: '' });
  },

  async ensureLoggedIn(nextUrl: string): Promise<boolean> {
    if (checkLogin()) return true;
    setPendingMiniRedirect(nextUrl);
    try {
      const result = await wechatLogin();
      if (result === 'success') return true;
      if (result === 'need_bind') {
        wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
        return false;
      }
    } catch (e) {
      wx.redirectTo({ url: '/pages/login/login' });
      return false;
    }
    wx.redirectTo({ url: '/pages/login/login' });
    return false;
  },

  async autoJoinByToken(token: string) {
    const t = String(token || '').trim();
    if (!t) return;
    if (this.data.loading) return;

    const nextUrl = `/pages/bank-join/bank-join?token=${encodeURIComponent(t)}`;
    const ok = await this.ensureLoggedIn(nextUrl);
    if (!ok) return;

    this.setData({ loading: true, errorMsg: '' });
    wx.showLoading({ title: '加入中...' });
    try {
      const res: any = await api.joinBankByToken(t);
      const bankId = Number(res?.bank_id || 0);
      const bankName = String(res?.bank_name || '').trim();
      wx.showToast({ title: bankName ? `已加入「${bankName}」` : '已加入', icon: 'success' });
      clearPendingMiniRedirect();
      if (bankId > 0) {
        safeNavigate(`/pages/bank-detail/bank-detail?id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
      } else {
        safeNavigate('/pages/my-banks-v2/my-banks-v2', 'switchTab');
      }
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加入失败';
      this.setData({ errorMsg: msg });
    } finally {
      wx.hideLoading();
      this.setData({ loading: false });
    }
  },

  async joinByCode(code: string) {
    const c = String(code || '').trim().toUpperCase();
    if (!c || c.length !== 6) {
      wx.showToast({ title: '请输入6位分享码', icon: 'none' });
      return;
    }
    if (this.data.loading) return;

    const nextUrl = `/pages/bank-join/bank-join?share_code=${encodeURIComponent(c)}`;
    const ok = await this.ensureLoggedIn(nextUrl);
    if (!ok) return;

    this.setData({ loading: true, errorMsg: '' });
    wx.showLoading({ title: '加入中...' });
    try {
      const res: any = await api.joinBankByCode(c);
      const bankId = Number(res?.bank_id || 0);
      const bankName = String(res?.bank_name || '').trim();
      wx.showToast({ title: bankName ? `已加入「${bankName}」` : '已加入', icon: 'success' });
      clearPendingMiniRedirect();
      if (bankId > 0) {
        safeNavigate(`/pages/bank-detail/bank-detail?id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
      } else {
        safeNavigate('/pages/my-banks-v2/my-banks-v2', 'switchTab');
      }
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加入失败';
      this.setData({ errorMsg: msg });
    } finally {
      wx.hideLoading();
      this.setData({ loading: false });
    }
  },

  onJoinByCodeTap() {
    const code = String(this.data.shareCode || '').trim().toUpperCase();
    this.joinByCode(code);
  },

  onRetry() {
    if (this.data.mode === 'token') {
      this.autoJoinByToken(String(this.data.token || ''));
      return;
    }
    this.joinByCode(String(this.data.shareCode || ''));
  },

  onSwitchToCode() {
    this.setData({ mode: 'code', token: '', errorMsg: '' });
  },

  onCancel() {
    // 分享打开的页面通常是页面栈第一个，无法 navigateBack，直接跳首页
    const pages = getCurrentPages();
    if (pages.length <= 1) {
      safeNavigate('/pages/hub-v2/hub-v2', 'switchTab');
      return;
    }
    wx.navigateBack({
      delta: 1,
      fail: () => {
        safeNavigate('/pages/hub-v2/hub-v2', 'switchTab');
      }
    });
  }
});
