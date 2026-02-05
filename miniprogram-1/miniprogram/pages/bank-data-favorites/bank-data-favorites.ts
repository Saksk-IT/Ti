import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeMode } from '../../utils/theme';

type DataSubTab = 'global' | 'mistakes' | 'favorites';
type DetailTab = 'practice' | 'exam' | 'search' | 'stats' | 'share';
type TrendView = {
  day: string;
  label: string;
  answered: number;
  correct: number;
  wrong: number;
  answeredPct: number;
  correctPctInAnswered: number;
};
type TypeBreakdownView = {
  q_type: string;
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  favorites: number;
  mistakes: number;
  accuracyText: string;
  completionText: string;
  completionWidth: number;
  metaText: string;
};
type AdviceItem = { title?: string; content?: string };
type StatsOverviewView = {
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  favorites: number;
  mistakes: number;
  mistakeTimes: number;
  accuracy: number;
  completion: number;
  accuracyText: string;
  completionText: string;
  streakDays: number;
  lastText: string;
};

function normalizeDays(input: any): 7 | 14 | 30 | 90 {
  const n = Number(input || 14);
  if (n === 7 || n === 14 || n === 30 || n === 90) return n;
  return 14;
}

function clampPct(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(100, v));
}

function formatDateTime(raw: any): string {
  const s = String(raw || '').trim();
  if (!s) return '-';
  try {
    const iso = s.includes('T') ? s : s.replace(' ', 'T');
    const d = new Date(iso);
    if (isNaN(d.getTime())) return s;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${hh}:${mm}`;
  } catch {
    return s;
  }
}

Page({
  data: {
    inited: false,
    loading: false,

    bankId: 0,
    bankName: '',
    bankDescription: '',
    dataSubTab: 'favorites' as DataSubTab,
    detailTab: 'stats' as DetailTab,

    statsDays: 14 as 7 | 14 | 30 | 90,
    statsLoadedDays: 0,
    statsLoading: false,
    statsError: '',

    statsOverview: {
      total: 0,
      answered: 0,
      correct: 0,
      wrong: 0,
      favorites: 0,
      mistakes: 0,
      mistakeTimes: 0,
      accuracy: 0,
      completion: 0,
      accuracyText: '0.0%',
      completionText: '0.0%',
      streakDays: 0,
      lastText: '-'
    } as StatsOverviewView,
    statsTrend: [] as TrendView[],
    statsByType: [] as TypeBreakdownView[],
    statsAdvice: [] as AdviceItem[],

    ringAccuracy: 0,
    ringCompletion: 0,
    ringActive: 0,
    activeDaysRate: 0,
    favMistakeRateText: '0%',
    heatCells: [] as Array<{ level: number }>,
    displayTypes: [] as TypeBreakdownView[]
  },

  onLoad(options: any) {
    const rawId = options?.id ?? options?.bank_id ?? options?.bankId;
    const bankId = Number(rawId || 0);
    let bankName = options?.bank ? String(options.bank) : options?.name ? String(options.name) : '';
    if (bankName) {
      try {
        bankName = decodeURIComponent(bankName);
      } catch (e) {}
    }
    const days = normalizeDays(options?.days);
    this.setData({
      bankId: Number.isFinite(bankId) ? bankId : 0,
      bankName,
      statsDays: days
    });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}

    if (!this.data.inited && !this.data.loading) {
      this.bootstrap();
    }
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData() as any), themeMode: mode });
  },

  onDetailTabTap(e: any) {
    const raw = String(e?.currentTarget?.dataset?.tab || 'practice').trim().toLowerCase();
    const tab: DetailTab =
      raw === 'exam' || raw === 'search' || raw === 'share'
        ? (raw as DetailTab)
        : raw === 'stats'
          ? 'stats'
          : 'practice';

    if (tab === 'stats') return;

    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    const pages = getCurrentPages();
    const prev = pages.length >= 2 ? (pages[pages.length - 2] as any) : null;
    const prevRoute = prev?.route;
    const prevId = Number(prev?.data?.bankId || 0);

    const returnKey = `bank_${bankId}_return_tab`;
    if (prevRoute === 'pages/bank-detail/bank-detail' && prevId === bankId) {
      try {
        wx.setStorageSync(returnKey, tab);
      } catch (err) {}
      wx.navigateBack({ delta: 1 });
      return;
    }

    try {
      wx.setStorageSync(returnKey, '');
    } catch (err) {}
    safeNavigate(`/pages/bank-detail/bank-detail?id=${encodeURIComponent(String(bankId))}&tab=${encodeURIComponent(tab)}`, 'redirectTo');
  },

  onDataTabTap(e: any) {
    const raw = String(e?.currentTarget?.dataset?.subtab || 'global');
    const subtab: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
    if (subtab === this.data.dataSubTab) return;
    const bankId = Number(this.data.bankId || 0);
    const bank = String(this.data.bankName || '').trim();
    const params: string[] = [];
    if (bankId) params.push(`id=${encodeURIComponent(String(bankId))}`);
    if (bank) params.push(`bank=${encodeURIComponent(bank)}`);
    const days = Number(this.data.statsDays || 14) || 14;
    if ([7, 14, 30, 90].includes(days)) params.push(`days=${encodeURIComponent(String(days))}`);
    const base =
      subtab === 'mistakes'
        ? '/pages/bank-data-mistakes/bank-data-mistakes'
        : subtab === 'favorites'
          ? '/pages/bank-data-favorites/bank-data-favorites'
          : '/pages/bank-data-global/bank-data-global';
    const url = params.length ? `${base}?${params.join('&')}` : base;
    safeNavigate(url, 'redirectTo');
  },

  onStatsDaysTap(e: any) {
    const days = Number(e?.currentTarget?.dataset?.days || 14) as 7 | 14 | 30 | 90;
    if (![7, 14, 30, 90].includes(days)) return;
    if (days === this.data.statsDays) return;
    this.setData({ statsDays: days, statsLoadedDays: 0 }, () => this.loadStatsDetail(days));
  },

  async bootstrap() {
    this.setData({ loading: true });
    try {
      await this.resolveBank();
      this.setData({ inited: true });
      await this.loadStatsDetail(this.data.statsDays);
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) ? String(e.message) : '数据加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  async resolveBank() {
    const bankName = String(this.data.bankName || '').trim();
    const bankId = Number(this.data.bankId || 0);
    if (bankName) return;
    if (!bankId) {
      throw new Error('缺少题库信息');
    }
    const res = await api.getBankDetail(bankId);
    const bankData = (res as any)?.data || res || {};
    const name = String(bankData?.name || '').trim();
    const description = String(bankData?.description || '').trim();
    this.setData({ bankName: name || `题库${bankId}`, bankDescription: description });
  },

  buildStatsView(data: any) {
    const total = Number(data?.total_count || 0) || 0;
    const answered = Number(data?.answered || 0) || 0;
    const correct = Number(data?.correct || 0) || 0;
    const wrong = Number(data?.wrong || 0) || 0;
    const favorites = Number(data?.favorites || 0) || 0;
    const mistakes = Number(data?.mistakes || 0) || 0;
    const mistakeTimes = Number(data?.mistakes_times || 0) || 0;
    const accuracy = Number(data?.accuracy || 0) || 0;
    const completion = Number(data?.completion || 0) || 0;
    const streakDays = Number(data?.streak_days || 0) || 0;
    const lastText = formatDateTime(data?.last_activity);

    const overview: StatsOverviewView = {
      total,
      answered,
      correct,
      wrong,
      favorites,
      mistakes,
      mistakeTimes,
      accuracy,
      completion,
      accuracyText: `${accuracy.toFixed(1)}%`,
      completionText: `${completion.toFixed(1)}%`,
      streakDays,
      lastText
    };

    const rawTrend = Array.isArray(data?.trend) ? data.trend : [];
    const maxAnswered = rawTrend.reduce((m: number, it: any) => Math.max(m, Number(it?.answered || 0) || 0), 0) || 0;
    const trend: TrendView[] = rawTrend.map((it: any) => {
      const day = String(it?.day || '');
      const label = day ? day.slice(5) : '';
      const a = Number(it?.answered || 0) || 0;
      const c = Number(it?.correct || 0) || 0;
      const w = Number(it?.wrong || 0) || Math.max(0, a - c);
      const answeredPct = maxAnswered > 0 ? clampPct((a / maxAnswered) * 100) : 0;
      const correctPctInAnswered = a > 0 ? clampPct((Math.min(a, c) / a) * 100) : 0;
      return { day, label, answered: a, correct: Math.min(a, c), wrong: w, answeredPct, correctPctInAnswered };
    });

    const rawByType = Array.isArray(data?.by_type) ? data.by_type : [];
    const byType: TypeBreakdownView[] = rawByType.map((it: any) => {
      const q_type = String(it?.q_type || '未知');
      const t = Number(it?.total || 0) || 0;
      const a = Number(it?.answered || 0) || 0;
      const c = Number(it?.correct || 0) || 0;
      const w = Number(it?.wrong || 0) || Math.max(0, a - c);
      const fav = Number(it?.favorites || 0) || 0;
      const mis = Number(it?.mistakes || 0) || 0;
      const acc = Number(it?.accuracy || 0) || 0;
      const comp = Number(it?.completion || 0) || 0;
      const completionWidth = clampPct(comp);
      return {
        q_type,
        total: t,
        answered: a,
        correct: c,
        wrong: w,
        favorites: fav,
        mistakes: mis,
        accuracyText: `${acc.toFixed(1)}%`,
        completionText: `${comp.toFixed(1)}%`,
        completionWidth,
        metaText: `收藏 ${fav} · 已做 ${a}/${t} · 正确率 ${acc.toFixed(1)}% · 覆盖率 ${comp.toFixed(1)}%`
      };
    });

    const advice: AdviceItem[] = Array.isArray(data?.advice) ? data.advice : [];
    return { overview, trend, byType, advice };
  },

  buildHeatCells(trend: TrendView[]) {
    const slice = trend.slice(-28);
    const maxAnswered = slice.reduce((m, it) => Math.max(m, it.answered || 0), 0) || 0;
    const cells = slice.map((it) => {
      if (!maxAnswered) return { level: 0 };
      const pct = it.answered / maxAnswered;
      const level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
      return { level };
    });
    const pad = 28 - cells.length;
    if (pad > 0) {
      return Array.from({ length: pad }, () => ({ level: 0 })).concat(cells);
    }
    return cells;
  },

  async loadStatsDetail(days: number) {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (this.data.statsLoading) return;
    this.setData({ statsLoading: true, statsError: '' });
    try {
      const data: any = await api.getBankStatsDetail(bankId, { days, source: 'favorites' });
      const view = this.buildStatsView(data || {});
      const activeDays = view.trend.filter((it) => it.answered > 0).length;
      const activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
      const favMistakeRate =
        view.overview.total > 0 ? clampPct((view.overview.mistakes / view.overview.total) * 100) : 0;
      const sortedTypes = [...view.byType].sort((a, b) => b.favorites - a.favorites);
      this.setData({
        statsLoadedDays: days,
        statsLoading: false,
        statsOverview: view.overview,
        statsTrend: view.trend,
        statsByType: view.byType,
        statsAdvice: view.advice,
        ringAccuracy: clampPct(view.overview.accuracy),
        ringCompletion: clampPct(view.overview.completion),
        ringActive: clampPct(activeDaysRate),
        activeDaysRate,
        favMistakeRateText: `${favMistakeRate.toFixed(0)}%`,
        heatCells: this.buildHeatCells(view.trend),
        displayTypes: sortedTypes
      });
    } catch (err: any) {
      this.setData({
        statsLoading: false,
        statsError: (err && err.message) ? String(err.message) : '统计加载失败'
      });
    }
  }
});
