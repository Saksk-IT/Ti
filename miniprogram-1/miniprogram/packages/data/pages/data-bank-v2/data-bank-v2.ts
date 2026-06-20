import { api } from '../../../../utils/api';
import { checkLogin } from '../../../../utils/auth';
import { safeNavigate } from '../../../../utils/nav';
import { themeManager, ThemeMode } from '../../../../utils/theme';
import { normalizeDays, toInt, pct1 } from '../../../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../../../utils/data-center-cache';
import { buildDataCenterCompatPayload, buildDataCenterChartOption, getDataCenterThemeTokens } from '../../utils/data-center-echarts';
import * as echarts from '../../components/ec-canvas/echarts';

type DataTabKey = 'global' | 'banks' | 'mistakes' | 'favorites' | 'tags';

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

function buildBankViewModel(res: any, currentDays: number) {
  const payload = buildDataCenterCompatPayload(res, 'banks');

  const allSummary = res?.all_summary || {};
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
      all_summary: allSummary,
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

const CHART_IDS: string[] = [
  'dcBankSplitChart',
  'dcBankCategoryChart',
  'dcBankBubbleChart',
  'dcBankRankChart',
  'dcSubjectProgressChart',
  'dcSubjectRiskChart'
];

Page({
  data: {
    ...(themeManager.getPageData()),
    loading: false,
    inited: false,
    lazyStage: 1,
    errorMsg: '',

    ecLazy: { lazyLoad: true },

    days: 30 as 7 | 30 | 90,
    window_days: 30,

    all_summary: {} as Record<string, unknown>,
    bank_summary: {} as Record<string, unknown>,

    total_questions: 0,
    answered_count: 0,
    accuracy: 0,

    window_answered: 0,
    window_accuracy: 0,

    subject_rows: [] as SubjectRow[],
    bank_rows: [] as BankRow[]
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    const url = `/packages/data/pages/data-center-v2/data-center-v2?tab=banks&days=${encodeURIComponent(String(days))}`;
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
          const built = buildBankViewModel(cached, this.data.days);
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
                    console.error('[data-bank-v2] renderCharts failed:', err);
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
      raw === 'global' || raw === 'mistakes' || raw === 'favorites' || raw === 'tags' ? (raw as DataTabKey) : 'banks';
    const days = this.data.days;
    const base = resolveDataTabUrl(tab);
    safeNavigate(`${base}?days=${encodeURIComponent(String(days))}`, 'redirectTo');
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
          console.error('[data-bank-v2] echarts.init failed:', id, err);
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
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res: any = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}

      const built = buildBankViewModel(res, this.data.days);
      self.__dcPayload = built.payload;

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
        }
      );
    } catch (e: any) {
      const msg = (e && e.message) || '加载失败，请稍后再试。';
      this.setData({ errorMsg: msg });
      try {
        const nowToast = Date.now();
        const lastToast = Number(self.__lastErrorToastAt || 0) || 0;
        if (nowToast - lastToast > 3500) {
          self.__lastErrorToastAt = nowToast;
          wx.showToast({ title: msg.length > 18 ? '数据加载失败' : msg, icon: 'none' });
        }
      } catch (e) {}
    } finally {
      this.setData({ loading: false });
    }
  }
});
