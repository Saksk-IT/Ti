import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type TabKey = 'public' | 'bank';
type ReviewKind = 'mistakes' | 'favorites' | 'tags';
type SourceType = 'public' | 'bank';
type CenterTab = 'practice' | 'search' | 'data';

type SubjectMeta = { id: number; name: string; question_count: number };

type BankCard = {
  id: number;
  name: string;
  question_count: number;
  sort_key?: string;
};

type LastSession = {
  ts?: number;
  kind: ReviewKind;
  tab: CenterTab;
  sourceType: SourceType;
  subject?: string;
  bankId?: number;
  qType?: string;
  tag?: string;
  shuffleQuestions?: boolean;
  shuffleOptions?: boolean;
  scopeLabel?: string;
  scopeName?: string;
  mode?: 'quiz' | 'memo';
  start_id?: number;
};

const KEY_TAB = 'review_hub_v3_tab';
const KEY_KW = 'review_hub_v3_kw';
const KEY_LAST_SESSION = 'review_last_session_v1';

function normalizeTab(input: any): TabKey {
  const s = String(input || '').trim().toLowerCase();
  return s === 'bank' ? 'bank' : 'public';
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

function normalizeSubject(raw: any): SubjectMeta | null {
  const id = Number(raw?.id || 0);
  const name = String(raw?.name || '').trim();
  if (!Number.isFinite(id) || id <= 0 || !name) return null;
  return { id, name, question_count: Number(raw?.question_count || 0) || 0 };
}

function normalizeBank(raw: any): BankCard | null {
  const isShared = raw && raw.bank_id != null;
  const id = Number(isShared ? raw.bank_id : raw?.id || 0);
  const name = String(isShared ? raw.bank_name : raw?.name || '').trim();
  if (!Number.isFinite(id) || id <= 0 || !name) return null;
  const question_count = Number(raw?.question_count || 0) || 0;
  const sort_key = String(isShared ? raw?.last_access_at : raw?.updated_at || '').trim();
  return { id, name, question_count, sort_key };
}

function normalizeLastSession(raw: any): LastSession | null {
  if (!raw) return null;
  let obj: any = raw;
  if (typeof raw === 'string') {
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  const kind = String(obj?.kind || '').trim();
  if (kind !== 'mistakes' && kind !== 'favorites' && kind !== 'tags') return null;

  const sourceType = String(obj?.sourceType || '').trim();
  if (sourceType !== 'public' && sourceType !== 'bank') return null;

  const subject = String(obj?.subject || '').trim();
  const bankId = Number(obj?.bankId || obj?.bank_id || 0) || 0;
  if (sourceType === 'public' && !subject) return null;
  if (sourceType === 'bank' && bankId <= 0) return null;

  const tabRaw = String(obj?.tab || 'practice').trim().toLowerCase();
  const tab: CenterTab = tabRaw === 'search' ? 'search' : tabRaw === 'data' ? 'data' : 'practice';

  const qType = String(obj?.qType || obj?.type || obj?.q_type || 'all') || 'all';
  const tag = String(obj?.tag || 'all') || 'all';

  const scopeLabel = String(obj?.scopeLabel || '').trim();
  const scopeName = String(obj?.scopeName || '').trim();

  const modeRaw = String(obj?.mode || '').trim().toLowerCase();
  const mode: 'quiz' | 'memo' | undefined = modeRaw === 'memo' ? 'memo' : modeRaw === 'quiz' ? 'quiz' : undefined;

  const start_id = Number(obj?.start_id || obj?.startId || 0) || 0;
  const ts = Number(obj?.ts || obj?.timestamp || 0) || 0;

  return {
    ts,
    kind: kind as ReviewKind,
    tab,
    sourceType: sourceType as SourceType,
    subject,
    bankId,
    qType,
    tag,
    shuffleQuestions: !!obj?.shuffleQuestions,
    shuffleOptions: !!obj?.shuffleOptions,
    scopeLabel,
    scopeName,
    mode,
    start_id: start_id > 0 ? start_id : undefined
  };
}

function readLastSession(): LastSession | null {
  try {
    return normalizeLastSession(wx.getStorageSync(KEY_LAST_SESSION));
  } catch (e) {
    return null;
  }
}

function kindLabel(kind: ReviewKind): string {
  if (kind === 'favorites') return '收藏';
  if (kind === 'tags') return '标签';
  return '错题';
}

function sourceTypeLabel(sourceType: SourceType): string {
  return sourceType === 'bank' ? '个人' : '公共';
}

function buildLastSessionSummary(s: LastSession): string {
  const scope =
    String(s.scopeName || '').trim() ||
    (s.sourceType === 'public' ? String(s.subject || '').trim() : `题库${Number(s.bankId || 0) || 0}`);
  const parts = [sourceTypeLabel(s.sourceType), scope, kindLabel(s.kind)].filter(Boolean);
  const filters: string[] = [];
  const qType = String(s.qType || 'all');
  const tag = String(s.tag || 'all');
  if (qType && qType !== 'all') filters.push(qType);
  if (tag && tag !== 'all') filters.push(tag);
  return filters.length ? `${parts.join(' · ')} · ${filters.join(' · ')}` : parts.join(' · ');
}

function buildReviewCenterUrl(session: LastSession, override?: Partial<Pick<LastSession, 'kind' | 'tab' | 'qType' | 'tag'>>): string {
  const kind = (override?.kind || session.kind || 'mistakes') as ReviewKind;
  const tab = (override?.tab || session.tab || 'practice') as CenterTab;
  const qType = String(override?.qType ?? session.qType ?? 'all') || 'all';
  const tag = String(override?.tag ?? session.tag ?? 'all') || 'all';
  const params: string[] = [`kind=${encodeURIComponent(kind)}`, `tab=${encodeURIComponent(tab)}`];

  if (session.sourceType === 'bank') {
    params.push(`bank_id=${encodeURIComponent(String(Number(session.bankId || 0) || 0))}`);
  } else {
    params.push(`subject=${encodeURIComponent(String(session.subject || '').trim())}`);
  }

  if (qType && qType !== 'all') params.push(`type=${encodeURIComponent(qType)}`);
  if (tag && tag !== 'all') params.push(`tag=${encodeURIComponent(tag)}`);
  if (session.shuffleQuestions) params.push('shuffle_questions=1');
  if (session.shuffleOptions) params.push('shuffle_options=1');

  return `/pages/review-center-v2/review-center-v2?${params.join('&')}`;
}

function buildQuizUrlFromSession(session: LastSession, mode: 'quiz' | 'memo'): string {
  const params: string[] = [`mode=${encodeURIComponent(mode)}`];

  if (session.sourceType === 'bank') {
    params.push(`bank_id=${encodeURIComponent(String(Number(session.bankId || 0) || 0))}`);
  } else {
    params.push(`subject=${encodeURIComponent(String(session.subject || '').trim())}`);
  }

  const qType = String(session.qType || 'all');
  if (qType && qType !== 'all') params.push(`type=${encodeURIComponent(qType)}`);

  const source = session.kind === 'mistakes' ? 'mistakes' : session.kind === 'favorites' ? 'favorites' : 'all';
  if (source !== 'all') params.push(`source=${encodeURIComponent(source)}`);

  const tag = String(session.tag || 'all');
  if (tag && tag !== 'all') params.push(`tag=${encodeURIComponent(tag)}`);

  if (session.shuffleQuestions) params.push('shuffle_questions=1');
  if (session.shuffleOptions) params.push('shuffle_options=1');

  const startId = Number(session.start_id || 0) || 0;
  if (startId > 0) params.push(`start_id=${encodeURIComponent(String(startId))}`);

  return `/pages/quiz/quiz?${params.join('&')}`;
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,

    tab: 'public' as TabKey,
    keyword: '',

    subjects: [] as SubjectMeta[],
    filteredSubjects: [] as SubjectMeta[],

    banks: [] as BankCard[],
    filteredBanks: [] as BankCard[],

    publicTotal: 0,
    bankTotal: 0,
    currentTotal: 0,
    shownTotal: 0,

    hasLastSession: false,
    lastSession: null as any,
    lastSessionSummary: ''
  },

  onLoad(options: any) {
    const storedTab = normalizeTab(getStoredString(KEY_TAB, 'public'));
    const storedKw = getStoredString(KEY_KW, '');
    const tab = normalizeTab(options?.tab || storedTab);
    const keyword = options?.keyword ? String(options.keyword) : storedKw;
    this.setData({ tab, keyword: keyword || '' });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}

    this.refreshLastSession();

    if (!this.data.inited && !this.data.loading) {
      this.bootstrap();
      return;
    }

    this.applyFilter();
  },

  refreshLastSession() {
    const session = readLastSession();
    this.setData({
      hasLastSession: !!session,
      lastSession: session,
      lastSessionSummary: session ? buildLastSessionSummary(session) : ''
    });
  },

  async bootstrap() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const [meta, myBanksRes, sharedBanksRes] = await Promise.all([
        api.getSubjectsMeta().catch(() => ({ subjects: [], quiz_count: 0 } as any)),
        api.getMyBanks().catch(() => ({ banks: [] } as any)),
        api.getSharedBanks().catch(() => ({ banks: [] } as any))
      ]);

      const subjectsRaw = Array.isArray((meta as any)?.subjects) ? (meta as any).subjects : [];
      const subjects: SubjectMeta[] = subjectsRaw.map(normalizeSubject).filter(Boolean) as any;
      subjects.sort((a, b) => a.id - b.id);

      const map = new Map<number, BankCard>();
      const myBanksRaw = Array.isArray((myBanksRes as any)?.banks) ? (myBanksRes as any).banks : [];
      const sharedBanksRaw = Array.isArray((sharedBanksRes as any)?.banks) ? (sharedBanksRes as any).banks : [];

      for (const b of myBanksRaw) {
        const item = normalizeBank(b);
        if (!item) continue;
        map.set(item.id, item);
      }

      for (const b of sharedBanksRaw) {
        const item = normalizeBank(b);
        if (!item) continue;
        if (!map.has(item.id)) map.set(item.id, item);
      }

      const banks = Array.from(map.values()).sort(
        (a, b) => String(b.sort_key || '').localeCompare(String(a.sort_key || '')) || b.id - a.id
      );

      this.setData(
        {
          inited: true,
          subjects,
          banks,
          publicTotal: subjects.length,
          bankTotal: banks.length
        },
        () => this.applyFilter()
      );
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
      try {
        wx.stopPullDownRefresh();
      } catch (e) {}
    }
  },

  onPullDownRefresh() {
    this.bootstrap();
  },

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab || 'public');
    if (tab === this.data.tab) return;
    this.setData({ tab }, () => this.applyFilter());
    setStoredString(KEY_TAB, tab);
  },

  onKeywordInput(e: any) {
    const keyword = String(e?.detail?.value || '');
    this.setData({ keyword }, () => this.applyFilter());
    setStoredString(KEY_KW, keyword);
  },

  onClearKeyword() {
    this.setData({ keyword: '' }, () => this.applyFilter());
    setStoredString(KEY_KW, '');
  },

  applyFilter() {
    const kw = String(this.data.keyword || '').trim().toLowerCase();
    const subjects = Array.isArray(this.data.subjects) ? this.data.subjects : [];
    const banks = Array.isArray(this.data.banks) ? this.data.banks : [];

    let filteredSubjects = subjects.slice();
    let filteredBanks = banks.slice();

    if (kw) {
      filteredSubjects = filteredSubjects.filter((s) => String(s.name || '').toLowerCase().includes(kw));
      filteredBanks = filteredBanks.filter((b) => String(b.name || '').toLowerCase().includes(kw));
    }

    const currentTotal = this.data.tab === 'bank' ? banks.length : subjects.length;
    const shownTotal = this.data.tab === 'bank' ? filteredBanks.length : filteredSubjects.length;

    this.setData({ filteredSubjects, filteredBanks, currentTotal, shownTotal });
  },

  onPublicBankTap(e: any) {
    const name = String(e?.currentTarget?.dataset?.name || '').trim();
    if (!name) return;
    const url = `/pages/review-center-v2/review-center-v2?kind=mistakes&subject=${encodeURIComponent(name)}`;
    safeNavigate(url, 'navigateTo');
  },

  onBankTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    const url = `/pages/review-center-v2/review-center-v2?kind=mistakes&bank_id=${encodeURIComponent(String(id))}`;
    safeNavigate(url, 'navigateTo');
  },

  onContinueLast() {
    const session: LastSession | null = this.data.lastSession;
    if (!session) {
      wx.showToast({ title: '暂无上次复盘记录', icon: 'none' });
      return;
    }
    safeNavigate(buildReviewCenterUrl(session), 'navigateTo');
  },

  onContinueLastQuick(e: any) {
    const session: LastSession | null = this.data.lastSession;
    if (!session) return;
    const modeRaw = String(e?.currentTarget?.dataset?.mode || '').trim().toLowerCase();
    const mode: 'quiz' | 'memo' = modeRaw === 'memo' ? 'memo' : 'quiz';
    safeNavigate(buildQuizUrlFromSession(session, mode), 'navigateTo');
  },

  onTodayFocus() {
    const session: LastSession | null = this.data.lastSession;
    if (!session) {
      wx.showToast({ title: '请先选择范围开始复盘', icon: 'none' });
      return;
    }
    safeNavigate(buildReviewCenterUrl(session, { kind: 'mistakes', tab: 'practice', qType: 'all', tag: 'all' }), 'navigateTo');
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
  }
});

