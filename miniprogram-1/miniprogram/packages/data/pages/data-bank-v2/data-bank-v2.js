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
  return map[tab] || map.banks;
}

function safeArr(v) {
  return Array.isArray(v) ? v : [];
}

function buildExportObject(tab, days, payload) {
  const p = tab === 'global' ? '/data/global' : `/data/${tab}`;
  const search = `?days=${encodeURIComponent(String(days || 30))}`;
  return {
    meta: { exported_at: new Date().toISOString(), path: p, search },
    data: payload,
  };
}

function buildBankViewModel(res, currentDays) {
  const payload = buildDataCenterCompatPayload(res, 'banks');

  const allSummary = (res && res.all_summary) || {};
  const bankSummary = (res && res.bank_summary) || {};

  const subjects = safeArr(res && res.subject_rows).map((s, idx) => ({
    key: String((s && s.subject_id) || (s && s.subject) || idx),
    subject_id: toInt(s && s.subject_id),
    subject: String((s && s.subject) || ''),
    total: toInt(s && s.total),
    answered: toInt(s && s.answered),
    accuracy: pct1(s && s.accuracy),
    completion: pct1(s && s.completion),
    mistakes: toInt(s && s.mistakes),
    favorites: toInt(s && s.favorites),
  }));

  const banks = safeArr(res && res.bank_rows).map((b, idx) => ({
    key: String((b && b.bank_id) || (b && b.name) || idx),
    bank_id: toInt(b && b.bank_id),
    name: String((b && b.name) || ''),
    category_name: String((b && b.category_name) || '未分类'),
    total: toInt(b && b.total),
    answered: toInt(b && b.answered),
    accuracy: pct1(b && b.accuracy),
    completion: pct1(b && b.completion),
    mistakes: toInt(b && b.mistakes),
    favorites: toInt(b && b.favorites),
  }));

  const windowDays = normalizeDays((res && res.window_days) || currentDays);

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummary,
      bank_summary: bankSummary,
      total_questions: toInt(res && res.total_questions),
      answered_count: toInt(res && res.answered_count),
      accuracy: pct1(res && res.accuracy),
      window_answered: toInt(res && res.window_answered),
      window_accuracy: pct1(res && res.window_accuracy),
      subject_rows: subjects,
      bank_rows: banks,
    },
  };
}

const CHART_IDS = [
  'dcBankSplitChart',
  'dcBankCategoryChart',
  'dcBankBubbleChart',
  'dcBankRankChart',
  'dcSubjectProgressChart',
  'dcSubjectRiskChart',
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

    all_summary: {},
    bank_summary: {},

    total_questions: 0,
    answered_count: 0,
    accuracy: 0,

    window_answered: 0,
    window_accuracy: 0,

    subject_rows: [],
    bank_rows: [],
  }),

  onLoad(options) {
    const days = normalizeDays(options && options.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=banks&days=${encodeURIComponent(String(days))}`;
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
          const built = buildBankViewModel(cached, this.data.days);
          this.__dcPayload = built.payload;
          this.__lastLoadedAt = Date.now();
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
                    console.error('[data-bank-v2] renderCharts failed:', err);
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
    const tab = raw === 'global' || raw === 'mistakes' || raw === 'favorites' || raw === 'tags' ? raw : 'banks';
    const days = this.data.days;
    const base = resolveDataTabUrl(tab);
    safeNavigate(`${base}?days=${encodeURIComponent(String(days))}`, 'redirectTo');
  },

  onGoMyBanks() {
    safeNavigate('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
  },

  onGoSubjectDetail(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const sid = Number(ds.subjectId || 0);
    const subject = ds.subject ? String(ds.subject) : '';
    if (!Number.isFinite(sid) || sid <= 0) return;
    const url =
      `/pages/subject-detail-v2/subject-detail-v2?id=${encodeURIComponent(String(sid))}` +
      (subject ? `&subject=${encodeURIComponent(String(subject))}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizSubject(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const subject = String(ds.subject || '').trim();
    if (!subject) return;
    safeNavigate(`/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}`, 'navigateTo');
  },

  onGoQuizBank(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const bankId = Number(ds.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/quiz/quiz?mode=quiz&source=all&bank_id=${encodeURIComponent(String(bankId))}`, 'navigateTo');
  },

  onGoBankDetail(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {};
    const bankId = Number(ds.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/bank-detail/bank-detail?bank_id=${encodeURIComponent(String(bankId))}`, 'navigateTo');
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

    const now = Date.now();
    const lastAt = Number(this.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 8000) return;

    this.__lastLoadedAt = now;
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      const built = buildBankViewModel(res, this.data.days);
      this.__dcPayload = built.payload;

      this.setData(
        built.data,
        () => {
          wx.nextTick(() => {
            try {
              this.renderCharts();
            } catch (err) {
              console.error('[data-bank-v2] renderCharts failed:', err);
            }
          });
        },
      );
    } catch (e) {
      const msg = (e && e.message) || '加载失败，请稍后再试。';
      this.setData({ errorMsg: msg });
      try {
        const nowToast = Date.now();
        const lastToast = Number(this.__lastErrorToastAt || 0) || 0;
        if (nowToast - lastToast > 3500) {
          this.__lastErrorToastAt = nowToast;
          wx.showToast({ title: msg.length > 18 ? '数据加载失败' : msg, icon: 'none' });
        }
      } catch (e) {}
    } finally {
      this.setData({ loading: false });
    }
  },
});
