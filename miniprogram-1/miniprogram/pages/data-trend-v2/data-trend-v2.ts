import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';
import { normalizeDays, toInt, pct1, buildTrendBars, buildHeatmapGrid } from '../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../utils/data-center-cache';

type HourBar = { hour: number; total: number; barPct: number };
type WeekdayBar = { name: string; total: number; barPct: number };
type TypeRow = { q_type: string; answered: number; accuracy: number };
type DifficultyRow = { difficulty: number; label: string; answered: number; accuracy: number };

function pickDaily(res: any): any[] {
  if (Array.isArray(res?.all_daily) && res.all_daily.length) return res.all_daily;
  if (Array.isArray(res?.daily) && res.daily.length) return res.daily;
  return [];
}

function buildTrendPatch(res: any) {
  const windowAnswered = toInt(res?.window_answered);
  const windowAccuracy = pct1(res?.window_accuracy);

  const dailySource = pickDaily(res);
  const dailyMax = Math.max(toInt(res?.all_daily_max), toInt(res?.daily_max), 1);
  const trendBars = buildTrendBars(dailySource, dailyMax);

  const heatmapRows = buildHeatmapGrid(res?.activity_heatmap?.all, res?.activity_heatmap?.max);

  const hourlyRaw = Array.isArray(res?.activity_hourly?.all) ? res.activity_hourly.all : [];
  const hourlyMax = Math.max(toInt(res?.activity_hourly?.max), 1);
  const hourlyBars: HourBar[] = hourlyRaw.map((h: any) => ({
    hour: toInt(h?.hour),
    total: toInt(h?.total),
    barPct: pct1((toInt(h?.total) * 100) / hourlyMax)
  }));

  const daySums = [0, 0, 0, 0, 0, 0, 0];
  const heatmapAll = Array.isArray(res?.activity_heatmap?.all) ? res.activity_heatmap.all : [];
  heatmapAll.forEach((it: any) => {
    if (!it || it.length < 3) return;
    const day = toInt(it[0]);
    const val = toInt(it[2]);
    if (day < 0 || day > 6) return;
    daySums[day] += val;
  });
  const dayMax = Math.max(1, ...daySums);
  const dayNames = ['鍛ㄤ竴', '鍛ㄤ簩', '鍛ㄤ笁', '鍛ㄥ洓', '鍛ㄤ簲', '鍛ㄥ叚', '鍛ㄦ棩'];
  const weekdayBars: WeekdayBar[] = daySums.map((val, idx) => ({
    name: dayNames[idx],
    total: val,
    barPct: pct1((val * 100) / dayMax)
  }));

  const typeRows: TypeRow[] = (Array.isArray(res?.type_rows) ? res.type_rows : []).map((t: any) => ({
    q_type: String(t?.q_type || ''),
    answered: toInt(t?.answered),
    accuracy: pct1(t?.accuracy)
  }));

  const difficultyRows: DifficultyRow[] = (Array.isArray(res?.difficulty_rows) ? res.difficulty_rows : []).map((d: any) => ({
    difficulty: toInt(d?.difficulty),
    label: String(d?.label || ''),
    answered: toInt(d?.answered),
    accuracy: pct1(d?.accuracy)
  }));

  return {
    inited: true,
    windowAnswered,
    windowAccuracy,
    trendBars,
    hourlyBars,
    weekdayBars,
    heatmapRows,
    typeRows,
    difficultyRows
  };
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,
    errorMsg: '',

    days: 30 as 7 | 30 | 90,

    windowAnswered: 0,
    windowAccuracy: 0,

    trendBars: [] as ReturnType<typeof buildTrendBars>,
    hourlyBars: [] as HourBar[],
    weekdayBars: [] as WeekdayBar[],
    heatmapRows: [] as ReturnType<typeof buildHeatmapGrid>,
    typeRows: [] as TypeRow[],
    difficultyRows: [] as DifficultyRow[]
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
          Object.assign(patch, buildTrendPatch(cached), { errorMsg: '' });
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

      const windowAnswered = toInt(res?.window_answered);
      const windowAccuracy = pct1(res?.window_accuracy);

      const dailySource = pickDaily(res);
      const dailyMax = Math.max(toInt(res?.all_daily_max), toInt(res?.daily_max), 1);
      const trendBars = buildTrendBars(dailySource, dailyMax);

      const heatmapRows = buildHeatmapGrid(res?.activity_heatmap?.all, res?.activity_heatmap?.max);

      const hourlyRaw = Array.isArray(res?.activity_hourly?.all) ? res.activity_hourly.all : [];
      const hourlyMax = Math.max(toInt(res?.activity_hourly?.max), 1);
      const hourlyBars: HourBar[] = hourlyRaw.map((h: any) => ({
        hour: toInt(h?.hour),
        total: toInt(h?.total),
        barPct: pct1((toInt(h?.total) * 100) / hourlyMax)
      }));

      const daySums = [0, 0, 0, 0, 0, 0, 0];
      const heatmapAll = Array.isArray(res?.activity_heatmap?.all) ? res.activity_heatmap.all : [];
      heatmapAll.forEach((it: any) => {
        if (!it || it.length < 3) return;
        const day = toInt(it[0]);
        const val = toInt(it[2]);
        if (day < 0 || day > 6) return;
        daySums[day] += val;
      });
      const dayMax = Math.max(1, ...daySums);
      const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
      const weekdayBars: WeekdayBar[] = daySums.map((val, idx) => ({
        name: dayNames[idx],
        total: val,
        barPct: pct1((val * 100) / dayMax)
      }));

      const typeRows: TypeRow[] = (Array.isArray(res?.type_rows) ? res.type_rows : []).map((t: any) => ({
        q_type: String(t?.q_type || ''),
        answered: toInt(t?.answered),
        accuracy: pct1(t?.accuracy)
      }));

      const difficultyRows: DifficultyRow[] = (Array.isArray(res?.difficulty_rows) ? res.difficulty_rows : []).map((d: any) => ({
        difficulty: toInt(d?.difficulty),
        label: String(d?.label || ''),
        answered: toInt(d?.answered),
        accuracy: pct1(d?.accuracy)
      }));

      this.setData({
        inited: true,
        windowAnswered,
        windowAccuracy,
        trendBars,
        hourlyBars,
        weekdayBars,
        heatmapRows,
        typeRows,
        difficultyRows
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后再试。' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
