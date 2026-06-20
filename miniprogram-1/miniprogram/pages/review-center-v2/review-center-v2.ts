import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeMode } from '../../utils/theme';

type ReviewKind = 'mistakes' | 'favorites' | 'tags';
type TabKey = 'practice' | 'search' | 'data';
type SourceType = 'public' | 'bank';

const KEY_LAST_SESSION = 'review_last_session_v1';

type Option<T> = { value: T; label: string };
type TagRow = { name: string; count?: number };

type PracticeMeta = {
  title: string;
  subtitle: string;
  recommend: string;
  tip: string;
  countLabel: string;
};

type AdviceAction = {
  label: string;
  kind?: ReviewKind;
  tab?: TabKey;
  qType?: string;
  tag?: string;
  startMode?: 'quiz' | 'memo';
};

type AdviceItem = {
  title: string;
  content: string;
  action?: AdviceAction;
};

function safeDecode(v: any): string {
  if (v == null) return '';
  const raw = String(v);
  try {
    return decodeURIComponent(raw);
  } catch (e) {
    return raw;
  }
}

function normalizeKind(input: any): ReviewKind {
  const v = String(input || '').trim().toLowerCase();
  if (v === 'favorites') return 'favorites';
  if (v === 'tags') return 'tags';
  return 'mistakes';
}

function normalizeTab(input: any): TabKey {
  const v = String(input || '').trim().toLowerCase();
  if (v === 'search') return 'search';
  if (v === 'data') return 'data';
  return 'practice';
}

function buildOptions(list: any[]): Array<Option<string>> {
  const uniq: string[] = [];
  (list || []).forEach((x) => {
    const s = String(x || '').trim();
    if (!s) return;
    if (!uniq.includes(s)) uniq.push(s);
  });
  return [{ value: 'all', label: '全部题型' }, ...uniq.map((s) => ({ value: s, label: s }))];
}

function normalizeTags(raw: any): TagRow[] {
  const tags = Array.isArray(raw) ? raw : [];
  const out: TagRow[] = [];
  tags.forEach((t: any) => {
    const name = String(t?.name || '').trim();
    if (!name) return;
    const count = Number(t?.count || 0) || 0;
    out.push({ name, count });
  });
  return out;
}

function isOptionShuffleSupported(qType: string): boolean {
  const t = String(qType || '').trim();
  if (!t || t === 'all') return false;
  if (t === '选择题' || t === '多选题') return true;
  if (t.includes('单选') || t.includes('多选')) return true;
  return false;
}

function formatCountText(n: any): string {
  const v = Number(n);
  if (!Number.isFinite(v)) return '0';
  if (v > 9999) return '9999+';
  return String(Math.max(0, Math.floor(v)));
}

function pctOf(n: number, maxN: number): number {
  if (maxN <= 0) return 0;
  const v = Math.max(0, Math.min(100, (n * 100) / maxN));
  return Math.round(v);
}

function extractFirstTypeFromAdvice(content: string): string {
  const s = String(content || '');
  const m = s.match(/「([^」]+)」/);
  if (!m || !m[1]) return '';
  return String(m[1])
    .split('、')[0]
    .trim();
}

function inferAdviceAction(kind: ReviewKind, title: string, content: string): AdviceAction | null {
  const t = String(title || '').trim();
  const c = String(content || '').trim();
  if (!t || !c) return null;

  if (t.includes('优先攻克题型')) {
    const qType = extractFirstTypeFromAdvice(c);
    if (qType) return { label: '按题型开练', tab: 'practice', qType, startMode: 'quiz' };
    return { label: '开始刷题', tab: 'practice', startMode: 'quiz' };
  }

  if (t.includes('聚焦薄弱点')) {
    if (kind !== 'mistakes') return { label: '开始刷错题', kind: 'mistakes', tab: 'practice', startMode: 'quiz' };
    return { label: '开始刷题', tab: 'practice', startMode: 'quiz' };
  }

  if (t.includes('错题要闭环')) {
    return { label: '开始背题', kind: 'mistakes', tab: 'practice', startMode: 'memo' };
  }

  if (t.includes('先建立手感') || t.includes('提高完成度') || t.includes('暂无题目')) {
    if (t.includes('暂无题目')) return { label: '去练习', tab: 'practice' };
    return { label: '开始刷题', tab: 'practice', startMode: 'quiz' };
  }

  return { label: '去练习', tab: 'practice' };
}

function defaultTitles(kind: ReviewKind): {
  navTitle: string;
  pageTitle: string;
  quizLabel: string;
  memoLabel: string;
} {
  if (kind === 'favorites') {
    return { navTitle: '收藏中心', pageTitle: '收藏中心', quizLabel: '刷题', memoLabel: '背题' };
  }
  if (kind === 'tags') {
    return { navTitle: '标签中心', pageTitle: '标签中心', quizLabel: '刷标签', memoLabel: '背标签' };
  }
  return { navTitle: '错题中心', pageTitle: '错题中心', quizLabel: '刷错题', memoLabel: '背错题' };
}

function getPracticeMeta(kind: ReviewKind): PracticeMeta {
  if (kind === 'favorites') {
    return {
      title: '收藏',
      subtitle: '范围固定为收藏。支持题型/标签/模式筛选，便于针对性复习。',
      recommend: '先刷后背',
      tip: '筛选仅作用于收藏范围',
      countLabel: '可用收藏'
    };
  }
  if (kind === 'tags') {
    return {
      title: '标签',
      subtitle: '按你的标签体系聚合题目：练习、搜索与数据复盘均可按标签过滤。',
      recommend: '分组复习',
      tip: '可选标签做专项复习，或保持全部标签直接开始',
      countLabel: '可用题目'
    };
  }
  return {
    title: '错题',
    subtitle: '范围固定为错题。支持题型/标签/模式筛选，便于集中复盘。',
    recommend: '错因复盘',
    tip: '筛选仅作用于错题范围',
    countLabel: '可用错题'
  };
}

Page({
  data: {
    loading: false,
    inited: false,

    kind: 'mistakes' as ReviewKind,
    sourceType: 'public' as SourceType,
    subject: '',
    bankId: 0,

    navTitle: '复盘中心',
    pageTitle: '复盘中心',
    pageSubtitle: '在当前题库范围内完成练习、搜索与数据复盘（与 Web 端保持同语义）。',
    scopeLabel: '公共',
    scopeName: '',

    tab: 'practice' as TabKey,

    practiceMeta: getPracticeMeta('mistakes') as PracticeMeta,

    types: [] as string[],
    typeOptions: [] as Array<Option<string>>,
    typeIndex: 0,
    qType: 'all',

    tagOptions: [] as Array<Option<string>>,
    tagIndex: 0,
    tag: 'all',
    tagChips: [] as TagRow[],
    isTagsMode: false,

    shuffleQuestions: false,
    shuffleOptions: false,
    shuffleOptionsDisabled: true,

    startCount: 0,
    startCountText: '0',
    startDisabled: true,
    startError: '',
    startQuizLabel: '刷题',
    startMemoLabel: '背题',
    filterHint: '',

    // 搜索
    searchKeyword: '',
    searched: false,
    searchLoading: false,
    page: 1,
    perPage: 20,
    total: 0,
    hasMore: false,
    questions: [] as Record<string, unknown>[],

    // 数据
    dataLoading: false,
    dataHint: '',
    dataDays: 14,
    dataTotalLabel: '可用题目',
    dataTotal: 0,
    dataAnswered: 0,
    dataCorrect: 0,
    dataWrong: 0,
    dataAccuracy: 0,
    dataCompletion: 0,
    dataFavorites: 0,
    dataMistakes: 0,
    dataMistakesTimes: 0,
    dataStreakDays: 0,
    dataLastActivityText: '—',
    dataTrendDays: 14,
    trendBars: [] as Array<{ day: string; accuracy: number; answered: number }>,
    dataTypeCount: 0,
    dataTagCount: 0,
    typeStats: [] as Array<{ q_type: string; count: number; pct: number; answered: number; accuracy: number }>,
    diffStats: [] as Array<{ label: string; count: number; pct: number; answered: number; accuracy: number }>,
    tagStats: [] as Array<{ name: string; count: number; pct: number }>,
    tagStatsAll: [] as Array<{ name: string; count: number; pct: number }>,
    tagStatsExpanded: false,
    advice: [] as AdviceItem[]
  },

  _startCountToken: 0 as number,
  _dataToken: 0 as number,
  _searchToken: 0 as number,

  onLoad(options: any) {
    const kind = normalizeKind(options?.kind || options?.entry || options?.mode);
    const tab = normalizeTab(options?.tab);

    const subject = safeDecode(options?.subject || '');
    const bankIdRaw = options?.bank_id ?? options?.bankId ?? options?.id;
    const bankId = Number(bankIdRaw || 0) || 0;

    const qType = safeDecode(options?.type || options?.q_type || 'all') || 'all';
    const tag = safeDecode(options?.tag || 'all') || 'all';

    const titles = defaultTitles(kind);
    const practiceMeta = getPracticeMeta(kind);

    const sourceType: SourceType = bankId > 0 ? 'bank' : 'public';
    const scopeLabel = sourceType === 'bank' ? '个人' : '公共';

    this.setData({
      kind,
      tab,
      subject: sourceType === 'public' ? subject : '',
      bankId: sourceType === 'bank' ? bankId : 0,
      navTitle: titles.navTitle,
      pageTitle: titles.pageTitle,
      startQuizLabel: titles.quizLabel,
      startMemoLabel: titles.memoLabel,
      isTagsMode: kind === 'tags',
      scopeLabel,
      practiceMeta,
      qType: qType || 'all',
      tag: tag || 'all'
    });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    if (!this.data.inited && !this.data.loading) {
      this.bootstrap();
    } else {
      this.refreshComputed();
    }
  },

  onPullDownRefresh() {
    this.bootstrap(true);
  },

  onReachBottom() {
    if (this.data.tab !== 'search') return;
    if (!this.data.hasMore || this.data.searchLoading) return;
    this.loadMore();
  },

  async bootstrap(force = false) {
    if (this.data.loading && !force) return;
    this.setData({ loading: true });

    try {
      const kind: ReviewKind = this.data.kind;
      const sourceType: SourceType = this.data.bankId > 0 ? 'bank' : 'public';
      const subject = String(this.data.subject || '').trim();
      const bankId = Number(this.data.bankId || 0) || 0;

      if (sourceType === 'public' && !subject) {
        wx.showToast({ title: '缺少科目参数', icon: 'none' });
        setTimeout(() => wx.navigateBack(), 500);
        return;
      }
      if (sourceType === 'bank' && bankId <= 0) {
        wx.showToast({ title: '缺少题库参数', icon: 'none' });
        setTimeout(() => wx.navigateBack(), 500);
        return;
      }

      const [info, tagsRes] = await Promise.all([
        sourceType === 'public'
          ? api.getSubjectInfo(subject).catch((): Record<string, unknown> => ({}))
          : api.getBankDetail(bankId).catch((): Record<string, unknown> => ({})),
        sourceType === 'public'
          ? api.getTags({ subject }).catch(() => ({ tags: [] as TagRow[] }))
          : api.getBankTags(bankId).catch(() => ({ tags: [] as TagRow[] }))
      ]);

      const infoData: Record<string, unknown> = ((info as Record<string, unknown>)?.data as Record<string, unknown>) || (info as Record<string, unknown>) || {};
      const scopeName =
        sourceType === 'public'
          ? String(infoData?.name || subject)
          : String(infoData?.name || `题库${bankId}`);

      const availableTypes = Array.isArray(infoData?.available_types) ? infoData.available_types : [];
      const types = (availableTypes || [])
        .filter((t: any) => typeof t === 'string' && String(t).trim())
        .map((t: any) => String(t).trim());
      const typeOptions = buildOptions(types);

      const tagsData: Record<string, unknown> = ((tagsRes as Record<string, unknown>)?.data as Record<string, unknown>) || (tagsRes as Record<string, unknown>) || {};
      const tagsList = normalizeTags(tagsData?.tags || []);
      const tagOptions: Array<Option<string>> = [
        { value: 'all', label: '全部标签' },
        ...tagsList.map((t) => ({ value: t.name, label: t.name }))
      ];

      // 修正当前索引
      const qType = String(this.data.qType || 'all');
      let typeIndex = typeOptions.findIndex((o) => o.value === qType);
      if (typeIndex < 0) typeIndex = 0;

      let tag = String(this.data.tag || 'all');
      let tagIndex = tagOptions.findIndex((o) => o.value === tag);
      if (tagIndex < 0) tagIndex = 0;
      tag = tagOptions[tagIndex]?.value || 'all';

      this.setData(
        {
          inited: true,
          sourceType,
          scopeName,
          types,
          typeOptions,
          typeIndex,
          qType: qType || 'all',
          tagOptions,
          tagIndex,
          tag,
          tagChips: tagsList,
          dataTagCount: tagsList.length
        },
        () => this.refreshComputed()
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

  refreshComputed() {
    const qType = String(this.data.qType || 'all');
    const tag = String(this.data.tag || 'all');
    const hintParts: string[] = [];
    if (qType && qType !== 'all') hintParts.push(qType);
    if (tag && tag !== 'all') hintParts.push(tag);
    const filterHint = hintParts.length ? hintParts.join(' · ') : '全部';

    const shuffleOptionsDisabled = !isOptionShuffleSupported(qType);
    const shuffleOptions = shuffleOptionsDisabled ? false : !!this.data.shuffleOptions;

    this.setData({ filterHint, shuffleOptionsDisabled, shuffleOptions });
    this.refreshStartCount();

    if (this.data.tab === 'data') {
      this.refreshDataStats();
    }
  },

  applyKind(nextKind: ReviewKind, after?: () => void) {
    if (nextKind === this.data.kind) {
      if (after) after();
      return;
    }

    this._startCountToken = (this._startCountToken || 0) + 1;
    this._dataToken = (this._dataToken || 0) + 1;
    this._searchToken = (this._searchToken || 0) + 1;

    const titles = defaultTitles(nextKind);
    const practiceMeta = getPracticeMeta(nextKind);

    this.setData(
      {
        kind: nextKind,
        navTitle: titles.navTitle,
        pageTitle: titles.pageTitle,
        startQuizLabel: titles.quizLabel,
        startMemoLabel: titles.memoLabel,
        isTagsMode: nextKind === 'tags',
        practiceMeta,

        // kind 会影响 search/source，避免残留旧结果
        searched: false,
        searchLoading: false,
        page: 1,
        total: 0,
        hasMore: false,
        questions: []
      },
      () => {
        if (after) after();
        else this.refreshComputed();
      }
    );
  },

  onKindTap(e: any) {
    const nextKind = normalizeKind(e?.currentTarget?.dataset?.kind || 'mistakes');
    this.applyKind(nextKind);
  },

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab || 'practice');
    if (tab === this.data.tab) return;
    this.setData({ tab }, () => {
      if (tab === 'data') this.refreshDataStats();
    });
  },

  onTypeTap(e: any) {
    const t = e?.currentTarget?.dataset?.type ? String(e.currentTarget.dataset.type) : 'all';
    const types = Array.isArray(this.data.types) ? this.data.types : [];
    const qType = t === 'all' || types.includes(t) ? t : 'all';
    const typeOptions = this.data.typeOptions || [];
    let typeIndex = typeOptions.findIndex((o) => o.value === qType);
    if (typeIndex < 0) typeIndex = 0;
    if (qType === this.data.qType && typeIndex === this.data.typeIndex) return;
    this.setData({ typeIndex, qType }, () => this.refreshComputed());
  },

  onTypePickerChange(e: any) {
    const idx = Number(e?.detail?.value || 0) || 0;
    const hit = (this.data.typeOptions || [])[idx];
    const qType = hit ? hit.value : 'all';
    this.setData({ typeIndex: idx, qType }, () => this.refreshComputed());
  },

  onTagTap(e: any) {
    const tag = e?.currentTarget?.dataset?.tag ? String(e.currentTarget.dataset.tag) : 'all';
    const tagOptions = this.data.tagOptions || [];
    let tagIndex = tagOptions.findIndex((o) => o.value === tag);
    if (tagIndex < 0) tagIndex = 0;
    const next = tagOptions[tagIndex]?.value || 'all';
    if (next === this.data.tag && tagIndex === this.data.tagIndex) return;
    this.setData({ tagIndex, tag: next }, () => this.refreshComputed());
  },

  onTagPickerChange(e: any) {
    const idx = Number(e?.detail?.value || 0) || 0;
    const hit = (this.data.tagOptions || [])[idx];
    const tag = hit ? hit.value : 'all';
    this.setData({ tagIndex: idx, tag }, () => this.refreshComputed());
  },

  onTagChipTap(e: any) {
    const tag = e?.currentTarget?.dataset?.tag ? String(e.currentTarget.dataset.tag) : 'all';
    const tagOptions = this.data.tagOptions || [];
    let tagIndex = tagOptions.findIndex((o) => o.value === tag);
    if (tagIndex < 0) tagIndex = 0;
    this.setData({ tagIndex, tag }, () => this.refreshComputed());
  },

  onSearchKeywordInput(e: any) {
    const v = String(e?.detail?.value || '');
    this.setData({ searchKeyword: v });
  },

  onClearSearchKeyword() {
    this.setData({ searchKeyword: '' });
  },

  async refreshStartCount() {
    this._startCountToken = (this._startCountToken || 0) + 1;
    const token = this._startCountToken;

    const kind: ReviewKind = this.data.kind;
    const sourceType: SourceType = this.data.sourceType;
    const subject = String(this.data.subject || '').trim();
    const bankId = Number(this.data.bankId || 0) || 0;
    const qType = String(this.data.qType || 'all');
    const tag = String(this.data.tag || 'all');

    this.setData({ startError: '', startCountText: '…' });

    try {
      let count = 0;
      if (sourceType === 'public') {
        const params: any = { subject };
        if (qType && qType !== 'all') params.type = qType;
        if (tag && tag !== 'all') params.tag = tag;

        const source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
        if (source !== 'all') params.source = source;

        const res: any = await api.getQuestionsCount(params);
        count = Number(res?.count || 0) || 0;
      } else {
        const params: any = {};
        if (qType && qType !== 'all') params.q_type = qType;
        const source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
        params.source = source;
        if (tag && tag !== 'all') params.tag = tag;
        const res: any = await api.getBankUserCounts(bankId, params);
        count = Number(res?.total || 0) || 0;
      }

      const startDisabled = count <= 0;
      if (token !== this._startCountToken) return;
      this.setData({ startCount: count, startCountText: formatCountText(count), startDisabled });
    } catch (e: any) {
      if (token !== this._startCountToken) return;
      this.setData({
        startCount: 0,
        startCountText: '0',
        startDisabled: true,
        startError: (e && e.message) || '统计失败'
      });
    }
  },

  buildQuizUrl(mode: 'quiz' | 'memo', extra?: { start_id?: number }) {
    const kind: ReviewKind = this.data.kind;
    const sourceType: SourceType = this.data.sourceType;
    const subject = String(this.data.subject || '').trim();
    const bankId = Number(this.data.bankId || 0) || 0;
    const qType = String(this.data.qType || 'all');
    const tag = String(this.data.tag || 'all');

    const params: string[] = [`mode=${encodeURIComponent(mode)}`];
    if (sourceType === 'public') params.push(`subject=${encodeURIComponent(subject)}`);
    else params.push(`bank_id=${encodeURIComponent(String(bankId))}`);

    if (qType && qType !== 'all') params.push(`type=${encodeURIComponent(qType)}`);

    const source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
    if (source !== 'all') params.push(`source=${encodeURIComponent(source)}`);

    if (tag && tag !== 'all') params.push(`tag=${encodeURIComponent(tag)}`);

    if (this.data.shuffleQuestions) params.push('shuffle_questions=1');
    if (this.data.shuffleOptions && !this.data.shuffleOptionsDisabled) params.push('shuffle_options=1');

    if (extra?.start_id) params.push(`start_id=${encodeURIComponent(String(extra.start_id))}`);

    return `/pages/quiz/quiz?${params.join('&')}`;
  },

  persistLastSession(mode: 'quiz' | 'memo', extra?: { start_id?: number }) {
    try {
      const payload: any = {
        ts: Date.now(),
        kind: this.data.kind,
        tab: this.data.tab,
        sourceType: this.data.sourceType,
        subject: this.data.subject,
        bankId: this.data.bankId,
        qType: this.data.qType,
        tag: this.data.tag,
        shuffleQuestions: !!this.data.shuffleQuestions,
        shuffleOptions: !!(this.data.shuffleOptions && !this.data.shuffleOptionsDisabled),
        scopeLabel: this.data.scopeLabel,
        scopeName: this.data.scopeName,
        mode,
        start_id: extra?.start_id
      };
      wx.setStorageSync(KEY_LAST_SESSION, payload);
    } catch (e) {}
  },

  onStartQuiz() {
    if (this.data.startDisabled) return;
    this.persistLastSession('quiz');
    safeNavigate(this.buildQuizUrl('quiz'), 'navigateTo');
  },

  onStartMemo() {
    if (this.data.startDisabled) return;
    this.persistLastSession('memo');
    safeNavigate(this.buildQuizUrl('memo'), 'navigateTo');
  },

  onResultTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    this.persistLastSession('quiz', { start_id: id });
    safeNavigate(this.buildQuizUrl('quiz', { start_id: id }), 'navigateTo');
  },

  onJumpPracticeType(e: any) {
    const t = e?.currentTarget?.dataset?.type ? String(e.currentTarget.dataset.type) : 'all';
    const idx = (this.data.typeOptions || []).findIndex((o) => o.value === t);
    const typeIndex = idx >= 0 ? idx : 0;
    const qType = (this.data.typeOptions || [])[typeIndex]?.value || 'all';
    this.setData({ tab: 'practice', typeIndex, qType }, () => this.refreshComputed());
  },

  onAdviceActionTap(e: any) {
    const idx = Number(e?.currentTarget?.dataset?.idx ?? -1);
    const list: AdviceItem[] = Array.isArray(this.data.advice) ? this.data.advice : [];
    if (!Number.isFinite(idx) || idx < 0 || idx >= list.length) return;
    const action = list[idx]?.action;
    if (!action) return;

    const startMode = action.startMode;
    const apply = () => {
      const patch: any = {};

      const tab = action.tab;
      if (tab && tab !== this.data.tab) patch.tab = tab;

      const rawType = action.qType != null ? String(action.qType) : '';
      if (rawType) {
        const types = Array.isArray(this.data.types) ? this.data.types : [];
        const qType = rawType === 'all' || types.includes(rawType) ? rawType : 'all';
        const typeOptions = this.data.typeOptions || [];
        let typeIndex = typeOptions.findIndex((o) => o.value === qType);
        if (typeIndex < 0) typeIndex = 0;
        patch.qType = qType;
        patch.typeIndex = typeIndex;
      }

      const rawTag = action.tag != null ? String(action.tag) : '';
      if (rawTag) {
        const tagOptions = this.data.tagOptions || [];
        let tagIndex = tagOptions.findIndex((o) => o.value === rawTag);
        if (tagIndex < 0) tagIndex = 0;
        const nextTag = tagOptions[tagIndex]?.value || 'all';
        patch.tag = nextTag;
        patch.tagIndex = tagIndex;
      }

      const done = () => {
        this.refreshComputed();
        if (startMode) safeNavigate(this.buildQuizUrl(startMode), 'navigateTo');
      };

      if (Object.keys(patch).length) this.setData(patch, done);
      else done();
    };

    const nextKind = action.kind;
    if (nextKind && nextKind !== this.data.kind) {
      this.applyKind(nextKind, apply);
      return;
    }
    apply();
  },

  buildTagStats() {
    const chips = Array.isArray(this.data.tagChips) ? this.data.tagChips : [];
    const rows = chips
      .map((t: any) => ({ name: String(t?.name || '').trim(), count: Number(t?.count || 0) || 0 }))
      .filter((t: any) => t.name && t.count > 0)
      .sort((a: any, b: any) => b.count - a.count);
    const maxN = rows.length ? rows[0].count : 0;
    return rows.map((r: any) => ({ name: r.name, count: r.count, pct: pctOf(r.count, maxN) }));
  },

  onDataDaysTap(e: any) {
    const days = Number(e?.currentTarget?.dataset?.days || 14);
    if (![7, 14, 30, 90].includes(days)) return;
    if (days === this.data.dataDays) return;
    this.setData({ dataDays: days }, () => {
      if (this.data.tab === 'data') this.refreshDataStats();
    });
  },

  onToggleTagStatsExpanded() {
    const next = !this.data.tagStatsExpanded;
    const all = Array.isArray(this.data.tagStatsAll) ? this.data.tagStatsAll : [];
    const tagStats = next ? all : all.slice(0, 12);
    this.setData({ tagStatsExpanded: next, tagStats });
  },

  async refreshDataStats() {
    this._dataToken = (this._dataToken || 0) + 1;
    const token = this._dataToken;

    this.setData({ dataLoading: true });
    try {
      const kind: ReviewKind = this.data.kind;
      const sourceType: SourceType = this.data.sourceType;
      const subject = String(this.data.subject || '').trim();
      const bankId = Number(this.data.bankId || 0) || 0;
      const tag = String(this.data.tag || 'all');
      const qType = String(this.data.qType || 'all');

      const source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
      const dataTotalLabel =
        kind === 'mistakes' ? '可用错题' : kind === 'favorites' ? '收藏题目' : tag && tag !== 'all' ? '标签题目' : '题库题目';

      const days = [7, 14, 30, 90].includes(Number(this.data.dataDays)) ? Number(this.data.dataDays) : 14;
      const params: any = { days };
      if (source !== 'all') params.source = source;
      if (qType && qType !== 'all') params.q_type = qType;
      if (tag && tag !== 'all') params.tag = tag;

      const stats: any =
        sourceType === 'public' ? await api.getSubjectStatsDetail(subject, params) : await api.getBankStatsDetail(bankId, params);

      const dataTotal = Number(stats?.total_count || 0) || 0;
      const dataAnswered = Number(stats?.answered || 0) || 0;
      const dataCorrect = Number(stats?.correct || 0) || 0;
      const dataWrong = Number(stats?.wrong || 0) || 0;
      const dataFavorites = Number(stats?.favorites || 0) || 0;
      const dataMistakes = Number(stats?.mistakes || 0) || 0;
      const dataMistakesTimes = Number(stats?.mistakes_times || 0) || 0;
      const dataAccuracy = Math.max(0, Math.min(100, Number(stats?.accuracy || 0) || 0));
      const dataCompletion = Math.max(0, Math.min(100, Number(stats?.completion || 0) || 0));
      const dataStreakDays = Number(stats?.streak_days || 0) || 0;
      const lastActivityRaw = stats?.last_activity ? String(stats.last_activity) : '';
      const dataLastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 16) : '—';
      const dataTrendDays = Number(stats?.trend_days || params.days || 14) || 14;

      const trend = Array.isArray(stats?.trend) ? stats.trend : [];
      const trendBars = trend.map((r: any) => {
        const answered = Number(r?.answered || 0) || 0;
        const correct = Number(r?.correct || 0) || 0;
        const accuracy = answered > 0 ? Math.round((correct * 1000) / answered) / 10 : 0;
        return { day: String(r?.day || ''), accuracy: Math.max(0, Math.min(100, accuracy)), answered };
      });

      const byType = Array.isArray(stats?.by_type) ? stats.by_type : [];
      const typeRows = byType
        .map((r: any) => ({
          q_type: String(r?.q_type || '').trim() || '未知',
          count: Number(r?.total || 0) || 0,
          answered: Number(r?.answered || 0) || 0,
          accuracy: Math.max(0, Math.min(100, Number(r?.accuracy || 0) || 0))
        }))
        .filter((r: any) => r.count > 0);
      typeRows.sort((a: any, b: any) => b.count - a.count);
      const maxType = typeRows.length ? typeRows[0].count : 0;
      const typeStats = typeRows.map((r: any) => ({ ...r, pct: pctOf(r.count, maxType) }));
      const dataTypeCount = typeRows.length;

      const byDiff = Array.isArray(stats?.by_difficulty) ? stats.by_difficulty : [];
      const diffRows = byDiff
        .map((r: any) => ({
          label: String(r?.label || '').trim() || `难度${Number(r?.difficulty || 1) || 1}`,
          count: Number(r?.total || 0) || 0,
          answered: Number(r?.answered || 0) || 0,
          accuracy: Math.max(0, Math.min(100, Number(r?.accuracy || 0) || 0))
        }))
        .filter((r: any) => r.count > 0);
      const maxDiff = diffRows.reduce((acc: number, cur: any) => Math.max(acc, Number(cur.count || 0) || 0), 0);
      const diffStats = diffRows.map((r: any) => ({ ...r, pct: pctOf(r.count, maxDiff) }));

      const advice: AdviceItem[] = Array.isArray(stats?.advice)
        ? stats.advice
            .map((a: any) => {
              const title = String(a?.title || '').trim();
              const content = String(a?.content || '').trim();
              if (!title || !content) return null;
              const action = inferAdviceAction(kind, title, content);
              return { title, content, action: action || undefined };
            })
            .filter(Boolean)
        : [];

      const tagStatsAll = this.buildTagStats();
      const tagStats = this.data.tagStatsExpanded ? tagStatsAll : tagStatsAll.slice(0, 12);

      if (token !== this._dataToken) return;
      this.setData({
        dataHint: '',
        dataDays: days,
        dataTotalLabel,
        dataTotal,
        dataAnswered,
        dataCorrect,
        dataWrong,
        dataAccuracy,
        dataCompletion,
        dataFavorites,
        dataMistakes,
        dataMistakesTimes,
        dataStreakDays,
        dataLastActivityText,
        dataTrendDays,
        trendBars,
        dataTypeCount,
        typeStats,
        diffStats,
        tagStats,
        tagStatsAll,
        advice
      });
    } catch (e) {
      const tagStatsAll = this.buildTagStats();
      const tagStats = this.data.tagStatsExpanded ? tagStatsAll : tagStatsAll.slice(0, 12);
      if (token !== this._dataToken) return;
      this.setData({
        dataHint: '',
        dataTotal: 0,
        dataAnswered: 0,
        dataCorrect: 0,
        dataWrong: 0,
        dataAccuracy: 0,
        dataCompletion: 0,
        dataFavorites: 0,
        dataMistakes: 0,
        dataMistakesTimes: 0,
        dataStreakDays: 0,
        dataLastActivityText: '—',
        trendBars: [],
        typeStats: [],
        dataTypeCount: 0,
        diffStats: [],
        tagStats,
        tagStatsAll,
        advice: []
      });
    } finally {
      if (token === this._dataToken) {
        this.setData({ dataLoading: false });
      }
    }
  },

  async onSearch() {
    const kw = String(this.data.searchKeyword || '').trim();
    if (!kw) {
      wx.showToast({ title: '请输入关键词', icon: 'none' });
      return;
    }
    if (this.data.searchLoading) return;
    this.setData({ searched: true, searchLoading: true, page: 1, total: 0, hasMore: false, questions: [] });
    await this.fetchSearchPage(1);
  },

  async loadMore() {
    if (this.data.searchLoading) return;
    const nextPage = (Number(this.data.page || 1) || 1) + 1;
    this.setData({ searchLoading: true });
    await this.fetchSearchPage(nextPage, true);
  },

  async fetchSearchPage(page: number, append = false) {
    this._searchToken = (this._searchToken || 0) + 1;
    const token = this._searchToken;

    try {
      const kind: ReviewKind = this.data.kind;
      const sourceType: SourceType = this.data.sourceType;
      const subject = String(this.data.subject || '').trim();
      const bankId = Number(this.data.bankId || 0) || 0;
      const qType = String(this.data.qType || 'all');
      const tag = String(this.data.tag || 'all');
      const keyword = String(this.data.searchKeyword || '').trim();

      const source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
      const per_page = Number(this.data.perPage || 20) || 20;

      let data: any = null;
      if (sourceType === 'public') {
        const params: any = { keyword, subject, page, per_page };
        if (qType && qType !== 'all') params.q_type = qType;
        if (source !== 'all') params.source = source;
        if (tag && tag !== 'all') params.tag = tag;
        data = await api.searchQuestions(params);
      } else {
        const params: any = { keyword, page, per_page };
        if (qType && qType !== 'all') params.q_type = qType;
        if (source !== 'all') params.source = source;
        if (tag && tag !== 'all') params.tag = tag;
        data = await api.searchBankQuestions(bankId, params);
      }

      const questions = (data && (data.questions || data.data?.questions)) ? (data.questions || data.data?.questions) : [];
      const total = Number(data?.total || data?.data?.total || 0) || 0;

      const nextList = append ? (this.data.questions || []).concat(questions) : questions;
      const hasMore = nextList.length < total;
      if (token !== this._searchToken) return;
      this.setData({ page, questions: nextList, total, hasMore });
    } catch (e: any) {
      if (token !== this._searchToken) return;
      wx.showToast({ title: (e && e.message) || '搜索失败', icon: 'none' });
      this.setData({ total: 0, hasMore: false });
    } finally {
      if (token === this._searchToken) {
        this.setData({ searchLoading: false });
      }
    }
  },

  onToggleTap(e: any) {
    const key = e?.currentTarget?.dataset?.key;
    if (!key) return;

    if (key === 'shuffleOptions' && this.data.shuffleOptionsDisabled) return;

    const current = (this.data as Record<string, unknown>)[key];
    const next = !current;
    this.setData({ [key]: next } as Record<string, unknown>, () => this.refreshComputed());
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  }
});
