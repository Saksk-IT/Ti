import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { createQuizSource } from '../../utils/quiz-source';
import { themeManager, ThemeMode } from '../../utils/theme';
import { requestStateBehavior } from '../../behaviors/request-state';
import { createSetDataBatcher } from '../../utils/set-data-batcher';
import {
  OPTION_TYPES,
  KEY_SHUFFLE_Q,
  KEY_SHUFFLE_O,
  DEFAULT_DETAIL_TAB_ORDER,
  VALID_DETAIL_TABS,
  normalizeDetailTabOrder,
  buildDetailTabViews,
  getBankDetailTabOrderKey,
  readBankDetailTabOrder,
  persistBankDetailTabOrder,
  normalizeScope,
  shouldCountForTab,
  normalizeTab,
  normalizeReinforceSubTab,
  getStoredString,
  setStoredString,
  normalizeTextLines,
  normalizeBankDetailOptions,
  getStoredBool,
  setStoredBool,
  clampPct,
  parseBoolFlag,
  buildExternalWebUrl,
  type Scope,
  type DetailTab,
  type TagItem,
  type SearchItem,
  type DetailOption,
  type AdviceItem,
  type StatsSubTab,
  type ReinforceSubTab,
  type ReinforceWrongTopItem,
  type ReinforceSimilarPairItem,
  type ReinforceWrongState,
  type ReinforceSimilarState,
  type TrendView,
  type TypeBreakdownView,
  type DifficultyBreakdownView,
  type StatsOverviewView,
  type StatsQuestionItem,
  type FavoritesTrend,
  type ShareItem,
  type BankUsageStats
} from './modules/bank-detail-helpers';

type _PrivState = {
  setDataBatcher?: (patch: Record<string, unknown>, cb?: () => void, options?: { immediate?: boolean }) => void;
  scopeForced?: string;
  tabExplicit?: boolean;
  qDetailReq?: number;
  statsReq?: number;
};
type JoinedBankSource = '' | 'public' | 'shared';
type JoinedBankRelation = '' | 'public' | 'shared' | 'both';
type BankSourceType = 'user' | 'system';

function normalizeBankSourceType(input: any): BankSourceType {
  return String(input || '').trim().toLowerCase() === 'system' ? 'system' : 'user';
}

function normalizeJoinedBankSource(input: any): JoinedBankSource {
  const raw = String(input || '').trim().toLowerCase();
  if (raw === 'public' || raw === 'shared') return raw;
  return '';
}

function normalizeJoinedBankRelation(input: any): JoinedBankRelation {
  const raw = String(input || '').trim().toLowerCase();
  if (raw === 'public' || raw === 'shared' || raw === 'both') return raw;
  return '';
}

function hasJoinedBankContext(source: JoinedBankSource, relation: JoinedBankRelation): boolean {
  return source === 'public' || source === 'shared' || relation === 'public' || relation === 'shared' || relation === 'both';
}
const _ps = new WeakMap<object, _PrivState>();
function _p(ctx: object): _PrivState {
  let s = _ps.get(ctx);
  if (!s) { s = {}; _ps.set(ctx, s); }
  return s;
}

Page({
  behaviors: [requestStateBehavior],
  data: {
    loading: false,
    inited: false,

    tab: 'practice' as DetailTab,
    entry: '',
    tabOrderOpen: false,
    detailTabs: buildDetailTabViews(DEFAULT_DETAIL_TAB_ORDER, false, false, false),

    bankId: 0,
    bankName: '',
    bankDescription: '',
    canManageShare: false,
    bankIsPublic: false,
    bankAllowCopy: true,
    bankPublicDescription: '',
    bankPublicSaving: false,
    bankPublicError: '',
    joinedBankSource: '' as JoinedBankSource,
    joinedBankRelation: '' as JoinedBankRelation,
    leaveBankSourceType: 'user' as BankSourceType,
    showLeaveBankAction: false,
    leavingBank: false,

    totalCount: 0,
    favCount: 0,
    mistakeCount: 0,
    examBuilderOpen: false,

    myStats: {
      total_answered: 0,
      correct_count: 0,
      wrong_count: 0,
      accuracy: 0
    },

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

    webLeadOpen: false,
    webLeadTitle: '',
    webLeadContent: '',
    webLeadUrl: '',

    practiceScope: 'all' as Scope,
    types: [] as string[],
    qType: 'all',
    tags: [] as TagItem[],
    tag: 'all',
    practiceAdvancedOpen: false,

    shuffleQuestions: false,
    shuffleOptions: false,
    shuffleOptionsDisabled: true,

    startCount: 0,
    startCountText: '—',
    startDisabled: true,
    startError: '',

    // 统计详情（对齐 Web 题库详情-统计子页面）
    statsSubTab: 'global' as StatsSubTab,
    statsDays: 14,
    statsLoading: false,
    statsLoadedDays: 0,
    statsLoadedSubTab: 'global' as StatsSubTab,
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
    statsAdvice: [] as AdviceItem[],
    statsHasDifficulty: false,
    statsQuestions: [] as StatsQuestionItem[],
    favoritesTrend: {} as FavoritesTrend,

    ringAccuracy: 0,
    ringCompletion: 0,
    ringActive: 0,
    activeDaysRate: 0,
    ringRepeat: 0,
    repeatRateText: '0%',
    mistakeRateText: '0%',
    favMistakeRateText: '0%',
    heatCells: [] as Array<{ level: number }>,
    displayTypes: [] as TypeBreakdownView[],

    // 分享管理（仅创建者可用；无权限时给出提示）
    shares: [] as ShareItem[],
    shareLoading: false,
    shareError: '',
    usageStats: { shared_users: 0, public_users: 0, total_users: 0 } as BankUsageStats,
    usageStatsLoaded: false,
    usageStatsLoading: false,
    wechatShareToken: '',
    wechatShareReady: false,
    wechatSharePreparing: false,
  },

  startCountTimer: null as ReturnType<typeof setTimeout> | null,
  startCountReq: 0,
  statsReq: 0,
  qDetailReq: 0,
  tabExplicit: false as boolean,
  scopeForced: '' as '' | Scope,
  setDataBatcher: null as null | ((patch: Record<string, any>, callback?: () => void, options?: { immediate?: boolean }) => void),

  ensureSetDataBatcher() {
    if (_p(this).setDataBatcher) return;
    _p(this).setDataBatcher = createSetDataBatcher(this.setData.bind(this));
  },

  patchData(patch: Record<string, any>, callback?: () => void, immediate: boolean = false) {
    this.ensureSetDataBatcher();
    const fn = _p(this).setDataBatcher;
    if (typeof fn === 'function') {
      fn(patch, callback, { immediate });
      return;
    }
    this.setData(patch, callback);
  },

  onLoad(options: any) {
    this.ensureSetDataBatcher();
    const bankId = Number(options?.id || options?.bank_id || options?.bankId || 0);
    const rawTab = options?.tab;
    const tab = normalizeTab(rawTab);
    const entry = String(options?.entry || '').trim().toLowerCase();
    const joinedBankSource = normalizeJoinedBankSource(options?.source || options?.joined_source || options?.joinedSource);
    const joinedBankRelation = normalizeJoinedBankRelation(options?.relation || options?.joined_relation || options?.joinedRelation || joinedBankSource);
    const leaveBankSourceType = normalizeBankSourceType(options?.source_type || options?.sourceType || options?.bank_type || options?.bankType);
    const tabKey = String(rawTab || '').trim().toLowerCase();
    const scopeFromParams = (tabKey === 'favorites' || tabKey === 'mistakes')
      ? normalizeScope(tabKey)
      : (entry === 'favorites' || entry === 'mistakes') ? normalizeScope(entry) : 'all';
    _p(this).scopeForced = scopeFromParams !== 'all' ? scopeFromParams : '';
    _p(this).tabExplicit = rawTab !== undefined && rawTab !== null && String(rawTab).trim() !== '';
    this.patchData({
      bankId: Number.isFinite(bankId) ? bankId : 0,
      tab,
      entry,
      joinedBankSource,
      joinedBankRelation,
      leaveBankSourceType,
      practiceScope: scopeFromParams
    }, undefined, true);
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.patchData(themeManager.getPageData(), undefined, true);
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
    if (this.data.tab === 'share' && this.data.canManageShare) {
      this.loadUsageStats();
    }
    if (this.data.tab === 'stats') {
      this.ensureStatsDetail();
    }
    if (this.data.tab === 'reinforce') {
      this.ensureReinforce(false);
    }
  },

  consumeReturnTab() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const key = `bank_${bankId}_return_tab`;
    const desired = getStoredString(key, '');
    if (!desired) return;
    setStoredString(key, '');
    const tab = normalizeTab(desired);
    if (tab === this.data.tab) return;
    this.setData({ tab });
  },

  openDataPage(subtab: StatsSubTab) {
    const raw = String(subtab || 'global');
    const next: StatsSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
    const bankId = Number(this.data.bankId || 0);
    if (bankId) setStoredString(`bank_${bankId}_stats_subtab`, next);
    this.setData({ tab: 'stats', statsSubTab: next, statsLoadedDays: 0, statsLoadedSubTab: next }, () => {
      this.ensureStatsDetail(true);
    });
  },

  async bootstrap() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) {
      wx.showToast({ title: '题库参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
      return;
    }

    this.initDetailTabOrder();

    const keyType = `bank_${bankId}_type`;
    const keyTag = `bank_${bankId}_tag`;
    const keyScope = `bank_${bankId}_scope`;
    const keySearchType = `bank_${bankId}_search_type`;
    const keyStatsSubTab = `bank_${bankId}_stats_subtab`;
    const keyReinforceSubTab = `bank_${bankId}_reinforce_subtab`;

    const storedType = getStoredString(keyType, 'all');
    const storedTag = getStoredString(keyTag, 'all');
    const storedScope = getStoredString(keyScope, 'all');
    const storedSearchType = getStoredString(keySearchType, 'all');
    const storedStatsSubTab = getStoredString(keyStatsSubTab, 'global');
    const storedReinforceSubTab = getStoredString(keyReinforceSubTab, 'wrong');
    const shuffleQuestions = getStoredBool(KEY_SHUFFLE_Q, false);
    const shuffleOptions = getStoredBool(KEY_SHUFFLE_O, false);

    const entry = String(this.data.entry || '').trim().toLowerCase();
    let tab: DetailTab = this.data.tab;
    let practiceScope: Scope = this.data.practiceScope || 'all';
    if (!_p(this).tabExplicit) {
      if (entry === 'favorites') {
        tab = 'practice';
        practiceScope = 'favorites';
        _p(this).scopeForced = 'favorites';
      } else if (entry === 'mistakes') {
        tab = 'practice';
        practiceScope = 'mistakes';
        _p(this).scopeForced = 'mistakes';
      } else if (entry === 'exam') {
        tab = 'exam';
      }
    }

    const forcedScope = _p(this).scopeForced || '';
    if (forcedScope === 'favorites' || forcedScope === 'mistakes') {
      practiceScope = forcedScope;
    } else {
      practiceScope = normalizeScope(storedScope);
    }

    const statsSubTab: StatsSubTab = (storedStatsSubTab === 'mistakes' || storedStatsSubTab === 'favorites') ? storedStatsSubTab : 'global';
    const reinforceSubTab: ReinforceSubTab = normalizeReinforceSubTab(storedReinforceSubTab);

    this.setData({ loading: true, startError: '' });
    try {
      const [detailRes, countsRes, myStatsRes, tagsRes] = await Promise.all([
        api.getBankDetail(bankId),
        api.getBankUserCounts(bankId, { source: 'all' }).catch(() => ({ data: { total: 0, favorites: 0, mistakes: 0 } })),
        api.getBankMyStats(bankId).catch(() => ({ data: { total_answered: 0, correct_count: 0, wrong_count: 0, accuracy: 0 } })),
        api.getBankTags(bankId).catch(() => ({ data: { tags: [] } }))
      ]);

      const bankData = ((detailRes as Record<string, unknown>)?.data || detailRes || {}) as Record<string, unknown>;
      const countsData = ((countsRes as Record<string, unknown>)?.data || countsRes || {}) as Record<string, unknown>;
      const myStatsData = ((myStatsRes as Record<string, unknown>)?.data || myStatsRes || {}) as Record<string, unknown>;
      const tagsResObj = (tagsRes && typeof tagsRes === 'object' ? tagsRes : {}) as Record<string, unknown>;
      const tagsData = ((tagsResObj.data && typeof tagsResObj.data === 'object' ? tagsResObj.data : tagsResObj) || {}) as Record<string, unknown>;

      const bankName = String(bankData?.name || '').trim();
      const bankDescription = String(bankData?.description || '').trim();

      const accessType = String(bankData?.access_type || '').trim().toLowerCase();
      const permission = String(bankData?.permission || '').trim().toLowerCase();
      const canManageShare = accessType === 'owner' || permission === 'owner';
      const showShareTab = canManageShare;

      const joinedSource = normalizeJoinedBankSource(this.data.joinedBankSource);
      const joinedRelation = normalizeJoinedBankRelation(this.data.joinedBankRelation || joinedSource);
      const leaveBankSourceType = normalizeBankSourceType(this.data.leaveBankSourceType);
      const showLeaveBankAction = !canManageShare && leaveBankSourceType === 'user' && hasJoinedBankContext(joinedSource, joinedRelation);
      const showSettingsTab = showLeaveBankAction;
      if ((tab === 'manage' || tab === 'share') && !canManageShare) tab = 'practice';
      if (tab === 'settings' && !showSettingsTab) tab = 'practice';

      const bankIsPublic = parseBoolFlag(bankData?.is_public, false);
      const bankAllowCopy = parseBoolFlag(bankData?.allow_copy, true);
      const bankPublicDescription = String(bankData?.public_description || '').trim();

      const tabOrderKey = getBankDetailTabOrderKey(bankId);
      const tabOrder = readBankDetailTabOrder(tabOrderKey, DEFAULT_DETAIL_TAB_ORDER);
      const detailTabs = buildDetailTabViews(tabOrder, canManageShare, showShareTab, showSettingsTab);

      const typesRaw = Array.isArray(bankData?.available_types) ? bankData.available_types : [];
      const types = (typesRaw || [])
        .filter((t: any) => typeof t === 'string' && t.trim())
        .map((t: any) => String(t).trim());

      const qType = storedType === 'all' || types.includes(storedType) ? storedType : 'all';

      const tagsDataInner = (tagsData.data && typeof tagsData.data === 'object' ? tagsData.data : {}) as Record<string, unknown>;
      const tagsRaw = Array.isArray(tagsData.tags)
        ? tagsData.tags
        : Array.isArray(tagsDataInner.tags)
          ? tagsDataInner.tags
          : [];
      const tags: TagItem[] = (tagsRaw || [])
        .map((t: any) => ({ name: String(t?.name || '').trim(), count: t?.count }))
        .filter((t: TagItem) => t.name);
      const tag = storedTag === 'all' || tags.some((t) => t.name === storedTag) ? storedTag : 'all';
      const searchType = storedSearchType === 'all' || types.includes(storedSearchType) ? storedSearchType : 'all';

      const totalCount = Number(countsData?.total ?? bankData?.question_count ?? 0) || 0;
      const favCount = Number(countsData?.favorites || 0) || 0;
      const mistakeCount = Number(countsData?.mistakes || 0) || 0;

      this.setData({
        inited: true,
        bankName: bankName || `题库${bankId}`,
        bankDescription,
        canManageShare,
        detailTabs,
        bankIsPublic,
        bankAllowCopy,
        bankPublicDescription,
        bankPublicSaving: false,
        bankPublicError: '',
        joinedBankSource: joinedSource,
        joinedBankRelation: joinedRelation,
        leaveBankSourceType,
        showLeaveBankAction,
        leavingBank: false,
        totalCount,
        favCount,
        mistakeCount,
        myStats: {
          total_answered: Number(myStatsData?.total_answered || 0) || 0,
          correct_count: Number(myStatsData?.correct_count || 0) || 0,
          wrong_count: Number(myStatsData?.wrong_count || 0) || 0,
          accuracy: Number(myStatsData?.accuracy || 0) || 0
        },
        tab,
        practiceScope,
        types,
        qType,
        tags,
        tag,
        searchType,
        statsSubTab,
        statsLoadedSubTab: statsSubTab,
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
        shuffleQuestions,
        shuffleOptions
      });

      setStoredString(keyType, qType);
      setStoredString(keyTag, tag);
      setStoredString(keyScope, practiceScope);
      setStoredString(keySearchType, searchType);
      setStoredString(keyStatsSubTab, statsSubTab);
      setStoredString(keyReinforceSubTab, reinforceSubTab);

      this.syncShuffleOptionsDisabled();
      if (shouldCountForTab(tab)) {
        this.scheduleStartCount();
      }
      if (tab === 'share' && canManageShare) {
        this.loadShares();
      }
      if (tab === 'stats') {
        this.ensureStatsDetail();
      }
      if (tab === 'reinforce') {
        this.ensureReinforce(true);
      }
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '加载失败', icon: 'none' });
    } finally {
      this.patchData({ loading: false }, undefined, true);
      try {
        wx.stopPullDownRefresh();
      } catch (e) {}
    }
  },

  onPullDownRefresh() {
    this.bootstrap();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.patchData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  initDetailTabOrder() {
    const bankId = Number(this.data.bankId || 0);
    const key = getBankDetailTabOrderKey(bankId);
    const order = readBankDetailTabOrder(key, DEFAULT_DETAIL_TAB_ORDER);
    const showShareTab = Boolean(this.data.canManageShare);
    const showSettingsTab = Boolean(this.data.showLeaveBankAction);
    this.patchData({ detailTabs: buildDetailTabViews(order, Boolean(this.data.canManageShare), showShareTab, showSettingsTab) });
  },

  applyDetailTabOrder(nextOrder: DetailTab[]) {
    const normalized = normalizeDetailTabOrder(nextOrder, DEFAULT_DETAIL_TAB_ORDER);
    const bankId = Number(this.data.bankId || 0);
    const key = getBankDetailTabOrderKey(bankId);
    persistBankDetailTabOrder(key, normalized);
    const showShareTab = Boolean(this.data.canManageShare);
    const showSettingsTab = Boolean(this.data.showLeaveBankAction);
    this.patchData({ detailTabs: buildDetailTabViews(normalized, Boolean(this.data.canManageShare), showShareTab, showSettingsTab) });
  },

  onOpenTabOrder() {
    this.patchData({ tabOrderOpen: true });
  },

  onCloseTabOrder() {
    this.patchData({ tabOrderOpen: false });
  },

  onTabOrderSheetTap() {},

  onMoveTabOrder(e: any) {
    const act = String(e?.currentTarget?.dataset?.act || '').trim();
    const keyRaw = String(e?.currentTarget?.dataset?.key || '').trim().toLowerCase();
    if (!VALID_DETAIL_TABS.has(keyRaw as DetailTab)) return;

    const order: DetailTab[] = (this.data.detailTabs || [])
      .map((it: any) => String(it?.key || '').trim().toLowerCase())
      .filter((k: string) => VALID_DETAIL_TABS.has(k as DetailTab)) as DetailTab[];
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

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab || 'practice');
    if (tab === this.data.tab) return;
    this.patchData({ tab, startError: '' }, () => {
      this.syncShuffleOptionsDisabled();
      if (shouldCountForTab(tab)) {
        this.scheduleStartCount();
      }
      if (tab === 'share' && this.data.canManageShare) {
        this.loadUsageStats();
      }
      if (tab === 'stats') {
        this.ensureStatsDetail();
      }
      if (tab === 'reinforce') {
        this.ensureReinforce(false);
      }
    });
  },

  onGoManageQuestions() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    this.openWebLead({
      title: '题目管理',
      content: '小程序端暂不支持题目管理，请在浏览器打开 Web 端进行新增/编辑/删除（建议电脑端）。',
      next: `/user/banks/${bankId}`
    });
  },

  onGoManageSettings() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    this.openWebLead({
      title: '题库设置',
      content: '题库设置（公开/私密、描述、复制权限等）请在浏览器打开 Web 端完成。',
      next: `/user/banks/${bankId}/edit`
    });
  },

  openWebLead(options: { title?: string; content: string; next: any }) {
    const title = String(options?.title || '请前往网页端').trim() || '请前往网页端';
    const content = String(options?.content || '').trim();
    const url = buildExternalWebUrl(options?.next);
    this.patchData({
      webLeadOpen: true,
      webLeadTitle: title,
      webLeadContent: content,
      webLeadUrl: url
    });
  },

  onWebLeadClose() {
    this.patchData({ webLeadOpen: false });
  },

  onWebLeadSheetTap() {},

  onWebLeadCopy() {
    const url = String(this.data.webLeadUrl || '').trim();
    if (!url) return;
    wx.setClipboardData({
      data: url,
      success: () => {
        wx.showToast({ title: '链接已复制', icon: 'success' });
        this.patchData({ webLeadOpen: false });
      },
      fail: () => wx.showToast({ title: '复制失败', icon: 'none' })
    });
  },

  onGoShareTab() {
    this.patchData({ tab: 'share', startError: '' }, () => {
      if (this.data.canManageShare) {
        this.loadUsageStats();
      }
    });
  },

  async onLeaveJoinedBank() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!this.data.showLeaveBankAction || this.data.leavingBank) return;

    const confirmed = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '退出题库',
        content: '确定要退出该题库吗？退出后会从“我的题库”中移除。',
        confirmText: '退出',
        confirmColor: '#dc2626',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!confirmed) return;

    this.patchData({ leavingBank: true }, undefined, true);
    try {
      await api.leavePublicBank('user', bankId);
      this.patchData({ showLeaveBankAction: false, leavingBank: false }, undefined, true);
      wx.showToast({ title: '已退出题库', icon: 'success' });
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/my-banks-v2/my-banks-v2',
          fail: () => wx.navigateBack()
        });
      }, 500);
    } catch (err: any) {
      const msg = (err && err.message) ? String(err.message) : '退出失败';
      this.patchData({ leavingBank: false }, undefined, true);
      wx.showToast({ title: msg, icon: 'none' });
    }
  },

  async onBankOwnershipTap(e: any) {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!this.data.canManageShare) {
      wx.showToast({ title: '无权操作', icon: 'none' });
      return;
    }

    const raw = e?.currentTarget?.dataset?.public;
    const nextPublic = raw === true || raw === 1 || raw === '1';
    if (nextPublic === Boolean(this.data.bankIsPublic)) return;
    if (this.data.bankPublicSaving) return;

    const confirmed = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: nextPublic ? '设为公共题库' : '设为个人题库',
        content: nextPublic
          ? '设为公共后将出现在题库广场，其他用户可进入使用。是否继续？'
          : '设为个人后将从题库广场移除（不影响你自己刷题）。是否继续？',
        confirmText: '确定',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!confirmed) return;

    const payload: any = {
      is_public: nextPublic,
      public_description: String(this.data.bankPublicDescription || '')
    };

    this.setData({ bankPublicSaving: true, bankPublicError: '' });
    try {
      const res: any = await api.setBankPublic(bankId, payload);
      const msg = String(res?.message || (nextPublic ? '题库已公开' : '题库已设为私密'));
      this.setData({ bankIsPublic: nextPublic });
      wx.showToast({ title: msg, icon: 'success' });
    } catch (err: any) {
      const msg = (err && err.message) ? String(err.message) : '保存失败';
      this.setData({ bankPublicError: msg });
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      this.setData({ bankPublicSaving: false });
    }
  },

  onReinforceSubTabTap(e: any) {
    const next = normalizeReinforceSubTab(e?.currentTarget?.dataset?.subtab || 'wrong');
    if (next === this.data.reinforceSubTab) return;
    const bankId = Number(this.data.bankId || 0);
    if (bankId) setStoredString(`bank_${bankId}_reinforce_subtab`, next);
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
    const bankId = Number(this.data.bankId || 0);
    const list = Array.isArray(ids)
      ? ids.map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0).map((n) => Math.floor(n))
      : [];
    if (!Number.isFinite(bankId) || bankId <= 0 || !list.length) return '';

    const qs =
      `bank_id=${encodeURIComponent(String(bankId))}` +
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    wx.navigateTo({ url: `/pages/quiz/quiz?bank_id=${encodeURIComponent(String(bankId))}&mode=quiz&source=mistakes` });
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (this.data.reinforceWrong.loading) return;

    this.setData({
      reinforceWrong: Object.assign({}, this.data.reinforceWrong, { loading: true, error: '' })
    });

    try {
      const data: any = await api.getQuizReinforce({
        source: 'user_bank',
        bank_id: bankId,
        include: 'wrong',
        wrong_list_n: 30
      });

      const wrongTotal = Number(data?.wrong_total || 0) || 0;
      const recommendIds = Array.isArray(data?.wrong_recommend_ids)
        ? this.parseIdList(data.wrong_recommend_ids.join(','), 200)
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
      });
    } catch (e: any) {
      this.setData({
        reinforceWrong: Object.assign({}, this.data.reinforceWrong, {
          loading: false,
          loaded: true,
          error: (e && e.message) ? String(e.message) : '加载失败',
          desc: '加载失败，请下拉刷新重试',
          listMeta: '加载失败'
        })
      });
    }
  },

  async loadReinforceSimilar() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (this.data.reinforceSimilar.loading) return;

    this.setData({
      reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, { loading: true, error: '' })
    });

    try {
      const data: any = await api.getQuizReinforce({
        source: 'user_bank',
        bank_id: bankId,
        include: 'similar',
        pairs_n: 30
      });

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

      if (similarMode === 'bank_dedupe' || similarMode === 'subject_dedupe') {
        if (similarOnlyIds.length) {
          startIds = similarOnlyIds.slice();
          const pairsText = pairsCount > 0 ? `${pairsCount} 组` : '';
          desc = `检测到${pairsText ? (' ' + pairsText) : ''}相似题（题干、选项相似），共 ${similarOnlyIds.length} 道。`;
        } else {
          desc = wrongTotal > 0 ? '暂未检测到明显相似题（题干/选项相似），可先做错题加强。' : '暂未检测到明显相似题（题干/选项相似）。';
        }
      } else {
        if (similarOnlyIds.length) {
          startIds = similarOnlyIds.slice();
          desc = `基于你最近的错题，为你匹配了 ${similarOnlyIds.length} 道相似题，可用于易混强化。`;
        } else if (wrongTotal > 0 && seedIds.length) {
          startIds = seedIds.slice();
          desc = `暂未匹配到足够稳定的相似题，先用最近错题 ${seedIds.length} 道作为“相似题种子训练”。`;
        } else {
          desc = wrongTotal > 0 ? '暂未匹配到足够稳定的相似题，建议先做错题加强。' : '先完成一些练习后，这里会给出相似题加强。';
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
      });
    } catch (e: any) {
      this.setData({
        reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, {
          loading: false,
          loaded: true,
          error: (e && e.message) ? String(e.message) : '加载失败',
          desc: '加载失败，请下拉刷新重试',
          listMeta: '加载失败'
        })
      });
    }
  },

  onScopeTap(e: any) {
    const next = normalizeScope(e?.currentTarget?.dataset?.scope || 'all');
    if (next === this.data.practiceScope) return;
    const bankId = Number(this.data.bankId || 0);
    if (bankId) setStoredString(`bank_${bankId}_scope`, next);
    _p(this).scopeForced = '';
    this.setData({ practiceScope: next, startError: '' }, () => {
      if (this.data.tab === 'practice') {
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return '';

    const qs = createQuizSource({ bankId });
    return qs.buildProgressKey(mode, {
      type: this.data.qType,
      source: this.data.practiceScope,
      tag: this.data.tag,
      shuffleQuestions: this.data.shuffleQuestions,
      shuffleOptions: this.data.shuffleOptions
    });
  },

  confirmAndClearProgress(mode: 'quiz' | 'memo') {
    const key = this.buildProgressKey(mode);
    if (!key) return;

    const scopeLabel = this.data.practiceScope === 'favorites' ? '收藏' : this.data.practiceScope === 'mistakes' ? '错题' : '全部';
    const typeLabel = this.data.qType === 'all' ? '全部题型' : String(this.data.qType || '').trim() || '全部题型';
    const tagLabel = this.data.tag && this.data.tag !== 'all' ? String(this.data.tag || '').trim() : '全部标签';
    const modeLabel = mode === 'memo' ? '背题' : '刷题';
    const shuffleQ = this.data.shuffleQuestions ? '开' : '关';
    const shuffleO = this.data.shuffleOptions ? '开' : '关';
    const bankName = String(this.data.bankName || '').trim() || `题库${Number(this.data.bankId || 0) || ''}`;

    wx.showModal({
      title: '确认清除',
      content: `将清除以下组合的进度：\n题库：${bankName}\n范围：${scopeLabel}\n题型：${typeLabel}\n标签：${tagLabel}\n模式：${modeLabel}\n打乱题目：${shuffleQ}  打乱选项：${shuffleO}`,
      confirmText: '清除',
      confirmColor: '#FF3B30',
      success: async (r) => {
        if (!r.confirm) return;
        wx.showLoading({ title: '清除中...' });
        try {
          await api.deleteProgress(key);
        } catch (e: any) {}
        try {
          wx.removeStorageSync(key);
        } catch (e) {}
        wx.hideLoading();
        wx.showToast({ title: '已清除', icon: 'success' });
      }
    });
  },

  onSearchInput(e: any) {
    this.setData({ searchKeyword: String(e?.detail?.value || '') });
  },

  onBankSearch() {
    this.doBankSearch(true);
  },

  onSearchTypeTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.type || 'all').trim() || 'all';
    const types = Array.isArray(this.data.types) ? this.data.types : [];
    const v = next === 'all' || types.includes(next) ? next : 'all';
    if (v === this.data.searchType) return;
    const bankId = Number(this.data.bankId || 0);
    if (bankId) setStoredString(`bank_${bankId}_search_type`, v);
    this.setData({ searchType: v }, () => {
      if (this.data.searchSearched && String(this.data.searchKeyword || '').trim()) {
        this.doBankSearch(true);
      }
    });
  },

  async doBankSearch(reset: boolean) {
    const kw = String(this.data.searchKeyword || '').trim();
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

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
    });

    try {
      const res: any = await api.getBankQuestions(bankId, {
        keyword: kw,
        q_type: this.data.searchType && this.data.searchType !== 'all' ? this.data.searchType : undefined,
        page,
        per_page: perPage
      });

      const list: SearchItem[] = Array.isArray(res?.questions) ? res.questions : [];
      const total = Number(res?.total || 0) || 0;
      const nextList = reset ? list : (this.data.searchResults || []).concat(list);

      this.setData({
        searchResults: nextList,
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
    this.doBankSearch(false);
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    this.openQuestionDetail(id);
  },

  async openQuestionDetail(questionId: number) {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const qid = Number(questionId || 0);
    if (!Number.isFinite(qid) || qid <= 0) return;

    const reqId = ++_p(this).qDetailReq;
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
    });

    try {
      const q: any = await api.getBankQuestionDetail(bankId, qid);
      if (reqId !== _p(this).qDetailReq) return;

      const qType = String(q?.q_type || '').trim();
      const options = normalizeBankDetailOptions(q?.options, qType);

      const metaParts = [`ID：${qid}`];
      if (qType) metaParts.push(qType);
      if (q?.difficulty != null && Number.isFinite(Number(q.difficulty))) metaParts.push(`难度 ${Number(q.difficulty)}`);

      this.setData({
        qDetailLoading: false,
        qDetailError: '',
        qDetailMeta: metaParts.join(' · '),
        qDetailContentLines: normalizeTextLines(q?.content),
        qDetailAnswerLines: normalizeTextLines(q?.answer),
        qDetailExplanationLines: normalizeTextLines(q?.explanation),
        qDetailOptions: options
      });
    } catch (err: any) {
      if (reqId !== _p(this).qDetailReq) return;
      this.setData({
        qDetailLoading: false,
        qDetailError: (err && err.message) ? String(err.message) : '加载失败'
      });
    }
  },

  onQDetailClose() {
    this.setData({ qDetailOpen: false });
  },

  onQDetailSheetTap() {
    // 阻止冒泡：点击面板内部不关闭
  },

  onQDetailGoQuiz() {
    const id = Number(this.data.qDetailId || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    this.onQDetailClose();
    wx.navigateTo({ url: `/pages/quiz/quiz?bank_id=${encodeURIComponent(String(bankId))}&mode=quiz&source=all&start_id=${id}` });
  },

  onTypeTap(e: any) {
    const type = String(e?.currentTarget?.dataset?.type || 'all').trim();
    const types = this.data.types || [];
    const next = type === 'all' || types.includes(type) ? type : 'all';
    if (next === this.data.qType) return;
    const keyType = `bank_${Number(this.data.bankId || 0)}_type`;
    this.setData({ qType: next });
    setStoredString(keyType, next);
    this.syncShuffleOptionsDisabled();
    if (shouldCountForTab(this.data.tab)) {
      this.scheduleStartCount();
    }
  },

  onTagTap(e: any) {
    const next = String(e?.currentTarget?.dataset?.tag || 'all').trim();
    const tags = this.data.tags || [];
    const ok = next === 'all' || tags.some((t) => t.name === next);
    const val = ok ? next : 'all';
    if (val === this.data.tag) return;
    const keyTag = `bank_${Number(this.data.bankId || 0)}_tag`;
    this.setData({ tag: val });
    setStoredString(keyTag, val);
    if (shouldCountForTab(this.data.tab)) {
      this.scheduleStartCount();
    }
  },

  onTagDeleteTap(e: any) {
    const name = String(e?.currentTarget?.dataset?.tag || '').trim();
    if (!name || name.toLowerCase() === 'all') return;

    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    wx.showModal({
      title: '删除标签',
      content: `删除标签「${name}」？\n\n仅删除：当前用户 · 当前题库下的标签，并移除该标签在本题库下所有题目上的绑定。`,
      confirmText: '删除',
      confirmColor: '#FF3B30',
      success: async (r) => {
        if (!r.confirm) return;
        wx.showLoading({ title: '删除中...' });
        try {
          const res: any = await api.deleteBankTag(bankId, name);
          const tagsRaw = Array.isArray(res?.tags)
            ? res.tags
            : Array.isArray(res?.data?.tags)
              ? res.data.tags
              : [];
          const tags: TagItem[] = (tagsRaw || [])
            .map((t: any) => ({ name: String(t?.name || '').trim(), count: t?.count }))
            .filter((t: TagItem) => t.name);

          const prevTag = String(this.data.tag || 'all').trim() || 'all';
          const nextTag = prevTag === name ? 'all' : prevTag;
          const keyTag = `bank_${bankId}_tag`;
          if (nextTag !== prevTag) setStoredString(keyTag, nextTag);

          this.setData({ tags, tag: nextTag }, () => {
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

  syncShuffleOptionsDisabled() {
    const disabled = true;
    if (disabled !== this.data.shuffleOptionsDisabled) {
      this.setData({ shuffleOptionsDisabled: disabled });
    }
  },

  onToggleShuffleQuestions() {
    const next = !this.data.shuffleQuestions;
    this.setData({ shuffleQuestions: next });
    setStoredBool(KEY_SHUFFLE_Q, next);
    if (shouldCountForTab(this.data.tab)) {
      this.scheduleStartCount();
    }
  },

  onToggleShuffleOptions() {
    if (this.data.shuffleOptionsDisabled) return;
    const next = !this.data.shuffleOptions;
    this.setData({ shuffleOptions: next });
    setStoredBool(KEY_SHUFFLE_O, next);
    if (shouldCountForTab(this.data.tab)) {
      this.scheduleStartCount();
    }
  },

  scheduleStartCount() {
    if (!shouldCountForTab(this.data.tab)) return;
    if (this.startCountTimer) {
      clearTimeout(this.startCountTimer);
      this.startCountTimer = null;
    }
    this.patchData({ startCountText: '…', startDisabled: true, startError: '' });
    this.startCountTimer = setTimeout(() => this.loadStartCount(), 260);
  },

  async loadStartCount() {
    const reqId = ++this.startCountReq;
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    try {
      const params: any = { source: this.data.practiceScope || 'all' };
      if (this.data.qType && this.data.qType !== 'all') params.q_type = this.data.qType;
      if (this.data.tag && this.data.tag !== 'all') params.tag = this.data.tag;

      const res: any = await api.getBankUserCounts(bankId, params);
      if (reqId !== this.startCountReq) return;
      const data = res?.data || res || {};
      const shuffleOptionsAvailable = !!data?.shuffle_options_available;
      const hadShuffleOptions = !!this.data.shuffleOptions;
      const count = Number(data?.total || 0) || 0;
      this.patchData({
        startCount: count,
        startCountText: String(count),
        startDisabled: count <= 0,
        shuffleOptionsDisabled: !shuffleOptionsAvailable,
        shuffleOptions: shuffleOptionsAvailable ? this.data.shuffleOptions : false,
        startError: ''
      });
      if (!shuffleOptionsAvailable && hadShuffleOptions) {
        setStoredBool(KEY_SHUFFLE_O, false);
      }
    } catch (e: any) {
      if (reqId !== this.startCountReq) return;
      const hadShuffleOptions = !!this.data.shuffleOptions;
      this.patchData({
        startCount: 0,
        startCountText: '0',
        startDisabled: true,
        shuffleOptionsDisabled: true,
        shuffleOptions: false,
        startError: (e && e.message) ? String(e.message) : '获取题量失败'
      });
      if (hadShuffleOptions) {
        setStoredBool(KEY_SHUFFLE_O, false);
      }
    }
  },

  buildQuizUrl(mode: 'quiz' | 'memo'): string {
    const bankId = Number(this.data.bankId || 0);
    const params: string[] = [];
    params.push(`bank_id=${bankId}`);
    params.push(`mode=${mode}`);
    params.push(`source=${encodeURIComponent(String(this.data.practiceScope || 'all'))}`);
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

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

    const name = String(this.data.bankName || '').trim() || `题库#${bankId}`;
    const detail = Object.keys(typesCfg).map((k) => `${k}:${typesCfg[k]}`).join('，');
    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '创建并开始考试',
        content: `题库：${name}\n时长：${duration}分钟\n题量：${total}（${detail}）`,
        confirmText: '开始',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    wx.showLoading({ title: '创建中…', mask: true });
    try {
      const res: any = await api.createExam({
        source: 'user_bank',
        subject: name,
        bank_id: bankId,
        duration,
        types: typesCfg,
        scores: {}
      });
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
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    wx.navigateTo({ url: `/pages/bank-exam-setup/bank-exam-setup?bank_id=${bankId}` });
  },

  // ===== 统计详情 =====
  statsSourceForSubTab(subtab: any): Scope {
    const s = String(subtab || '').trim().toLowerCase();
    if (s === 'mistakes') return 'mistakes';
    if (s === 'favorites') return 'favorites';
    return 'all';
  },

  onStatsSubTabTap(e: any) {
    const raw = String(e?.detail?.subtab || e?.currentTarget?.dataset?.subtab || '').trim().toLowerCase();
    const next: StatsSubTab = (raw === 'mistakes' || raw === 'favorites') ? raw : 'global';
    if (next === this.data.statsSubTab) return;
    const bankId = Number(this.data.bankId || 0);
    if (bankId) setStoredString(`bank_${bankId}_stats_subtab`, next);
    this.patchData({ statsSubTab: next, statsLoadedDays: 0, statsLoadedSubTab: next }, () => {
      if (this.data.tab === 'stats') {
        this.ensureStatsDetail(true);
      }
    });
  },

  onStatsDaysTap(e: any) {
    const days = Number(e?.detail?.days || e?.currentTarget?.dataset?.days || 14);
    if (![7, 14, 30, 90].includes(days)) return;
    if (days === this.data.statsDays) return;
    this.patchData({ statsDays: days, statsLoadedDays: 0 }, () => {
      if (this.data.tab === 'stats') {
        this.ensureStatsDetail(true);
      }
    });
  },

  onStatsQuickStart(e: any) {
    const raw = String(e?.detail?.subtab || e?.currentTarget?.dataset?.subtab || '').trim().toLowerCase();
    const subtab = raw === 'mistakes' || raw === 'favorites' ? raw : '';
    if (!subtab) return;
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    wx.navigateTo({ url: `/pages/quiz/quiz?bank_id=${encodeURIComponent(String(bankId))}&mode=quiz&source=${encodeURIComponent(subtab)}` });
  },

  ensureStatsDetail(force = false) {
    if (this.data.statsLoading) return;
    const days = Number(this.data.statsDays || 14) || 14;
    const subtab = this.data.statsSubTab || 'global';
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

  async loadStatsDetail(days: number, subtab: StatsSubTab) {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    const reqId = ++_p(this).statsReq;
    this.patchData({ statsLoading: true, statsError: '', statsQuestions: [], favoritesTrend: {} });

    try {
      const source = this.statsSourceForSubTab(subtab || 'global');

      const statsPromise: Promise<any> =
        source === 'all'
          ? api.getBankStatsDetail(bankId, days)
          : api.getBankStatsDetail(bankId, { days, source });

      let questionsPromise: Promise<any> = Promise.resolve(null);
      let favTrendPromise: Promise<any> = Promise.resolve(null);
      if (subtab === 'mistakes') {
        questionsPromise = api.getBankQuestions(bankId, { source: 'mistakes', page: 1, per_page: 300 });
      } else if (subtab === 'favorites') {
        questionsPromise = api.getBankQuestions(bankId, { source: 'favorites', page: 1, per_page: 200 });
        favTrendPromise = api.getBankFavoritesTrend(bankId, days);
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
      if (reqId !== _p(this).statsReq) return;
      if (!statsRes.ok) throw (statsRes as { ok: false; reason: unknown }).reason;

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

      this.patchData({
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
      if (reqId !== _p(this).statsReq) return;
      this.patchData({
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

  onCopyBankName() {
    const name = String(this.data.bankName || '').trim();
    if (!name) return;
    wx.setClipboardData({ data: name });
  },

  // ==================== 分享管理（仅创建者） ====================
  formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${month}-${day}`;
    } catch {
      return '';
    }
  },

  async loadShares() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!this.data.canManageShare) return;
    if (this.data.shareLoading) return;

    this.patchData({ shareLoading: true, shareError: '' });
    try {
      const res: any = await api.getBankShares(bankId);
      const data = res?.data || res || {};
      const raw = Array.isArray(data?.shares) ? data.shares : [];

      const shares: ShareItem[] = raw
        .filter((s: any) => !!s?.is_active)
        .map((s: any) => {
          return Object.assign({}, s, {
            expires_at_display: s?.expires_at ? this.formatDate(String(s.expires_at)) : ''
          });
        });

      const picked = this.pickShareTokenFromShares(shares);
      this.patchData({
        shares,
        shareLoading: false,
        wechatShareToken: picked,
        wechatShareReady: !!picked
      });
    } catch (err: any) {
      const msg = (err && err.message) ? String(err.message) : '无权查看分享（仅创建者可管理）';
      this.patchData({
        shares: [],
        shareLoading: false,
        shareError: msg,
        wechatShareToken: '',
        wechatShareReady: false
      });
    }
  },

  isExpiredIso(expiresAt: any): boolean {
    const s = String(expiresAt || '').trim();
    if (!s) return false;
    try {
      const d = new Date(s);
      const ts = d.getTime();
      if (!Number.isFinite(ts)) return true;
      return ts < Date.now();
    } catch {
      return true;
    }
  },

  pickShareTokenFromShares(shares: ShareItem[]): string {
    const list = Array.isArray(shares) ? shares : [];
    for (const s of list) {
      if (!s) continue;
      if (!s.is_active) continue;
      const token = s.share_token ? String(s.share_token).trim() : '';
      if (!token) continue;
      if (s.expires_at && this.isExpiredIso(s.expires_at)) continue;
      return token;
    }
    return '';
  },

  async ensureWechatShareToken(force: boolean = false): Promise<string> {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return '';
    if (!this.data.canManageShare) return '';
    const currentToken = String(this.data.wechatShareToken || '').trim();
    if (!force && this.data.wechatShareReady && currentToken) return currentToken;
    if (this.data.wechatSharePreparing) return currentToken;

    this.patchData({ wechatSharePreparing: true, wechatShareReady: false });
    try {
      await this.loadShares();
      let token = String(this.data.wechatShareToken || '').trim();

      if (!token) {
        const payload: any = {
          type: 'link',
          permission: 'read',
          expires_in: null
        };

        const created: any = await api.createBankShare(bankId, payload);
        token = String(created?.share_token || '').trim() || this.extractTokenFromShareLink(created?.share_link);
      }

      if (token) {
        this.patchData({ wechatShareToken: token, wechatShareReady: true });
        await this.loadShares();
        this.loadUsageStats();
      }
      return token;
    } catch (e: any) {
      this.patchData({ wechatShareToken: '', wechatShareReady: false });
      throw e;
    } finally {
      this.patchData({ wechatSharePreparing: false });
    }
  },

  async loadUsageStats() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!this.data.canManageShare) return;
    if (this.data.usageStatsLoading) return;

    this.patchData({ usageStatsLoading: true });
    try {
      const res: any = await api.getBankUsageStats(bankId);
      const data = res?.data || res || {};
      const stats: BankUsageStats = {
        bank_id: bankId,
        is_public: !!data.is_public,
        owner_id: Number(data.owner_id || 0),
        owner_count: Number(data.owner_count || 1),
        shared_users: Number(data.shared_users || 0),
        public_users: Number(data.public_users || 0),
        total_users: Number(data.total_users || 0),
        total_users_excluding_owner: Number(data.total_users_excluding_owner || 0)
      };
      this.patchData({ usageStats: stats, usageStatsLoaded: true, usageStatsLoading: false });
    } catch (err: any) {
      this.patchData({ usageStatsLoaded: false, usageStatsLoading: false });
    }
  },

  extractTokenFromShareLink(input: any): string {
    const s = String(input || '').trim();
    if (!s) return '';
    if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?')) return s;
    const m = s.match(/[?&]token=([^&#]+)/i);
    if (m && m[1]) {
      try {
        return decodeURIComponent(m[1]);
      } catch {
        return m[1];
      }
    }
    return '';
  },

  async onWechatShareCard() {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!this.data.canManageShare) {
      wx.showToast({ title: '无权操作', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '准备分享...' });
    try {
      const token = await this.ensureWechatShareToken(false);
      if (!token) throw new Error('微信分享准备失败');

      wx.showToast({ title: '已准备好，请再次点击微信分享', icon: 'none' });
    } catch (err: any) {
      wx.showToast({ title: (err && err.message) ? String(err.message) : '分享失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  async onCreateShare(_e: any) {
    const bankId = Number(this.data.bankId || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;

    wx.showLoading({ title: '创建中...' });
    try {
      const payload: any = {
        type: 'code',
        permission: 'read',
        expires_in: null
      };

      const res: any = await api.createBankShare(bankId, payload);
      const data = res?.data || res || {};

      const code = data.share_code ? String(data.share_code) : '';
      if (code) {
        wx.setClipboardData({ data: code });
        wx.showToast({ title: '已复制', icon: 'success' });
      } else {
        wx.showToast({ title: '创建成功', icon: 'success' });
      }

      await this.loadShares();
    } catch (err: any) {
      wx.showToast({ title: (err && err.message) ? String(err.message) : '创建失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onCopyShareCode(e: any) {
    const code = String(e?.currentTarget?.dataset?.code || '').trim();
    if (!code) return;
    wx.setClipboardData({ data: code });
  },

  onDeleteShare(e: any) {
    const bankId = Number(this.data.bankId || 0);
    const shareId = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(bankId) || bankId <= 0) return;
    if (!Number.isFinite(shareId) || shareId <= 0) return;

    wx.showModal({
      title: '确认撤销',
      content: '撤销后，使用此分享加入的用户将无法继续访问。',
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (!res.confirm) return;
        wx.showLoading({ title: '撤销中...' });
        try {
          await api.deleteBankShare(bankId, shareId);
          wx.showToast({ title: '已撤销', icon: 'success' });
          await this.loadShares();
          this.loadUsageStats();
        } catch (err: any) {
          wx.showToast({ title: (err && err.message) ? String(err.message) : '撤销失败', icon: 'none' });
        } finally {
          wx.hideLoading();
        }
      }
    });
  },

  onShareAppMessage() {
    const bankId = Number(this.data.bankId || 0);
    const name = String(this.data.bankName || '').trim();
    if (this.data.canManageShare) {
      const token = String(this.data.wechatShareToken || '').trim();
      if (token) {
        return {
          title: name ? `邀请你加入题库：${name}` : '邀请你加入题库',
          path: `/pages/bank-join/bank-join?token=${encodeURIComponent(token)}`
        };
      }
    }

    const path = bankId ? `/pages/bank-detail/bank-detail?id=${bankId}` : '/pages/my-banks-v2/my-banks-v2';
    return {
      title: name ? `题库：${name}` : '题库分享',
      path
    };
  }
});
