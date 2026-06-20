import { api, normalizeImageUrls } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager, ThemeMode } from '../../utils/theme';

type Option<T> = { value: T; label: string };

const FALLBACK_TYPES = ['选择题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
const questionDetailCache = new Map<number, any>();

function buildOptions(list: string[], allLabel: string): Option<string>[] {
  const uniq = Array.from(new Set((list || []).filter((s) => typeof s === 'string' && s.trim()).map((s) => s.trim())));
  return [{ value: 'all', label: allLabel }, ...uniq.map((s) => ({ value: s, label: s }))];
}

function findLabel(options: Option<string>[], value: string, fallback: string) {
  const hit = (options || []).find((o) => o && o.value === value);
  return hit ? hit.label : fallback;
}

function looksLikeCode(text: string): boolean {
  const s = (text || '').toString();
  if (!s.includes('\n')) return false;
  const hasIndent = /(^|\n)[ \t]{2,}\S/.test(s);
  const hasCodeTokens =
    /\b(for|while|if|else|elif|def|class|print|return|break|continue|import|from|int|float|public|private|static|void|main)\b/.test(
      s
    );
  const hasSymbols = /[{}();=<>]/.test(s);
  return hasIndent || hasCodeTokens || hasSymbols;
}

function preserveSpacesForCode(text: string): string {
  const s = (text || '').toString().replace(/\t/g, '  ');
  return s
    .split('\n')
    .map((line) => line.replace(/ /g, '\u00A0'))
    .join('\n');
}

function formatAnswerForDisplay(qType: string, answer: string): string {
  const a = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
  if (qType === '填空题') {
    return a.replace(/;;/g, ' / ').replace(/;/g, ' 或 ');
  }
  return a;
}

Page({
  activeDetailReqId: 0,
  data: {
    loading: false,
    searched: false,
    advancedOpen: false,

    keyword: '',
    preselectSubject: '',
    preselectType: '',
    questions: [] as Record<string, unknown>[],
    page: 1,
    per_page: 20,
    total: 0,
    hasMore: true,

    subjectOptions: [] as Option<string>[],
    subjectIndex: 0,
    subject: 'all',
    subjectLabel: '全部科目',

    typeOptions: [] as Option<string>[],
    typeIndex: 0,
    qType: 'all',
    typeLabel: '全部题型',

    detailOpen: false,
    detailLoading: false,
    detailError: '',
    detailQuestionId: 0,
    detailSubjectFromList: '',
    detailQTypeFromList: '',
    detailQuestion: null as Record<string, unknown> | null,
    detailOptions: [] as Record<string, unknown>[],
    detailImages: [] as string[]
  },

  onLoad(options: any) {
    const keyword = options && options.keyword ? String(options.keyword) : '';
    let preselectSubject = options && options.subject ? String(options.subject) : '';
    let preselectType = options && (options.q_type || options.type) ? String(options.q_type || options.type) : '';

    if (preselectSubject) {
      try {
        preselectSubject = decodeURIComponent(preselectSubject);
      } catch (e) {}
    }
    if (preselectType) {
      try {
        preselectType = decodeURIComponent(preselectType);
      } catch (e) {}
    }

    this.setData({
      keyword,
      preselectSubject,
      preselectType
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

    if (!this.data.subjectOptions.length) {
      this.bootstrap();
    }
  },

  async bootstrap() {
    try {
      const res: any = await api.getSubjects();
      const list = Array.isArray(res?.subjects) ? res.subjects : [];
      const subjects: string[] = list
        .filter((s: any) => typeof s === 'string' && s.trim())
        .map((s: any) => String(s).trim());
      const subjectOptions = [{ value: 'all', label: '全部科目' } as Option<string>, ...subjects.map((s) => ({ value: s, label: s }))];

      let subjectIndex = 0;
      let subject = 'all';
      let subjectLabel = '全部科目';

      const wantedSubject = String(this.data.preselectSubject || '').trim();
      if (wantedSubject) {
        const idx = subjectOptions.findIndex((o) => o && o.value === wantedSubject);
        if (idx >= 0) {
          subjectIndex = idx;
          subject = wantedSubject;
          subjectLabel = findLabel(subjectOptions, wantedSubject, '全部科目');
        }
      }

      let typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
      let typeIndex = 0;
      let qType = 'all';
      let typeLabel = '全部题型';

      if (subject !== 'all') {
        try {
          const info: any = await api.getSubjectInfo(subject);
          const types = Array.isArray(info?.available_types)
            ? info.available_types
            : Array.isArray(info?.data?.available_types)
              ? info.data.available_types
              : [];
          typeOptions = buildOptions(types.length ? types : FALLBACK_TYPES, '全部题型');
        } catch (e) {
          typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
        }
      }

      const wantedType = String(this.data.preselectType || '').trim();
      if (wantedType && wantedType !== 'all') {
        const idx = typeOptions.findIndex((o) => o && o.value === wantedType);
        if (idx >= 0) {
          typeIndex = idx;
          qType = wantedType;
          typeLabel = findLabel(typeOptions, wantedType, '全部题型');
        }
      }

      this.setData(
        {
          subjectOptions,
          subjectIndex,
          subject,
          subjectLabel,
          typeOptions,
          typeIndex,
          qType,
          typeLabel
        },
        () => {
          if (this.data.keyword) this.onSearch();
        }
      );
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '初始化失败', icon: 'none' });
    }
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onKeywordInput(e: any) {
    this.setData({ keyword: String(e?.detail?.value || '') });
  },

  onClearKeyword() {
    this.setData({ keyword: '' });
  },

  onToggleAdvanced() {
    this.setData({ advancedOpen: !this.data.advancedOpen });
  },

  async onSubjectPicker(e: any) {
    const idx = Number(e?.detail?.value || 0);
    const options = this.data.subjectOptions || [];
    const picked = options[idx] ? options[idx].value : 'all';
    const subject = picked || 'all';

    this.setData({
      subjectIndex: idx,
      subject,
      subjectLabel: findLabel(options, subject, '全部科目'),
      qType: 'all',
      typeIndex: 0,
      typeLabel: '全部题型'
    });

    if (subject === 'all') {
      const typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
      this.setData({ typeOptions });
      return;
    }

    try {
      const info: any = await api.getSubjectInfo(subject);
      const types = Array.isArray(info?.available_types) ? info.available_types : Array.isArray(info?.data?.available_types) ? info.data.available_types : [];
      const typeOptions = buildOptions(types.length ? types : FALLBACK_TYPES, '全部题型');
      this.setData({ typeOptions });
    } catch (e) {
      const typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
      this.setData({ typeOptions });
    }
  },

  onTypePicker(e: any) {
    const idx = Number(e?.detail?.value || 0);
    const options = this.data.typeOptions || [];
    const picked = options[idx] ? options[idx].value : 'all';
    const qType = picked || 'all';
    this.setData({
      typeIndex: idx,
      qType,
      typeLabel: findLabel(options, qType, '全部题型')
    });
  },

  onSearch() {
    const kw = String(this.data.keyword || '').trim();
    if (!kw) {
      wx.showToast({ title: '请输入关键词', icon: 'none' });
      return;
    }
    this.loadResults(true);
  },

  async loadResults(reset = false) {
    if (this.data.loading) return;
    const keyword = String(this.data.keyword || '').trim();
    if (!keyword) return;

    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true });

    try {
      const params: any = { keyword, page, per_page: this.data.per_page };
      if (this.data.subject && this.data.subject !== 'all') params.subject = this.data.subject;
      if (this.data.qType && this.data.qType !== 'all') params.q_type = this.data.qType;

      const result: any = await api.searchQuestions(params);
      const list = Array.isArray(result?.questions) ? result.questions : [];
      const next = reset ? list : (this.data.questions || []).concat(list);

      this.setData({
        questions: next,
        total: Number(result?.total || 0) || 0,
        page: page + 1,
        hasMore: list.length === this.data.per_page,
        searched: true,
        loading: false
      });
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '搜索失败', icon: 'none' });
      this.setData({ loading: false, searched: true });
    }
  },

  onPullDownRefresh() {
    this.loadResults(true)
      .catch(() => {})
      .then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadResults(false);
    }
  },

  noop() {},

  onDetailClose() {
    this.activeDetailReqId = Number(this.activeDetailReqId || 0) + 1;
    this.setData({ detailOpen: false });
  },

  onDetailRetry() {
    const id = Number(this.data.detailQuestionId || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    this.openQuestionDetail(id, true);
  },

  onDetailGoQuiz() {
    const id = Number(this.data.detailQuestionId || 0);
    if (!Number.isFinite(id) || id <= 0) return;

    const subject = String(this.data.detailQuestion?.subject || this.data.detailSubjectFromList || '').trim();
    if (!subject) {
      wx.showToast({ title: '缺少科目信息，无法跳转', icon: 'none' });
      return;
    }

    const qType = String(this.data.detailQuestion?.q_type || this.data.detailQTypeFromList || '').trim();

    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(subject)}`);
    params.push('mode=reinforce');
    params.push(`ids=${encodeURIComponent(String(id))}`);
    if (qType && qType !== 'all') params.push(`type=${encodeURIComponent(qType)}`);
    params.push(`start_id=${id}`);

    this.onDetailClose();
    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  },

  prepareQuestionDetail(raw: any) {
    const q: any = raw || {};
    const qType = (q.q_type || '').toString();

    let displayContent = (q.content || '').toString();
    if (qType === '填空题') {
      displayContent = displayContent.replace(/__/g, '____');
    }
    const contentIsCode = looksLikeCode(displayContent);
    if (contentIsCode) displayContent = preserveSpacesForCode(displayContent);

    const rawExplanation = (q.explanation || '').toString();
    const explanationIsCode = looksLikeCode(rawExplanation);
    const displayExplanation = explanationIsCode ? preserveSpacesForCode(rawExplanation) : rawExplanation;

    const rawAnswer = (q.answer || '').toString();
    const displayAnswer = formatAnswerForDisplay(qType, rawAnswer);

    const detailQuestion = Object.assign({}, q, {
      displayContent,
      contentIsCode,
      displayAnswer,
      displayExplanation,
      explanationIsCode
    });

    const detailOptions = Array.isArray(q.options)
      ? q.options
          .map((opt: any) => ({
            key: (opt && opt.key != null ? String(opt.key) : '').trim(),
            value: opt && opt.value != null ? String(opt.value) : ''
          }))
          .filter((opt: any) => opt && (opt.key || opt.value))
      : [];

    const detailImages = normalizeImageUrls(q.image_path);

    return { detailQuestion, detailOptions, detailImages };
  },

  async openQuestionDetail(questionId: number, forceReload = false, meta?: { subject?: string; qType?: string }) {
    const id = Number(questionId || 0);
    if (!Number.isFinite(id) || id <= 0) return;

    this.activeDetailReqId = Number(this.activeDetailReqId || 0) + 1;
    const reqId = this.activeDetailReqId;

    const subjectFromList =
      meta && typeof meta.subject === 'string'
        ? meta.subject
        : String(this.data.detailSubjectFromList || '');
    const qTypeFromList =
      meta && typeof meta.qType === 'string'
        ? meta.qType
        : String(this.data.detailQTypeFromList || '');

    this.setData({
      detailOpen: true,
      detailLoading: true,
      detailError: '',
      detailQuestionId: id,
      detailSubjectFromList: subjectFromList,
      detailQTypeFromList: qTypeFromList,
      detailQuestion: null,
      detailOptions: [],
      detailImages: []
    });

    if (!forceReload && questionDetailCache.has(id)) {
      const cached = questionDetailCache.get(id);
      this.setData({ detailLoading: false, ...(cached || {}) });
      return;
    }

    try {
      const q: any = await api.getQuestionDetail(id);
      const prepared = this.prepareQuestionDetail(q);
      questionDetailCache.set(id, prepared);
      if (reqId !== this.activeDetailReqId) return;
      this.setData({ detailLoading: false, ...prepared });
    } catch (e: any) {
      if (reqId !== this.activeDetailReqId) return;
      this.setData({ detailLoading: false, detailError: (e && e.message) || '加载失败' });
    }
  },

  onResultTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;

    const subject = String(e?.currentTarget?.dataset?.subject || '').trim();
    const qType = String(e?.currentTarget?.dataset?.qtype || '').trim();

    this.openQuestionDetail(id, false, { subject, qType });
  }
});
