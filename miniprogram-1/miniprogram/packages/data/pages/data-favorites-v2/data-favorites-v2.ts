import { api } from '../../../../utils/api';
import { checkLogin } from '../../../../utils/auth';
import { safeNavigate } from '../../../../utils/nav';
import { themeManager, ThemeMode } from '../../../../utils/theme';
import { normalizeDays, toInt, pct1 } from '../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../utils/data-center-cache';
import { buildDataCenterCompatPayload, buildDataCenterChartOption, getDataCenterThemeTokens } from '../../utils/data-center-echarts';
import * as echarts from '../../components/ec-canvas/echarts';

type DataTabKey = 'global' | 'banks' | 'mistakes' | 'favorites' | 'tags';

type FavoriteTopItem = {
  key: string;
  source: string;
  scope_label: string;
  name: string;
  count: number;
  bank_id: number;
  can_quiz_bank: boolean;
  bar_pct: number;
};

type RecentPublicItem = {
  key: string;
  subject: string;
  q_type: string;
  difficulty: number;
  snippet: string;
};

type RecentBankItem = {
  key: string;
  bank_id: number;
  bank_name: string;
  q_type: string;
  difficulty: number;
  snippet: string;
};

function resolveDataTabUrl(tab: DataTabKey): string {
  const map: Record<DataTabKey, string> = {
    global: '/packages/data/pages/data-global-v2/data-global-v2',
    banks: '/packages/data/pages/data-bank-v2/data-bank-v2',
    mistakes: '/packages/data/pages/data-mistakes-v2/data-mistakes-v2',
    favorites: '/packages/data/pages/data-favorites-v2/data-favorites-v2',
    tags: '/packages/data/pages/data-tags-v2/data-tags-v2'
  };
  return map[tab];
}

function safeArr<T>(v: any): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

function buildExportObject(tab: DataTabKey, days: number, payload: any) {
  const p = tab === 'global' ? '/data/global' : `/data/${tab}`;
  const search = `?days=${encodeURIComponent(String(days || 30))}`;
  return {
    meta: { exported_at: new Date().toISOString(), path: p, search },
    data: payload
  };
}

function sumDailyAll(list: any): number {
  const rows = Array.isArray(list) ? list : [];
  return rows.reduce((acc, r) => acc + toInt(r?.all), 0);
}

function buildFavoritesViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'favorites');

  const allSummary = res?.all_summary || {};
  const windowDays = normalizeDays(res?.window_days || currentDays);

  const favoritesNew = sumDailyAll(res?.favorites_daily);
  const answeredAll = toInt(allSummary?.answered);
  const favAll = toInt(allSummary?.favorites);
  const favoritesDensity = answeredAll > 0 ? pct1((favAll * 100) / answeredAll) : 0;

  const topRaw = safeArr<any>(res?.favorites_top_items).slice(0, 12);
  const denom = Math.max(1, ...topRaw.map((it: any) => toInt(it?.count)));
  const topItems: FavoriteTopItem[] = topRaw.map((it: any, idx: number) => {
    const source = String(it?.source || '');
    const bankId = toInt(it?.bank_id);
    const c = toInt(it?.count);
    return {
      key: String(it?.bank_id || it?.name || idx),
      source,
      scope_label: source === 'public' ? '公共' : '个人',
      name: String(it?.name || ''),
      count: c,
      bank_id: bankId,
      can_quiz_bank: source === 'banks' && bankId > 0,
      bar_pct: pct1((c * 100) / denom)
    };
  });

  const recentPublic: RecentPublicItem[] = safeArr<any>(res?.recent_favorites_public)
    .slice(0, 6)
    .map((f: any, idx: number) => ({
      key: String(f?.question_id || idx),
      subject: String(f?.subject || ''),
      q_type: String(f?.q_type || ''),
      difficulty: toInt(f?.difficulty),
      snippet: String(f?.snippet || '')
    }));

  const recentBank: RecentBankItem[] = safeArr<any>(res?.recent_favorites_bank)
    .slice(0, 6)
    .map((f: any, idx: number) => ({
      key: String(f?.question_id || f?.bank_id || idx),
      bank_id: toInt(f?.bank_id),
      bank_name: String(f?.bank_name || ''),
      q_type: String(f?.q_type || ''),
      difficulty: toInt(f?.difficulty),
      snippet: String(f?.snippet || '')
    }));

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummary,
      health_score: toInt(res?.health_score),
      favorites_new: favoritesNew,
      favorites_density: favoritesDensity,
      favorites_top_items: topItems,
      recent_favorites_public: recentPublic,
      recent_favorites_bank: recentBank
    }
  };
}

const CHART_IDS: string[] = ['dcFavoriteTrendChart', 'dcFavoriteTopChart', 'dcFavoriteDifficultyChart', 'dcFavoriteTypeChart'];

Page({
  data: {
    ...(themeManager.getPageData()),
    loading: false,
    inited: false,
    lazyStage: 1,
    errorMsg: '',

    ecLazy: { lazyLoad: true },

    days: 30 as 7 | 30 | 90,
    window_days: 30,

    all_summary: {} as Record<string, unknown>,
    health_score: 0,

    favorites_new: 0,
    favorites_density: 0,

    favorites_top_items: [] as FavoriteTopItem[],
    recent_favorites_public: [] as RecentPublicItem[],
    recent_favorites_bank: [] as RecentBankItem[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=favorites&days=${encodeURIComponent(String(days))}`;
    wx.redirectTo({
      url,
      fail: () => {
        this.setData({ days, window_days: days });
      }
    });
  },

  onReady() {
    const self = this;
    self.__pageReady = true;
    this.initViewportLazy();
    if (self.__pendingRender) {
      self.__pendingRender = false;
      this.renderCharts();
    }
  },

  initViewportLazy() {
    const self = this;
    if (this.data.lazyStage >= 2) return;
    if (self.__lazyObserver) return;

    let ob: any;
    try {
      ob = this.createIntersectionObserver({ observeAll: false });
    } catch (e) {
      return;
    }

    self.__lazyObserver = ob;
    try {
      ob.relativeToViewport({ bottom: 600 }).observe('#dcLazyStage2Trigger', (res: any) => {
        if (!res || res.intersectionRatio <= 0) return;
        if (this.data.lazyStage >= 2) return;

        this.setData({ lazyStage: 2 }, () => {
          wx.nextTick(() => {
            try {
              this.renderCharts();
            } catch (err) {}
          });
        });

        try {
          ob.disconnect();
        } catch (e) {}
        self.__lazyObserver = null;
      });
    } catch (e) {}
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const patch: any = {};
    let hydrated = false;
    try {
      Object.assign(patch, themeManager.getPageData());
    } catch (e) {}

    if (!this.data.inited) {
      try {
        const cached = getCachedDataCenter(this.data.days);
        if (cached) {
          const built = buildFavoritesViewModel(cached, this.data.days);
          const self = this;
          self.__dcPayload = built.payload;
          self.__lastLoadedAt = Date.now();
          Object.assign(patch, built.data);
          hydrated = true;
        }
      } catch (e) {}
    }

    try {
      if (Object.keys(patch).length) {
        this.setData(
          patch,
          hydrated
            ? () => {
                wx.nextTick(() => {
                  try {
                    this.renderCharts();
                  } catch (err) {
                    console.error('[data-favorites-v2] renderCharts failed:', err);
                  }
                });
              }
            : undefined
        );
      }
    } catch (e) {}

    if (!hydrated && !this.data.inited && !this.data.loading) {
      this.loadStats(true);
      return;
    }

    if (!hydrated) this.renderCharts();
  },

  onUnload() {
    const self = this;
    try {
      self.__lazyObserver && typeof self.__lazyObserver.disconnect === 'function' && self.__lazyObserver.disconnect();
    } catch (e) {}
    self.__lazyObserver = null;
    const charts = (self.__charts || {}) as Record<string, any>;
    Object.keys(charts).forEach((k) => {
      try {
        charts[k] && typeof charts[k].dispose === 'function' && charts[k].dispose();
      } catch (e) {}
    });
    self.__charts = {};
  },

  onThemeChange(isDark: boolean) {
    this.renderCharts(false, isDark);
  },

  onPullDownRefresh() {
    this.loadStats(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onDaysTap(e: any) {
    const days = normalizeDays(e?.currentTarget?.dataset?.days);
    if (days === this.data.days) return;
    this.setData({ days, window_days: days }, () => {
      this.loadStats(true);
    });
  },

  onTabTap(e: any) {
    const raw = String(e?.currentTarget?.dataset?.tab || '').trim().toLowerCase();
    const tab: DataTabKey =
      raw === 'global' || raw === 'banks' || raw === 'mistakes' || raw === 'tags' ? (raw as DataTabKey) : 'favorites';
    const days = this.data.days;
    const base = resolveDataTabUrl(tab);
    safeNavigate(`${base}?days=${encodeURIComponent(String(days))}`, 'redirectTo');
  },

  onGoFavoritesCenter() {
    safeNavigate('/pages/favorites-v2/favorites-v2', 'redirectTo');
  },

  onGoBankFavorites(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizBankFavorites(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  renderCharts(forceInit = false, isDarkOverride?: boolean) {
    const self = this;
    const payload = self.__dcPayload;
    if (!payload) return;

    if (!self.__pageReady) {
      self.__pendingRender = true;
      return;
    }

    const isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : themeManager.isDarkMode();
    const style = themeManager.getStyle();
    const tokens = getDataCenterThemeTokens(isDark, style);

    const charts = (self.__charts || (self.__charts = {})) as Record<string, any>;
    CHART_IDS.forEach((id) => {
      const comp: any = this.selectComponent(`#${id}`);
      if (!comp || typeof comp.init !== 'function') return;

      const existing = charts[id];
      if (existing && !forceInit) {
        try {
          const opt = buildDataCenterChartOption(id, payload, tokens, existing);
          if (opt) existing.setOption(opt, { notMerge: true, lazyUpdate: false });
        } catch (e) {}
        return;
      }

      if (existing) {
        try {
          existing.dispose && existing.dispose();
        } catch (e) {}
        delete charts[id];
      }

      comp.init((canvas: any, width: number, height: number, dpr: number) => {
        const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
        canvas.setChart(chart);
        charts[id] = chart;
        try {
          const opt = buildDataCenterChartOption(id, payload, tokens, chart);
          if (opt) chart.setOption(opt, { notMerge: true, lazyUpdate: false });
        } catch (e) {}
        return chart;
      });
    });
  },

  async loadStats(force = false) {
    if (this.data.loading) return;
    const self = this;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 8000) return;

    self.__lastLoadedAt = now;
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res: any = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      const built = buildFavoritesViewModel(res, this.data.days);
      self.__dcPayload = built.payload;

      this.setData(
        built.data,
        () => {
          wx.nextTick(() => {
            try {
              this.renderCharts();
            } catch (err) {
              console.error('[data-favorites-v2] renderCharts failed:', err);
            }
          });
        }
      );
    } catch (e: any) {
      this.setData({ errorMsg: (e && e.message) || '加载失败，请稍后再试。' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
