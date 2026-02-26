import { api } from '../../../../utils/api';
import { checkLogin } from '../../../../utils/auth';
import { safeNavigate } from '../../../../utils/nav';
import { syncUserSettingsToServer } from '../../../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../../../utils/theme';
import { normalizeDays, toInt, pct1 } from '../../../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../../../utils/data-center-cache';
import { buildDataCenterCompatPayload, buildDataCenterChartOption, getDataCenterThemeTokens } from '../../utils/data-center-echarts';
import * as echarts from '../../components/ec-canvas/echarts';

type DataTabKey = 'global' | 'banks' | 'mistakes' | 'favorites' | 'tags';

type TagsKpis = {
  all_tag_count: number;
  public_tag_count: number;
  banks_tag_count: number;
  all_tagged_questions: number;
  public_tagged_questions: number;
  banks_tagged_questions: number;
  tagged_answered_coverage: number;
};

type TagRow = {
  key: string;
  tag: string;
  count: number;
  answered: number;
  accuracy: number;
  mistakes_times: number;
  favorites: number;
  bar_count_pct: number;
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

function buildTagsViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'tags');

  const windowDays = normalizeDays(res?.window_days || currentDays);

  const kpiRaw = res?.tags_kpis || {};
  const tagsKpis: TagsKpis = {
    all_tag_count: toInt(kpiRaw?.all_tag_count),
    public_tag_count: toInt(kpiRaw?.public_tag_count),
    banks_tag_count: toInt(kpiRaw?.banks_tag_count),
    all_tagged_questions: toInt(kpiRaw?.all_tagged_questions),
    public_tagged_questions: toInt(kpiRaw?.public_tagged_questions),
    banks_tagged_questions: toInt(kpiRaw?.banks_tagged_questions),
    tagged_answered_coverage: pct1(kpiRaw?.tagged_answered_coverage)
  };

  const publicRaw = safeArr<any>(res?.tags_public).slice(0, 12);
  const banksRaw = safeArr<any>(res?.tags_banks).slice(0, 12);
  const publicDen = Math.max(1, ...publicRaw.map((t: any) => toInt(t?.count)));
  const banksDen = Math.max(1, ...banksRaw.map((t: any) => toInt(t?.count)));

  const tagsPublic: TagRow[] = publicRaw.map((t: any, idx: number) => {
    const count = toInt(t?.count);
    return {
      key: String(t?.tag || idx),
      tag: String(t?.tag || ''),
      count,
      answered: toInt(t?.answered),
      accuracy: pct1(t?.accuracy),
      mistakes_times: toInt(t?.mistakes_times),
      favorites: toInt(t?.favorites),
      bar_count_pct: pct1((count * 100) / publicDen)
    };
  });

  const tagsBanks: TagRow[] = banksRaw.map((t: any, idx: number) => {
    const count = toInt(t?.count);
    return {
      key: String(t?.tag || idx),
      tag: String(t?.tag || ''),
      count,
      answered: toInt(t?.answered),
      accuracy: pct1(t?.accuracy),
      mistakes_times: toInt(t?.mistakes_times),
      favorites: toInt(t?.favorites),
      bar_count_pct: pct1((count * 100) / banksDen)
    };
  });

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      tags_kpis: tagsKpis,
      health_score: toInt(res?.health_score),
      tags_public: tagsPublic,
      tags_banks: tagsBanks
    }
  };
}

const CHART_IDS: string[] = ['dcTagGraphChart', 'dcTagTreemapChart', 'dcTagTopChart', 'dcTagAccuracyChart'];

Page({
  data: {
    ...(themeManager.getPageData()),
    drawerOpen: false,
    loading: false,
    inited: false,
    lazyStage: 1,
    errorMsg: '',

    ecLazy: { lazyLoad: true },

    days: 30 as 7 | 30 | 90,
    window_days: 30,

    tags_kpis: {
      all_tag_count: 0,
      public_tag_count: 0,
      banks_tag_count: 0,
      all_tagged_questions: 0,
      public_tagged_questions: 0,
      banks_tagged_questions: 0,
      tagged_answered_coverage: 0
    } as TagsKpis,

    health_score: 0,

    tags_public: [] as TagRow[],
    tags_banks: [] as TagRow[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=tags&days=${encodeURIComponent(String(days))}`;
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
          const built = buildTagsViewModel(cached, this.data.days);
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
                    console.error('[data-tags-v2] renderCharts failed:', err);
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
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
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
      raw === 'global' || raw === 'banks' || raw === 'mistakes' || raw === 'favorites' ? (raw as DataTabKey) : 'tags';
    const days = this.data.days;
    const base = resolveDataTabUrl(tab);
    safeNavigate(`${base}?days=${encodeURIComponent(String(days))}`, 'redirectTo');
  },

  onGoTagsCenter() {
    safeNavigate('/pages/tags-v2/tags-v2', 'redirectTo');
  },

  onGoTagCenterPublic(e: any) {
    const tag = String(e?.currentTarget?.dataset?.tag || '').trim();
    const url = `/pages/tags-v2/tags-v2?tab=public&keyword=${encodeURIComponent(tag)}`;
    safeNavigate(url, 'redirectTo');
  },

  onGoTagCenterBanks(e: any) {
    const tag = String(e?.currentTarget?.dataset?.tag || '').trim();
    const url = `/pages/tags-v2/tags-v2?tab=bank&keyword=${encodeURIComponent(tag)}`;
    safeNavigate(url, 'redirectTo');
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

      const built = buildTagsViewModel(res, this.data.days);
      self.__dcPayload = built.payload;

      this.setData(
        built.data,
        () => {
          wx.nextTick(() => {
            try {
              this.renderCharts();
            } catch (err) {
              console.error('[data-tags-v2] renderCharts failed:', err);
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
