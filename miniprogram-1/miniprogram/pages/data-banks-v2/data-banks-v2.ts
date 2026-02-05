import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { normalizeDays, toInt, pct1 } from '../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../utils/data-center-cache';

type CategoryRow = { category_id: number; category_name: string; answered: number; accuracy: number; barPct: number };
type BankRow = { bank_id: number; name: string; answered: number; accuracy: number; barPct: number };

function buildBanksPatch(res: any) {
  const allSummary = res?.all_summary || {};
  const bankSummary = res?.bank_summary || {};

  const lastActivityRaw = allSummary?.last_activity ? String(allSummary.last_activity) : '';
  const lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';

  const bankTotal = toInt(bankSummary?.bank_total);
  const bankTotalQuestions = toInt(bankSummary?.total_questions);
  const bankAnswered = toInt(bankSummary?.answered);
  const bankAccuracy = pct1(bankSummary?.accuracy);
  const bankCompletion = pct1(bankSummary?.completion);

  const publicAnswered = toInt(res?.answered_count);
  const publicAccuracy = pct1(res?.accuracy);

  const allAccuracy = pct1(allSummary?.accuracy);
  const allFavorites = toInt(allSummary?.favorites);
  const allMistakes = toInt(allSummary?.mistakes);

  const answeredTotal = publicAnswered + bankAnswered;
  const sharePublicPct = answeredTotal > 0 ? pct1((publicAnswered * 100) / answeredTotal) : 0;
  const shareBankPct = answeredTotal > 0 ? pct1((bankAnswered * 100) / answeredTotal) : 0;

  const catRaw = Array.isArray(res?.bank_category_rows) ? res.bank_category_rows : [];
  const catMax = Math.max(1, ...catRaw.map((c: any) => toInt(c?.answered)));
  const categoryRows: CategoryRow[] = catRaw.map((c: any) => ({
    category_id: toInt(c?.category_id),
    category_name: String(c?.category_name || '未分类'),
    answered: toInt(c?.answered),
    accuracy: pct1(c?.accuracy),
    barPct: pct1((toInt(c?.answered) * 100) / catMax)
  }));

  const bankRows = Array.isArray(res?.bank_rows) ? res.bank_rows : [];
  const topMax = Math.max(1, ...bankRows.map((b: any) => toInt(b?.answered)));
  const bankTopRows: BankRow[] = bankRows
    .map((b: any) => ({
      bank_id: toInt(b?.bank_id),
      name: String(b?.name || ''),
      answered: toInt(b?.answered),
      accuracy: pct1(b?.accuracy),
      barPct: pct1((toInt(b?.answered) * 100) / topMax)
    }))
    .sort((a, b) => b.answered - a.answered)
    .slice(0, 10);

  return {
    inited: true,
    lastActivityText,
    bankTotal,
    bankTotalQuestions,
    bankAnswered,
    bankAccuracy,
    bankCompletion,
    publicAnswered,
    publicAccuracy,
    allAccuracy,
    allFavorites,
    allMistakes,
    sharePublicPct,
    shareBankPct,
    categoryRows,
    bankTopRows,
    bankRows
  };
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,
    errorMsg: '',

    days: 30 as 7 | 30 | 90,

    lastActivityText: '—',

    bankTotal: 0,
    bankTotalQuestions: 0,
    bankAnswered: 0,
    bankAccuracy: 0,
    bankCompletion: 0,

    publicAnswered: 0,
    publicAccuracy: 0,

    allAccuracy: 0,
    allFavorites: 0,
    allMistakes: 0,

    sharePublicPct: 0,
    shareBankPct: 0,

    categoryRows: [] as CategoryRow[],
    bankTopRows: [] as BankRow[],
    bankRows: [] as any[]
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
      Object.assign(patch, themeManager.getPageData() as any);
    } catch (e) {}
    if (!this.data.inited) {
      try {
        const cached = getCachedDataCenter(this.data.days);
        if (cached) {
          Object.assign(patch, buildBanksPatch(cached), { errorMsg: '' });
          const self: any = this as any;
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
    this.setData(themeManager.getPageData() as any);
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData() as any), themeMode: mode });
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

  onGoBankPractice(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!bankId) return;
    wx.navigateTo({ url: `/pages/bank-detail/bank-detail?bank_id=${bankId}` });
  },

  onGoBankManage(e: any) {
    const bankId = Number(e?.currentTarget?.dataset?.bankId || 0);
    if (!bankId) return;
    wx.navigateTo({ url: `/pages/bank-detail/bank-detail?bank_id=${bankId}&tab=manage` });
  },

  async loadStats(force = false) {
    if (this.data.loading) return;
    const self: any = this as any;
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

      const lastActivityRaw = allSummary?.last_activity ? String(allSummary.last_activity) : '';
      const lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';

      const bankTotal = toInt(bankSummary?.bank_total);
      const bankTotalQuestions = toInt(bankSummary?.total_questions);
      const bankAnswered = toInt(bankSummary?.answered);
      const bankAccuracy = pct1(bankSummary?.accuracy);
      const bankCompletion = pct1(bankSummary?.completion);

      const publicAnswered = toInt(res?.answered_count);
      const publicAccuracy = pct1(res?.accuracy);

      const allAccuracy = pct1(allSummary?.accuracy);
      const allFavorites = toInt(allSummary?.favorites);
      const allMistakes = toInt(allSummary?.mistakes);

      const answeredTotal = publicAnswered + bankAnswered;
      const sharePublicPct = answeredTotal > 0 ? pct1((publicAnswered * 100) / answeredTotal) : 0;
      const shareBankPct = answeredTotal > 0 ? pct1((bankAnswered * 100) / answeredTotal) : 0;

      const catRaw = Array.isArray(res?.bank_category_rows) ? res.bank_category_rows : [];
      const catMax = Math.max(1, ...catRaw.map((c: any) => toInt(c?.answered)));
      const categoryRows: CategoryRow[] = catRaw.map((c: any) => ({
        category_id: toInt(c?.category_id),
        category_name: String(c?.category_name || '未分类'),
        answered: toInt(c?.answered),
        accuracy: pct1(c?.accuracy),
        barPct: pct1((toInt(c?.answered) * 100) / catMax)
      }));

      const bankRows = Array.isArray(res?.bank_rows) ? res.bank_rows : [];
      const topMax = Math.max(1, ...bankRows.map((b: any) => toInt(b?.answered)));
      const bankTopRows: BankRow[] = bankRows
        .map((b: any) => ({
          bank_id: toInt(b?.bank_id),
          name: String(b?.name || ''),
          answered: toInt(b?.answered),
          accuracy: pct1(b?.accuracy),
          barPct: pct1((toInt(b?.answered) * 100) / topMax)
        }))
        .sort((a, b) => b.answered - a.answered)
        .slice(0, 10);

      this.setData({
        inited: true,
        lastActivityText,
        bankTotal,
        bankTotalQuestions,
        bankAnswered,
        bankAccuracy,
        bankCompletion,
        publicAnswered,
        publicAccuracy,
        allAccuracy,
        allFavorites,
        allMistakes,
        sharePublicPct,
        shareBankPct,
        categoryRows,
        bankTopRows,
        bankRows
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后再试。' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
