// web-frontend.ts - Web 前台（web-view 1:1 复刻）
import { api, getApiOrigin } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    src: '',
    next: '/hub',
    loading: false
  },

  onLoad(options: Record<string, any>) {
    const next = (options && options.next ? String(options.next) : '').trim();
    if (next) {
      this.setData({ next });
    }
  },

  onShow() {
    this.loadWebFrontend();
  },

  async loadWebFrontend() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    if (this.data.loading) return;
    this.setData({ loading: true, src: '' });

    try {
      const res = await api.getMiniWebViewUrl(this.data.next || '/hub');
      const origin = getApiOrigin();
      const src = `${origin}${res.path}`;
      this.setData({ src, loading: false });
    } catch (err: any) {
      console.error('加载 Web 前台失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
      this.setData({ loading: false, src: '' });
    }
  },

  onRetryTap() {
    this.loadWebFrontend();
  },

  onWebLoad() {
    this.setData({ loading: false });
  },

  onWebError(e: any) {
    console.error('web-view error:', e);
    this.setData({ loading: false, src: '' });
  }
});
