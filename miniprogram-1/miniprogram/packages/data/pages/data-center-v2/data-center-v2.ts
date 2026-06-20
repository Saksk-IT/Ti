import { api } from '../../../../utils/api';
import { checkLogin } from '../../../../utils/auth';
import { safeNavigate } from '../../../../utils/nav';
import { themeManager, ThemeMode } from '../../../../utils/theme';
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
  question_id?: number;
  snippet: string;
  difficulty: number;
};

type SubjectRow = {
  key: string;
  subject_id: number;
  subject: string;
  total: number;
  answered: number;
  accuracy: number;
  completion: number;
  mistakes: number;
  favorites: number;
};

type BankRow = {
  key: string;
  bank_id: number;
  name: string;
  category_name: string;
  total: number;
  answered: number;
  accuracy: number;
  completion: number;
  mistakes: number;
  favorites: number;
};

type MistakeTopItem = {
  key: string;
  source: string;
  scope_label: string;
  name: string;
  count: number;
  times: number;
  bank_id: number;
  can_quiz_bank: boolean;
  bar_pct: number;
};

type RecentBankItem = {
  key: string;
  bank_id: number;
  bank_name: string;
  q_type: string;
  difficulty: number;
  snippet: string;
  wrong_count?: number | null;
};

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

type RecentFavoriteBankItem = {
  key: string;
  bank_id: number;
  bank_name: string;
  q_type: string;
  difficulty: number;
  snippet: string;
};

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

const TAB_META: Record<DataTabKey, { title: string; desc: string }> = {
  global: { title: '全局', desc: '全局视角：覆盖、正确、连续与复盘资产，一屏把握你的学习系统。' },
  banks: { title: '题库', desc: '题库全景：规模、覆盖、质量，把投入方向选得更聪明。' },
  mistakes: { title: '错题', desc: '错题是最有杠杆的提升入口：高频先闭环，薄弱再专项。' },
  favorites: { title: '收藏', desc: '收藏是高价值题库：复习、背题、考前冲刺都能复用。' },
  tags: { title: '标签', desc: '标签让题目资产结构化：复盘与专项训练更容易“复用”。' }
};

const CHART_IDS_BY_TAB: Record<DataTabKey, string[]> = {
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
    'dcDifficultyDistChart'
  ],
  banks: ['dcBankSplitChart', 'dcBankCategoryChart', 'dcBankBubbleChart', 'dcBankRankChart', 'dcSubjectProgressChart', 'dcSubjectRiskChart'],
  mistakes: ['dcMistakeTrendChart', 'dcMistakeTopChart', 'dcMistakeDifficultyChart', 'dcMistakeTypeChart'],
  favorites: ['dcFavoriteTrendChart', 'dcFavoriteTopChart', 'dcFavoriteDifficultyChart', 'dcFavoriteTypeChart'],
  tags: ['dcTagGraphChart', 'dcTagTreemapChart', 'dcTagTopChart', 'dcTagAccuracyChart']
};

function normalizeTab(raw: any): DataTabKey {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'banks' || v === 'mistakes' || v === 'favorites' || v === 'tags') return v as DataTabKey;
  return 'global';
}

function safeSlice<T>(list: any, n: number): T[] {
  const arr = Array.isArray(list) ? (list as T[]) : [];
  if (n <= 0) return [];
  return arr.slice(0, n);
}

function safeArr<T>(v: any): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

function lastActivity16(input: any): string {
  const s = String(input || '').trim();
  if (!s) return '—';
  return s.slice(0, 16);
}

function pickAllSummaryLite(summary: any) {
  const s = summary && typeof summary === 'object' ? summary : {};
  return {
    answered: toInt(s.answered),
    accuracy: pct1(s.accuracy),
    completion: pct1(s.completion),
    mistakes: toInt(s.mistakes),
    mistakes_times: toInt(s.mistakes_times),
    favorites: toInt(s.favorites)
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

function buildBankViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'banks');
  const allSummaryLite = pickAllSummaryLite(res?.all_summary || {});
  const bankSummary = res?.bank_summary || {};

  const subjects: SubjectRow[] = safeArr<any>(res?.subject_rows).map((s: any, idx: number) => ({
    key: String(s?.subject_id || s?.subject || idx),
    subject_id: toInt(s?.subject_id),
    subject: String(s?.subject || ''),
    total: toInt(s?.total),
    answered: toInt(s?.answered),
    accuracy: pct1(s?.accuracy),
    completion: pct1(s?.completion),
    mistakes: toInt(s?.mistakes),
    favorites: toInt(s?.favorites)
  }));

  const banks: BankRow[] = safeArr<any>(res?.bank_rows).map((b: any, idx: number) => ({
    key: String(b?.bank_id || b?.name || idx),
    bank_id: toInt(b?.bank_id),
    name: String(b?.name || ''),
    category_name: String(b?.category_name || '未分类'),
    total: toInt(b?.total),
    answered: toInt(b?.answered),
    accuracy: pct1(b?.accuracy),
    completion: pct1(b?.completion),
    mistakes: toInt(b?.mistakes),
    favorites: toInt(b?.favorites)
  }));

  const windowDays = normalizeDays(res?.window_days || currentDays);

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummaryLite,
      bank_summary: bankSummary,
      total_questions: toInt(res?.total_questions),
      answered_count: toInt(res?.answered_count),
      accuracy: pct1(res?.accuracy),
      window_answered: toInt(res?.window_answered),
      window_accuracy: pct1(res?.window_accuracy),
      subject_rows: subjects,
      bank_rows: banks
    }
  };
}

function sumDailyAll(list: any): number {
  const rows = Array.isArray(list) ? list : [];
  return rows.reduce((acc, r) => acc + toInt(r?.all), 0);
}

function buildMistakesViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'mistakes');
  const allSummaryLite = pickAllSummaryLite(res?.all_summary || {});
  const windowDays = normalizeDays(res?.window_days || currentDays);
  const mistakesNew = sumDailyAll(res?.mistakes_daily);

  const topRaw = safeArr<any>(res?.mistakes_top_items).slice(0, 12);
  const weights = topRaw.map((it: any) => toInt(it?.times || it?.count));
  const denom = Math.max(1, ...weights);
  const topItems: MistakeTopItem[] = topRaw.map((it: any, idx: number) => {
    const source = String(it?.source || '');
    const bankId = toInt(it?.bank_id);
    const w = toInt(it?.times || it?.count);
    return {
      key: String(it?.bank_id || it?.name || idx),
      source,
      scope_label: source === 'public' ? '公共' : '个人',
      name: String(it?.name || ''),
      count: toInt(it?.count),
      times: toInt(it?.times),
      bank_id: bankId,
      can_quiz_bank: source === 'banks' && bankId > 0,
      bar_pct: pct1((w * 100) / denom)
    };
  });

  const recentPublic: RecentPublicItem[] = safeArr<any>(res?.recent_mistakes)
    .slice(0, 6)
    .map((m: any, idx: number) => ({
      key: String(m?.question_id || idx),
      subject: String(m?.subject || ''),
      q_type: String(m?.q_type || ''),
      difficulty: toInt(m?.difficulty),
      snippet: String(m?.snippet || '')
    }));

  const recentBank: RecentBankItem[] = safeArr<any>(res?.recent_mistakes_bank)
    .slice(0, 6)
    .map((m: any, idx: number) => ({
      key: String(m?.question_id || m?.bank_id || idx),
      bank_id: toInt(m?.bank_id),
      bank_name: String(m?.bank_name || ''),
      q_type: String(m?.q_type || ''),
      difficulty: toInt(m?.difficulty),
      snippet: String(m?.snippet || ''),
      wrong_count: m?.wrong_count == null ? null : toInt(m?.wrong_count)
    }));

  return {
    payload,
    data: {
      inited: true,
      window_days: windowDays,
      errorMsg: '',
      all_summary: allSummaryLite,
      health_score: toInt(res?.health_score),
      mistakes_new: mistakesNew,
      mistakes_top_items: topItems,
      recent_mistakes: recentPublic,
      recent_mistakes_bank: recentBank
    }
  };
}

function buildFavoritesViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'favorites');
  const allSummaryLite = pickAllSummaryLite(res?.all_summary || {});
  const windowDays = normalizeDays(res?.window_days || currentDays);

  const favoritesNew = sumDailyAll(res?.favorites_daily);
  const answeredAll = toInt(allSummaryLite?.answered);
  const favAll = toInt(allSummaryLite?.favorites);
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

  const recentBank: RecentFavoriteBankItem[] = safeArr<any>(res?.recent_favorites_bank)
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
      all_summary: allSummaryLite,
      health_score: toInt(res?.health_score),
      favorites_new: favoritesNew,
      favorites_density: favoritesDensity,
      favorites_top_items: topItems,
      recent_favorites_public: recentPublic,
      recent_favorites_bank: recentBank
    }
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

function trySetData(page: any, data: any, cb?: () => void): boolean {
  try {
    if (typeof cb === 'function') page.setData(data, cb);
    else page.setData(data);
    return true;
  } catch (err) {
    console.error('[data-center-v2] setData failed:', err);
    return false;
  }
}

function buildCompatPayloadSafe(res: any, tab: DataTabKey) {
  try {
    return buildDataCenterCompatPayload(res, tab);
  } catch (err) {
    console.error('[data-center-v2] buildDataCenterCompatPayload failed:', tab, err);
    return { active_tab: tab, window_days: normalizeDays(res?.window_days || 30) };
  }
}

type TabVmResult = { payload: Record<string, unknown>; data: Record<string, unknown>; fallbackData?: Record<string, unknown> };

function buildTabVm(tab: DataTabKey, res: any, days: number): TabVmResult {
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
  data: {
    ...(themeManager.getPageData()),
    loading: false,
    inited: false,
    errorMsg: '',

    tab: 'global' as DataTabKey,
    tabTitle: TAB_META.global.title,
    tabDesc: TAB_META.global.desc,
    scrollIntoView: '',

    lazyStage: 1,
    ecLazy: { lazyLoad: true },

    days: 30 as 7 | 30 | 90,
    window_days: 30,

    last_activity_16: '—',

    all_summary: pickAllSummaryLite({}),
    health_score: 0,

    global_insights: [] as InsightItem[],
    next_actions: [] as NextActionItem[],
    weakness_rows: [] as WeaknessRow[],
    recent_mistakes: [] as RecentPublicItem[],
    recent_favorites_public: [] as RecentPublicItem[],

    bank_summary: {} as Record<string, unknown>,
    total_questions: 0,
    answered_count: 0,
    accuracy: 0,
    window_answered: 0,
    window_accuracy: 0,
    subject_rows: [] as SubjectRow[],
    bank_rows: [] as BankRow[],

    mistakes_new: 0,
    mistakes_top_items: [] as MistakeTopItem[],
    recent_mistakes_bank: [] as RecentBankItem[],

    favorites_new: 0,
    favorites_density: 0,
    favorites_top_items: [] as FavoriteTopItem[],
    recent_favorites_bank: [] as RecentFavoriteBankItem[],

    tags_kpis: {
      all_tag_count: 0,
      public_tag_count: 0,
      banks_tag_count: 0,
      all_tagged_questions: 0,
      public_tagged_questions: 0,
      banks_tagged_questions: 0,
      tagged_answered_coverage: 0
    } as TagsKpis,
    tags_public: [] as TagRow[],
    tags_banks: [] as TagRow[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    const tab = normalizeTab(options?.tab);
    const meta = TAB_META[tab] || TAB_META.global;
    this.setData({ tab, tabTitle: meta.title, tabDesc: meta.desc, days, window_days: days, lazyStage: 1 });
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

        const stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {})) as Record<string, number>;
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
        self.__lazyObserver = null;
      });
    } catch (e) {}
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const self = this;
    const tab: DataTabKey = normalizeTab(this.data.tab);
    const days = this.data.days;

    const patch: any = {};
    let hydrated = false;
    try {
      Object.assign(patch, themeManager.getPageData());
    } catch (e) {}

    const meta = TAB_META[tab] || TAB_META.global;
    patch.tabTitle = meta.title;
    patch.tabDesc = meta.desc;

    try {
      const stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {})) as Record<string, number>;
      patch.lazyStage = Number(stageMap[tab] || 1) || 1;
    } catch (e) {}

    if (!this.data.inited || self.__dcResDays !== days) {
      try {
        const cached = getCachedDataCenter(days);
        if (cached) {
          self.__dcRes = cached;
          self.__dcResDays = days;
          self.__vmCache = {};
          self.__dcPayloadByTab = {};
          self.__lastLoadedAt = Date.now();

          const built = buildTabVm(tab, cached, days);
          (self.__vmCache || (self.__vmCache = {}))[tab] = built;
          (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;
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
            : undefined
        );
      }
    } catch (e) {}

    if (!hydrated && (!this.data.inited || self.__dcResDays !== days) && !this.data.loading) {
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

    const self = this;
    self.__dcRes = null;
    self.__dcResDays = 0;
    self.__vmCache = {};
    self.__dcPayloadByTab = {};
    self.__lastLoadedAt = 0;
    self.__lazyStageByTab = {};

    this.setData({ days, window_days: days, lazyStage: 1, scrollIntoView: 'dcTop' }, () => {
      this.setData({ scrollIntoView: '' });
      this.loadStats(true);
    });
  },

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab);
    this.switchTab(tab);
  },

  ensureTabVm(tab: DataTabKey) {
    const self = this;
    const res = self.__dcRes;
    if (!res) return null;
    const days = this.data.days;

    const cache = (self.__vmCache || (self.__vmCache = {})) as Record<string, TabVmResult>;
    if (cache[tab]) return cache[tab];

    const built = buildTabVm(tab, res, days);
    cache[tab] = built;
    (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;
    return built;
  },

  disposeChartsAndObserver() {
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

  switchTab(nextTab: DataTabKey) {
    const self = this;
    const current = normalizeTab(this.data.tab);
    const tab = normalizeTab(nextTab);
    if (tab === current) return;

    const stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {})) as Record<string, number>;
    stageMap[current] = Number(this.data.lazyStage || 1) || 1;
    const nextStage = Number(stageMap[tab] || 1) || 1;

    this.disposeChartsAndObserver();

    const meta = TAB_META[tab] || TAB_META.global;
    const patch: any = { tab, tabTitle: meta.title, tabDesc: meta.desc, lazyStage: nextStage, scrollIntoView: 'dcTop', errorMsg: '' };

    if (self.__dcRes && self.__dcResDays === this.data.days) {
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
      if (!self.__dcRes || self.__dcResDays !== this.data.days) {
        this.loadStats(true);
      }
    });
  },

  renderCharts(forceInit = false, isDarkOverride?: boolean) {
    const self = this;
    const tab: DataTabKey = normalizeTab(this.data.tab);
    const payload = (self.__dcPayloadByTab || {})[tab];
    if (!payload) return;

    if (!self.__pageReady) {
      self.__pendingRender = true;
      return;
    }

    const ids = CHART_IDS_BY_TAB[tab] || [];
    const isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : themeManager.isDarkMode();
    const style = themeManager.getStyle();
    const tokens = getDataCenterThemeTokens(isDark, style);

    const charts = (self.__charts || (self.__charts = {})) as Record<string, any>;
    ids.forEach((id) => {
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
          console.error('[data-center-v2] echarts.init failed:', id, err);
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

    const tab: DataTabKey = normalizeTab(this.data.tab);
    const days = this.data.days;

    let stage = 'init';
    try {
      stage = 'getDataCenter';
      const res: any = await api.getDataCenter(days);
      try {
        setCachedDataCenter(days, res);
      } catch (e) {}

      self.__dcRes = res;
      self.__dcResDays = days;
      self.__vmCache = {};
      self.__dcPayloadByTab = {};

      stage = 'buildViewModel';
      const built = buildTabVm(tab, res, days);
      (self.__vmCache || (self.__vmCache = {}))[tab] = built;
      (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;

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
      const ok = trySetData(this, { ...built.data, tabTitle: meta.title, tabDesc: meta.desc }, afterSet);
      if (!ok) {
        const fallback = built.fallbackData || {};
        const ok2 = trySetData(this, { ...fallback, tabTitle: meta.title, tabDesc: meta.desc }, afterSet);
        if (!ok2) trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
      }
    } catch (e: any) {
      console.error('[data-center-v2] loadStats failed:', stage, e);
      const raw = e && e.message ? String(e.message) : '加载失败，请稍后再试。';
      const msg = raw.includes('Maximum call stack size exceeded') ? `数据渲染异常（${stage}）：${raw}` : raw;
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
  },

  onGoMyBanks() {
    safeNavigate('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
  },

  onGoSubjectDetail(e: any) {
    const sid = Number(e?.currentTarget?.dataset?.subjectId || 0);
    const subject = e?.currentTarget?.dataset?.subject ? String(e.currentTarget.dataset.subject) : '';
    if (!Number.isFinite(sid) || sid <= 0) return;
    const url =
      `/pages/subject-detail-v2/subject-detail-v2?id=${encodeURIComponent(String(sid))}` +
      (subject ? `&subject=${encodeURIComponent(String(subject))}` : '');
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizSubject(e: any) {
    const subject = String(e?.currentTarget?.dataset?.subject || '').trim();
    if (!subject) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=all&subject=${encodeURIComponent(subject)}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoQuizBank(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=all&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoBankDetail(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/bank-detail/bank-detail?bank_id=${encodeURIComponent(String(bankId))}`, 'navigateTo');
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

  onGoBankMistakes(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/mistakes-v2/mistakes-v2?bank_id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
  },

  onGoQuizBankMistakes(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=mistakes&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoBankFavorites(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    safeNavigate(`/pages/favorites-v2/favorites-v2?bank_id=${encodeURIComponent(String(bankId))}`, 'redirectTo');
  },

  onGoQuizBankFavorites(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const url = `/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=${encodeURIComponent(String(bankId))}`;
    safeNavigate(url, 'navigateTo');
  },

  onGoTagsCenter() {
    safeNavigate('/pages/tags-v2/tags-v2', 'redirectTo');
  },

  onGoTagCenterPublic(e: any) {
    const tag = String(e?.currentTarget?.dataset?.tag || '').trim();
    if (!tag) return;
    safeNavigate(`/pages/tags-v2/tags-v2?source=public&tag=${encodeURIComponent(tag)}`, 'redirectTo');
  },

  onGoTagCenterBanks(e: any) {
    const tag = String(e?.currentTarget?.dataset?.tag || '').trim();
    if (!tag) return;
    safeNavigate(`/pages/tags-v2/tags-v2?source=banks&tag=${encodeURIComponent(tag)}`, 'redirectTo');
  }
});
