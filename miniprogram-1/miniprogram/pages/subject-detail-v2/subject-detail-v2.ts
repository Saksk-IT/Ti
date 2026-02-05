import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { createQuizSource } from '../../utils/quiz-source';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type Scope = 'all' | 'favorites' | 'mistakes';
type DetailTab = 'practice' | 'reinforce' | 'exam' | 'search' | 'stats' | 'share';
type DataSubTab = 'global' | 'mistakes' | 'favorites';
type SubjectMeta = { id: number; name: string; question_count: number };
type TagItem = { name: string; count?: number };
type SearchItem = {
  id: number;
  content?: string;
  content_preview?: string;
  q_type?: string;
  is_fav?: number | boolean;
  is_mistake?: number | boolean;
};
type DetailOption = { key: string; value: string };
type AdviceItem = { title?: string; content?: string };
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
type DifficultyBreakdownView = {
  label: string;
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  accuracyText: string;
  completionText: string;
  completionWidth: number;
};
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
type StatsQuestionItem = {
  id: number;
  content_preview?: string;
  q_type?: string;
  difficulty?: number;
  mistake_wrong_count?: number;
  mistake_created_at?: string;
  mistake_updated_at?: string;
  favorite_created_at?: string;
  last_is_correct?: number | boolean | null;
  last_answered_at?: string;
  [key: string]: any;
};
type FavoritesTrend = {
  total_added?: number;
  trend?: Array<{ day?: string; added?: number }>;
  [key: string]: any;
};

const OPTION_TYPES = new Set(['选择题', '多选题']);
const KEY_SHUFFLE_Q = 'shuffle_questions';
const KEY_SHUFFLE_O = 'shuffle_options';

type ReinforceSubTab = 'wrong' | 'similar';
type ReinforceWrongTopItem = {
  question_id: number;
  wrong_count: number;
  q_type?: string;
  content_preview?: string;
};
type ReinforceSimilarPairItem = {
  key?: string;
  a_id: number;
  b_id: number;
  a_type?: string;
  b_type?: string;
  a_preview?: string;
  b_preview?: string;
  stem_sim?: number;
  opt_sim?: number;
  sim_pct?: number;
  sim_pct_text?: string;
};
type ReinforceWrongState = {
  loading: boolean;
  loaded: boolean;
  error: string;
  desc: string;
  listMeta: string;
  wrongTotal: number;
  recommendIds: number[];
  top: ReinforceWrongTopItem[];
};
type ReinforceSimilarState = {
  loading: boolean;
  loaded: boolean;
  error: string;
  desc: string;
  listMeta: string;
  wrongTotal: number;
  similarMode: string;
  pairsCount: number;
  seedIds: number[];
  startIds: number[];
  pairs: ReinforceSimilarPairItem[];
};

type DetailTabView = { key: DetailTab; label: string };

const DEFAULT_DETAIL_TAB_ORDER: DetailTab[] = ['practice', 'reinforce', 'exam', 'search', 'stats', 'share'];
const VALID_DETAIL_TABS = new Set(DEFAULT_DETAIL_TAB_ORDER);
const DETAIL_TAB_LABELS: Record<DetailTab, string> = {
  practice: '练习',
  reinforce: '加强',
  exam: '考试',
  search: '搜索',
  stats: '数据',
  share: '分享'
};

function normalizeDetailTabOrder(input: any, fallback: DetailTab[]): DetailTab[] {
  const base = Array.isArray(fallback) ? fallback : DEFAULT_DETAIL_TAB_ORDER;
  const out: DetailTab[] = [];
  const seen = new Set<string>();

  const push = (k: any) => {
    const key = String(k || '').trim().toLowerCase();
    if (!VALID_DETAIL_TABS.has(key as DetailTab)) return;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(key as DetailTab);
  };

  (Array.isArray(input) ? input : []).forEach(push);
  base.forEach(push);
  return out;
}

function buildDetailTabViews(order: DetailTab[]): DetailTabView[] {
  const list = Array.isArray(order) ? order : DEFAULT_DETAIL_TAB_ORDER;
  return list.map((key) => ({ key, label: DETAIL_TAB_LABELS[key] || key }));
}

function getSubjectDetailTabOrderKey(subjectId: number, subjectName: string): string {
  const id = Number(subjectId || 0);
  if (Number.isFinite(id) && id > 0) return `subject_${Math.floor(id)}_detail_tab_order_v1`;
  const name = String(subjectName || '').trim();
  return name ? `subject_${name}_detail_tab_order_v1` : '';
}

function readSubjectDetailTabOrder(key: string, fallback: DetailTab[]): DetailTab[] {
  if (!key) return normalizeDetailTabOrder(null, fallback);
  try {
    const raw: any = wx.getStorageSync(key);
    if (Array.isArray(raw)) return normalizeDetailTabOrder(raw, fallback);
    if (typeof raw === 'string') {
      const s = raw.trim();
      if (!s) return normalizeDetailTabOrder(null, fallback);
      try {
        return normalizeDetailTabOrder(JSON.parse(s), fallback);
      } catch (e) {
        return normalizeDetailTabOrder(null, fallback);
      }
    }
    return normalizeDetailTabOrder(null, fallback);
  } catch (e) {
    return normalizeDetailTabOrder(null, fallback);
  }
}

function persistSubjectDetailTabOrder(key: string, order: DetailTab[]): void {
  if (!key) return;
  try {
    wx.setStorageSync(key, Array.isArray(order) ? order : []);
  } catch (e) {}
}

function scopeFromEntry(entry: string): Scope {
  if (entry === 'favorites') return 'favorites';
  if (entry === 'mistakes') return 'mistakes';
  return 'all';
}

function shouldCountForTab(tab: DetailTab): boolean {
  return tab === 'practice';
}

function normalizeTab(input: any): DetailTab {
  const s = String(input || '').trim().toLowerCase();
  if (s === 'data') return 'stats';
  if (s === 'exam') return 'exam';
  if (s === 'reinforce' || s === 'strengthen' || s === 'enhance') return 'reinforce';
  if (s === 'search') return 'search';
  if (s === 'stats') return 'stats';
  if (s === 'favorites' || s === 'mistakes') return 'practice';
  if (s === 'share') return 'share';
  return 'practice';
}

function normalizeReinforceSubTab(input: any): ReinforceSubTab {
  const s = String(input || '').trim().toLowerCase();
  return s === 'similar' ? 'similar' : 'wrong';
}

function getStoredString(key: string, fallback: string): string {
  try {
    const raw = wx.getStorageSync(key);
    const s = String(raw || '').trim();
    return s ? s : fallback;
  } catch (e) {
    return fallback;
  }
}

function setStoredString(key: string, value: string): void {
  try {
    wx.setStorageSync(key, String(value || ''));
  } catch (e) {}
}

function normalizeTextLines(input: any): string[] {
  const text = String(input ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = text.split('\n').map((s) => String(s ?? '').trimEnd());
  while (lines.length && !lines[lines.length - 1]) lines.pop();
  return lines;
}

function normalizeSubjectDetailOptions(rawOptions: any, qType: string): DetailOption[] {
  const qt = String(qType || '').trim();
  const list = Array.isArray(rawOptions) ? rawOptions : [];
  if (!list.length && qt === '判断题') {
    return [
      { key: '正确', value: '正确' },
      { key: '错误', value: '错误' }
    ];
  }
  const out: DetailOption[] = [];
  list.forEach((opt, idx) => {
    if (opt && typeof opt === 'object') {
      const key = String((opt as any).key ?? '').trim();
      const value = String((opt as any).value ?? '').trim();
      if (key || value) out.push({ key: key || String(idx + 1), value });
    } else {
      const value = String(opt ?? '').trim();
      if (value) out.push({ key: String(idx + 1), value });
    }
  });
  return out;
}

function getStoredBool(key: string, fallback = false): boolean {
  try {
    const raw: any = wx.getStorageSync(key);
    if (raw === true || raw === 1 || raw === '1') return true;
    if (raw === false || raw === 0 || raw === '0') return false;
    return fallback;
  } catch (e) {
    return fallback;
  }
}

function setStoredBool(key: string, value: boolean): void {
  try {
    wx.setStorageSync(key, value ? '1' : '0');
  } catch (e) {}
}

function clampPct(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(100, v));
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,

    tab: 'practice' as DetailTab,
    entry: '',
    tabOrderOpen: false,
    detailTabs: buildDetailTabViews(DEFAULT_DETAIL_TAB_ORDER),
    dataSubTab: 'global' as DataSubTab,

    subjectId: 0,
    subjectName: '',
    totalCount: 0,
    favCount: 0,
    mistakeCount: 0,
    examBuilderOpen: false,

    searchKeyword: '',
    searchType: 'all',
    searchResults: [] as SearchItem[],
    searchTotal: 0,
    searchPage: 1,
    searchPerPage: 20,
    searchLoading: false,
    searchSearched: false,
    searchError: '',

    qDetailOpen: false,
    qDetailLoading: false,
    qDetailError: '',
    qDetailId: 0,
    qDetailMeta: '',
    qDetailContentLines: [] as string[],
    qDetailAnswerLines: [] as string[],
    qDetailExplanationLines: [] as string[],
    qDetailOptions: [] as DetailOption[],

    scope: 'all' as Scope,
    types: [] as string[],
    qType: 'all',
    tags: [] as TagItem[],
    tag: 'all',
    practiceAdvancedOpen: false,

    shuffleQuestions: false,
    shuffleOptions: false,
    shuffleOptionsDisabled: false,

    startCount: 0,
    startCountText: '—',
    startDisabled: true,
    startError: '',

    // 统计详情（对齐 Web 题库详情-统计子页面）
    statsDays: 14,
    statsLoading: false,
    statsLoadedDays: 0,
    statsLoadedSubTab: 'global' as DataSubTab,
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
      lastText: '—'
    } as StatsOverviewView,
    statsTrend: [] as TrendView[],
    statsByType: [] as TypeBreakdownView[],
    statsByDifficulty: [] as DifficultyBreakdownView[],
    statsAdvice: [] as AdviceItem[],
    statsHasDifficulty: false,
    statsQuestions: [] as StatsQuestionItem[],
    favoritesTrend: {} as FavoritesTrend,

    // 加强模块（对齐 Web：错题/相似题）
    reinforceSubTab: 'wrong' as ReinforceSubTab,
    reinforceWrong: {
      loading: false,
      loaded: false,
      error: '',
      desc: '—',
      listMeta: '—',
      wrongTotal: 0,
      recommendIds: [],
      top: []
    } as ReinforceWrongState,
    reinforceSimilar: {
      loading: false,
      loaded: false,
      error: '',
      desc: '—',
      listMeta: '—',
      wrongTotal: 0,
      similarMode: '',
      pairsCount: 0,
      seedIds: [],
      startIds: [],
      pairs: []
    } as ReinforceSimilarState,

    ringAccuracy: 0,
    ringCompletion: 0,
    ringActive: 0,
    activeDaysRate: 0,
    ringRepeat: 0,
    repeatRateText: '0%',
    mistakeRateText: '0%',
    favMistakeRateText: '0%',
    heatCells: [] as Array<{ level: number }>,
    displayTypes: [] as TypeBreakdownView[]
  },

  startCountTimer: null as any,
  startCountReq: 0,
  statsReq: 0,
  qDetailReq: 0,
  tabExplicit: false as boolean,

  onLoad(options: any) {
    const sidRaw = options?.id ?? options?.subject_id ?? options?.subjectId;
    const subjectId = Number(sidRaw || 0);
    let subjectName = options?.subject ? String(options.subject) : '';
    if (subjectName) {
      try {
        subjectName = decodeURIComponent(subjectName);
      } catch (e) {}
    }
    const rawTab = options?.tab;
    const tab = normalizeTab(rawTab);
    const entry = String(options?.entry || '').trim().toLowerCase();
    const entryScope = scopeFromEntry(entry);
    (this as any).tabExplicit = rawTab !== undefined && rawTab !== null && String(rawTab).trim() !== '';
    this.setData({
      subjectId: Number.isFinite(subjectId) ? subjectId : 0,
      subjectName,
      tab,
      entry,
      scope: entryScope
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
    try {
      wx.showShareMenu({ withShareTicket: true });
    } catch (e) {}

    this.consumeReturnTab();

    if (!this.data.inited && !this.data.loading) {
      this.bootstrap();
      return;
    }
    this.syncShuffleOptionsDisabled();
    if (shouldCountForTab(this.data.tab)) {
      this.scheduleStartCount();
    }
    if (this.data.tab === 'stats') {
      this.ensureStatsDetail();
    }
    if (this.data.tab === 'reinforce') {
      this.ensureReinforce(false);
    }
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

  applyDetailTabOrder(nextOrder: DetailTab[]) {
    const normalized = normalizeDetailTabOrder(nextOrder, DEFAULT_DETAIL_TAB_ORDER);
    const key = getSubjectDetailTabOrderKey(Number(this.data.subjectId || 0), String(this.data.subjectName || ''));
    persistSubjectDetailTabOrder(key, normalized);
    this.setData({ detailTabs: buildDetailTabViews(normalized) });
  },

  onOpenTabOrder() {
    this.setData({ tabOrderOpen: true });
  },

  onCloseTabOrder() {
    this.setData({ tabOrderOpen: false });
  },

  onTabOrderSheetTap() {},

  onMoveTabOrder(e: any) {
    const act = String(e?.currentTarget?.dataset?.act || '').trim();
    const keyRaw = String(e?.currentTarget?.dataset?.key || '').trim().toLowerCase();
    if (!VALID_DETAIL_TABS.has(keyRaw as DetailTab)) return;

    const order: DetailTab[] = (this.data.detailTabs || [])
      .map((it: any) => String(it?.key || '').trim().toLowerCase())
      .filter((k: any) => VALID_DETAIL_TABS.has(k as DetailTab)) as any;
    const idx = order.indexOf(keyRaw as DetailTab);
    if (idx < 0) return;

    const delta = act === 'up' ? -1 : act === 'down' ? 1 : 0;
    if (!delta) return;
    const next = idx + delta;
    if (next < 0 || next >= order.length) return;

    const copy = order.slice();
    const [it] = copy.splice(idx, 1);
    copy.splice(next, 0, it);
    this.applyDetailTabOrder(copy);
  },

  onResetTabOrder() {
    this.applyDetailTabOrder(DEFAULT_DETAIL_TAB_ORDER.slice());
  },

  consumeReturnTab() {
    const subjectId = Number(this.data.subjectId || 0);
    const subject = String(this.data.subjectName || '').trim();
    const key = subjectId ? `subject_${subjectId}_return_tab` : subject ? `subject_${subject}_return_tab` : '';
    if (!key) return;
    const desired = getStoredString(key, '');
    if (!desired) return;
    setStoredString(key, '');
    const tab = normalizeTab(desired);
    if (tab === this.data.tab) return;
    this.setData({ tab });
  },

  openDataPage(subtab: DataSubTab) {
    const raw = String(subtab || 'global');
    const next: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_stats_subtab`, next);
    this.setData({ tab: 'stats', dataSubTab: next, statsLoadedDays: 0, statsLoadedSubTab: next }, () => {
      this.ensureStatsDetail(true);
    });
  },

  async bootstrap() {
    this.setData({ loading: true, startError: '' });
    try {
      const meta = await api.getSubjectsMeta();
      const subjects: SubjectMeta[] = Array.isArray((meta as any)?.subjects) ? (meta as any).subjects : [];

      const subjectId = Number(this.data.subjectId || 0);
      let subject = subjectId ? subjects.find((s) => Number(s?.id) === subjectId) : null;
      if (!subject && this.data.subjectName) {
        const name = String(this.data.subjectName || '').trim();
        subject = subjects.find((s) => String(s?.name || '').trim() === name) || null;
      }

      if (!subject) {
        wx.showToast({ title: '科目不存在或无权限', icon: 'none' });
        setTimeout(() => wx.navigateBack(), 1200);
        return;
      }

      const subjectName = String(subject.name || '').trim();
      const subjectIdFinal = Number(subject.id || 0);
      const totalCount = Number(subject.question_count || 0) || 0;

      const tabOrderKey = getSubjectDetailTabOrderKey(subjectIdFinal, subjectName);
      const tabOrder = readSubjectDetailTabOrder(tabOrderKey, DEFAULT_DETAIL_TAB_ORDER);
      const detailTabs = buildDetailTabViews(tabOrder);

      const keyType = `subject_${subjectIdFinal}_type`;
      const keyTag = `subject_${subjectIdFinal}_tag`;
      const keySearchType = `subject_${subjectIdFinal}_search_type`;
      const keyScope = `subject_${subjectIdFinal}_scope`;
      const keyStatsSubTab = `subject_${subjectIdFinal}_stats_subtab`;
      const keyReinforceSubTab = `subject_${subjectIdFinal}_reinforce_subtab`;

      const storedType = getStoredString(keyType, 'all');
      const storedTag = getStoredString(keyTag, 'all');
      const storedSearchType = getStoredString(keySearchType, 'all');
      const storedScope = getStoredString(keyScope, 'all');
      const storedStatsSubTab = getStoredString(keyStatsSubTab, 'global');
      const storedReinforceSubTab = getStoredString(keyReinforceSubTab, 'wrong');
      const shuffleQuestions = getStoredBool(KEY_SHUFFLE_Q, false);
      const shuffleOptions = getStoredBool(KEY_SHUFFLE_O, false);

      const entry = String(this.data.entry || '').trim().toLowerCase();
      let tab: DetailTab = this.data.tab;
      if (!(this as any).tabExplicit) {
        if (entry === 'exam') tab = 'exam';
      }
      const entryScope = scopeFromEntry(entry);
      const scope =
        entryScope !== 'all'
          ? entryScope
          : storedScope === 'favorites' || storedScope === 'mistakes'
            ? storedScope
            : 'all';

      const [info, counts, tagsRes] = await Promise.all([
        api.getSubjectInfo(subjectName),
        api.getUserCounts({ subject: subjectName, type: 'all', tag: 'all' }).catch(() => ({ favorites: 0, mistakes: 0 } as any)),
        api.getTags({ subject: subjectName }).catch(() => ({ tags: [] } as any))
      ]);

      const availableTypes = Array.isArray((info as any)?.available_types)
        ? (info as any).available_types
        : Array.isArray((info as any)?.data?.available_types)
          ? (info as any).data.available_types
          : [];
      const types = (availableTypes || [])
        .filter((t: any) => typeof t === 'string' && t.trim())
        .map((t: any) => String(t).trim());

      const tagsRaw = Array.isArray((tagsRes as any)?.tags)
        ? (tagsRes as any).tags
        : Array.isArray((tagsRes as any)?.data?.tags)
          ? (tagsRes as any).data.tags
          : [];
      const tags: TagItem[] = (tagsRaw || [])
        .map((t: any) => ({ name: String(t?.name || '').trim(), count: t?.count }))
        .filter((t: any) => t.name);

      const qType = storedType === 'all' || types.includes(storedType) ? storedType : 'all';
      const tag = storedTag === 'all' || tags.some((t) => t.name === storedTag) ? storedTag : 'all';
      const searchType = storedSearchType === 'all' || types.includes(storedSearchType) ? storedSearchType : 'all';
      const dataSubTab: DataSubTab = (storedStatsSubTab === 'mistakes' || storedStatsSubTab === 'favorites') ? storedStatsSubTab : 'global';
      const reinforceSubTab: ReinforceSubTab = normalizeReinforceSubTab(storedReinforceSubTab);

      this.setData({
        inited: true,
        subjectId: subjectIdFinal,
        subjectName,
        totalCount,
        detailTabs,
        favCount: Number((counts as any)?.favorites || 0) || 0,
        mistakeCount: Number((counts as any)?.mistakes || 0) || 0,
        tab,
        dataSubTab,
        reinforceSubTab,
        reinforceWrong: {
          loading: false,
          loaded: false,
          error: '',
          desc: '—',
          listMeta: '—',
          wrongTotal: 0,
          recommendIds: [],
          top: []
        },
        reinforceSimilar: {
          loading: false,
          loaded: false,
          error: '',
          desc: '—',
          listMeta: '—',
          wrongTotal: 0,
          similarMode: '',
          pairsCount: 0,
          seedIds: [],
          startIds: [],
          pairs: []
        },
        scope,
        types,
        qType,
        tags,
        tag,
        searchType,
        shuffleQuestions,
        shuffleOptions
      });

      setStoredString(keyType, qType);
      setStoredString(keyTag, tag);
      setStoredString(keySearchType, searchType);
      setStoredString(keyScope, scope);
      setStoredString(keyStatsSubTab, dataSubTab);
      setStoredString(keyReinforceSubTab, reinforceSubTab);

      this.syncShuffleOptionsDisabled();
      if (shouldCountForTab(tab)) {
        this.scheduleStartCount();
      }
      if (tab === 'stats') {
        this.setData({ statsLoadedDays: 0, statsLoadedSubTab: dataSubTab }, () => this.ensureStatsDetail());
      }
      if (tab === 'reinforce') {
        this.ensureReinforce(true);
      }
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '初始化失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onSearchInput(e: any) {
    this.setData({ searchKeyword: String(e?.detail?.value || '') });
  },

  onSubjectSearch() {
    this.doSubjectSearch(true);
  },

  onSearchTypeTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.type || 'all').trim() || 'all';
    const types = Array.isArray(this.data.types) ? this.data.types : [];
    const v = next === 'all' || types.includes(next) ? next : 'all';
    if (v === this.data.searchType) return;
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_search_type`, v);
    this.setData({ searchType: v }, () => {
      if (this.data.searchSearched && String(this.data.searchKeyword || '').trim()) {
        this.doSubjectSearch(true);
      }
    });
  },

  async doSubjectSearch(reset: boolean) {
    const kw = String(this.data.searchKeyword || '').trim();
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;

    if (!kw) {
      this.setData({
        searchSearched: true,
        searchResults: [],
        searchTotal: 0,
        searchPage: 1,
        searchError: ''
      });
      wx.showToast({ title: '请输入关键词', icon: 'none' });
      return;
    }

    if (this.data.searchLoading) return;

    const page = reset ? 1 : Number(this.data.searchPage || 1) || 1;
    const perPage = Number(this.data.searchPerPage || 20) || 20;

    this.setData({
      searchLoading: true,
      searchSearched: true,
      searchError: '',
      ...(reset ? { searchResults: [], searchTotal: 0, searchPage: 1 } : {})
    } as any);

    try {
      const res: any = await api.searchQuestions({
        keyword: kw,
        subject,
        type: this.data.searchType && this.data.searchType !== 'all' ? this.data.searchType : undefined,
        page,
        per_page: perPage
      } as any);

      const list: SearchItem[] = Array.isArray(res?.questions) ? res.questions : [];
      const total = Number(res?.total || 0) || 0;
      const next = reset ? list : (this.data.searchResults || []).concat(list);

      this.setData({
        searchResults: next,
        searchTotal: total,
        searchPage: page + 1,
        searchLoading: false
      });
    } catch (err: any) {
      this.setData({ searchLoading: false, searchError: (err && err.message) ? String(err.message) : '搜索失败' });
    }
  },

  onSearchLoadMore() {
    if (this.data.searchLoading) return;
    if ((this.data.searchResults || []).length >= (this.data.searchTotal || 0)) return;
    this.doSubjectSearch(false);
  },

  onSearchClear() {
    this.setData({
      searchKeyword: '',
      searchSearched: false,
      searchResults: [],
      searchTotal: 0,
      searchPage: 1,
      searchError: ''
    });
  },

  onSearchResultTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    this.openQuestionDetail(id);
  },

  async openQuestionDetail(questionId: number) {
    const qid = Number(questionId || 0);
    if (!Number.isFinite(qid) || qid <= 0) return;

    const reqId = ++(this as any).qDetailReq;
    this.setData({
      qDetailOpen: true,
      qDetailLoading: true,
      qDetailError: '',
      qDetailId: qid,
      qDetailMeta: `ID：${qid}`,
      qDetailContentLines: [],
      qDetailAnswerLines: [],
      qDetailExplanationLines: [],
      qDetailOptions: []
    } as any);

    try {
      const q: any = await api.getQuestionDetail(qid);
      if (reqId !== (this as any).qDetailReq) return;

      const qType = String(q?.q_type || '').trim();
      const options = normalizeSubjectDetailOptions(q?.options, qType);

      const metaParts = [`ID：${qid}`];
      if (qType) metaParts.push(qType);
      if (q?.is_fav) metaParts.push('收藏');
      if (q?.is_mistake) metaParts.push('错题');

      this.setData({
        qDetailLoading: false,
        qDetailError: '',
        qDetailMeta: metaParts.join(' · '),
        qDetailContentLines: normalizeTextLines(q?.content),
        qDetailAnswerLines: normalizeTextLines(q?.answer),
        qDetailExplanationLines: normalizeTextLines(q?.explanation),
        qDetailOptions: options
      } as any);
    } catch (err: any) {
      if (reqId !== (this as any).qDetailReq) return;
      this.setData({
        qDetailLoading: false,
        qDetailError: (err && err.message) ? String(err.message) : '加载失败'
      } as any);
    }
  },

  onQDetailClose() {
    this.setData({ qDetailOpen: false } as any);
  },

  onQDetailSheetTap() {
    // 阻止冒泡：点击面板内部不关闭
  },

  onQDetailGoQuiz() {
    const id = Number(this.data.qDetailId || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    this.onQDetailClose();
    wx.navigateTo({ url: `/pages/quiz/quiz?subject=${encodeURIComponent(subject)}&mode=quiz&source=all&start_id=${id}` });
  },

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab || 'practice');
    if (tab === this.data.tab) return;
    this.setData({ tab, startError: '' }, () => {
      this.syncShuffleOptionsDisabled();
      if (shouldCountForTab(tab)) {
        this.scheduleStartCount();
      }
      if (tab === 'reinforce') {
        this.ensureReinforce(false);
      }
      if (tab === 'stats') {
        this.ensureStatsDetail();
      }
    });
  },

  onReinforceSubTabTap(e: any) {
    const next = normalizeReinforceSubTab(e?.currentTarget?.dataset?.subtab || 'wrong');
    if (next === this.data.reinforceSubTab) return;
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_reinforce_subtab`, next);
    this.setData({ reinforceSubTab: next }, () => {
      this.ensureReinforce(false);
    });
  },

  ensureReinforce(force: boolean) {
    const kind = this.data.reinforceSubTab as ReinforceSubTab;
    if (kind === 'similar') {
      if (force || !this.data.reinforceSimilar.loaded) this.loadReinforceSimilar();
      return;
    }
    if (force || !this.data.reinforceWrong.loaded) this.loadReinforceWrong();
  },

  onReinforceRetry() {
    this.ensureReinforce(true);
  },

  parseIdList(raw: any, maxLen: number = 200): number[] {
    const s = String(raw || '').replace(/，/g, ',').trim();
    if (!s) return [];
    const parts = s.split(',').map((x) => String(x || '').trim()).filter(Boolean);
    const out: number[] = [];
    const seen = new Set<number>();
    for (const p of parts) {
      if (out.length >= maxLen) break;
      const n = Number(p);
      if (!Number.isFinite(n) || n <= 0) continue;
      const id = Math.floor(n);
      if (seen.has(id)) continue;
      seen.add(id);
      out.push(id);
    }
    return out;
  },

  buildReinforceQuizUrl(ids: number[], rk: 'wrong' | 'similar'): string {
    const subject = String(this.data.subjectName || '').trim();
    const list = Array.isArray(ids)
      ? ids.map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0).map((n) => Math.floor(n))
      : [];
    if (!subject || !list.length) return '';

    const qs =
      `subject=${encodeURIComponent(subject)}` +
      `&mode=reinforce` +
      `&rk=${encodeURIComponent(rk)}` +
      `&ids=${list.join(',')}`;
    return `/pages/quiz/quiz?${qs}`;
  },

  onStartReinforceWrong() {
    const ids = (this.data.reinforceWrong && Array.isArray(this.data.reinforceWrong.recommendIds))
      ? this.data.reinforceWrong.recommendIds
      : [];
    const url = this.buildReinforceQuizUrl(ids, 'wrong');
    if (!url) return;
    wx.navigateTo({ url });
  },

  onStartReinforceWrongAll() {
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    wx.navigateTo({ url: `/pages/quiz/quiz?subject=${encodeURIComponent(subject)}&mode=quiz&source=mistakes` });
  },

  onStartReinforceWrongOne(e: any) {
    const qid = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(qid) || qid <= 0) return;
    const url = this.buildReinforceQuizUrl([qid], 'wrong');
    if (!url) return;
    wx.navigateTo({ url });
  },

  onStartReinforceSimilar() {
    const ids = (this.data.reinforceSimilar && Array.isArray(this.data.reinforceSimilar.startIds))
      ? this.data.reinforceSimilar.startIds
      : [];
    const url = this.buildReinforceQuizUrl(ids, 'similar');
    if (!url) return;
    wx.navigateTo({ url });
  },

  onStartReinforceSimilarPair(e: any) {
    const a = Number(e?.currentTarget?.dataset?.a || 0);
    const b = Number(e?.currentTarget?.dataset?.b || 0);
    if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0) return;
    const url = this.buildReinforceQuizUrl([a, b], 'similar');
    if (!url) return;
    wx.navigateTo({ url });
  },

  async loadReinforceWrong() {
    const subjectId = Number(this.data.subjectId || 0);
    if (!Number.isFinite(subjectId) || subjectId <= 0) return;
    if (this.data.reinforceWrong.loading) return;

    this.setData({
      reinforceWrong: Object.assign({}, this.data.reinforceWrong, { loading: true, error: '' })
    } as any);

    try {
      const data: any = await api.getQuizReinforce({
        source: 'public',
        subject_id: subjectId,
        include: 'wrong',
        wrong_list_n: 30
      } as any);

      const wrongTotal = Number(data?.wrong_total || 0) || 0;
      const recommendIds = Array.isArray(data?.wrong_recommend_ids)
        ? this.parseIdList((data.wrong_recommend_ids || []).join(','), 200)
        : this.parseIdList(data?.wrong_recommend_ids, 200);
      const topRaw = Array.isArray(data?.wrong_top) ? data.wrong_top : [];
      const top: ReinforceWrongTopItem[] = topRaw
        .map((it: any) => ({
          question_id: Number(it?.question_id || 0) || 0,
          wrong_count: Number(it?.wrong_count || 1) || 1,
          q_type: String(it?.q_type || '').trim(),
          content_preview: String(it?.content_preview || '').trim()
        }))
        .filter((it: ReinforceWrongTopItem) => it.question_id > 0);

      const recommendN = recommendIds.length ? recommendIds.length : Math.min(wrongTotal, 20);
      const desc = wrongTotal > 0
        ? `你在本题库累计错题 ${wrongTotal} 道，推荐优先巩固其中 ${recommendN} 道高频错题。`
        : '当前没有错题记录，继续保持！';
      const listMeta = wrongTotal > 0
        ? `展示 ${top.length} 题 · 共错题 ${wrongTotal} 题`
        : '暂无错题记录';

      this.setData({
        reinforceWrong: {
          loading: false,
          loaded: true,
          error: '',
          desc,
          listMeta,
          wrongTotal,
          recommendIds,
          top
        }
      } as any);
    } catch (e: any) {
      this.setData({
        reinforceWrong: Object.assign({}, this.data.reinforceWrong, {
          loading: false,
          loaded: true,
          error: (e && e.message) ? String(e.message) : '加载失败',
          desc: '加载失败，点此重试',
          listMeta: '加载失败'
        })
      } as any);
    }
  },

  async loadReinforceSimilar() {
    const subjectId = Number(this.data.subjectId || 0);
    if (!Number.isFinite(subjectId) || subjectId <= 0) return;
    if (this.data.reinforceSimilar.loading) return;

    this.setData({
      reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, { loading: true, error: '' })
    } as any);

    try {
      const data: any = await api.getQuizReinforce({
        source: 'public',
        subject_id: subjectId,
        include: 'similar',
        pairs_n: 30
      } as any);

      const wrongTotal = Number(data?.wrong_total || 0) || 0;
      const seedIds = Array.isArray(data?.similar_seed_ids)
        ? (data.similar_seed_ids || []).map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0).map((n: number) => Math.floor(n))
        : [];
      const seedSet = new Set(seedIds);
      const similarIds = Array.isArray(data?.similar_training_ids)
        ? (data.similar_training_ids || []).map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0).map((n: number) => Math.floor(n))
        : [];
      const similarOnlyIds = similarIds.filter((id: number) => !seedSet.has(id));

      const similarMode = String(data?.similar_mode || '').trim().toLowerCase();
      const pairsCount = Number(data?.similar_pairs_count || 0) || 0;
      const pairsRaw = Array.isArray(data?.similar_pairs) ? data.similar_pairs : [];
      const pairs: ReinforceSimilarPairItem[] = pairsRaw
        .map((p: any) => {
          const stem = Number(p?.stem_sim || 0) || 0;
          const opt = Number(p?.opt_sim || 0) || 0;
          const pct = Math.max(stem, opt) > 0 ? Math.round(Math.max(stem, opt) * 100) : 0;
          const aId = Number(p?.a_id || 0) || 0;
          const bId = Number(p?.b_id || 0) || 0;
          return {
            key: (aId > 0 && bId > 0) ? `${aId}_${bId}` : '',
            a_id: aId,
            b_id: bId,
            a_type: String(p?.a_type || '').trim(),
            b_type: String(p?.b_type || '').trim(),
            a_preview: String(p?.a_preview || '').trim(),
            b_preview: String(p?.b_preview || '').trim(),
            stem_sim: stem,
            opt_sim: opt,
            sim_pct: pct,
            sim_pct_text: pct > 0 ? `相似 ${pct}%` : '相似'
          };
        })
        .filter((p: ReinforceSimilarPairItem) => p.a_id > 0 && p.b_id > 0);

      let startIds: number[] = [];
      let desc = '先完成一些练习后，这里会给出相似题加强。';

      if (similarMode === 'subject_dedupe' || similarMode === 'bank_dedupe') {
        if (similarOnlyIds.length) {
          startIds = similarOnlyIds.slice();
          const pairsText = pairsCount > 0 ? `${pairsCount} 组` : '';
          desc = `已在本题库检测到${pairsText ? (' ' + pairsText) : ''}相似题（题干相似优先，选项相似兜底），训练共 ${similarOnlyIds.length} 道。`;
        } else {
          desc = wrongTotal > 0 ? '暂无明显相似题（题干/选项相似），可先做错题加强。' : '暂无明显相似题（题干/选项相似）。';
        }
      } else {
        if (similarOnlyIds.length) {
          startIds = similarOnlyIds.slice();
          desc = `基于你最近的错题，为你匹配了 ${similarOnlyIds.length} 道相似题，可用于易混强化。`;
        } else if (wrongTotal > 0 && seedIds.length) {
          startIds = seedIds.slice();
          desc = `暂无足够稳定的相似题，先用最近错题 ${seedIds.length} 道作为“相似题种子训练”。`;
        } else {
          desc = wrongTotal > 0 ? '暂无足够稳定的相似题，建议先做错题加强。' : '先完成一些练习后，这里会给出相似题加强。';
        }
      }

      const listMeta = pairs.length
        ? `展示 ${pairs.length} / ${pairsCount || pairs.length} 组`
        : (pairsCount > 0 ? `已检测到 ${pairsCount} 组（暂无可展示详情）` : '暂无相似题目');

      this.setData({
        reinforceSimilar: {
          loading: false,
          loaded: true,
          error: '',
          desc,
          listMeta,
          wrongTotal,
          similarMode,
          pairsCount,
          seedIds,
          startIds,
          pairs
        }
      } as any);
    } catch (e: any) {
      this.setData({
        reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, {
          loading: false,
          loaded: true,
          error: (e && e.message) ? String(e.message) : '加载失败',
          desc: '加载失败，点此重试',
          listMeta: '加载失败'
        })
      } as any);
    }
  },

  onScopeTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.scope || 'all').trim() || 'all';
    if (next === this.data.scope) return;
    const scope = next === 'favorites' || next === 'mistakes' ? next : 'all';
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_scope`, scope);
    this.setData({ scope }, () => {
      if (shouldCountForTab(this.data.tab)) {
        this.scheduleStartCount();
      }
    });
  },

  onTogglePracticeAdvanced() {
    this.setData({ practiceAdvancedOpen: !this.data.practiceAdvancedOpen });
  },

  onClearProgressTap() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    if (this.data.loading) {
      wx.showToast({ title: '加载中，请稍候', icon: 'none' });
      return;
    }

    wx.showActionSheet({
      itemList: ['清除刷题进度', '清除背题进度'],
      success: (res) => {
        const mode: 'quiz' | 'memo' = res.tapIndex === 1 ? 'memo' : 'quiz';
        this.confirmAndClearProgress(mode);
      }
    });
  },

  buildProgressKey(mode: 'quiz' | 'memo'): string {
    const subjectName = String(this.data.subjectName || '').trim();
    if (!subjectName) return '';

    const qs = createQuizSource({ subject: subjectName });
    return qs.buildProgressKey(mode, {
      type: this.data.qType,
      source: this.data.scope,
      tag: this.data.tag,
      shuffleQuestions: this.data.shuffleQuestions,
      shuffleOptions: this.data.shuffleOptions
    });
  },

  confirmAndClearProgress(mode: 'quiz' | 'memo') {
    const key = this.buildProgressKey(mode);
    if (!key) return;

    const scopeLabel = this.data.scope === 'favorites' ? '收藏' : this.data.scope === 'mistakes' ? '错题' : '全部';
    const typeLabel = this.data.qType === 'all' ? '全部题型' : String(this.data.qType || '').trim() || '全部题型';
    const tagLabel = this.data.tag && this.data.tag !== 'all' ? String(this.data.tag || '').trim() : '全部标签';
    const modeLabel = mode === 'memo' ? '背题' : '刷题';
    const shuffleQ = this.data.shuffleQuestions ? '开' : '关';
    const shuffleO = this.data.shuffleOptions ? '开' : '关';
    const subjectName = String(this.data.subjectName || '').trim() || '科目';

    wx.showModal({
      title: '确认清除',
      content: `将清除以下组合的进度：\n科目：${subjectName}\n范围：${scopeLabel}\n题型：${typeLabel}\n标签：${tagLabel}\n模式：${modeLabel}\n打乱题目：${shuffleQ}  打乱选项：${shuffleO}`,
      confirmText: '清除',
      confirmColor: '#FF3B30',
      success: async (r) => {
        if (!r.confirm) return;
        wx.showLoading({ title: '清除中...' });
        try {
          await api.deleteProgress(key);
        } catch (e: any) {
          console.error('清除云端进度失败:', e);
        }
        try {
          wx.removeStorageSync(key);
        } catch (e) {}
        wx.hideLoading();
        wx.showToast({ title: '已清除', icon: 'success' });
      }
    });
  },

  onDataTabTap(e: any) {
    const raw = String(e?.detail?.subtab || e?.currentTarget?.dataset?.subtab || 'global');
    const subtab: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
    if (subtab === this.data.dataSubTab) return;
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_stats_subtab`, subtab);
    this.setData({ dataSubTab: subtab, statsLoadedDays: 0, statsLoadedSubTab: subtab }, () => {
      if (this.data.tab === 'stats') {
        this.ensureStatsDetail(true);
      }
    });
  },

  onTypeTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.type || 'all').trim() || 'all';
    if (next === this.data.qType) return;
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_type`, next);
    this.setData({ qType: next }, () => {
      this.syncShuffleOptionsDisabled();
      if (shouldCountForTab(this.data.tab)) {
        this.scheduleStartCount();
      }
    });
  },

  onTagTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.tag || 'all').trim() || 'all';
    if (next === this.data.tag) return;
    const subjectId = Number(this.data.subjectId || 0);
    if (subjectId) setStoredString(`subject_${subjectId}_tag`, next);
    this.setData({ tag: next }, () => {
      if (shouldCountForTab(this.data.tab)) {
        this.scheduleStartCount();
      }
    });
  },

  onTagDeleteTap(e: any) {
    const name = String(e?.currentTarget?.dataset?.tag || '').trim();
    if (!name || name.toLowerCase() === 'all') return;

    const subjectId = Number(this.data.subjectId || 0);
    const subjectName = String(this.data.subjectName || '').trim();
    if (!subjectId || !subjectName) return;

    wx.showModal({
      title: '删除标签',
      content: `删除标签「${name}」？\n\n仅删除：当前用户 · 当前题库（科目）下的标签，并移除该标签在本题库下所有题目上的绑定。`,
      confirmText: '删除',
      confirmColor: '#FF3B30',
      success: async (r) => {
        if (!r.confirm) return;
        wx.showLoading({ title: '删除中...' });
        try {
          const res: any = await api.deleteTag(name, { subject_id: subjectId, subject: subjectName });
          const tagsRaw = Array.isArray(res?.tags)
            ? res.tags
            : Array.isArray(res?.data?.tags)
              ? res.data.tags
              : [];
          const tags: TagItem[] = (tagsRaw || [])
            .map((t: any) => ({ name: String(t?.name || '').trim(), count: t?.count }))
            .filter((t: any) => t.name);

          const prevTag = String(this.data.tag || 'all').trim() || 'all';
          const nextTag = prevTag === name ? 'all' : prevTag;
          if (nextTag !== prevTag) setStoredString(`subject_${subjectId}_tag`, nextTag);

          this.setData({ tags, tag: nextTag } as any, () => {
            if (shouldCountForTab(this.data.tab)) {
              this.scheduleStartCount();
            }
          });
          wx.showToast({ title: '已删除', icon: 'success' });
        } catch (err: any) {
          wx.showToast({ title: (err && err.message) ? String(err.message) : '删除失败', icon: 'none' });
        } finally {
          try { wx.hideLoading(); } catch (e) {}
        }
      }
    });
  },

  onToggleShuffleQuestions() {
    const next = !this.data.shuffleQuestions;
    setStoredBool(KEY_SHUFFLE_Q, next);
    this.setData({ shuffleQuestions: next });
  },

  onToggleShuffleOptions() {
    if (this.data.shuffleOptionsDisabled) return;
    const next = !this.data.shuffleOptions;
    setStoredBool(KEY_SHUFFLE_O, next);
    this.setData({ shuffleOptions: next });
  },

  syncShuffleOptionsDisabled() {
    const t = String(this.data.qType || 'all');
    const allowed = t === 'all' || OPTION_TYPES.has(t);
    const disabled = !allowed;
    if (disabled && this.data.shuffleOptions) {
      setStoredBool(KEY_SHUFFLE_O, false);
      this.setData({ shuffleOptions: false });
    }
    this.setData({ shuffleOptionsDisabled: disabled });
  },

  scheduleStartCount() {
    if (!shouldCountForTab(this.data.tab)) return;
    if (this.startCountTimer) {
      clearTimeout(this.startCountTimer);
      this.startCountTimer = null;
    }
    const reqId = ++this.startCountReq;
    this.setData({ startCountText: '…', startDisabled: true, startError: '' });
    this.startCountTimer = setTimeout(() => this.refreshStartCount(reqId), 220);
  },

  async refreshStartCount(reqId: number) {
    if (reqId !== this.startCountReq) return;
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;

    try {
      const params: any = { subject, type: 'all', source: this.data.scope || 'all' };
      if (this.data.qType && this.data.qType !== 'all') params.type = this.data.qType;
      if (this.data.tag && this.data.tag !== 'all') params.tag = this.data.tag;

      const res: any = await api.getQuestionsCount(params);
      if (reqId !== this.startCountReq) return;
      const count = Number(res?.count || 0) || 0;
      this.setData({
        startCount: count,
        startCountText: String(count),
        startDisabled: count <= 0,
        startError: ''
      });
    } catch (e: any) {
      if (reqId !== this.startCountReq) return;
      this.setData({
        startCount: 0,
        startCountText: '0',
        startDisabled: true,
        startError: (e && e.message) ? String(e.message) : '获取题量失败'
      });
    }
  },

  buildQuizUrl(mode: 'quiz' | 'memo'): string {
    const subject = String(this.data.subjectName || '').trim();
    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(subject)}`);
    params.push(`mode=${mode}`);
    params.push(`source=${encodeURIComponent(String(this.data.scope || 'all'))}`);
    if (this.data.qType && this.data.qType !== 'all') params.push(`type=${encodeURIComponent(String(this.data.qType))}`);
    if (this.data.tag && this.data.tag !== 'all') params.push(`tag=${encodeURIComponent(String(this.data.tag))}`);
    if (this.data.shuffleQuestions) params.push('shuffle_questions=1');
    if (this.data.shuffleOptions && !this.data.shuffleOptionsDisabled) params.push('shuffle_options=1');
    return `/pages/quiz/quiz?${params.join('&')}`;
  },

  onStartQuiz() {
    if (this.data.startDisabled) return;
    wx.navigateTo({ url: this.buildQuizUrl('quiz') });
  },

  onStartMemo() {
    if (this.data.startDisabled) return;
    wx.navigateTo({ url: this.buildQuizUrl('memo') });
  },

  async onQuickExam() {
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    if (this.data.scope && this.data.scope !== 'all') {
      wx.showToast({ title: '考试当前仅支持全题库范围', icon: 'none' });
      return;
    }

    const typesList = Array.isArray(this.data.types) ? this.data.types.filter((t) => !!t) : [];
    if (!typesList.length) {
      wx.showToast({ title: '暂无可用题型', icon: 'none' });
      return;
    }

    const duration = 60;
    const total = 30;
    const typesCfg: Record<string, number> = {};

    if (this.data.qType && this.data.qType !== 'all') {
      typesCfg[String(this.data.qType)] = total;
    } else {
      const n = Math.max(1, typesList.length);
      const base = Math.floor(total / n);
      let rem = total % n;
      typesList.forEach((t) => {
        const v = base + (rem > 0 ? 1 : 0);
        if (rem > 0) rem -= 1;
        if (v > 0) typesCfg[String(t)] = v;
      });
    }

    const detail = Object.keys(typesCfg).map((k) => `${k}:${typesCfg[k]}`).join('，');
    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '创建并开始考试',
        content: `科目：${subject}\n时长：${duration}分钟\n题量：${total}（${detail}）`,
        confirmText: '开始',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    wx.showLoading({ title: '创建中…', mask: true });
    try {
      const res: any = await api.createExam({ source: 'public', subject, duration, types: typesCfg, scores: {} });
      const examId = Number(res?.exam_id || res?.id || 0);
      if (!Number.isFinite(examId) || examId <= 0) {
        wx.showToast({ title: '创建考试失败', icon: 'none' });
        return;
      }
      wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
    } catch (err: any) {
      wx.showToast({ title: (err && err.message) ? String(err.message) : '创建失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onToggleExamBuilder() {
    this.setData({ examBuilderOpen: !this.data.examBuilderOpen });
  },

  onOpenExamSetup() {
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    wx.navigateTo({ url: `/pages/exam-setup/exam-setup?subject=${encodeURIComponent(subject)}` });
  },

  // ===== 统计详情 =====
  statsSourceForSubTab(subtab: any): Scope {
    const s = String(subtab || '').trim().toLowerCase();
    if (s === 'mistakes') return 'mistakes';
    if (s === 'favorites') return 'favorites';
    return 'all';
  },

  onStatsDaysTap(e: any) {
    const days = Number(e?.detail?.days || e?.currentTarget?.dataset?.days || 14);
    if (![7, 14, 30, 90].includes(days)) return;
    if (days === this.data.statsDays) return;
    this.setData({ statsDays: days, statsLoadedDays: 0 }, () => {
      if (this.data.tab === 'stats') {
        this.ensureStatsDetail(true);
      }
    });
  },

  onStatsQuickStart(e: any) {
    const raw = String(e?.detail?.subtab || e?.currentTarget?.dataset?.subtab || '');
    const subtab = raw === 'mistakes' || raw === 'favorites' ? raw : '';
    if (!subtab) return;
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    wx.navigateTo({ url: `/pages/quiz/quiz?subject=${encodeURIComponent(subject)}&mode=quiz&source=${encodeURIComponent(subtab)}` });
  },

  ensureStatsDetail(force = false) {
    if (this.data.statsLoading) return;
    const days = Number(this.data.statsDays || 14) || 14;
    const subtab = this.data.dataSubTab || 'global';
    if (!force && this.data.statsLoadedDays === days && this.data.statsLoadedSubTab === subtab) return;
    this.loadStatsDetail(days, subtab);
  },

  formatDateTime(raw: any): string {
    const s = String(raw || '').trim();
    if (!s) return '—';
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
    const lastText = this.formatDateTime(data?.last_activity);

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
      const completionWidth = Math.max(0, Math.min(100, comp));
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
        metaText: `已做 ${a}/${t} · 正确率 ${acc.toFixed(1)}% · 覆盖率 ${comp.toFixed(1)}% · 收藏 ${fav} · 错题 ${mis}`
      };
    });

    const rawByDiff = Array.isArray(data?.by_difficulty) ? data.by_difficulty : [];
    const byDifficulty: DifficultyBreakdownView[] = rawByDiff.map((it: any) => {
      const label = String(it?.label || it?.difficulty || '');
      const t = Number(it?.total || 0) || 0;
      const a = Number(it?.answered || 0) || 0;
      const c = Number(it?.correct || 0) || 0;
      const w = Number(it?.wrong || 0) || Math.max(0, a - c);
      const acc = Number(it?.accuracy || 0) || 0;
      const comp = Number(it?.completion || 0) || 0;
      const completionWidth = Math.max(0, Math.min(100, comp));
      return {
        label,
        total: t,
        answered: a,
        correct: c,
        wrong: w,
        accuracyText: `${acc.toFixed(1)}%`,
        completionText: `${comp.toFixed(1)}%`,
        completionWidth
      };
    });

    const advice: AdviceItem[] = Array.isArray(data?.advice) ? data.advice : [];
    return { overview, trend, byType, byDifficulty, advice };
  },

  buildHeatCells(trend: TrendView[]) {
    const slice = trend.slice(-28);
    const maxAnswered = slice.reduce((m: number, it: any) => Math.max(m, Number(it?.answered || 0) || 0), 0) || 0;
    const cells = slice.map((it) => {
      if (!maxAnswered) return { level: 0 };
      const pct = (it.answered || 0) / maxAnswered;
      const level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
      return { level };
    });
    const pad = 28 - cells.length;
    if (pad > 0) {
      return Array.from({ length: pad }, () => ({ level: 0 })).concat(cells);
    }
    return cells;
  },

  async loadStatsDetail(days: number, subtab: DataSubTab) {
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    const reqId = ++(this as any).statsReq;
    this.setData({ statsLoading: true, statsError: '', statsQuestions: [], favoritesTrend: {} });

    try {
      const source = this.statsSourceForSubTab(subtab || 'global');

      const statsPromise: Promise<any> =
        source === 'all'
          ? api.getSubjectStatsDetail(subject, days)
          : api.getSubjectStatsDetail(subject, { days, source });

      let questionsPromise: Promise<any> = Promise.resolve(null);
      let favTrendPromise: Promise<any> = Promise.resolve(null);
      if (subtab === 'mistakes') {
        questionsPromise = api.getSubjectQuestions(subject, { source: 'mistakes', page: 1, per_page: 300 });
      } else if (subtab === 'favorites') {
        questionsPromise = api.getSubjectQuestions(subject, { source: 'favorites', page: 1, per_page: 200 });
        favTrendPromise = api.getSubjectFavoritesTrend(subject, days);
      }

      const settle = (p: Promise<any>) =>
        p.then(
          (value) => ({ ok: true as const, value }),
          (reason) => ({ ok: false as const, reason })
        );
      const [statsRes, qRes, favRes] = await Promise.all([
        settle(statsPromise),
        settle(questionsPromise),
        settle(favTrendPromise)
      ]);
      if (reqId !== (this as any).statsReq) return;
      if (!statsRes.ok) throw (statsRes as any).reason;

      const data: any = statsRes.value;
      const qPayload: any = qRes.ok ? qRes.value : null;
      const statsQuestions: StatsQuestionItem[] = Array.isArray(qPayload?.questions) ? qPayload.questions : [];
      const favoritesTrend: FavoritesTrend = favRes.ok ? (favRes.value || {}) : {};

      const view = this.buildStatsView(data || {});
      const ringAccuracy = clampPct(view.overview.accuracy);
      const ringCompletion = clampPct(view.overview.completion);
      const heatCells = this.buildHeatCells(view.trend);

      let displayTypes: TypeBreakdownView[] = view.byType || [];
      let ringActive = 0;
      let activeDaysRate = 0;
      let ringRepeat = 0;
      let repeatRateText = '0%';
      let mistakeRateText = '0%';
      let favMistakeRateText = '0%';

      if (subtab === 'mistakes') {
        const repeatRate =
          view.overview.total > 0 ? clampPct((view.overview.mistakeTimes / view.overview.total) * 100) : 0;
        const mistakeRate =
          view.overview.answered > 0 ? clampPct((view.overview.wrong / view.overview.answered) * 100) : 0;
        ringRepeat = repeatRate;
        repeatRateText = `${repeatRate.toFixed(0)}%`;
        mistakeRateText = `${mistakeRate.toFixed(0)}%`;
        displayTypes = (view.byType || [])
          .map((t) =>
            Object.assign({}, t, {
              metaText: `错题 ${t.mistakes} · 已做 ${t.answered}/${t.total} · 正确率 ${t.accuracyText} · 覆盖率 ${t.completionText}`
            })
          )
          .sort((a, b) => b.wrong - a.wrong);
      } else if (subtab === 'favorites') {
        const activeDays = view.trend.filter((it) => it.answered > 0).length;
        activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
        ringActive = clampPct(activeDaysRate);
        const favMistakeRate =
          view.overview.total > 0 ? clampPct((view.overview.mistakes / view.overview.total) * 100) : 0;
        favMistakeRateText = `${favMistakeRate.toFixed(0)}%`;
        displayTypes = (view.byType || [])
          .map((t) =>
            Object.assign({}, t, {
              metaText: `收藏 ${t.favorites} · 已做 ${t.answered}/${t.total} · 正确率 ${t.accuracyText} · 覆盖率 ${t.completionText}`
            })
          )
          .sort((a, b) => b.favorites - a.favorites);
      } else {
        const activeDays = view.trend.filter((it) => it.answered > 0).length;
        activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
        ringActive = clampPct(activeDaysRate);
        displayTypes = view.byType || [];
      }

      this.setData({
        statsLoadedDays: days,
        statsLoadedSubTab: subtab,
        statsLoading: false,
        statsOverview: view.overview,
        statsTrend: view.trend,
        statsByType: view.byType,
        statsByDifficulty: view.byDifficulty,
        statsAdvice: view.advice,
        statsHasDifficulty: view.byDifficulty.length > 0,
        statsQuestions,
        favoritesTrend,

        ringAccuracy,
        ringCompletion,
        ringActive,
        activeDaysRate,
        ringRepeat,
        repeatRateText,
        mistakeRateText,
        favMistakeRateText,
        heatCells,
        displayTypes
      });
    } catch (err: any) {
      if (reqId !== (this as any).statsReq) return;
      this.setData({
        statsLoading: false,
        statsError: (err && err.message) ? String(err.message) : '统计加载失败',
        statsQuestions: [],
        favoritesTrend: {}
      });
    }
  },

  onStatsQuestionTap(e: any) {
    const id = Number(e?.detail?.id || e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    this.openQuestionDetail(id);
  },

  onCopySubjectName() {
    const subject = String(this.data.subjectName || '').trim();
    if (!subject) return;
    wx.setClipboardData({ data: subject });
  },

  onShareAppMessage() {
    const subject = String(this.data.subjectName || '').trim();
    const subjectId = Number(this.data.subjectId || 0);
    const path = subjectId
      ? `/pages/subject-detail-v2/subject-detail-v2?id=${subjectId}`
      : `/pages/subject-detail-v2/subject-detail-v2?subject=${encodeURIComponent(subject)}`;
    return {
      title: subject ? `题库：${subject}` : '题库分享',
      path
    };
  }
});
