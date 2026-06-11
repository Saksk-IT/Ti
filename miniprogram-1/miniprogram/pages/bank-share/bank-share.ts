// bank-share.ts - 个人题库分享设置页面
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

interface ShareItem {
  id: number;
  share_code?: string;
  share_token?: string;
  permission: 'read' | 'copy';
  expires_at?: string;
  expires_at_display?: string;
  current_uses: number;
  max_uses?: number;
  is_active: boolean;
}

Page({
  data: {
    bankId: 0,
    bankInfo: {
      name: '',
      question_count: 0
    },
    shares: [] as ShareItem[],
    loading: false,
    wechatShareToken: '',
    wechatShareReady: false,
    wechatSharePreparing: false,
    showCodeModal: false,
    generatedCode: ''
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const bankId = Number(options.bank_id || 0);
    if (!bankId) {
      wx.showToast({ title: '题库参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ bankId });
    wx.showShareMenu({ withShareTicket: true });
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const results: any[] = await Promise.all([
        api.getBankDetail(this.data.bankId),
        api.getBankShares(this.data.bankId)
      ]);

      const detailRes = results[0];
      const sharesRes = results[1];
      const bankData = detailRes.data || detailRes || {};
      const sharesData = sharesRes.data || sharesRes || {};
      const shares = (sharesData.shares || [])
        .filter((s: any) => !!s?.is_active)
        .map((s: any) => {
          return Object.assign({}, s, {
            expires_at_display: s.expires_at ? this.formatDate(s.expires_at) : ''
          });
        });

      this.setData({
        bankInfo: {
          name: bankData.name || '未知题库',
          question_count: bankData.question_count || 0
        },
        shares,
        loading: false,
        wechatShareToken: this.pickShareTokenFromShares(shares),
        wechatShareReady: !!this.pickShareTokenFromShares(shares)
      });
    } catch (err: any) {
      console.error('加载数据失败:', err);
      if (err.message?.includes('401') || err.message?.includes('登录')) {
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  isExpiredIso(expiresAt: any): boolean {
    const s = String(expiresAt || '').trim();
    if (!s) return false;
    const d = new Date(s);
    const ts = d.getTime();
    return !Number.isFinite(ts) || ts < Date.now();
  },

  pickShareTokenFromShares(shares: ShareItem[]): string {
    const list = Array.isArray(shares) ? shares : [];
    for (const s of list) {
      if (!s || !s.is_active) continue;
      const token = String(s.share_token || '').trim();
      if (!token) continue;
      if (s.expires_at && this.isExpiredIso(s.expires_at)) continue;
      return token;
    }
    return '';
  },

  extractTokenFromShareLink(input: any): string {
    const s = String(input || '').trim();
    if (!s) return '';
    if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?')) return s;
    const m = s.match(/[?&]token=([^&#]+)/i);
    if (m && m[1]) {
      try {
        return decodeURIComponent(m[1]);
      } catch {
        return m[1];
      }
    }
    return '';
  },

  async ensureWechatShareToken(force: boolean = false): Promise<string> {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return '';
    const currentToken = String(this.data.wechatShareToken || '').trim();
    if (!force && this.data.wechatShareReady && currentToken) return currentToken;
    if (this.data.wechatSharePreparing) return currentToken;

    this.setData({ wechatSharePreparing: true, wechatShareReady: false });
    try {
      await this.loadData();
      let token = String(this.data.wechatShareToken || '').trim();
      if (!token) {
        const created: any = await api.createBankShare(bankId, {
          type: 'link',
          permission: 'read',
          expires_in: null
        });
        token = String(created?.share_token || '').trim() || this.extractTokenFromShareLink(created?.share_link);
      }
      this.setData({ wechatShareToken: token, wechatShareReady: !!token });
      if (token) await this.loadData();
      return token;
    } finally {
      this.setData({ wechatSharePreparing: false });
    }
  },

  formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${month}-${day}`;
    } catch {
      return '';
    }
  },

  async onCreateShare(_e: any) {
    const { bankId } = this.data;

    wx.showLoading({ title: '创建中...' });
    try {
      const res: any = await api.createBankShare(bankId, {
        type: 'code',
        permission: 'read',
        expires_in: null
      });

      wx.hideLoading();

      const shareData = res.data || res || {};
      if (shareData.share_code) {
        this.setData({
          showCodeModal: true,
          generatedCode: shareData.share_code
        });
      }

      // 刷新列表
      this.loadData();
    } catch (err: any) {
      wx.hideLoading();
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    }
  },

  onCloseCodeModal() {
    this.setData({ showCodeModal: false });
  },

  onCopyGeneratedCode() {
    wx.setClipboardData({
      data: this.data.generatedCode,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
        this.setData({ showCodeModal: false });
      }
    });
  },

  onCopyCode(e: any) {
    const code = e.currentTarget.dataset.code;
    if (!code) {
      wx.showToast({ title: '暂无分享码', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: code,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  },

  onDeleteShare(e: any) {
    const shareId = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认撤销',
      content: '撤销后，使用此分享码加入的用户将无法继续访问',
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (!res.confirm) return;

        wx.showLoading({ title: '撤销中...' });
        try {
          await api.deleteBankShare(this.data.bankId, shareId);
          wx.hideLoading();
          wx.showToast({ title: '已撤销', icon: 'success' });
          this.loadData();
        } catch (err: any) {
          wx.hideLoading();
          wx.showToast({ title: err.message || '撤销失败', icon: 'none' });
        }
      }
    });
  },

  async onWechatShareTap() {
    if (this.data.wechatSharePreparing) return;
    wx.showLoading({ title: '准备分享...' });
    try {
      const token = await this.ensureWechatShareToken(false);
      if (!token) throw new Error('微信分享准备失败');

      wx.showToast({ title: '已准备好，请再次点击微信分享', icon: 'none' });
    } catch (err: any) {
      wx.showToast({ title: (err && err.message) ? String(err.message) : '分享失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onShareAppMessage() {
    const { bankInfo } = this.data;
    const token = String(this.data.wechatShareToken || '').trim();
    return {
      title: `邀请你加入题库：${bankInfo.name}`,
      path: token
        ? `/pages/bank-join/bank-join?token=${encodeURIComponent(token)}`
        : '/pages/my-banks-v2/my-banks-v2'
    };
  }
});
