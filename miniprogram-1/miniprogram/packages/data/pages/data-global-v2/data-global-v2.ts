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

type InsightItem = { key: string; title: string; value: string; hint: string };
type NextActionItem = { key: string; title: string; reason: string; metrics: string; subject: string; q_type: string };
type WeaknessRow = { key: string; subject: string; q_type: string; answered: number; accuracy: number; mistakes: number };
type RecentPublicItem = {
  key: string;
  subject: string;
  q_type: string;
  question_id: number;
  snippet: string;
  difficulty: number;
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

function safeSlice<T>(list: any, n: number): T[] {
  const arr = Array.isArray(list) ? (list as T[]) : [];
  if (n <= 0) return [];
  return arr.slice(0, n);
}

function lastActivity16(input: any): string {
  const s = String(input || '').trim();
  if (!s) return '—';
  return s.slice(0, 16);
}

function buildExportObject(tab: DataTabKey, days: number, payload: any) {
  const p = tab === 'global' ? '/data/global' : `/data/${tab}`;
  const search = `?days=${encodeURIComponent(String(days || 30))}`;
  return {
    meta: { exported_at: new Date().toISOString(), path: p, search },
    data: payload
  };
}

function pickAllSummaryLite(summary: any) {
  const s = summary && typeof summary === 'object' ? summary : {} as Record<string, unknown>;
  return {
    answered: toInt(s.answered),
    accuracy: pct1(s.accuracy),
    completion: pct1(s.completion)
  };
}

function buildGlobalViewModel(res: any, currentDays: number) {
  const allSummary = res?.all_summary || {};
  const allSummaryLite = pickAllSummaryLite(allSummary);

  const globalInsights: InsightItem[] = safeSlice<any>(res?.global_insights, 999).map((it: any, idx: number) => ({
    key: String(it?.title || idx),
    title: String(it?.title || ''),
    value: String(it?.value || ''),
    hint: String(it?.hint || '')
  }));

  const nextActions: NextActionItem[] = safeSlice<any>(res?.next_actions, 8).map((a: any, idx: number) => ({
    key: String(a?.title || idx),
    title: String(a?.title || ''),
    reason: String(a?.reason || ''),
    metrics: String(a?.metrics || ''),
    subject: String(a?.subject || ''),
    q_type: String(a?.q_type || '')
  }));

  const weaknessRows: WeaknessRow[] = safeSlice<any>(res?.weakness_rows, 8).map((w: any, idx: number) => ({
    key: String(w?.key || `${w?.subject || ''}__${w?.q_type || ''}__${idx}`),
    subject: String(w?.subject || ''),
    q_type: String(w?.q_type || ''),
    answered: toInt(w?.answered),
    accuracy: pct1(w?.accuracy),
    mistakes: toInt(w?.mistakes)
  }));

  const recentMistakes: RecentPublicItem[] = safeSlice<any>(res?.recent_mistakes, 6).map((m: any, idx: number) => ({
    key: String(m?.question_id || idx),
    subject: String(m?.subject || ''),
    q_type: String(m?.q_type || ''),
    question_id: toInt(m?.question_id),
    snippet: String(m?.snippet || ''),
    difficulty: toInt(m?.difficulty)
  }));

  const recentFavoritesPublic: RecentPublicItem[] = safeSlice<any>(res?.recent_favorites_public, 6).map((m: any, idx: number) => ({
    key: String(m?.question_id || idx),
    subject: String(m?.subject || ''),
    q_type: String(m?.q_type || ''),
    question_id: toInt(m?.question_id),
    snippet: String(m?.snippet || ''),
    difficulty: toInt(m?.difficulty)
  }));

  const windowDays = normalizeDays(res?.window_days || currentDays);
  const baseData = {
    inited: true,
    window_days: windowDays,
    last_activity_16: lastActivity16(allSummary?.last_activity),
    // 避免把后端 ctx 的大对象直接塞进 data（可能触发 setData 栈溢出）
    all_summary: allSummaryLite,
    health_score: toInt(res?.health_score),
    errorMsg: ''
  };

  return {
    windowDays,
    fullData: {
      ...baseData,
      global_insights: globalInsights,
      next_actions: nextActions,
      weakness_rows: weaknessRows,
      recent_mistakes: recentMistakes,
      recent_favorites_public: recentFavoritesPublic
    },
    fallbackData: {
      ...baseData,
      global_insights: [],
      next_actions: [],
      weakness_rows: [],
      recent_mistakes: [],
      recent_favorites_public: []
    }
  };
}

function trySetData(page: any, data: any, cb?: () => void): boolean {
  try {
    if (typeof cb === 'function') page.setData(data, cb);
    else page.setData(data);
    return true;
  } catch (err) {
    console.error('[data-global-v2] setData failed:', err);
    return false;
  }
}

const CHART_IDS: string[] = [
  'dcTrendDetailChart',
  'dcGlobalLoopChart',
  'dcHealthGaugeChart',
  'dcCalendarChart',
  'dcHeatmapChart',
  'dcHourlyChart',
  'dcWeekdayChart',
  'dcAssetTrendChart',
  'dcRadarChart',
  'dcTopMixChart',
  'dcTypeDistChart',
  'dcDifficultyDistChart'
];

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

    last_activity_16: '—',

    all_summary: {} as Record<string, unknown>,
    health_score: 0,

    global_insights: [] as InsightItem[],
    next_actions: [] as NextActionItem[],
    weakness_rows: [] as WeaknessRow[],

    recent_mistakes: [] as RecentPublicItem[],
    recent_favorites_public: [] as RecentPublicItem[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=global&days=${encodeURIComponent(String(days))}`;
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
          const self = this;
          self.__lastLoadedAt = Date.now();
          try {
            self.__dcPayload = buildDataCenterCompatPayload(cached, 'global');
          } catch (err) {
            console.error('[data-global-v2] buildDataCenterCompatPayload failed (hydrate):', err);
            self.__dcPayload = {
              active_tab: 'global',
              window_days: normalizeDays(cached?.window_days || this.data.days)
            };
          }
          Object.assign(patch, buildGlobalViewModel(cached, this.data.days).fullData);
          hydrated = true;
        }
      } catch (e) {}
    }

    try {
      if (Object.keys(patch).length) {
        trySetData(
          this,
          patch,
          hydrated
            ? () => {
                wx.nextTick(() => {
                  try {
                    this.renderCharts();
                  } catch (err) {
                    console.error('[data-global-v2] renderCharts failed:', err);
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
      raw === 'banks' || raw === 'mistakes' || raw === 'favorites' || raw === 'tags' ? (raw as DataTabKey) : 'global';
    const days = this.data.days;
    const base = resolveDataTabUrl(tab);
    safeNavigate(`${base}?days=${encodeURIComponent(String(days))}`, 'redirectTo');
  },

  onGoMistakesCenter() {
    safeNavigate('/pages/mistakes-v2/mistakes-v2', 'redirectTo');
  },

  onGoFavoritesCenter() {
    safeNavigate('/pages/favorites-v2/favorites-v2', 'redirectTo');
  },

  onGoQuizPublicMistakes(e: any) {
    const subject = String(e?.currentTarget?.dataset?.subject || '').trim();
    const qType = String(e?.currentTarget?.dataset?.qType || '').trim();
    if (!subject) return;
    const url =
      `/pages/quiz/quiz?mode=quiz&source=mistakes&subject=${encodeURIComponent(subject)}` +
      (qType ? `&type=${encodeURIComponent(qType)}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizPublicAll(e: any) {
    const subject = String(e?.currentTarget?.dataset?.subject || '').trim();
    const qType = String(e?.currentTarget?.dataset?.qType || '').trim();
    if (!subject) return;
    const url =
      `/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}` + (qType ? `&type=${encodeURIComponent(qType)}` : '');
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
        let chart: any;
        try {
          chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
        } catch (err) {
          console.error('[data-global-v2] echarts.init failed:', id, err);
          return undefined as unknown;
        }
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
    trySetData(this, { loading: true, errorMsg: '' });

    let stage = 'init';
    try {
      stage = 'getDataCenter';
      const res: any = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      stage = 'buildCompatPayload';
      try {
        self.__dcPayload = buildDataCenterCompatPayload(res, 'global');
      } catch (err) {
        console.error('[data-global-v2] buildDataCenterCompatPayload failed:', err);
        self.__dcPayload = {
          active_tab: 'global',
          window_days: normalizeDays(res?.window_days || this.data.days)
        };
      }

      stage = 'buildViewModel';
      const vm = buildGlobalViewModel(res, this.data.days);

      stage = 'setData';
      const afterSet = () => {
        wx.nextTick(() => {
          try {
            this.renderCharts();
          } catch (err) {
            console.error('[data-global-v2] renderCharts failed:', err);
          }
        });
      };

      if (!trySetData(this, vm.fullData, afterSet)) {
        // 兜底：如果 setData 仍异常，降级为「不渲染列表」的最小数据，确保页面可用
        const ok = trySetData(
          this,
          vm.fallbackData,
          afterSet
        );
        if (!ok) {
          trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
        }
      }
    } catch (e: any) {
      console.error('[data-global-v2] loadStats failed:', stage, e);
      const raw = (e && e.message) ? String(e.message) : '加载失败，请稍后再试。';
      const isStack = raw.includes('Maximum call stack size exceeded');
      const msg = isStack ? `数据渲染异常（${stage}）：${raw}` : raw;
      trySetData(this, { errorMsg: msg });
      try {
        const nowToast = Date.now();
        const lastToast = Number(self.__lastErrorToastAt || 0) || 0;
        if (nowToast - lastToast > 3500) {
          self.__lastErrorToastAt = nowToast;
          wx.showToast({ title: msg.length > 18 ? '数据加载失败' : msg, icon: 'none' });
        }
      } catch (e) {}
    } finally {
      trySetData(this, { loading: false });
    }
  }
});
