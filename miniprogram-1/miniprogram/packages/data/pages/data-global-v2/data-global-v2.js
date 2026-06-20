'use strict';

const { api } = require('../../../../utils/api');
const { checkLogin } = require('../../../../utils/auth');
const { safeNavigate } = require('../../../../utils/nav');
const { themeManager } = require('../../../../utils/theme');
const { normalizeDays, toInt, pct1 } = require('../../../../utils/data-center');
const { getCachedDataCenter, setCachedDataCenter } = require('../../../../utils/data-center-cache');
const { buildDataCenterCompatPayload, buildDataCenterChartOption, getDataCenterThemeTokens } = require('../../utils/data-center-echarts');
const echarts = require('../../components/ec-canvas/echarts');

function resolveDataTabUrl(tab) {
  const map = {
    global: '/packages/data/pages/data-global-v2/data-global-v2',
    banks: '/packages/data/pages/data-bank-v2/data-bank-v2',
    mistakes: '/packages/data/pages/data-mistakes-v2/data-mistakes-v2',
    favorites: '/packages/data/pages/data-favorites-v2/data-favorites-v2',
    tags: '/packages/data/pages/data-tags-v2/data-tags-v2',
  };
  return map[tab] || map.global;
}

function safeSlice(list, n) {
  const arr = Array.isArray(list) ? list : [];
  if (n <= 0) return [];
  return arr.slice(0, n);
}

function lastActivity16(input) {
  const s = String(input || '').trim();
  if (!s) return '—';
  return s.slice(0, 16);
}

function buildExportObject(tab, days, payload) {
  const p = tab === 'global' ? '/data/global' : `/data/${tab}`;
  const search = `?days=${encodeURIComponent(String(days || 30))}`;
  return {
    meta: { exported_at: new Date().toISOString(), path: p, search },
    data: payload,
  };
}

function pickAllSummaryLite(summary) {
  const s = summary && typeof summary === 'object' ? summary : {};
  return {
    answered: toInt(s.answered),
    accuracy: pct1(s.accuracy),
    completion: pct1(s.completion),
  };
}

function buildGlobalViewModel(res, currentDays) {
  const allSummary = (res && res.all_summary) || {};
  const allSummaryLite = pickAllSummaryLite(allSummary);

  const globalInsights = safeSlice(res && res.global_insights, 999).map((it, idx) => ({
    key: String((it && it.title) || idx),
    title: String((it && it.title) || ''),
    value: String((it && it.value) || ''),
    hint: String((it && it.hint) || ''),
  }));

  const nextActions = safeSlice(res && res.next_actions, 8).map((a, idx) => ({
    key: String((a && a.title) || idx),
    title: String((a && a.title) || ''),
    reason: String((a && a.reason) || ''),
    metrics: String((a && a.metrics) || ''),
    subject: String((a && a.subject) || ''),
    q_type: String((a && a.q_type) || ''),
  }));

  const weaknessRows = safeSlice(res && res.weakness_rows, 8).map((w, idx) => ({
    key: String((w && w.key) || `${(w && w.subject) || ''}__${(w && w.q_type) || ''}__${idx}`),
    subject: String((w && w.subject) || ''),
    q_type: String((w && w.q_type) || ''),
    answered: toInt(w && w.answered),
    accuracy: pct1(w && w.accuracy),
    mistakes: toInt(w && w.mistakes),
  }));

  const recentMistakes = safeSlice(res && res.recent_mistakes, 6).map((m, idx) => ({
    key: String((m && m.question_id) || idx),
    subject: String((m && m.subject) || ''),
    q_type: String((m && m.q_type) || ''),
    question_id: toInt(m && m.question_id),
    snippet: String((m && m.snippet) || ''),
    difficulty: toInt(m && m.difficulty),
  }));

  const recentFavoritesPublic = safeSlice(res && res.recent_favorites_public, 6).map((m, idx) => ({
    key: String((m && m.question_id) || idx),
    subject: String((m && m.subject) || ''),
    q_type: String((m && m.q_type) || ''),
    question_id: toInt(m && m.question_id),
    snippet: String((m && m.snippet) || ''),
    difficulty: toInt(m && m.difficulty),
  }));

  const windowDays = normalizeDays((res && res.window_days) || currentDays);
  const baseData = {
    inited: true,
    window_days: windowDays,
    last_activity_16: lastActivity16(allSummary && allSummary.last_activity),
    // 避免把后端 ctx 的大对象直接塞进 data（可能触发 setData 栈溢出）
    all_summary: allSummaryLite,
    health_score: toInt(res && res.health_score),
    errorMsg: '',
  };

  return {
    fullData: {
      ...baseData,
      global_insights: globalInsights,
      next_actions: nextActions,
      weakness_rows: weaknessRows,
      recent_mistakes: recentMistakes,
      recent_favorites_public: recentFavoritesPublic,
    },
    fallbackData: {
      ...baseData,
      global_insights: [],
      next_actions: [],
      weakness_rows: [],
      recent_mistakes: [],
      recent_favorites_public: [],
    },
  };
}

function trySetData(page, data, cb) {
  try {
    if (typeof cb === 'function') page.setData(data, cb);
    else page.setData(data);
    return true;
  } catch (err) {
    console.error('[data-global-v2] setData failed:', err);
    return false;
  }
}

const CHART_IDS = [
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
  'dcDifficultyDistChart',
];

Page({
  data: Object.assign({}, themeManager.getPageData(), {
    loading: false,
    inited: false,
    lazyStage: 1,
    errorMsg: '',

    ecLazy: { lazyLoad: true },

    days: 30,
    window_days: 30,

    last_activity_16: '—',

    all_summary: {},
    health_score: 0,

    global_insights: [],
    next_actions: [],
    weakness_rows: [],

    recent_mistakes: [],
    recent_favorites_public: [],
  }),

  onLoad(options) {
    const days = normalizeDays(options && options.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=global&days=${encodeURIComponent(String(days))}`;
    wx.redirectTo({
      url,
      fail: () => {
        this.setData({ days, window_days: days });
      },
    });
  },

  onReady() {
    this.__pageReady = true;
    this.initViewportLazy();
    if (this.__pendingRender) {
      this.__pendingRender = false;
      this.renderCharts();
    }
  },

  initViewportLazy() {
    if (this.data.lazyStage >= 2) return;
    if (this.__lazyObserver) return;

    let ob;
    try {
      ob = this.createIntersectionObserver({ observeAll: false });
    } catch (e) {
      return;
    }

    this.__lazyObserver = ob;
    try {
      ob.relativeToViewport({ bottom: 600 }).observe('#dcLazyStage2Trigger', (res) => {
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
        this.__lazyObserver = null;
      });
    } catch (e) {}
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const patch = {};
    let hydrated = false;
    try {
      Object.assign(patch, themeManager.getPageData());
    } catch (e) {}

    if (!this.data.inited) {
      try {
        const cached = getCachedDataCenter(this.data.days);
        if (cached) {
          this.__lastLoadedAt = Date.now();
          try {
            this.__dcPayload = buildDataCenterCompatPayload(cached, 'global');
          } catch (err) {
            console.error('[data-global-v2] buildDataCenterCompatPayload failed (hydrate):', err);
            this.__dcPayload = {
              active_tab: 'global',
              window_days: normalizeDays((cached && cached.window_days) || this.data.days),
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
            : undefined,
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
    try {
      this.__lazyObserver && typeof this.__lazyObserver.disconnect === 'function' && this.__lazyObserver.disconnect();
    } catch (e) {}
    this.__lazyObserver = null;
    const charts = this.__charts || {};
    Object.keys(charts).forEach((k) => {
      try {
        charts[k] && typeof charts[k].dispose === 'function' && charts[k].dispose();
      } catch (e) {}
    });
    this.__charts = {};
  },

  onThemeChange(isDark) {
    this.renderCharts(false, isDark);
  },

  onPullDownRefresh() {
    this.loadStats(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode();
    this.setData({ ...themeManager.getPageData(), themeMode: mode });
  },

  onDaysTap(e) {
    const days = normalizeDays(e && e.currentTarget && e.currentTarget.dataset ? e.currentTarget.dataset.days : 30);
    if (days === this.data.days) return;
    this.setData({ days, window_days: days }, () => {
      this.loadStats(true);
    });
  },

  onTabTap(e) {
    const raw = String((e && e.currentTarget && e.currentTarget.dataset ? e.currentTarget.dataset.tab : '') || '')
      .trim()
      .toLowerCase();
    const tab = raw === 'banks' || raw === 'mistakes' || raw === 'favorites' || raw === 'tags' ? raw : 'global';
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

  onGoQuizPublicMistakes(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const subject = String(ds.subject || '').trim();
    const qType = String(ds.qType || '').trim();
    if (!subject) return;
    const url =
      `/pages/quiz/quiz?mode=quiz&source=mistakes&subject=${encodeURIComponent(subject)}` +
      (qType ? `&type=${encodeURIComponent(qType)}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizPublicAll(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const subject = String(ds.subject || '').trim();
    const qType = String(ds.qType || '').trim();
    if (!subject) return;
    const url =
      `/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}` +
      (qType ? `&type=${encodeURIComponent(qType)}` : '');
    safeNavigate(url, 'navigateTo');
  },

  renderCharts(forceInit = false, isDarkOverride) {
    const payload = this.__dcPayload;
    if (!payload) return;

    if (!this.__pageReady) {
      this.__pendingRender = true;
      return;
    }

    const isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : themeManager.isDarkMode();
    const style = themeManager.getStyle();
    const tokens = getDataCenterThemeTokens(isDark, style);

    const charts = this.__charts || (this.__charts = {});
    const page = this;

    CHART_IDS.forEach((id) => {
      const comp = page.selectComponent(`#${id}`);
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

      comp.init((canvas, width, height, dpr) => {
        let chart;
        try {
          chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
        } catch (err) {
          console.error('[data-global-v2] echarts.init failed:', id, err);
          return;
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

    const now = Date.now();
    const lastAt = Number(this.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 8000) return;

    this.__lastLoadedAt = now;
    trySetData(this, { loading: true, errorMsg: '' });

    let stage = 'init';
    try {
      stage = 'getDataCenter';
      const res = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      stage = 'buildCompatPayload';
      try {
        this.__dcPayload = buildDataCenterCompatPayload(res, 'global');
      } catch (err) {
        console.error('[data-global-v2] buildDataCenterCompatPayload failed:', err);
        this.__dcPayload = {
          active_tab: 'global',
          window_days: normalizeDays((res && res.window_days) || this.data.days),
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
        const ok = trySetData(this, vm.fallbackData, afterSet);
        if (!ok) {
          trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
        }
      }
    } catch (e) {
      console.error('[data-global-v2] loadStats failed:', stage, e);
      const raw = e && e.message ? String(e.message) : '加载失败，请稍后再试。';
      const isStack = raw.includes('Maximum call stack size exceeded');
      const msg = isStack ? `数据渲染异常（${stage}）：${raw}` : raw;
      trySetData(this, { errorMsg: msg });
      try {
        const nowToast = Date.now();
        const lastToast = Number(this.__lastErrorToastAt || 0) || 0;
        if (nowToast - lastToast > 3500) {
          this.__lastErrorToastAt = nowToast;
          wx.showToast({ title: msg.length > 18 ? '数据加载失败' : msg, icon: 'none' });
        }
      } catch (e) {}
    } finally {
      trySetData(this, { loading: false });
    }
  },
});
