import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { normalizeDays, toInt, pct1, buildTrendBars, buildHeatmapGrid, buildTopMix } from '../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../utils/data-center-cache';

type NextAction = { title: string; meta: string; subject: string; q_type: string };
type WeaknessRow = { key: string; subject: string; q_type: string; answered: number; accuracy: number };
type AbilityItem = { name: string; value: number };
type TopMixItem = { name: string; answered: number; accuracy: number; barPct: number };

function pickDaily(res: any): any[] {
  if (Array.isArray(res?.all_daily) && res.all_daily.length) return res.all_daily;
  if (Array.isArray(res?.daily) && res.daily.length) return res.daily;
  return [];
}

function buildHistoryPatch(res: any) {
  const allSummary = res?.all_summary || {};
  const bankSummary = res?.bank_summary || {};

  const totalQuestions = toInt(allSummary?.total_questions);
  const answeredCount = toInt(allSummary?.answered);
  const correctCount = toInt(allSummary?.correct);
  const accuracy = pct1(allSummary?.accuracy);
  const completion = pct1(allSummary?.completion);
  const favoritesCount = toInt(allSummary?.favorites);
  const mistakesCount = toInt(allSummary?.mistakes);
  const mistakesTimes = toInt(allSummary?.mistakes_times);
  const streakDays = toInt(allSummary?.streak_days);
  const lastActivityRaw = allSummary?.last_activity ? String(allSummary.last_activity) : '';
  const lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';

  const publicAnswered = toInt(res?.answered_count);
  const bankAnswered = toInt(bankSummary?.answered);

  const windowAnswered = toInt(res?.window_answered);
  const windowAccuracy = pct1(res?.window_accuracy);

  const dailySource = pickDaily(res);
  const dailyMax = Math.max(toInt(res?.all_daily_max), toInt(res?.daily_max), 1);
  const trendBars = buildTrendBars(dailySource, dailyMax);

  const heatmapRows = buildHeatmapGrid(res?.activity_heatmap?.all, res?.activity_heatmap?.max);

  const abilityList = (Array.isArray(res?.ability_radar) ? res.ability_radar : []).map((a: any) => ({
    name: String(a?.name || ''),
    value: pct1(a?.value)
  }));

  const topMixRaw = buildTopMix(res?.subject_rows || [], res?.bank_rows || [], 8);
  const topMax = Math.max(1, ...topMixRaw.map((it) => toInt((it as Record<string, unknown>).answered)));
  const topMix: TopMixItem[] = topMixRaw.map((it) => ({
    name: it.name,
    answered: toInt((it as Record<string, unknown>).answered),
    accuracy: pct1((it as Record<string, unknown>).accuracy),
    barPct: pct1((toInt((it as Record<string, unknown>).answered) * 100) / topMax)
  }));

  const nextActions = Array.isArray(res?.next_actions) ? (res.next_actions as NextAction[]) : [];
  const weaknessRaw = Array.isArray(res?.weakness_rows) ? res.weakness_rows : [];
  const weaknessRows: WeaknessRow[] = weaknessRaw.map((w: any) => ({
    key: `${String(w?.subject || '')}__${String(w?.q_type || '')}`,
    subject: String(w?.subject || ''),
    q_type: String(w?.q_type || ''),
    answered: toInt(w?.answered),
    accuracy: pct1(w?.accuracy)
  }));

  return {
    inited: true,
    totalQuestions,
    answeredCount,
    correctCount,
    accuracy,
    completion,
    favoritesCount,
    mistakesCount,
    mistakesTimes,
    streakDays,
    lastActivityText,
    publicAnswered,
    bankAnswered,
    windowAnswered,
    windowAccuracy,
    trendBars,
    heatmapRows,
    abilityList,
    topMix,
    nextActions,
    weaknessRows
  };
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,
    errorMsg: '',

    days: 30 as 7 | 30 | 90,
    activeTab: 'overview',

    totalQuestions: 0,
    answeredCount: 0,
    correctCount: 0,
    accuracy: 0,
    completion: 0,
    favoritesCount: 0,
    mistakesCount: 0,
    mistakesTimes: 0,
    streakDays: 0,
    lastActivityText: '—',

    publicAnswered: 0,
    bankAnswered: 0,

    windowAnswered: 0,
    windowAccuracy: 0,

    trendBars: [] as ReturnType<typeof buildTrendBars>,
    heatmapRows: [] as ReturnType<typeof buildHeatmapGrid>,
    abilityList: [] as AbilityItem[],
    topMix: [] as TopMixItem[],
    nextActions: [] as NextAction[],
    weaknessRows: [] as WeaknessRow[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    this.setData({ days });
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
          Object.assign(patch, buildHistoryPatch(cached), { errorMsg: '' });
          const self = this;
          self.__lastLoadedAt = Date.now();
          hydrated = true;
        }
      } catch (e) {}
    }
    try {
      if (Object.keys(patch).length) this.setData(patch);
    } catch (e) {}

    if (!hydrated && !this.data.inited && !this.data.loading) {
      this.loadStats(true);
    }
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
    this.setData({ days }, () => {
      this.loadStats(true);
    });
  },

  onTabTap(e: any) {
    const tab = String(e?.currentTarget?.dataset?.tab || '');
    const days = this.data.days;
    const map: Record<string, string> = {
      overview: '/pages/history-v2/history-v2',
      banks: '/pages/data-banks-v2/data-banks-v2',
      trend: '/pages/data-trend-v2/data-trend-v2',
      ai: '/pages/data-ai-v2/data-ai-v2'
    };
    if (!map[tab]) return;
    safeNavigate(`${map[tab]}?days=${days}`, 'reLaunch');
  },

  onDayBarTap(e: any) {
    const day = String(e?.currentTarget?.dataset?.day || '');
    const total = toInt(e?.currentTarget?.dataset?.total);
    const accuracy = pct1(e?.currentTarget?.dataset?.accuracy);
    if (!day) return;
    wx.showToast({ title: `${day}：${total}题，正确率 ${accuracy}%`, icon: 'none' });
  },

  onGoQuiz(e: any) {
    const subject = String(e?.currentTarget?.dataset?.subject || 'all');
    const type = String(e?.currentTarget?.dataset?.type || 'all');
    const source = String(e?.currentTarget?.dataset?.source || 'all');
    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(subject)}`);
    params.push('mode=quiz');
    params.push(`source=${encodeURIComponent(source)}`);
    if (type && type !== 'all') params.push(`type=${encodeURIComponent(type)}`);
    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  },

  async loadStats(force = false) {
    if (this.data.loading) return;
    const self = this;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 10000) return;

    self.__lastLoadedAt = now;
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res: any = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      const allSummary = res?.all_summary || {};
      const bankSummary = res?.bank_summary || {};

      const totalQuestions = toInt(allSummary?.total_questions);
      const answeredCount = toInt(allSummary?.answered);
      const correctCount = toInt(allSummary?.correct);
      const accuracy = pct1(allSummary?.accuracy);
      const completion = pct1(allSummary?.completion);
      const favoritesCount = toInt(allSummary?.favorites);
      const mistakesCount = toInt(allSummary?.mistakes);
      const mistakesTimes = toInt(allSummary?.mistakes_times);
      const streakDays = toInt(allSummary?.streak_days);
      const lastActivityRaw = allSummary?.last_activity ? String(allSummary.last_activity) : '';
      const lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';

      const publicAnswered = toInt(res?.answered_count);
      const bankAnswered = toInt(bankSummary?.answered);

      const windowAnswered = toInt(res?.window_answered);
      const windowAccuracy = pct1(res?.window_accuracy);

      const dailySource = pickDaily(res);
      const dailyMax = Math.max(toInt(res?.all_daily_max), toInt(res?.daily_max), 1);
      const trendBars = buildTrendBars(dailySource, dailyMax);

      const heatmapRows = buildHeatmapGrid(res?.activity_heatmap?.all, res?.activity_heatmap?.max);

      const abilityList = (Array.isArray(res?.ability_radar) ? res.ability_radar : []).map((a: any) => ({
        name: String(a?.name || ''),
        value: pct1(a?.value)
      }));

      const topMixRaw = buildTopMix(res?.subject_rows || [], res?.bank_rows || [], 8);
      const topMax = Math.max(1, ...topMixRaw.map((it) => toInt(it.answered)));
      const topMix: TopMixItem[] = topMixRaw.map((it) => ({
        name: it.name,
        answered: toInt(it.answered),
        accuracy: pct1(it.accuracy),
        barPct: pct1((toInt(it.answered) * 100) / topMax)
      }));

      const nextActions = Array.isArray(res?.next_actions) ? (res.next_actions as NextAction[]) : [];
      const weaknessRaw = Array.isArray(res?.weakness_rows) ? res.weakness_rows : [];
      const weaknessRows: WeaknessRow[] = weaknessRaw.map((w: any) => ({
        key: `${String(w?.subject || '')}__${String(w?.q_type || '')}`,
        subject: String(w?.subject || ''),
        q_type: String(w?.q_type || ''),
        answered: toInt(w?.answered),
        accuracy: pct1(w?.accuracy)
      }));

      this.setData({
        inited: true,
        totalQuestions,
        answeredCount,
        correctCount,
        accuracy,
        completion,
        favoritesCount,
        mistakesCount,
        mistakesTimes,
        streakDays,
        lastActivityText,
        publicAnswered,
        bankAnswered,
        windowAnswered,
        windowAccuracy,
        trendBars,
        heatmapRows,
        abilityList,
        topMix,
        nextActions,
        weaknessRows
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后再试。' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
