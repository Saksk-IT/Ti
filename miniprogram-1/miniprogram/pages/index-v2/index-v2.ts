import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager, ThemeMode } from '../../utils/theme';
import { requestStateBehavior } from './behaviors/request-state';
import { createSetDataBatcher } from './utils/set-data-batcher';
import {
  QUICK_PRESETS,
  SYSTEM_TEMPLATES,
  FALLBACK_PUBLIC_Q_TYPES,
  DEFAULT_PICKED_TYPES,
  qTypesCache,
  clampInt,
  clampFloat,
  formatNum,
  todayStamp,
  setDataAsync,
  uniqueBanks,
  buildSubjectOptions,
  buildBankOptions,
  findOptionLabel,
  normalizeTemplateConfig,
  buildTemplateScopeLabel,
  distributeCounts,
  type TabKey,
  type ExamSource,
  type SystemTemplate,
  type Option,
  type BankMeta,
  type ExamTypeRow,
  type ExamScope,
  type ExamConfig,
  type UserTemplate,
  type UserTemplateCard
} from './modules/index-v2-helpers';

let examPresetApplied = false;
Page({
  behaviors: [requestStateBehavior],
  data: {
    tab: 'new' as TabKey,
    inited: false,
    bootstrapping: false,

    subjectOptions: [] as Option<string>[],
    bankOptions: [] as Option<number>[],

    examSource: 'public' as ExamSource,
    examSubject: 'all',
    examSubjectLabel: '全部科目',
    examSubjectIndex: 0,
    examBankId: null as number | null,
    examBankLabel: '请选择题库',
    examBankIndex: 0,
    examDuration: 60,
    examTargetTotal: 30,
    quickPresets: QUICK_PRESETS,

    examTypes: [] as ExamTypeRow[],
    examLoading: false,
    examCreating: false,
    examStartDisabled: true,
    examMsg: '',
    examMsgKind: '' as '' | 'error',

    examSumScope: '-',
    examSumDuration: '-',
    examSumAssigned: '-',
    examSumScore: '-',
    examSumTypes: [] as Array<{ name: string; meta: string; subtotal: string }>,

    tplSource: 'public' as ExamSource,
    tplSubject: 'all',
    tplSubjectLabel: '全部科目',
    tplSubjectIndex: 0,
    tplBankId: null as number | null,
    tplBankLabel: '请选择题库',
    tplBankIndex: 0,

    systemTemplates: SYSTEM_TEMPLATES,
    userTemplateCards: [] as UserTemplateCard[],
    userTemplateConfigById: {} as Record<string, ExamConfig>,
    userTemplatesLoaded: false,
    templatesLoading: false,
    templateMsg: '',
    templateMsgKind: '' as '' | 'error',

    saveModalOpen: false,
    saveTemplateTitle: '',
    savingTemplate: false,

    // === 考试记录（tab=records） ===
    recordsSource: 'all' as 'all' | 'public' | 'user_bank',
    recordsSubject: 'all',
    recordsSubjectLabel: '全部科目',
    recordsSubjectIndex: 0,

    recordsBankOptions: [] as Option<number>[],
    recordsBankId: 0,
    recordsBankLabel: '全部题库',
    recordsBankIndex: 0,

    recordsSizeOptions: [
      { value: 10, label: '10/页' },
      { value: 20, label: '20/页' },
      { value: 50, label: '50/页' }
    ] as Array<Option<number>>,
    recordsSize: 10,
    recordsSizeIndex: 0,
    recordsSizeLabel: '10/页',
    recordsPage: 1,
    recordsTotal: 0,
    recordsTotalPages: 1,
    recordsOngoing: [] as Record<string, unknown>[],
    recordsSubmitted: [] as Record<string, unknown>[],
    recordsLoading: false,
    recordsMsg: '',
    recordsMsgKind: '' as '' | 'error',

    // === 考试数据（tab=data） ===
    statsLoading: false,
    statsLoaded: false,
    statsOverview: {
      submitted_count: 0,
      avg_score: 0,
      avg_accuracy: 0,
      last7_count: 0,
      last7_avg_accuracy: 0
    },
    recentExams: [] as Record<string, unknown>[],
    typeDist: [] as Record<string, unknown>[],
    statsFilterKey: '',
    statsScopeText: '',
    statsAdvice: [] as Array<{ title: string; content: string }>,
    statsMsg: '',
    statsMsgKind: '' as '' | 'error'
  },
  setDataBatcher: null as null | ((patch: Record<string, any>, callback?: () => void, options?: { immediate?: boolean }) => void),

  ensureSetDataBatcher() {
    if ((this as any).setDataBatcher) return;
    (this as any).setDataBatcher = createSetDataBatcher(this.setData.bind(this));
  },

  patchData(patch: Record<string, any>, callback?: () => void, immediate: boolean = false) {
    this.ensureSetDataBatcher();
    const fn = (this as any).setDataBatcher;
    if (typeof fn === 'function') {
      fn(patch, callback, { immediate });
      return;
    }
    this.setData(patch, callback);
  },

  onLoad(options: any) {
    this.ensureSetDataBatcher();
    const tab = options && options.tab ? String(options.tab) : '';
    const patch: any = {};
    if (tab === 'templates' || tab === 'new' || tab === 'records' || tab === 'data' || tab === 'settings') {
      patch.tab = tab;
    }

    // exams-select-v2 -> index-v2：tab=new 时，把 source/subject/bank_id 解释为「新建考试」的预选条件
    if (patch.tab === 'new') {
      const navSource = (options?.source || '').toString().trim().toLowerCase();
      if (navSource === 'public' || navSource === 'user_bank') {
        patch.examSource = navSource;
      }

      let navSubject = options?.subject ? String(options.subject) : '';
      if (navSubject) {
        try {
          navSubject = decodeURIComponent(navSubject);
        } catch (e) {}
        patch.examSubject = navSubject;
      }

      const navBankId = Number(options?.bank_id || 0);
      if (Number.isFinite(navBankId) && navBankId > 0) {
        patch.examBankId = navBankId;
      }
    } else if (patch.tab === 'templates') {
      // 题库详情页 -> 考试中心：tab=templates 时，把 source/subject/bank_id 解释为「模板范围」的预选条件
      const tplSource = (options?.source || '').toString().trim().toLowerCase();
      if (tplSource === 'public' || tplSource === 'user_bank') {
        patch.tplSource = tplSource;
      }

      let tplSubject = options?.subject ? String(options.subject) : '';
      if (tplSubject) {
        try {
          tplSubject = decodeURIComponent(tplSubject);
        } catch (e) {}
        patch.tplSubject = tplSubject;
      }

      const tplBankId = Number(options?.bank_id || 0);
      if (Number.isFinite(tplBankId) && tplBankId > 0) {
        patch.tplBankId = tplBankId;
      }
    } else {
      // 兼容 Web /exams?tab=records 的 query：source/subject/bank_id/page/size
      const recSource = (options?.source || '').toString().trim().toLowerCase();
      if (recSource === 'all' || recSource === 'public' || recSource === 'user_bank') {
        patch.recordsSource = recSource;
      }

      let recSubject = options?.subject ? String(options.subject) : '';
      if (recSubject) {
        try {
          recSubject = decodeURIComponent(recSubject);
        } catch (e) {}
        patch.recordsSubject = recSubject;
      }

      const recBankId = Number(options?.bank_id || 0);
      if (Number.isFinite(recBankId) && recBankId > 0) {
        patch.recordsBankId = recBankId;
      }

      const recPage = clampInt(options?.page, 1, 1, 9999);
      if (recPage > 1) patch.recordsPage = recPage;

      const recSize = clampInt(options?.size, 10, 5, 50);
      if (recSize === 10 || recSize === 20 || recSize === 50) {
        patch.recordsSize = recSize;
      }
    }

    if (Object.keys(patch).length) {
      this.patchData(patch, undefined, true);
    }
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.patchData(themeManager.getPageData(), undefined, true);
    } catch (e) {}

    if (!this.data.inited && !this.data.bootstrapping) {
      this.bootstrap();
    }
  },

  async bootstrap() {
    this.patchData({ bootstrapping: true });
    try {
      const [subjectsRes, myBanksRes, sharedBanksRes] = await Promise.all([
        api.getSubjects(),
        api.getMyBanks().catch(() => ({ banks: [] })),
        api.getSharedBanks().catch(() => ({ banks: [] }))
      ]);

      const subjectListRaw = (subjectsRes as Record<string, unknown>)?.subjects || [];
      const subjects = Array.isArray(subjectListRaw)
        ? subjectListRaw.filter((x: any) => typeof x === 'string' && x.trim()).map((s: any) => String(s).trim())
        : [];
      const subjectOptions = buildSubjectOptions(subjects);

      const banks = uniqueBanks([...(myBanksRes as Record<string, unknown>)?.banks as unknown[] || [], ...(sharedBanksRes as Record<string, unknown>)?.banks as unknown[] || []]);
      const bankOptions = buildBankOptions(banks);
      const firstBankId = bankOptions.length ? bankOptions[0].value : null;
      const recordsBankOptions: Option<number>[] = [{ value: 0, label: '全部题库' }, ...bankOptions];
      const sizeList = [10, 20, 50];
      const wantedSize = sizeList.includes(Number(this.data.recordsSize)) ? Number(this.data.recordsSize) : 10;
      const wantedSizeIndex = Math.max(0, sizeList.indexOf(wantedSize));
      const wantedSizeLabel = wantedSize === 50 ? '50/页' : wantedSize === 20 ? '20/页' : '10/页';
      const firstBankLabel = bankOptions.length ? bankOptions[0].label : '请选择题库';

      // exams-select-v2 导航预设：优先沿用 onLoad 写入的数据
      const desiredExamSource: ExamSource = this.data.examSource === 'user_bank' ? 'user_bank' : 'public';
      let desiredExamSubject = String(this.data.examSubject || 'all').trim() || 'all';
      if (desiredExamSource === 'public') {
        const exists = subjectOptions.some((o) => o.value === desiredExamSubject);
        if (!exists) desiredExamSubject = 'all';
      } else {
        desiredExamSubject = 'all';
      }
      const desiredExamSubjectIndex = Math.max(0, subjectOptions.findIndex((o) => o.value === desiredExamSubject));
      const desiredExamSubjectLabel = findOptionLabel(subjectOptions, desiredExamSubject, '全部科目');

      let desiredExamBankId: number | null = firstBankId;
      const wantedBankId = this.data.examBankId != null ? Number(this.data.examBankId) : null;
      if (wantedBankId != null && Number.isFinite(wantedBankId)) {
        const exists = bankOptions.some((o) => o.value === wantedBankId);
        if (exists) desiredExamBankId = wantedBankId;
      }
      const desiredExamBankIndex =
        desiredExamBankId != null ? Math.max(0, bankOptions.findIndex((o) => o.value === desiredExamBankId)) : 0;
      const desiredExamBankLabel = desiredExamBankId != null ? findOptionLabel(bankOptions, desiredExamBankId, firstBankLabel) : '请选择题库';

      // 题库详情页 -> 考试中心：模板范围预设（优先沿用 onLoad 写入的数据）
      const desiredTplSource: ExamSource = this.data.tplSource === 'user_bank' ? 'user_bank' : 'public';
      let desiredTplSubject = String(this.data.tplSubject || 'all').trim() || 'all';
      if (desiredTplSource === 'public') {
        const exists = subjectOptions.some((o) => o.value === desiredTplSubject);
        if (!exists) desiredTplSubject = 'all';
      } else {
        desiredTplSubject = 'all';
      }
      const desiredTplSubjectIndex = Math.max(0, subjectOptions.findIndex((o) => o.value === desiredTplSubject));
      const desiredTplSubjectLabel = findOptionLabel(subjectOptions, desiredTplSubject, '全部科目');

      let desiredTplBankId: number | null = firstBankId;
      const wantedTplBankId = this.data.tplBankId != null ? Number(this.data.tplBankId) : null;
      if (wantedTplBankId != null && Number.isFinite(wantedTplBankId)) {
        const exists = bankOptions.some((o) => o.value === wantedTplBankId);
        if (exists) desiredTplBankId = wantedTplBankId;
      }
      const desiredTplBankIndex =
        desiredTplBankId != null ? Math.max(0, bankOptions.findIndex((o) => o.value === desiredTplBankId)) : 0;
      const desiredTplBankLabel = desiredTplBankId != null ? findOptionLabel(bankOptions, desiredTplBankId, firstBankLabel) : firstBankLabel;

      await setDataAsync(this, {
        inited: true,
        subjectOptions,
        bankOptions,
        recordsBankOptions,
        recordsSize: wantedSize,
        recordsSizeIndex: wantedSizeIndex,
        recordsSizeLabel: wantedSizeLabel,
        examSource: desiredExamSource,
        examSubject: desiredExamSubject,
        examSubjectLabel: desiredExamSubjectLabel,
        examSubjectIndex: desiredExamSubjectIndex,
        examBankId: desiredExamBankId,
        examBankLabel: desiredExamBankLabel,
        examBankIndex: desiredExamBankIndex,
        tplSource: desiredTplSource,
        tplSubject: desiredTplSubject,
        tplSubjectLabel: desiredTplSubjectLabel,
        tplSubjectIndex: desiredTplSubjectIndex,
        tplBankId: desiredTplBankId,
        tplBankLabel: desiredTplBankLabel,
        tplBankIndex: desiredTplBankIndex
      });

      await this.reloadExamTypes();
      this.syncRecordsFilters();
      if (this.data.tab === 'templates') this.loadUserTemplates();
      if (this.data.tab === 'records') this.loadExamRecords(true);
      if (this.data.tab === 'data') this.loadExamStats();
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '初始化失败', icon: 'none' });
    } finally {
      this.patchData({ bootstrapping: false }, undefined, true);
    }
  },

  stopTap() {},

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.patchData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onGoNewTab() {
    this.patchData({ tab: 'new' });
  },

  onGoTemplatesTab() {
    this.patchData({ tab: 'templates' }, () => {
      this.loadUserTemplates();
    });
  },

  onTabTap(e: any) {
    const tab = e?.currentTarget?.dataset?.tab;
    if (!tab || tab === this.data.tab) return;
    this.patchData({ tab }, () => {
      if (tab === 'templates') this.loadUserTemplates();
      if (tab === 'records') this.loadExamRecords(true);
      if (tab === 'data') this.loadExamStats();
    });
  },

  // === records（考试记录）===
  setRecordsMsg(text: string, kind: '' | 'error' = '') {
    this.patchData({ recordsMsg: String(text || ''), recordsMsgKind: kind });
  },

  syncRecordsFilters() {
    const subjectOptions = this.data.subjectOptions || [];
    const bankOptions = this.data.recordsBankOptions || [];

    let recordsSource: any = String(this.data.recordsSource || 'all').toLowerCase();
    if (recordsSource !== 'all' && recordsSource !== 'public' && recordsSource !== 'user_bank') recordsSource = 'all';

    let recordsSubject = String(this.data.recordsSubject || 'all');
    if (recordsSource === 'user_bank') recordsSubject = 'all';
    const subjectIdx = Math.max(0, subjectOptions.findIndex((o) => o && o.value === recordsSubject));
    const subjectOpt = subjectOptions[subjectIdx] || subjectOptions[0] || { value: 'all', label: '全部科目' };
    recordsSubject = subjectOpt.value;
    const recordsSubjectLabel = subjectOpt.label || '全部科目';

    let recordsBankId = Number(this.data.recordsBankId || 0);
    if (!Number.isFinite(recordsBankId) || recordsBankId < 0) recordsBankId = 0;
    if (recordsSource === 'public') recordsBankId = 0;
    const bankIdx = Math.max(0, bankOptions.findIndex((o) => o && o.value === recordsBankId));
    const bankOpt = bankOptions[bankIdx] || bankOptions[0] || { value: 0, label: '全部题库' };
    recordsBankId = bankOpt.value;
    const recordsBankLabel = bankOpt.label || '全部题库';

    const sizeList = [10, 20, 50];
    let recordsSize = Number(this.data.recordsSize || 10);
    if (!sizeList.includes(recordsSize)) recordsSize = 10;
    const recordsSizeIndex = Math.max(0, sizeList.indexOf(recordsSize));
    const recordsSizeLabel = recordsSize === 50 ? '50/页' : recordsSize === 20 ? '20/页' : '10/页';

    const total = Math.max(0, Number(this.data.recordsTotal || 0) || 0);
    const totalPages = Math.max(1, Math.ceil(total / Math.max(1, recordsSize)));
    const recordsTotalPages = totalPages;
    const recordsPage = clampInt(this.data.recordsPage, 1, 1, totalPages);

    this.patchData({
      recordsSource,
      recordsSubject,
      recordsSubjectIndex: subjectIdx,
      recordsSubjectLabel,
      recordsBankId,
      recordsBankIndex: bankIdx,
      recordsBankLabel,
      recordsSize,
      recordsSizeIndex,
      recordsSizeLabel,
      recordsTotalPages,
      recordsPage
    });
  },

  onRecordsSourceTap(e: any) {
    const source = String(e?.currentTarget?.dataset?.source || '').trim().toLowerCase();
    if (source !== 'all' && source !== 'public' && source !== 'user_bank') return;
    if (source === this.data.recordsSource) return;
    this.patchData({ recordsSource: source, recordsPage: 1 }, () => {
      this.syncRecordsFilters();
      if (this.data.tab === 'records') this.loadExamRecords(true);
      if (this.data.tab === 'data') this.loadExamStats(true);
    });
  },

  onRecordsSubjectPicker(e: any) {
    if (this.data.recordsSource === 'user_bank') return;
    const idx = Number(e?.detail?.value);
    const subjectOptions = this.data.subjectOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
    const opt = subjectOptions[safeIdx];
    if (!opt) return;
    this.patchData(
      {
        recordsSubjectIndex: safeIdx,
        recordsSubject: opt.value,
        recordsSubjectLabel: opt.label,
        recordsPage: 1
      },
      () => {
        if (this.data.tab === 'records') this.loadExamRecords(true);
        if (this.data.tab === 'data') this.loadExamStats(true);
      }
    );
  },

  onRecordsBankPicker(e: any) {
    if (this.data.recordsSource === 'public') return;
    const idx = Number(e?.detail?.value);
    const bankOptions = this.data.recordsBankOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
    const opt = bankOptions[safeIdx];
    if (!opt) return;
    this.patchData(
      {
        recordsBankIndex: safeIdx,
        recordsBankId: opt.value,
        recordsBankLabel: opt.label,
        recordsPage: 1
      },
      () => {
        if (this.data.tab === 'records') this.loadExamRecords(true);
        if (this.data.tab === 'data') this.loadExamStats(true);
      }
    );
  },

  onRecordsSizePicker(e: any) {
    const idx = Number(e?.detail?.value);
    const options = this.data.recordsSizeOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(options.length - 1, idx)) : 0;
    const opt = options[safeIdx];
    if (!opt) return;
    this.patchData(
      { recordsSizeIndex: safeIdx, recordsSize: opt.value, recordsSizeLabel: opt.label, recordsPage: 1 },
      () => this.loadExamRecords(true)
    );
  },

  onRecordsPrevPage() {
    if (this.data.recordsLoading) return;
    const p = clampInt(this.data.recordsPage, 1, 1, 9999);
    if (p <= 1) return;
    this.patchData({ recordsPage: p - 1 }, () => this.loadExamRecords(false));
  },

  onRecordsNextPage() {
    if (this.data.recordsLoading) return;
    const p = clampInt(this.data.recordsPage, 1, 1, 9999);
    const totalPages = clampInt(this.data.recordsTotalPages, 1, 1, 9999);
    if (p >= totalPages) return;
    this.patchData({ recordsPage: p + 1 }, () => this.loadExamRecords(false));
  },

  async loadExamRecords(resetPage: boolean = false) {
    if (this.data.recordsLoading) return;
    const page = resetPage ? 1 : clampInt(this.data.recordsPage, 1, 1, 9999);
    const size = clampInt(this.data.recordsSize, 10, 5, 50);
    if (resetPage && this.data.recordsPage !== 1) this.patchData({ recordsPage: 1 }, undefined, true);

    this.patchData({ recordsLoading: true });
    this.setRecordsMsg('', '');

    try {
      const params: any = {
        source: this.data.recordsSource || 'all',
        page,
        size
      };

      if (this.data.recordsSource !== 'user_bank' && this.data.recordsSubject && this.data.recordsSubject !== 'all') {
        params.subject = this.data.recordsSubject;
      }
      if (this.data.recordsSource !== 'public' && Number(this.data.recordsBankId || 0) > 0) {
        params.bank_id = Number(this.data.recordsBankId);
      }

      const res: any = await api.getExamRecords(params);
      const ongoing = Array.isArray(res?.ongoing) ? res.ongoing : [];
      const submitted = Array.isArray(res?.submitted) ? res.submitted : [];
      const total = Number(res?.total || 0) || 0;
      const page = clampInt(res?.page, params.page, 1, 9999);
      const size = clampInt(res?.size, params.size, 5, 50);
      const totalPages = Math.max(1, Math.ceil(total / Math.max(1, size)));

      this.patchData({
        recordsOngoing: ongoing,
        recordsSubmitted: submitted,
        recordsTotal: total,
        recordsPage: clampInt(page, 1, 1, totalPages),
        recordsSize: size,
        recordsTotalPages: totalPages,
        recordsLoading: false
      });
      this.syncRecordsFilters();
    } catch (e: any) {
      this.patchData({
        recordsOngoing: [],
        recordsSubmitted: [],
        recordsTotal: 0,
        recordsTotalPages: 1,
        recordsLoading: false
      });
      this.syncRecordsFilters();
      this.setRecordsMsg((e && e.message) || '获取考试记录失败', 'error');
    }
  },

  onExamContinueTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${id}` });
  },

  onExamDetailTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${id}` });
  },

  onExamToMistakesTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    wx.showLoading({ title: '处理中…' });
    api
      .examToMistakes(id)
      .then((res: any) => {
        wx.hideLoading();
        const cnt = Number(res?.count || 0) || 0;
        wx.showToast({ title: cnt ? `已加入 ${cnt} 题` : '已加入错题本', icon: 'none' });
      })
      .catch((err: any) => {
        wx.hideLoading();
        wx.showToast({ title: (err && err.message) || '操作失败', icon: 'none' });
      });
  },

  onExamDeleteTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;

    wx.showModal({
      title: '删除考试',
      content: `确定删除考试 #${id} 吗？`,
      confirmText: '删除',
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (!res.confirm) return;
        wx.showLoading({ title: '删除中…' });
        try {
          await api.deleteExam(id);
          wx.hideLoading();
          wx.showToast({ title: '已删除', icon: 'success' });
          this.loadExamRecords(true);
        } catch (err: any) {
          wx.hideLoading();
          wx.showToast({ title: (err && err.message) || '删除失败', icon: 'none' });
        }
      }
    });
  },

  // === data（考试数据）===
  setStatsMsg(text: string, kind: '' | 'error' = '') {
    this.patchData({ statsMsg: String(text || ''), statsMsgKind: kind });
  },

  async loadExamStats(force: boolean = false) {
    if (this.data.statsLoading) return;

    const params: any = { source: this.data.recordsSource || 'all' };
    if (params.source !== 'user_bank' && this.data.recordsSubject && this.data.recordsSubject !== 'all') {
      params.subject = this.data.recordsSubject;
    }
    const bankId = Number(this.data.recordsBankId || 0) || 0;
    if (params.source !== 'public' && bankId > 0) {
      params.bank_id = bankId;
    }

    const statsScopeText = (() => {
      const src = String(params.source || 'all');
      const srcLabel = src === 'public' ? '公共题库' : src === 'user_bank' ? '个人题库' : '全部';
      const subjectLabel = String(this.data.recordsSubjectLabel || '全部科目');
      const bankLabel = String(this.data.recordsBankLabel || '全部题库');
      if (src === 'public') return `${srcLabel} · ${subjectLabel}`;
      if (src === 'user_bank') return `${srcLabel} · ${bankLabel}`;
      return `${srcLabel} · ${subjectLabel} · ${bankLabel}`;
    })();

    const filterKey = JSON.stringify(params);
    if (this.data.statsLoaded && !force && this.data.statsFilterKey === filterKey) return;
    this.patchData({ statsLoading: true });
    this.setStatsMsg('', '');

    try {
      const res: any = await api.getExamStats(params);
      const statsOverview = res?.stats_overview || {};
      const recentExams = Array.isArray(res?.recent_exams) ? res.recent_exams : [];
      const typeDist = Array.isArray(res?.type_dist) ? res.type_dist : [];
      const statsAdvice = Array.isArray(res?.advice)
        ? res.advice
            .map((a: any) => ({ title: String(a?.title || '').trim(), content: String(a?.content || '').trim() }))
            .filter((a: any) => a.title && a.content)
        : [];

      this.patchData({
        statsOverview,
        recentExams,
        typeDist,
        statsFilterKey: filterKey,
        statsScopeText,
        statsAdvice,
        statsLoaded: true,
        statsLoading: false
      });
    } catch (e: any) {
      this.patchData({
        statsOverview: {
          submitted_count: 0,
          avg_score: 0,
          avg_accuracy: 0,
          last7_count: 0,
          last7_avg_accuracy: 0
        },
        recentExams: [],
        typeDist: [],
        statsFilterKey: filterKey,
        statsScopeText,
        statsAdvice: [],
        statsLoaded: true,
        statsLoading: false
      });
      this.setStatsMsg((e && e.message) || '获取考试数据失败', 'error');
    }
  },

  getExamScope(): ExamScope {
    return {
      source: this.data.examSource,
      subject: this.data.examSubject || 'all',
      bank_id: this.data.examBankId
    };
  },

  getTplScope(): ExamScope {
    return {
      source: this.data.tplSource,
      subject: this.data.tplSubject || 'all',
      bank_id: this.data.tplBankId
    };
  },

  async getQTypesForScope(scope: ExamScope): Promise<string[]> {
    if (scope.source === 'user_bank') {
      if (!scope.bank_id) return [];
      const key = `bank:${scope.bank_id}`;
      if (qTypesCache.has(key)) return (qTypesCache.get(key) || []).slice();
      try {
        const res: any = await api.getBankDetail(scope.bank_id);
        const arr = Array.isArray(res?.available_types) ? res.available_types : [];
        const qTypes = arr.filter((x: any) => typeof x === 'string' && x.trim()).map((s: any) => String(s).trim());
        qTypesCache.set(key, qTypes);
        return qTypes.slice();
      } catch (e) {
        qTypesCache.set(key, []);
        return [];
      }
    }

    if (!scope.subject || scope.subject === 'all') {
      return FALLBACK_PUBLIC_Q_TYPES.slice();
    }

    const key = `subject:${scope.subject}`;
    if (qTypesCache.has(key)) return (qTypesCache.get(key) || []).slice();
    try {
      const info: any = await api.getSubjectInfo(scope.subject);
      const arr = Array.isArray(info?.available_types) ? info.available_types : [];
      const qTypes = arr.filter((x: any) => typeof x === 'string' && x.trim()).map((s: any) => String(s).trim());
      qTypesCache.set(key, qTypes);
      return qTypes.slice();
    } catch (e) {
      qTypesCache.set(key, []);
      return [];
    }
  },

  async reloadExamTypes(opts?: { applyConfig?: ExamConfig }) {
    if (this.data.examLoading) return;
    this.patchData({ examLoading: true, examMsg: '', examMsgKind: '' });

    const scope = this.getExamScope();
    try {
      const qTypes = (await this.getQTypesForScope(scope)).filter(Boolean);
      if (!qTypes.length) {
        this.patchData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
        return;
      }

      const counts = await Promise.all(
        qTypes.map(async (t) => {
          try {
            if (scope.source === 'user_bank') {
              const bankId = scope.bank_id || 0;
              const res: any = await api.getBankUserCounts(bankId, { q_type: t, source: 'all' });
              return { name: t, available: clampInt(res?.total, 0, 0, 999999) };
            }
            const res: any = await api.getQuestionsCount({ subject: scope.subject || 'all', type: t });
            return { name: t, available: clampInt(res?.count, 0, 0, 999999) };
          } catch (e) {
            return { name: t, available: 0 };
          }
        })
      );

      const prevMap = new Map<string, ExamTypeRow>();
      (this.data.examTypes || []).forEach((r) => prevMap.set(r.name, r));

      let rows: ExamTypeRow[] = counts
        .filter((x) => x.available > 0)
        .map((x) => {
          const prev = prevMap.get(x.name);
          const enabled = prev ? !!prev.enabled : false;
          const score = prev ? clampFloat(prev.score, 1, 0, 1000) : 1;
          const count = enabled ? clampInt(prev?.count, 0, 0, x.available) : 0;
          return { name: x.name, enabled, available: x.available, count, score, subtotalText: '0' };
        });

      if (opts?.applyConfig) {
        examPresetApplied = true;
        const cfg = opts.applyConfig;
        rows = rows.map((r) => {
          const want = cfg.types && cfg.types[r.name] != null ? Number(cfg.types[r.name]) : 0;
          const enabled = want > 0;
          const count = enabled ? clampInt(want, 0, 0, r.available) : 0;
          const scoreRaw = cfg.scores && cfg.scores[r.name] != null ? Number(cfg.scores[r.name]) : 1;
          const score = enabled ? clampFloat(scoreRaw, 1, 0, 1000) : 1;
          return { ...r, enabled, count, score };
        });
      }

      rows = this.applyDefaultPresetIfEmpty(rows);
      rows = this.recomputeTypeSubtotals(rows);

      this.patchData({ examTypes: rows, examLoading: false }, () => this.refreshExamSummary());
    } catch (e) {
      this.patchData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
    }
  },

  recomputeTypeSubtotals(rows: ExamTypeRow[]): ExamTypeRow[] {
    return (rows || []).map((r) => {
      const subtotal = r.enabled ? (Number(r.count) || 0) * (Number(r.score) || 0) : 0;
      return { ...r, subtotalText: formatNum(subtotal) };
    });
  },

  applyDefaultPresetIfEmpty(rows: ExamTypeRow[]): ExamTypeRow[] {
    const assigned = (rows || []).reduce((sum, r) => sum + (r.enabled ? Math.max(0, Number(r.count) || 0) : 0), 0);
    if (assigned > 0) return rows;
    if (examPresetApplied) return rows;

    examPresetApplied = true;
    const qTypes = rows.map((r) => r.name);
    const picked = DEFAULT_PICKED_TYPES.filter((t) => qTypes.includes(t));
    const fallbackPicked = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));

    const enabledTypes = rows
      .filter((r) => fallbackPicked.includes(r.name))
      .map((r) => ({ name: r.name, available: r.available }));
    const distributed = distributeCounts(this.data.examTargetTotal, enabledTypes);

    return rows.map((r) => {
      const enabled = fallbackPicked.includes(r.name);
      const count = enabled ? clampInt(distributed[r.name] || 0, 0, 0, r.available) : 0;
      return { ...r, enabled, count, score: 1 };
    });
  },

  refreshExamSummary() {
    const scope = this.getExamScope();
    const rows = this.data.examTypes || [];

    const types: Record<string, number> = {};
    const scores: Record<string, number> = {};
    let assigned = 0;
    let totalScore = 0;

    rows.forEach((r) => {
      if (!r.enabled) return;
      const count = clampInt(r.count, 0, 0, 500);
      const score = clampFloat(r.score, 1, 0, 1000);
      if (count <= 0) return;
      types[r.name] = count;
      scores[r.name] = score;
      assigned += count;
      totalScore += count * score;
    });

    const scopeLabel =
      scope.source === 'user_bank'
        ? `个人题库 · ${this.data.examBankLabel || '未选择'}`
        : `公共题库 · ${scope.subject === 'all' ? '全部科目' : scope.subject}`;

    const examSumTypes = Object.keys(types).map((name) => {
      const count = types[name] || 0;
      const score = scores[name] ?? 1;
      return { name, meta: `${count} × ${formatNum(score)}`, subtotal: formatNum(count * score) };
    });

    const startDisabled = assigned <= 0 || (scope.source === 'user_bank' && !scope.bank_id);

    this.setData({
      examSumScope: scopeLabel,
      examSumDuration: `${clampInt(this.data.examDuration, 60, 1, 1440)} 分钟`,
      examSumAssigned: `${assigned} 题`,
      examSumScore: `${formatNum(totalScore)} 分`,
      examSumTypes,
      examStartDisabled: startDisabled
    });
  },

  // === 新建考试：范围 ===
  async onExamSourceTap(e: any) {
    const source = (e?.currentTarget?.dataset?.source || '').toLowerCase();
    if (source !== 'public' && source !== 'user_bank') return;
    if (source === this.data.examSource) return;

    const next: any = { examSource: source, examMsg: '', examMsgKind: '' };
    if (source === 'user_bank') {
      const bankOptions = this.data.bankOptions || [];
      if (!this.data.examBankId && bankOptions.length) {
        next.examBankId = bankOptions[0].value;
        next.examBankIndex = 0;
        next.examBankLabel = bankOptions[0].label;
      }
    }
    await setDataAsync(this, next);
    await this.reloadExamTypes();
  },

  async onExamSubjectPicker(e: any) {
    const idx = Number(e?.detail?.value);
    const subjectOptions = this.data.subjectOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
    const opt = subjectOptions[safeIdx];
    if (!opt) return;
    await setDataAsync(this, {
      examSubjectIndex: safeIdx,
      examSubject: opt.value,
      examSubjectLabel: opt.label,
      examMsg: '',
      examMsgKind: ''
    });
    await this.reloadExamTypes();
  },

  async onExamBankPicker(e: any) {
    const idx = Number(e?.detail?.value);
    const bankOptions = this.data.bankOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
    const opt = bankOptions[safeIdx];
    if (!opt) return;
    await setDataAsync(this, {
      examBankIndex: safeIdx,
      examBankId: opt.value,
      examBankLabel: opt.label,
      examMsg: '',
      examMsgKind: ''
    });
    await this.reloadExamTypes();
  },

  onExamDurationInput(e: any) {
    const duration = clampInt(e?.detail?.value, 60, 1, 1440);
    this.setData({ examDuration: duration }, () => this.refreshExamSummary());
  },

  onExamTargetTotalInput(e: any) {
    const total = clampInt(e?.detail?.value, 30, 1, 300);
    this.setData({ examTargetTotal: total }, () => this.refreshExamSummary());
  },

  // === 新建考试：题型与分值 ===
  onTypeToggleTap(e: any) {
    const name = e?.currentTarget?.dataset?.name;
    if (!name) return;
    const next = (this.data.examTypes || []).map((r) => {
      if (r.name !== name) return r;
      const enabled = !r.enabled;
      return { ...r, enabled, count: enabled ? r.count : 0 };
    });
    this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () =>
      this.refreshExamSummary()
    );
  },

  onTypeCountInput(e: any) {
    const name = e?.currentTarget?.dataset?.name;
    if (!name) return;
    const next = (this.data.examTypes || []).map((r) => {
      if (r.name !== name) return r;
      const count = clampInt(e?.detail?.value, 0, 0, r.available);
      return { ...r, count };
    });
    this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () =>
      this.refreshExamSummary()
    );
  },

  onTypeScoreInput(e: any) {
    const name = e?.currentTarget?.dataset?.name;
    if (!name) return;
    const next = (this.data.examTypes || []).map((r) => {
      if (r.name !== name) return r;
      const score = clampFloat(e?.detail?.value, 1, 0, 1000);
      return { ...r, score };
    });
    this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () =>
      this.refreshExamSummary()
    );
  },

  onQuickPresetTap(e: any) {
    const duration = clampInt(e?.currentTarget?.dataset?.duration, 60, 1, 1440);
    const total = clampInt(e?.currentTarget?.dataset?.total, 30, 1, 300);
    this.setData({ examDuration: duration, examTargetTotal: total }, () => {
      this.onAutoDistributeTap();
      this.refreshExamSummary();
    });
  },

  onAutoDistributeTap() {
    const enabledRows = (this.data.examTypes || []).filter((r) => r.enabled);
    if (!enabledRows.length) {
      this.setData({ examMsg: '请先勾选至少一种题型，再进行均分。', examMsgKind: 'error' }, () => this.refreshExamSummary());
      return;
    }
    const distributed = distributeCounts(
      this.data.examTargetTotal,
      enabledRows.map((r) => ({ name: r.name, available: r.available }))
    );
    const next = (this.data.examTypes || []).map((r) => {
      if (!r.enabled) return { ...r, count: 0 };
      return { ...r, count: clampInt(distributed[r.name] || 0, 0, 0, r.available) };
    });
    this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () =>
      this.refreshExamSummary()
    );
  },

  onResetScoresTap() {
    const next = (this.data.examTypes || []).map((r) => ({ ...r, score: 1 }));
    this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () =>
      this.refreshExamSummary()
    );
  },

  collectExamConfig(): (ExamConfig & { assigned: number; totalScore: number }) | null {
    const scope = this.getExamScope();
    if (scope.source === 'user_bank' && !scope.bank_id) return null;

    const duration = clampInt(this.data.examDuration, 60, 1, 1440);
    const targetTotal = clampInt(this.data.examTargetTotal, 30, 1, 300);

    const types: Record<string, number> = {};
    const scores: Record<string, number> = {};
    let assigned = 0;
    let totalScore = 0;

    (this.data.examTypes || []).forEach((r) => {
      if (!r.enabled) return;
      const count = clampInt(r.count, 0, 0, 500);
      const score = clampFloat(r.score, 1, 0, 1000);
      if (count <= 0) return;
      types[r.name] = count;
      scores[r.name] = score;
      assigned += count;
      totalScore += count * score;
    });

    return { ...scope, duration, targetTotal, types, scores, assigned, totalScore };
  },

  async onStartExamTap() {
    if (this.data.examCreating || this.data.examLoading) return;
    const cfg = this.collectExamConfig();
    if (!cfg) {
      this.setData({ examMsg: '请选择个人题库。', examMsgKind: 'error' }, () => this.refreshExamSummary());
      return;
    }
    if (!Object.keys(cfg.types).length) {
      this.setData({ examMsg: '请先设置题型与题量。', examMsgKind: 'error' }, () => this.refreshExamSummary());
      return;
    }

    this.setData({ examCreating: true, examMsg: '', examMsgKind: '' });
    wx.showLoading({ title: '创建中…' });
    try {
      const res: any = await api.createExam({
        source: cfg.source,
        subject: cfg.subject,
        bank_id: cfg.bank_id,
        duration: cfg.duration,
        types: cfg.types,
        scores: cfg.scores
      });
      const examId = Number(res?.exam_id);
      if (!Number.isFinite(examId) || examId <= 0) throw new Error('创建考试失败');
      wx.hideLoading();
      this.setData({ examCreating: false });
      wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
    } catch (e: any) {
      wx.hideLoading();
      this.setData({ examCreating: false, examMsg: (e && e.message) || '创建失败', examMsgKind: 'error' }, () =>
        this.refreshExamSummary()
      );
    }
  },

  onOpenSaveTemplate() {
    const cfg = this.collectExamConfig();
    if (!cfg) {
      this.setData({ examMsg: '请选择个人题库。', examMsgKind: 'error' }, () => this.refreshExamSummary());
      return;
    }
    if (!Object.keys(cfg.types).length) {
      this.setData({ examMsg: '请先设置题型与题量。', examMsgKind: 'error' }, () => this.refreshExamSummary());
      return;
    }
    const title = `自定义模板 ${todayStamp()}`;
    this.setData({ saveModalOpen: true, saveTemplateTitle: title });
  },

  onCloseSaveModal() {
    if (this.data.savingTemplate) return;
    this.setData({ saveModalOpen: false, saveTemplateTitle: '' });
  },

  onSaveTemplateTitleInput(e: any) {
    const v = e && e.detail && e.detail.value ? String(e.detail.value) : '';
    this.setData({ saveTemplateTitle: v });
  },

  async onConfirmSaveTemplate() {
    if (this.data.savingTemplate) return;
    const title = String(this.data.saveTemplateTitle || '').trim();
    if (!title) {
      wx.showToast({ title: '模板名称不能为空', icon: 'none' });
      return;
    }

    const cfg = this.collectExamConfig();
    if (!cfg) {
      wx.showToast({ title: '请选择个人题库', icon: 'none' });
      return;
    }
    if (!Object.keys(cfg.types).length) {
      wx.showToast({ title: '请先设置题型与题量', icon: 'none' });
      return;
    }

    this.setData({ savingTemplate: true });
    wx.showLoading({ title: '保存中…' });
    try {
      await api.createExamTemplate({
        title,
        config: {
          source: cfg.source,
          subject: cfg.subject,
          bank_id: cfg.bank_id,
          duration: cfg.duration,
          targetTotal: cfg.targetTotal,
          types: cfg.types,
          scores: cfg.scores
        }
      });
      wx.hideLoading();
      this.setData({ savingTemplate: false, saveModalOpen: false, saveTemplateTitle: '' });
      wx.showToast({ title: '已保存为模板', icon: 'success' });
      this.loadUserTemplates(true);
    } catch (e: any) {
      wx.hideLoading();
      this.setData({ savingTemplate: false });
      wx.showToast({ title: (e && e.message) || '保存失败', icon: 'none' });
    }
  },

  // === 模板：范围 ===
  onTplSourceTap(e: any) {
    const source = (e?.currentTarget?.dataset?.source || '').toLowerCase();
    if (source !== 'public' && source !== 'user_bank') return;
    if (source === this.data.tplSource) return;

    const next: any = { tplSource: source };
    if (source === 'user_bank') {
      const bankOptions = this.data.bankOptions || [];
      if (!this.data.tplBankId && bankOptions.length) {
        next.tplBankId = bankOptions[0].value;
        next.tplBankIndex = 0;
        next.tplBankLabel = bankOptions[0].label;
      }
    }
    this.setData(next);
  },

  onTplSubjectPicker(e: any) {
    const idx = Number(e?.detail?.value);
    const subjectOptions = this.data.subjectOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
    const opt = subjectOptions[safeIdx];
    if (!opt) return;
    this.setData({ tplSubjectIndex: safeIdx, tplSubject: opt.value, tplSubjectLabel: opt.label });
  },

  onTplBankPicker(e: any) {
    const idx = Number(e?.detail?.value);
    const bankOptions = this.data.bankOptions || [];
    const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
    const opt = bankOptions[safeIdx];
    if (!opt) return;
    this.setData({ tplBankIndex: safeIdx, tplBankId: opt.value, tplBankLabel: opt.label });
  },

  setTemplateMsg(text: string, kind: '' | 'error' = '') {
    this.setData({ templateMsg: String(text || ''), templateMsgKind: kind });
  },

  async loadUserTemplates(force: boolean = false) {
    if (this.data.templatesLoading) return;
    if (this.data.userTemplatesLoaded && !force) return;
    this.setData({ templatesLoading: true });
    this.setTemplateMsg('', '');

    try {
      const list = (await api.getExamTemplates()) as UserTemplate[];
      const bankOptions = this.data.bankOptions || [];

      const userTemplateConfigById: Record<string, ExamConfig> = {};
      const userTemplateCards: UserTemplateCard[] = [];

      (Array.isArray(list) ? list : []).forEach((tpl) => {
        const cfg = normalizeTemplateConfig(tpl?.config || {});
        if (!cfg) return;
        const bankLabel = cfg.bank_id ? findOptionLabel(bankOptions, cfg.bank_id, '') : '';
        const scopeLabel = buildTemplateScopeLabel(cfg, bankLabel);

        userTemplateConfigById[String(tpl.id)] = { ...cfg, label: tpl.title || '自定义模板' };
        userTemplateCards.push({
          id: tpl.id,
          title: tpl.title || '未命名模板',
          meta: `${cfg.duration} 分钟 · ${cfg.targetTotal} 题 · ${scopeLabel}`,
          tags: ['我的模板']
        });
      });

      this.setData({
        userTemplateCards,
        userTemplateConfigById,
        userTemplatesLoaded: true,
        templatesLoading: false
      });
    } catch (e: any) {
      this.setData({
        userTemplateCards: [],
        userTemplateConfigById: {},
        userTemplatesLoaded: true,
        templatesLoading: false
      });
      this.setTemplateMsg((e && e.message) || '获取模板失败。', 'error');
    }
  },

  async applyConfigToNew(cfg: ExamConfig) {
    if (!cfg) return;
    if (cfg.source === 'user_bank' && !cfg.bank_id) {
      this.setTemplateMsg('请选择个人题库。', 'error');
      return;
    }

    const subjectOptions = this.data.subjectOptions || [];
    const bankOptions = this.data.bankOptions || [];

    let examSubject = cfg.subject || 'all';
    if (cfg.source === 'public') {
      const exists = subjectOptions.some((o) => o.value === examSubject);
      if (!exists) examSubject = 'all';
    }

    const examBankId = cfg.source === 'user_bank' ? cfg.bank_id : this.data.examBankId;
    if (cfg.source === 'user_bank') {
      const exists = examBankId != null && bankOptions.some((o) => o.value === examBankId);
      if (!exists) {
        this.setTemplateMsg('题库不可用，请先同步/加入该题库。', 'error');
        return;
      }
    }

    const examSubjectIndex = Math.max(0, subjectOptions.findIndex((o) => o.value === examSubject));
    const examBankIndex = examBankId != null ? Math.max(0, bankOptions.findIndex((o) => o.value === examBankId)) : 0;

    const patch: any = {
      tab: 'new',
      examSource: cfg.source,
      examSubject,
      examSubjectIndex,
      examSubjectLabel: findOptionLabel(subjectOptions, examSubject, '全部科目'),
      examBankId,
      examBankIndex,
      examBankLabel: examBankId != null ? findOptionLabel(bankOptions, examBankId, '请选择题库') : '请选择题库',
      examDuration: clampInt(cfg.duration, 60, 1, 1440),
      examTargetTotal: clampInt(cfg.targetTotal, 30, 1, 300),
      examMsg: '',
      examMsgKind: ''
    };

    examPresetApplied = true;
    await setDataAsync(this, patch);
    await this.reloadExamTypes({ applyConfig: cfg });
  },

  async startExamWithConfig(cfg: ExamConfig) {
    if (!cfg) return;
    if (cfg.source === 'user_bank' && !cfg.bank_id) {
      this.setTemplateMsg('请选择个人题库。', 'error');
      return;
    }
    if (!cfg.types || !Object.keys(cfg.types).length) {
      this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
      return;
    }

    wx.showLoading({ title: '创建中…' });
    try {
      const res: any = await api.createExam({
        source: cfg.source,
        subject: cfg.subject,
        bank_id: cfg.bank_id,
        duration: cfg.duration,
        types: cfg.types,
        scores: cfg.scores
      });
      const examId = Number(res?.exam_id);
      if (!Number.isFinite(examId) || examId <= 0) throw new Error('创建考试失败');
      wx.hideLoading();
      wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
    } catch (e: any) {
      wx.hideLoading();
      this.setTemplateMsg((e && e.message) || '创建考试失败，请稍后再试。', 'error');
    }
  },

  async buildSystemTemplateConfig(tpl: SystemTemplate): Promise<ExamConfig | null> {
    const scope = this.getTplScope();
    const qTypes = (await this.getQTypesForScope(scope)).filter(Boolean);
    if (!qTypes.length) return null;

    const preferred = Array.isArray(tpl.preferred) ? tpl.preferred : [];
    const picked = preferred.filter((t) => qTypes.includes(t));
    const selected = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));

    const total = clampInt(tpl.total, 30, 1, 300);
    const base = Math.floor(total / selected.length);
    let rem = total % selected.length;

    const types: Record<string, number> = {};
    const scores: Record<string, number> = {};
    selected.forEach((t) => {
      const count = base + (rem > 0 ? 1 : 0);
      if (rem > 0) rem -= 1;
      types[t] = count;
      scores[t] = 1;
    });

    return {
      source: scope.source,
      subject: scope.subject,
      bank_id: scope.bank_id,
      duration: clampInt(tpl.duration, 45, 1, 1440),
      targetTotal: total,
      types,
      scores,
      label: tpl.title
    };
  },

  async onSystemTemplateApplyTap(e: any) {
    const id = String(e?.currentTarget?.dataset?.id || '');
    const tpl = (this.data.systemTemplates || []).find((t: any) => String(t.id) === id);
    if (!tpl) return;
    this.setTemplateMsg('', '');
    const cfg = await this.buildSystemTemplateConfig(tpl);
    if (!cfg) {
      this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
      return;
    }
    await this.applyConfigToNew(cfg);
  },

  async onSystemTemplateStartTap(e: any) {
    const id = String(e?.currentTarget?.dataset?.id || '');
    const tpl = (this.data.systemTemplates || []).find((t: any) => String(t.id) === id);
    if (!tpl) return;
    this.setTemplateMsg('', '');
    const cfg = await this.buildSystemTemplateConfig(tpl);
    if (!cfg) {
      this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
      return;
    }
    await this.startExamWithConfig(cfg);
  },

  async onUserTemplateApplyTap(e: any) {
    const id = String(e?.currentTarget?.dataset?.id || '');
    const cfg = (this.data.userTemplateConfigById || {})[id];
    if (!cfg) return;
    this.setTemplateMsg('', '');
    await this.applyConfigToNew(cfg);
  },

  async onUserTemplateStartTap(e: any) {
    const id = String(e?.currentTarget?.dataset?.id || '');
    const cfg = (this.data.userTemplateConfigById || {})[id];
    if (!cfg) return;
    this.setTemplateMsg('', '');
    await this.startExamWithConfig(cfg);
  },

  async onUserTemplateDeleteTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id);
    if (!Number.isFinite(id) || id <= 0) return;

    wx.showModal({
      title: '删除模板',
      content: '确定要删除该模板吗？',
      confirmText: '删除',
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (!res.confirm) return;
        wx.showLoading({ title: '删除中…' });
        try {
          await api.deleteExamTemplate(id);
          wx.hideLoading();
          this.loadUserTemplates(true);
        } catch (e: any) {
          wx.hideLoading();
          this.setTemplateMsg((e && e.message) || '删除模板失败。', 'error');
        }
      }
    });
  }
});
