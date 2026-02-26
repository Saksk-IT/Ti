// data-web-v2.ts - Web 数据中心（web-view 1:1 复刻）
import { api, getApiOrigin } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager } from '../../utils/theme';

function normalizeDays(v: any): 7 | 30 | 90 {
  const n = Number(v);
  if (n === 7 || n === 30 || n === 90) return n;
  return 30;
}

function withDays(nextPath: string, days: 7 | 30 | 90): string {
  const raw = String(nextPath || '').trim() || '/data';
  const path = raw.startsWith('/') ? raw : `/${raw}`;
  const parts = path.split('?');
  const base = parts[0] || '/data';
  const query = parts.slice(1).join('?');
  const params = new Map<string, string>();
  if (query) {
    for (const seg of query.split('&')) {
      if (!seg) continue;
      const idx = seg.indexOf('=');
      if (idx >= 0) params.set(seg.slice(0, idx), seg.slice(idx + 1));
      else params.set(seg, '');
    }
  }
  params.set('days', encodeURIComponent(String(days)));
  const qs = Array.from(params.entries())
    .map(([k, val]) => (val === '' ? k : `${k}=${val}`))
    .join('&');
  return qs ? `${base}?${qs}` : base;
}

Page({
  data: {
    src: '',
    next: '/data',
    days: 30 as 7 | 30 | 90,
    loading: false
  },

  onLoad(options: Record<string, any>) {
    const days = normalizeDays(options?.days);
    const tab = String(options?.tab || '').trim();
    const nextRaw = (options && options.next ? String(options.next) : '').trim();

    const tabMap: Record<string, string> = {
      global: '/data/global',
      banks: '/data/banks',
      mistakes: '/data/mistakes',
      favorites: '/data/favorites',
      tags: '/data/tags'
    };

    const next = nextRaw || tabMap[tab] || '/data';
    this.setData({ next, days });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    this.loadWebDataCenter();
  },

  onPullDownRefresh() {
    this.loadWebDataCenter(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadWebDataCenter(force = false) {
    if (this.data.loading) return;

    const self = this;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 8000 && this.data.src) return;
    self.__lastLoadedAt = now;

    this.setData({ loading: true, src: '' });

    try {
      const next = withDays(this.data.next || '/data', this.data.days);
      const res = await api.getMiniWebViewUrl(next);
      const origin = getApiOrigin();
      const src = `${origin}${res.path}`;
      this.setData({ src, loading: false });
    } catch (err: any) {
      console.error('加载 Web 数据中心失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
      this.setData({ loading: false, src: '' });
    }
  },

  onRetryTap() {
    this.loadWebDataCenter(true);
  },

  onWebLoad() {
    this.setData({ loading: false });
  },

  onWebError(e: any) {
    console.error('web-view error:', e);
    this.setData({ loading: false, src: '' });
  }
});

