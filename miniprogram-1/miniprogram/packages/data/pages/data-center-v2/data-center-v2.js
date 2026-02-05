'use strict';

const { api } = require('../../../../utils/api');
const { checkLogin } = require('../../../../utils/auth');
const { safeNavigate } = require('../../../../utils/nav');
const { syncUserSettingsToServer } = require('../../../../utils/user-settings');
const { themeManager } = require('../../../../utils/theme');
const { normalizeDays, toInt, pct1 } = require('../../../../utils/data-center');
const { getCachedDataCenter, setCachedDataCenter } = require('../../../../utils/data-center-cache');
const { buildDataCenterCompatPayload, buildDataCenterChartOption, getDataCenterThemeTokens } = require('../../utils/data-center-echarts');
const echarts = require('../../components/ec-canvas/echarts');

const TAB_META = {
  global: { title: '全局', desc: '全局视角：覆盖、正确、连续与复盘资产，一屏把握你的学习系统。' },
  banks: { title: '题库', desc: '题库全景：规模、覆盖、质量，把投入方向选得更聪明。' },
  mistakes: { title: '错题', desc: '错题是最有杠杆的提升入口：高频先闭环，薄弱再专项。' },
  favorites: { title: '收藏', desc: '收藏是高价值题库：复习、背题、考前冲刺都能复用。' },
  tags: { title: '标签', desc: '标签让题目资产结构化：复盘与专项训练更容易“复用”。' },
};

const CHART_IDS_BY_TAB = {
  global: [
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
  ],
  banks: ['dcBankSplitChart', 'dcBankCategoryChart', 'dcBankBubbleChart', 'dcBankRankChart', 'dcSubjectProgressChart', 'dcSubjectRiskChart'],
  mistakes: ['dcMistakeTrendChart', 'dcMistakeTopChart', 'dcMistakeDifficultyChart', 'dcMistakeTypeChart'],
  favorites: ['dcFavoriteTrendChart', 'dcFavoriteTopChart', 'dcFavoriteDifficultyChart', 'dcFavoriteTypeChart'],
  tags: ['dcTagGraphChart', 'dcTagTreemapChart', 'dcTagTopChart', 'dcTagAccuracyChart'],
};

function normalizeTab(raw) {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'banks' || v === 'mistakes' || v === 'favorites' || v === 'tags') return v;
  return 'global';
}

function safeSlice(list, n) {
  const arr = Array.isArray(list) ? list : [];
  if (n <= 0) return [];
  return arr.slice(0, n);
}

function safeArr(v) {
  return Array.isArray(v) ? v : [];
}

function lastActivity16(input) {
  const s = String(input || '').trim();
  if (!s) return '—';
  return s.slice(0, 16);
}

function pickAllSummaryLite(summary) {
  const s = summary && typeof summary === 'object' ? summary : {};
  return {
    answered: toInt(s.answered),
    accuracy: pct1(s.accuracy),
    completion: pct1(s.completion),
    mistakes: toInt(s.mistakes),
    mistakes_times: toInt(s.mistakes_times),
    favorites: toInt(s.favorites),
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
    all_summary: allSummaryLite,
    health_score: toInt(res && res.health_score),
    errorMsg: '',
  };

  return {
    windowDays,
    fullData: Object.assign({}, baseData, {
      global_insights: globalInsights,
      next_actions: nextActions,
      weakness_rows: weaknessRows,
      recent_mistakes: recentMistakes,
      recent_favorites_public: recentFavoritesPublic,
    }),
    fallbackData: Object.assign({}, baseData, {
      global_insights: [],
      next_actions: [],
      weakness_rows: [],
      recent_mistakes: [],
      recent_favorites_public: [],
    }),
  };
}

function buildBankViewModel(res, currentDays) {
  const payload = buildDataCenterCompatPayload(res, 'banks');
  const allSummaryLite = pickAllSummaryLite((res && res.all_summary) || {});
  const bankSummary = (res && res.bank_summary) || {};

  const subjects = safeArr(res && res.subject_rows).map((s, idx) => ({
    key: String((s && (s.subject_id || s.subject)) || idx),
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
    key: String((b && (b.bank_id || b.name)) || idx),
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
      all_summary: allSummaryLite,
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

function sumDailyAll(list) {
  const rows = Array.isArray(list) ? list : [];
  return rows.reduce((acc, r) => acc + toInt(r && r.all), 0);
}

function buildMistakesViewModel(res, currentDays) {
  const payload = buildDataCenterCompatPayload(res, 'mistakes');
  const allSummaryLite = pickAllSummaryLite((res && res.all_summary) || {});
  const windowDays = normalizeDays((res && res.window_days) || currentDays);
  const mistakesNew = sumDailyAll(res && res.mistakes_daily);

  const topRaw = safeArr(res && res.mistakes_top_items).slice(0, 12);
  const weights = topRaw.map((it) => toInt(it && (it.times || it.count)));
  const denom = Math.max(1, ...weights);
  const topItems = topRaw.map((it, idx) => {
    const source = String((it && it.source) || '');
    const bankId = toInt(it && it.bank_id);
    const w = toInt(it && (it.times || it.count));
    return {
      key: String((it && (it.bank_id || it.name)) || idx),
      source,
      scope_label: source === 'public' ? '公共' : '个人',
      name: String((it && it.name) || ''),
      count: toInt(it && it.count),
      times: toInt(it && it.times),
      bank_id: bankId,
      can_quiz_bank: source === 'banks' && bankId > 0,
      bar_pct: pct1((w * 100) / denom),
    };
  });

  const recentPublic = safeArr(res && res.recent_mistakes)
    .slice(0, 6)
    .map((m, idx) => ({
      key: String((m && m.question_id) || idx),
      subject: String((m && m.subject) || ''),
      q_type: String((m && m.q_type) || ''),
      difficulty: toInt(m && m.difficulty),
      snippet: String((m && m.snippet) || ''),
    }));

  const recentBank = safeArr(res && res.recent_mistakes_bank)
    .slice(0, 6)
    .map((m, idx) => ({
      key: String((m && (m.question_id || m.bank_id)) || idx),
      bank_id: toInt(m && m.bank_id),
      bank_name: String((m && m.bank_name) || ''),
      q_type: String((m && m.q_type) || ''),
      difficulty: toInt(m && m.difficulty),
      snippet: String((m && m.snippet) || ''),
      wrong_count: m && m.wrong_count == null ? null : toInt(m && m.wrong_count),
    }));

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummaryLite,
      health_score: toInt(res && res.health_score),
      mistakes_new: mistakesNew,
      mistakes_top_items: topItems,
      recent_mistakes: recentPublic,
      recent_mistakes_bank: recentBank,
    },
  };
}

function buildFavoritesViewModel(res, currentDays) {
  const payload = buildDataCenterCompatPayload(res, 'favorites');
  const allSummaryLite = pickAllSummaryLite((res && res.all_summary) || {});
  const windowDays = normalizeDays((res && res.window_days) || currentDays);

  const favoritesNew = sumDailyAll(res && res.favorites_daily);
  const answeredAll = toInt(allSummaryLite && allSummaryLite.answered);
  const favAll = toInt(allSummaryLite && allSummaryLite.favorites);
  const favoritesDensity = answeredAll > 0 ? pct1((favAll * 100) / answeredAll) : 0;

  const topRaw = safeArr(res && res.favorites_top_items).slice(0, 12);
  const denom = Math.max(1, ...topRaw.map((it) => toInt(it && it.count)));
  const topItems = topRaw.map((it, idx) => {
    const source = String((it && it.source) || '');
    const bankId = toInt(it && it.bank_id);
    const c = toInt(it && it.count);
    return {
      key: String((it && (it.bank_id || it.name)) || idx),
      source,
      scope_label: source === 'public' ? '公共' : '个人',
      name: String((it && it.name) || ''),
      count: c,
      bank_id: bankId,
      can_quiz_bank: source === 'banks' && bankId > 0,
      bar_pct: pct1((c * 100) / denom),
    };
  });

  const recentPublic = safeArr(res && res.recent_favorites_public)
    .slice(0, 6)
    .map((f, idx) => ({
      key: String((f && f.question_id) || idx),
      subject: String((f && f.subject) || ''),
      q_type: String((f && f.q_type) || ''),
      difficulty: toInt(f && f.difficulty),
      snippet: String((f && f.snippet) || ''),
    }));

  const recentBank = safeArr(res && res.recent_favorites_bank)
    .slice(0, 6)
    .map((f, idx) => ({
      key: String((f && (f.question_id || f.bank_id)) || idx),
      bank_id: toInt(f && f.bank_id),
      bank_name: String((f && f.bank_name) || ''),
      q_type: String((f && f.q_type) || ''),
      difficulty: toInt(f && f.difficulty),
      snippet: String((f && f.snippet) || ''),
    }));

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummaryLite,
      health_score: toInt(res && res.health_score),
      favorites_new: favoritesNew,
      favorites_density: favoritesDensity,
      favorites_top_items: topItems,
      recent_favorites_public: recentPublic,
      recent_favorites_bank: recentBank,
    },
  };
}

function buildTagsViewModel(res, currentDays) {
  const payload = buildDataCenterCompatPayload(res, 'tags');
  const windowDays = normalizeDays((res && res.window_days) || currentDays);

  const kpiRaw = (res && res.tags_kpis) || {};
  const tagsKpis = {
    all_tag_count: toInt(kpiRaw && kpiRaw.all_tag_count),
    public_tag_count: toInt(kpiRaw && kpiRaw.public_tag_count),
    banks_tag_count: toInt(kpiRaw && kpiRaw.banks_tag_count),
    all_tagged_questions: toInt(kpiRaw && kpiRaw.all_tagged_questions),
    public_tagged_questions: toInt(kpiRaw && kpiRaw.public_tagged_questions),
    banks_tagged_questions: toInt(kpiRaw && kpiRaw.banks_tagged_questions),
    tagged_answered_coverage: pct1(kpiRaw && kpiRaw.tagged_answered_coverage),
  };

  const publicRaw = safeArr(res && res.tags_public).slice(0, 12);
  const banksRaw = safeArr(res && res.tags_banks).slice(0, 12);
  const publicDen = Math.max(1, ...publicRaw.map((t) => toInt(t && t.count)));
  const banksDen = Math.max(1, ...banksRaw.map((t) => toInt(t && t.count)));

  const tagsPublic = publicRaw.map((t, idx) => {
    const count = toInt(t && t.count);
    return {
      key: String((t && t.tag) || idx),
      tag: String((t && t.tag) || ''),
      count,
      answered: toInt(t && t.answered),
      accuracy: pct1(t && t.accuracy),
      mistakes_times: toInt(t && t.mistakes_times),
      favorites: toInt(t && t.favorites),
      bar_count_pct: pct1((count * 100) / publicDen),
    };
  });

  const tagsBanks = banksRaw.map((t, idx) => {
    const count = toInt(t && t.count);
    return {
      key: String((t && t.tag) || idx),
      tag: String((t && t.tag) || ''),
      count,
      answered: toInt(t && t.answered),
      accuracy: pct1(t && t.accuracy),
      mistakes_times: toInt(t && t.mistakes_times),
      favorites: toInt(t && t.favorites),
      bar_count_pct: pct1((count * 100) / banksDen),
    };
  });

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      tags_kpis: tagsKpis,
      health_score: toInt(res && res.health_score),
      tags_public: tagsPublic,
      tags_banks: tagsBanks,
    },
  };
}

function trySetData(page, data, cb) {
  try {
    if (typeof cb === 'function') page.setData(data, cb);
    else page.setData(data);
    return true;
  } catch (err) {
    console.error('[data-center-v2] setData failed:', err);
    return false;
  }
}

function buildCompatPayloadSafe(res, tab) {
  try {
    return buildDataCenterCompatPayload(res, tab);
  } catch (err) {
    console.error('[data-center-v2] buildDataCenterCompatPayload failed:', tab, err);
    return { active_tab: tab, window_days: normalizeDays((res && res.window_days) || 30) };
  }
}

function buildTabVm(tab, res, days) {
  if (tab === 'global') {
    const payload = buildCompatPayloadSafe(res, 'global');
    const vm = buildGlobalViewModel(res, days);
    return { payload, data: vm.fullData, fallbackData: vm.fallbackData };
  }
  if (tab === 'banks') return buildBankViewModel(res, days);
  if (tab === 'mistakes') return buildMistakesViewModel(res, days);
  if (tab === 'favorites') return buildFavoritesViewModel(res, days);
  return buildTagsViewModel(res, days);
}

Page({
  data: Object.assign({}, themeManager.getPageData(), {
    drawerOpen: false,
    loading: false,
    inited: false,
    errorMsg: '',

    tab: 'global',
    tabTitle: TAB_META.global.title,
    tabDesc: TAB_META.global.desc,
    scrollIntoView: '',

    lazyStage: 1,
    ecLazy: { lazyLoad: true },

    days: 30,
    window_days: 30,

    last_activity_16: '—',

    all_summary: pickAllSummaryLite({}),
    health_score: 0,

    global_insights: [],
    next_actions: [],
    weakness_rows: [],
    recent_mistakes: [],
    recent_favorites_public: [],

    bank_summary: {},
    total_questions: 0,
    answered_count: 0,
    accuracy: 0,
    window_answered: 0,
    window_accuracy: 0,
    subject_rows: [],
    bank_rows: [],

    mistakes_new: 0,
    mistakes_top_items: [],
    recent_mistakes_bank: [],

    favorites_new: 0,
    favorites_density: 0,
    favorites_top_items: [],
    recent_favorites_bank: [],

    tags_kpis: {
      all_tag_count: 0,
      public_tag_count: 0,
      banks_tag_count: 0,
      all_tagged_questions: 0,
      public_tagged_questions: 0,
      banks_tagged_questions: 0,
      tagged_answered_coverage: 0,
    },
    tags_public: [],
    tags_banks: [],
  }),

  onLoad(options) {
    const days = normalizeDays(options && options.days);
    const tab = normalizeTab(options && options.tab);
    const meta = TAB_META[tab] || TAB_META.global;
    this.setData({ tab, tabTitle: meta.title, tabDesc: meta.desc, days, window_days: days, lazyStage: 1 });
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

        const stageMap = this.__lazyStageByTab || (this.__lazyStageByTab = {});
        stageMap[this.data.tab] = 2;

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

    const tab = normalizeTab(this.data.tab);
    const days = this.data.days;

    const patch = {};
    let hydrated = false;
    try {
      Object.assign(patch, themeManager.getPageData());
    } catch (e) {}

    const meta = TAB_META[tab] || TAB_META.global;
    patch.tabTitle = meta.title;
    patch.tabDesc = meta.desc;

    try {
      const stageMap = this.__lazyStageByTab || (this.__lazyStageByTab = {});
      patch.lazyStage = Number(stageMap[tab] || 1) || 1;
    } catch (e) {}

    if (!this.data.inited || this.__dcResDays !== days) {
      try {
        const cached = getCachedDataCenter(days);
        if (cached) {
          this.__dcRes = cached;
          this.__dcResDays = days;
          this.__vmCache = {};
          this.__dcPayloadByTab = {};
          this.__lastLoadedAt = Date.now();

          const built = buildTabVm(tab, cached, days);
          (this.__vmCache || (this.__vmCache = {}))[tab] = built;
          (this.__dcPayloadByTab || (this.__dcPayloadByTab = {}))[tab] = built.payload;
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
                    console.error('[data-center-v2] renderCharts failed:', err);
                  }
                });
              }
            : undefined,
        );
      }
    } catch (e) {}

    if (!hydrated && (!this.data.inited || this.__dcResDays !== days) && !this.data.loading) {
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

  onHamburgerTap() {
    this.setData({ drawerOpen: true });
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false });
  },

  onDrawerNavigate(e) {
    const url = e && e.detail && e.detail.url;
    const navType = e && e.detail && e.detail.navType;
    this.setData({ drawerOpen: false });
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e) {
    const style = (e && e.detail && e.detail.style) || 'default';
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode();
    this.setData(Object.assign({}, themeManager.getPageData(), { themeMode: mode }));
  },

  onDaysTap(e) {
    const days = normalizeDays(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.days);
    if (days === this.data.days) return;

    this.__dcRes = null;
    this.__dcResDays = 0;
    this.__vmCache = {};
    this.__dcPayloadByTab = {};
    this.__lastLoadedAt = 0;
    this.__lazyStageByTab = {};

    this.setData({ days, window_days: days, lazyStage: 1, scrollIntoView: 'dcTop' }, () => {
      this.setData({ scrollIntoView: '' });
      this.loadStats(true);
    });
  },

  onTabTap(e) {
    const tab = normalizeTab(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.tab);
    this.switchTab(tab);
  },

  ensureTabVm(tab) {
    const res = this.__dcRes;
    if (!res) return null;
    const days = this.data.days;

    const cache = this.__vmCache || (this.__vmCache = {});
    if (cache[tab]) return cache[tab];

    const built = buildTabVm(tab, res, days);
    cache[tab] = built;
    (this.__dcPayloadByTab || (this.__dcPayloadByTab = {}))[tab] = built.payload;
    return built;
  },

  disposeChartsAndObserver() {
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

  switchTab(nextTab) {
    const current = normalizeTab(this.data.tab);
    const tab = normalizeTab(nextTab);
    if (tab === current) return;

    const stageMap = this.__lazyStageByTab || (this.__lazyStageByTab = {});
    stageMap[current] = Number(this.data.lazyStage || 1) || 1;
    const nextStage = Number(stageMap[tab] || 1) || 1;

    this.disposeChartsAndObserver();

    const meta = TAB_META[tab] || TAB_META.global;
    const patch = { tab, tabTitle: meta.title, tabDesc: meta.desc, lazyStage: nextStage, scrollIntoView: 'dcTop', errorMsg: '' };

    if (this.__dcRes && this.__dcResDays === this.data.days) {
      try {
        const built = this.ensureTabVm(tab);
        if (built && built.data) Object.assign(patch, built.data);
      } catch (e) {}
    }

    this.setData(patch, () => {
      this.setData({ scrollIntoView: '' });
      this.initViewportLazy();
      wx.nextTick(() => {
        try {
          this.renderCharts(true);
        } catch (e) {}
      });
      if (!this.__dcRes || this.__dcResDays !== this.data.days) {
        this.loadStats(true);
      }
    });
  },

  renderCharts(forceInit = false, isDarkOverride) {
    const tab = normalizeTab(this.data.tab);
    const payload = (this.__dcPayloadByTab || {})[tab];
    if (!payload) return;

    if (!this.__pageReady) {
      this.__pendingRender = true;
      return;
    }

    const ids = CHART_IDS_BY_TAB[tab] || [];
    const isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : themeManager.isDarkMode();
    const style = themeManager.getStyle();
    const tokens = getDataCenterThemeTokens(isDark, style);

    const charts = this.__charts || (this.__charts = {});
    ids.forEach((id) => {
      const comp = this.selectComponent(`#${id}`);
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
          console.error('[data-center-v2] echarts.init failed:', id, err);
          return undefined;
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

    const tab = normalizeTab(this.data.tab);
    const days = this.data.days;

    let stage = 'init';
    try {
      stage = 'getDataCenter';
      const res = await api.getDataCenter(days);
      try {
        setCachedDataCenter(days, res);
      } catch (e) {}

      this.__dcRes = res;
      this.__dcResDays = days;
      this.__vmCache = {};
      this.__dcPayloadByTab = {};

      stage = 'buildViewModel';
      const built = buildTabVm(tab, res, days);
      (this.__vmCache || (this.__vmCache = {}))[tab] = built;
      (this.__dcPayloadByTab || (this.__dcPayloadByTab = {}))[tab] = built.payload;

      const afterSet = () => {
        wx.nextTick(() => {
          try {
            this.renderCharts(true);
          } catch (err) {
            console.error('[data-center-v2] renderCharts failed:', err);
          }
        });
      };

      stage = 'setData';
      const meta = TAB_META[tab] || TAB_META.global;
      const ok = trySetData(this, Object.assign({}, built.data, { tabTitle: meta.title, tabDesc: meta.desc }), afterSet);
      if (!ok) {
        const fallback = built.fallbackData || {};
        const ok2 = trySetData(this, Object.assign({}, fallback, { tabTitle: meta.title, tabDesc: meta.desc }), afterSet);
        if (!ok2) trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
      }
    } catch (e) {
      console.error('[data-center-v2] loadStats failed:', stage, e);
      const raw = e && e.message ? String(e.message) : '加载失败，请稍后再试。';
      const msg = raw.includes('Maximum call stack size exceeded') ? `数据渲染异常（${stage}）：${raw}` : raw;
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

  onGoMyBanks() {
    safeNavigate('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
  },

  onGoSubjectDetail(e) {
    const sid = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.subjectId) || 0);
    const subject = e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.subject ? String(e.currentTarget.dataset.subject) : '';
    if (!Number.isFinite(sid) || sid <= 0) return;
    const url = `/pages/subject-detail-v2/subject-detail-v2?id=${encodeURIComponent(String(sid))}` + (subject ? `&subject=${encodeURIComponent(String(subject))}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizSubject(e) {
    const subject = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.subject) || '').trim();
    if (!subject) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizBank(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=all&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoBankDetail(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/bank-detail/bank-detail?bank_id=${encodeURIComponent(String(bankId))}`, 'navigateTo');
  },

  onGoMistakesCenter() {
    safeNavigate('/pages/mistakes-v2/mistakes-v2', 'redirectTo');
  },

  onGoFavoritesCenter() {
    safeNavigate('/pages/favorites-v2/favorites-v2', 'redirectTo');
  },

  onGoQuizPublicMistakes(e) {
    const subject = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.subject) || '').trim();
    const qType = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.qType) || '').trim();
    if (!subject) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=mistakes&subject=${encodeURIComponent(subject)}` + (qType ? `&type=${encodeURIComponent(qType)}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizPublicAll(e) {
    const subject = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.subject) || '').trim();
    const qType = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.qType) || '').trim();
    if (!subject) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}` + (qType ? `&type=${encodeURIComponent(qType)}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoBankMistakes(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/mistakes-v2/mistakes-v2?bank_id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
  },

  onGoQuizBankMistakes(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=mistakes&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoBankFavorites(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/favorites-v2/favorites-v2?bank_id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
  },

  onGoQuizBankFavorites(e) {
    const bankId = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.bankId) || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoTagsCenter() {
    safeNavigate('/pages/tags-v2/tags-v2', 'redirectTo');
  },

  onGoTagCenterPublic(e) {
    const tag = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.tag) || '').trim();
    if (!tag) return;
    safeNavigate(`/pages/tags-v2/tags-v2?source=public&tag=${encodeURIComponent(tag)}`, 'redirectTo');
  },

  onGoTagCenterBanks(e) {
    const tag = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.tag) || '').trim();
    if (!tag) return;
    safeNavigate(`/pages/tags-v2/tags-v2?source=banks&tag=${encodeURIComponent(tag)}`, 'redirectTo');
  }
});
