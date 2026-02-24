// quiz.ts - 刷题/背题页面
// 支持公有题库（subject参数）和个人题库（bank_id参数）双数据源
import { api, normalizeImageUrls } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { createSourceFromOptions, IQuizSource } from '../../utils/quiz-source';
import { markdownToRichTextHtml } from '../../utils/markdown';
import { themeManager } from '../../utils/theme';
import { requestStateBehavior } from '../../behaviors/request-state';
import { createSetDataBatcher } from '../../utils/set-data-batcher';
import {
  parseIdList,
  uniqUrls,
  readAIExplainCache,
  writeAIExplainCache,
  stripHtmlToText,
  extractInlineImageUrls,
  type OptionItem,
  type DisplayOption,
  type QuestionType
} from './modules/quiz-helpers';

// 数据源实例（页面级别）
let quizSource: IQuizSource | null = null;
Page({
  behaviors: [requestStateBehavior],
  data: {
    mode: 'quiz',              // 模式：'quiz' | 'memo' | 'reinforce'
    // 数据源信息
    sourceType: '' as 'public' | 'bank' | '',  // 数据源类型
    sourceId: '' as string | number,            // 数据源标识
    displayName: '',                            // 显示名称
    source: 'all',             // 数据范围：all/favorites/mistakes
    qType: 'all',              // 题型筛选（用于进度key）
    tag: 'all',                // 标签筛选（用于进度key & 服务端筛选）
    shuffleQuestions: false,   // 打乱题目（用于进度key）
    shuffleOptions: false,     // 打乱选项（用于进度key & 服务端确定性打乱）
    reinforceKind: '' as '' | 'wrong' | 'similar', // 加强：rk=wrong/similar（仅 mode=reinforce 生效，用于进度隔离）
    reinforceIds: [] as number[],                 // 加强：ids=1,2,3（指定题目列表）
    startId: 0,                // 从搜索等入口指定起始题目ID
    questions: [] as any[],    // 题目列表
    currentIndex: 0,           // 当前题目索引
    currentQuestion: null as any,  // 当前题目对象
    selectedAnswer: '',        // 选中的答案（刷题模式 - 单选题/判断题/填空题）
    selectedAnswers: [] as string[], // 多选题答案数组
    showAnswer: false,         // 是否显示答案（刷题模式）
    isFavorite: false,         // 是否收藏
    isCorrect: false,          // 回答是否正确（刷题模式）
    isJudgable: true,          // 是否可自动判分（主观题为 false）
    loading: false,            // 加载状态
    showQuestionList: false,   // 是否显示题目列表抽屉
    displayOptions: [] as DisplayOption[],
    blankAnswers: [] as string[],
    blankIndexes: [] as number[],
    blankCount: 0,
    showSubmitButton: false,
    submitDisabled: true,
    userAnswerText: '',

    // 刷题设置
    showSettings: false,
    practiceSettings: {
      autoNextOnCorrect: false,   // 答对自动切题（答错不切题）
      autoFavoriteOnWrong: false, // 做错自动收藏
      vibrationFeedback: false    // 答题震动反馈
    },

    // 字体大小（仅影响答题页字体）
    quizFontSize: 'md' as any,    // 'sm' | 'md' | 'lg'
    quizFontClass: 'quiz-font-md' as any,
    themeStyleName: '默认' as any,

    // 主题（深浅/风格）
    isDarkMode: false,
    themeMode: 'system' as any,
    themeClass: '' as any,
    themeStyle: 'default' as any,
    themeStyleClass: '' as any,
    themeCtaColor: '#007AFF' as any,

    // AI 解析
    showAIExplain: false,
    scrollIntoView: '',
    aiLoading: false,
    aiExplainText: '',
    aiExplainRichText: '',
    aiExplainError: '',
    aiExplainQuestionId: 0,

    // 进度信息
    progress: {
      current: 0,              // 当前题号
      total: 0                 // 总题数
    },

    // 答题记录（用于题目列表显示状态）
    answerRecords: {} as Record<number, { answered: boolean; isCorrect: boolean }>,

    // 标签管理
    canEdit: false,                // 是否可以编辑题目
    currentQuestionTags: [] as string[],  // 当前题目的标签
    showTagModal: false,           // 是否显示标签弹窗
    allTags: [] as Array<{ name: string; count: number; selected: boolean }>,  // 所有标签
    newTagName: '',                // 新标签名称输入

    // 编辑题目
    showEditModal: false,          // 是否显示编辑弹窗
    editForm: {
      content: '',
      options: '',
      answer: '',
      explanation: '',
      showOptions: false
    },
    editSaving: false,              // 编辑保存中

    // 滑屏切题
    touchStartX: 0,
    touchStartY: 0,

    // 分页懒加载
    paginationEnabled: false,       // 是否启用分页
    paginationPage: 1,              // 当前已加载页码
    paginationPerPage: 50,          // 每页题数
    paginationTotal: 0,             // 服务端总题数
    paginationHasMore: false,       // 是否还有更多题目
    paginationLoading: false        // 是否正在加载更多
  },

  // === 进度同步（与 Web 端 /api/progress 互通）===
  progressKey: '' as any,
  progressStatusMap: {} as any,
  progressAnswerMap: {} as any,
  progressOrder: null as any,
  saveProgressTimer: null as any,
  syncPending: false as any,
  lastSavedPayload: null as any,
  practiceSettingsKey: 'quiz_practice_settings_v1' as any,
  quizFontSizeKey: 'quiz_font_size_v1' as any,
  sessionStartedAt: 0 as any,
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

  onShow() {
    try {
      wx.hideShareMenu();
    } catch (e) {}
  },

  // 统一退出：返回进入本次答题页的页面（优先 navigateBack，单页栈兜底回首页）
  navigateBackToEntry() {
    const pages = getCurrentPages();
    if (pages && pages.length > 1) {
      wx.navigateBack({ delta: 1 });
      return;
    }
    wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
  },

  onNavBack() {
    this.navigateBackToEntry();
  },

  onLoad(options: any) {
    this.ensureSetDataBatcher();

    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    this.sessionStartedAt = Date.now();

    // 编辑权限初始为 false，在 loadQuestions 中根据数据源类型判断
    // 公有题库：管理员或科目管理员
    // 个人题库：题库创建者

    // 初始化主题（保证进入页面即命中 themeClass / themeStyleClass）
    try {
      this.patchData(Object.assign({ canEdit: false }, themeManager.getPageData()), undefined, true);
      this.syncThemeStyleName();
    } catch (e) {
      this.patchData({ canEdit: false }, undefined, true);
    }

    // 使用工厂函数创建数据源
    quizSource = createSourceFromOptions(options);

    if (!quizSource) {
      wx.showToast({ title: '参数缺失', icon: 'none' });
      setTimeout(() => {
        this.navigateBackToEntry();
      }, 1500);
      return;
    }

    // 解析参数
    const modeRaw = String(options.mode || 'quiz').trim().toLowerCase();
    const mode = (modeRaw === 'memo' || modeRaw === 'reinforce') ? modeRaw : 'quiz';

    let type = options.type || 'all';
    let tag = options.tag || 'all';
    const source = mode === 'reinforce' ? 'all' : (options.source || 'all');
    const shuffleQuestions = options.shuffle_questions === '1';
    const shuffleOptions = options.shuffle_options === '1';
    const startId = Number(options.start_id || 0);

    const rkRaw = String(options.rk || '').trim().toLowerCase();
    const reinforceKind: '' | 'wrong' | 'similar' =
      mode === 'reinforce' && (rkRaw === 'wrong' || rkRaw === 'similar') ? (rkRaw as any) : '';
    const reinforceIds = mode === 'reinforce' ? parseIdList(options.ids || options.question_ids, 200) : [];

    if (mode === 'reinforce' && !reinforceIds.length) {
      wx.showToast({ title: '缺少加强题目列表', icon: 'none' });
      setTimeout(() => {
        this.navigateBackToEntry();
      }, 1200);
      return;
    }

    // 题型可能会被 encodeURIComponent（如"选择题"），需显式解码避免后端筛选不匹配
    try {
      type = decodeURIComponent(type);
    } catch (e) {
      // ignore decode error
    }

    // 标签可能会被 encodeURIComponent（如"重点"），需显式解码
    try {
      tag = decodeURIComponent(tag);
    } catch (e) {
      // ignore decode error
    }

    this.setData({
      mode,
      sourceType: quizSource.sourceType,
      sourceId: quizSource.sourceId,
      displayName: quizSource.displayName || String(quizSource.sourceId),
      source,
      qType: type || 'all',
      tag: tag || 'all',
      shuffleQuestions,
      shuffleOptions,
      reinforceKind,
      reinforceIds,
      startId: isFinite(startId) && startId > 0 ? startId : 0,
      loading: true
    });

    this.initPracticeSettings();
    this.initQuizFontSize();
    this.syncThemeStyleName();

    this.loadQuestions(type, source, shuffleQuestions, shuffleOptions, tag);
  },

  isNonEmptyAnswerValue(val: any): boolean {
    if (val == null) return false;
    if (Array.isArray(val)) {
      if (!val.length) return false;
      return val.some((x) => String(x || '').trim().length > 0);
    }
    const s = String(val || '').trim();
    return s.length > 0;
  },

  openQuizSettlement() {
    const questions = Array.isArray(this.data.questions) ? this.data.questions : [];
    const total = questions.length;
    const statusMap = (this.progressStatusMap && typeof this.progressStatusMap === 'object') ? this.progressStatusMap : {};
    const answerMap = (this.progressAnswerMap && typeof this.progressAnswerMap === 'object') ? this.progressAnswerMap : {};

    let answered = 0;
    let correct = 0;
    let wrong = 0;
    const wrongIds: number[] = [];

    for (let i = 0; i < total; i++) {
      const st = statusMap[String(i)];
      if (st === 'correct') correct += 1;
      if (st === 'wrong') wrong += 1;

      const hasStatus = st === 'correct' || st === 'wrong';
      const hasAnswer = this.isNonEmptyAnswerValue(answerMap[String(i)]);
      if (hasStatus || hasAnswer) {
        answered += 1;
      }

      if (st === 'wrong') {
        const q = questions[i];
        const qid = Number(q && q.id ? q.id : 0);
        if (Number.isFinite(qid) && qid > 0) wrongIds.push(qid);
      }
    }

    const accuracy = answered ? Math.round((correct * 1000) / answered) / 10 : 0;
    const usedSec = this.sessionStartedAt ? Math.max(0, Math.floor((Date.now() - Number(this.sessionStartedAt || 0)) / 1000)) : 0;

    const payload: any = {
      ts: Date.now(),
      sourceType: this.data.sourceType,
      sourceId: this.data.sourceId,
      displayName: this.data.displayName || '',
      mode: this.data.mode,
      source: this.data.source,
      qType: this.data.qType,
      tag: this.data.tag,
      shuffleQuestions: !!this.data.shuffleQuestions,
      shuffleOptions: !!this.data.shuffleOptions,
      reinforceKind: this.data.reinforceKind || '',
      total,
      answered,
      correct,
      wrong,
      accuracy,
      usedSec,
      wrongIds
    };

    try {
      wx.setStorageSync('quiz_settlement_payload_v1', payload);
    } catch (e) {}

    wx.navigateTo({
      url: '/pages/quiz-settlement/quiz-settlement',
      fail: (e) => {
        // ignore
        wx.redirectTo({ url: '/pages/quiz-settlement/quiz-settlement' });
      }
    });
  },

  initPracticeSettings() {
    try {
      const raw = wx.getStorageSync(this.practiceSettingsKey);
      if (raw && typeof raw === 'object') {
        const s: any = raw;
        const next = {
          autoNextOnCorrect: !!s.autoNextOnCorrect,
          autoFavoriteOnWrong: !!s.autoFavoriteOnWrong,
          vibrationFeedback: !!s.vibrationFeedback
        };
        this.setData({ practiceSettings: next });
      }
    } catch (e) {
      // 忽略本地存储异常
    }
  },

  savePracticeSettings() {
    try {
      wx.setStorageSync(this.practiceSettingsKey, this.data.practiceSettings);
    } catch (e) {
      // 忽略本地存储异常
    }
  },

  normalizeQuizFontSize(raw: any): 'sm' | 'md' | 'lg' {
    const v = String(raw || '').trim().toLowerCase();
    return (v === 'sm' || v === 'md' || v === 'lg') ? (v as any) : 'md';
  },

  initQuizFontSize() {
    try {
      const raw = wx.getStorageSync(this.quizFontSizeKey);
      const size = this.normalizeQuizFontSize(raw);
      this.setData({ quizFontSize: size, quizFontClass: `quiz-font-${size}` });
    } catch (e) {
      // ignore
    }
  },

  saveQuizFontSize(size: 'sm' | 'md' | 'lg') {
    try {
      wx.setStorageSync(this.quizFontSizeKey, size);
    } catch (e) {
      // ignore
    }
  },

  setQuizFontSize(size: any) {
    const next = this.normalizeQuizFontSize(size);
    this.setData({ quizFontSize: next, quizFontClass: `quiz-font-${next}` }, () => {
      this.saveQuizFontSize(next);
      wx.showToast({ title: '已切换字体', icon: 'none' });
    });
  },

  onFontSizeSelect(e: any) {
    const size = e.currentTarget?.dataset?.size;
    this.setQuizFontSize(size);
  },

  syncThemeStyleName() {
    try {
      this.setData({ themeStyleName: themeManager.getStyleName() });
    } catch (e) {
      // ignore
    }
  },

  onThemeChange(_isDark: boolean) {
    this.syncThemeStyleName();
  },

  onCycleThemeStyle() {
    try {
      const next = themeManager.cycleStyle();
      this.syncThemeStyleName();
      wx.showToast({ title: `已切换到${themeManager.getStyleName()}主题`, icon: 'none' });
      return next;
    } catch (e) {
      // ignore
    }
  },

  onToggleTheme() {
    try {
      themeManager.toggleDark();
      this.setData(themeManager.getPageData());
    } catch (e) {
      // ignore
    }
  },

  onOpenSettings() {
    this.setData({ showSettings: true });
  },

  onCloseSettings() {
    this.setData({ showSettings: false });
  },

  onSettingSwitchChange(e: any) {
    const key = e.currentTarget?.dataset?.key;
    const value = !!(e && e.detail && e.detail.value);
    if (!key) return;

    const next = Object.assign({}, this.data.practiceSettings);
    (next as any)[key] = value;
    this.setData({ practiceSettings: next }, () => this.savePracticeSettings());
  },

  onClearCurrentAnswerRecord() {
    const cq = this.data.currentQuestion;
    if (!cq) return;

    wx.showModal({
      title: '清除本题记录',
      content: '确定清除本题的作答与本地进度吗？',
      confirmText: '清除',
      confirmColor: '#ff3b30',
      success: (res) => {
        if (!res.confirm) return;

        const idx = Number(this.data.currentIndex) || 0;
        const qType: QuestionType = (cq.q_type || '').toString();

        // 清理本地进度缓存（answers/status）
        try {
          if (this.progressAnswerMap && typeof this.progressAnswerMap === 'object') {
            delete this.progressAnswerMap[String(idx)];
          }
          if (this.progressStatusMap && typeof this.progressStatusMap === 'object') {
            delete this.progressStatusMap[String(idx)];
          }
        } catch (e) {}

        // 清理题目列表状态（✓/✕）
        try {
          const nextRecords: any = Object.assign({}, this.data.answerRecords || {});
          if (cq && typeof cq.id === 'number') {
            delete nextRecords[cq.id];
          }
          this.setData({ answerRecords: nextRecords });
        } catch (e) {}

        const nextBlankAnswers =
          qType === '填空题' ? new Array(Number(this.data.blankCount) || 0).fill('') : [];

        this.setData({
          showSettings: false,
          showAnswer: false,
          isCorrect: false,
          userAnswerText: '',
          selectedAnswer: '',
          selectedAnswers: [],
          blankAnswers: nextBlankAnswers,
          showAIExplain: false,
          aiLoading: false,
          aiExplainText: '',
          aiExplainRichText: '',
          aiExplainError: '',
          aiExplainQuestionId: 0,
          scrollIntoView: ''
        }, () => {
          this.refreshDisplayOptions();
          this.updateSubmitState();
        });

        // 立即同步到云端（仅进度/答案缓存；不回滚服务器的答题统计）
        this.saveProgressIndex(true);

        wx.showToast({ title: '已清除', icon: 'none' });
      }
    });
  },

  // 加载题目列表（使用数据源适配器）
  async loadQuestions(type: string, source: string, shuffleQuestions: boolean, shuffleOptions: boolean, tag: string) {
    if (!quizSource) {
      
      this.setData({ loading: false });
      return;
    }

    try {
      const { mode, sourceType, sourceId } = this.data;
      const requestMode = mode === 'reinforce' ? 'quiz' : mode;
      const reinforceIds = mode === 'reinforce' ? (this.data.reinforceIds || []) : [];

      // 检查编辑权限 + 获取题库名称
      let canEdit = false;
      try {
        const userInfo = wx.getStorageSync('userInfo') || {};
        const currentUserId = userInfo.id || userInfo.user_id;

        if (sourceType === 'public') {
          // 公有题库：管理员或科目管理员
          canEdit = !!(userInfo.is_admin || userInfo.is_subject_admin);
        } else if (sourceType === 'bank') {
          // 个人题库：获取详情（用于名称 + 权限检查）
          try {
            const bankDetail: any = await api.getBankDetail(Number(sourceId));
            // 更新题库显示名称
            const bankName = bankDetail?.name || bankDetail?.data?.name;
            if (bankName && (!this.data.displayName || /^\d+$/.test(this.data.displayName))) {
              this.setData({ displayName: bankName });
            }
            // 检查是否是题库创建者
            if (currentUserId) {
              const bankOwnerId = bankDetail?.user_id || bankDetail?.data?.user_id;
              canEdit = bankOwnerId && Number(bankOwnerId) === Number(currentUserId);
            }
          } catch (e) {
            // ignore
          }
        }
      } catch (e) {
        // 忽略
      }
      this.setData({ canEdit });

      // 使用数据源适配器获取题目
      // 分页策略：打乱/reinforce 模式需要完整集合，其余按需分页
      const needFullLoad = shuffleQuestions || (reinforceIds && reinforceIds.length > 0);
      const perPage = needFullLoad ? 1000 : this.data.paginationPerPage;
      const result = await quizSource.getQuestions({
        mode: requestMode,
        source: source,
        type: type !== 'all' ? type : undefined,
        tag: tag && tag !== 'all' ? tag : undefined,
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
        ids: (reinforceIds && reinforceIds.length) ? reinforceIds : undefined,
        page: needFullLoad ? undefined : 1,
        per_page: perPage
      });

      let questions = result.questions || [];
      const total = result.total || questions.length;

      // 统一 options 结构，避免不同历史数据格式导致前端无法渲染
      questions = questions.map((q: any) => {
        const normalizedOptions = this.normalizeOptions(q.options, q.q_type, q.answer);
        const imageUrls = uniqUrls([
          ...normalizeImageUrls(q.image_path),
          ...extractInlineImageUrls(q.content)
        ]);
        const imagePath = imageUrls.length > 0 ? imageUrls[0] : '';
        return Object.assign({}, q, { options: normalizedOptions, image_urls: imageUrls, image_path: imagePath });
      });
      
      // 为每个题目生成预览内容
      let questionsWithPreview = questions.map((q: any) => {
        const content = q.content || '';
        const textContent = content.replace(/<[^>]+>/g, ''); // 移除HTML标签
        const preview = textContent.length > 40 ? textContent.substring(0, 40) + '...' : textContent;
        return Object.assign({}, q, { contentPreview: preview });
      });

      // 进度key（必须与 Web progressKey() 格式一致）
      const pKey = this.buildProgressKey();
      this.progressKey = pKey;

      // 先尝试恢复云端/本地进度（含题目顺序）
      const saved = await this.loadProgressState(pKey);
      const savedPayload = (saved && typeof saved === 'object') ? saved : null;

      // 初始化进度缓存
      this.progressStatusMap = (savedPayload && savedPayload.status && typeof savedPayload.status === 'object') ? savedPayload.status : {};
      this.progressAnswerMap = (savedPayload && savedPayload.answers && typeof savedPayload.answers === 'object') ? savedPayload.answers : {};
      this.progressOrder = (savedPayload && Array.isArray(savedPayload.order)) ? savedPayload.order : null;

      // 打乱题目顺序：优先使用已保存的 order；无 order 时再生成并同步到云端
      if (shuffleQuestions && questionsWithPreview.length > 0) {
        const hasHistory =
          !!(savedPayload && ((savedPayload.status && Object.keys(savedPayload.status).length) || (savedPayload.answers && Object.keys(savedPayload.answers).length)));

        if (this.progressOrder && Array.isArray(this.progressOrder)) {
          questionsWithPreview = this.applyQuestionOrder(questionsWithPreview, this.progressOrder);
        } else {
          // 如果已有历史答题痕迹但缺少order，兜底：把当前顺序作为order保存，避免索引错位
          if (hasHistory) {
            this.progressOrder = questionsWithPreview.map((q: any) => q.id);
          } else {
            questionsWithPreview = this.shuffleArray(questionsWithPreview.slice());
            this.progressOrder = questionsWithPreview.map((q: any) => q.id);
          }

          const nextPayload: any = Object.assign({}, savedPayload || {});
          if (typeof nextPayload.index !== 'number') nextPayload.index = 0;
          if (!nextPayload.status || typeof nextPayload.status !== 'object') nextPayload.status = this.progressStatusMap || {};
          if (!nextPayload.answers || typeof nextPayload.answers !== 'object') nextPayload.answers = this.progressAnswerMap || {};
          nextPayload.order = this.progressOrder;
          nextPayload.timestamp = Date.now();

          // 保存一次order（避免多端乱序不一致）
          this.saveProgressState(nextPayload, true);
        }
      }

      // 基于已保存的状态，恢复题目列表正确/错误标记
      const restoredRecords = this.buildAnswerRecordsFromStatus(questionsWithPreview, this.progressStatusMap);

      // 分页状态
      const paginationEnabled = !needFullLoad;
      const loadedCount = questionsWithPreview.length;
      const paginationHasMore = paginationEnabled && loadedCount < total;

      this.setData({
        questions: questionsWithPreview,
        loading: false,
        answerRecords: restoredRecords,
        progress: {
          current: 1,
          total: total
        },
        paginationEnabled,
        paginationPage: 1,
        paginationTotal: total,
        paginationHasMore,
        paginationLoading: false
      });
      
      // 加载第一题
      if (questionsWithPreview.length > 0) {
        let idx = savedPayload && typeof savedPayload.index === 'number' ? savedPayload.index : 0;
        const startId = this.data.startId;
        if (startId && startId > 0) {
          const found = questionsWithPreview.findIndex((q: any) => q && q.id === startId);
          if (found >= 0) {
            idx = found;
          }
        }
        const safeIndex = Math.max(0, Math.min(idx, questionsWithPreview.length - 1));
        this.loadQuestion(safeIndex);
      } else {
        wx.showToast({ title: '暂无题目', icon: 'none' });
        setTimeout(() => {
          this.navigateBackToEntry();
        }, 1500);
      }
    } catch (err: any) {
      
      const errorMsg = (err && err.message) || '加载失败';
      
      if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      
      wx.showToast({ title: errorMsg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 分页懒加载：加载下一批题目
  async loadMoreQuestions() {
    if (!quizSource || !this.data.paginationEnabled || !this.data.paginationHasMore || this.data.paginationLoading) {
      return;
    }

    const nextPage = this.data.paginationPage + 1;
    this.setData({ paginationLoading: true });

    try {
      const { mode, source, qType, tag, shuffleOptions } = this.data;
      const requestMode = mode === 'reinforce' ? 'quiz' : mode;

      const result = await quizSource.getQuestions({
        mode: requestMode,
        source: source,
        type: qType !== 'all' ? qType : undefined,
        tag: tag && tag !== 'all' ? tag : undefined,
        shuffle_questions: false,
        shuffle_options: !!shuffleOptions,
        page: nextPage,
        per_page: this.data.paginationPerPage
      });

      const newQuestions = (result.questions || []).map((q: any) => {
        const normalizedOptions = this.normalizeOptions(q.options, q.q_type, q.answer);
        const imageUrls = uniqUrls([
          ...normalizeImageUrls(q.image_path),
          ...extractInlineImageUrls(q.content)
        ]);
        const imagePath = imageUrls.length > 0 ? imageUrls[0] : '';
        const content = q.content || '';
        const textContent = content.replace(/<[^>]+>/g, '');
        const preview = textContent.length > 40 ? textContent.substring(0, 40) + '...' : textContent;
        return Object.assign({}, q, { options: normalizedOptions, image_urls: imageUrls, image_path: imagePath, contentPreview: preview });
      });

      if (newQuestions.length > 0) {
        const merged = this.data.questions.concat(newQuestions);
        const total = result.total || this.data.paginationTotal;
        const hasMore = merged.length < total;

        this.setData({
          questions: merged,
          paginationPage: nextPage,
          paginationTotal: total,
          paginationHasMore: hasMore,
          paginationLoading: false
        });
      } else {
        this.setData({ paginationHasMore: false, paginationLoading: false });
      }
    } catch (err) {
      this.setData({ paginationLoading: false });
    }
  },

  // 加载指定题目
  loadQuestion(index: number) {
    const { questions } = this.data;
    if (index < 0 || index >= questions.length) {
      return;
    }

    // 分页预加载：距离已加载末尾 10 题时触发
    if (this.data.paginationEnabled && this.data.paginationHasMore && index >= questions.length - 10) {
      this.loadMoreQuestions();
    }
    
    const question = questions[index];
    const qType: QuestionType = question.q_type || '';
    const rawContent = (question.content || '').toString();
    const rawAnswer = (question.answer || '').toString();

    let displayContent = this.formatContentForDisplay(rawContent);
    if (qType === '填空题') {
      // 填空题挖空：仅填空题替换，避免代码里的 __ 被误改
      displayContent = displayContent.replace(/__/g, '____');
    }

    const isCode = this.looksLikeCode(displayContent);
    if (isCode) {
      displayContent = this.preserveSpacesForCode(displayContent);
    }
    const displayAnswer = this.formatAnswerForDisplay(qType, rawAnswer);

    const rawExplanation = (question.explanation || '').toString();
    const explanationIsCode = this.looksLikeCode(rawExplanation);
    const displayExplanation = explanationIsCode ? this.preserveSpacesForCode(rawExplanation) : rawExplanation;

    const normalizedOptions = this.normalizeOptions(question.options, qType, rawAnswer);
    const blankState = this.initBlankState(qType, rawContent, rawAnswer);
    let blankCount = blankState.blankCount;
    const blankAnswers = blankState.blankAnswers;
    let blankIndexes = blankState.blankIndexes;

    // 恢复当前题目的已保存作答（未提交也会恢复“草稿”）
    const savedAnswer = this.getSavedAnswerForIndex(index);
    const savedStatus = this.getSavedStatusForIndex(index);

    let selectedAnswer = '';
    let selectedAnswers: string[] = [];
    let nextBlankAnswers = blankAnswers.slice();
    let showAnswer = false;
    let isCorrect = false;
    let userAnswerText = '';

    if (Array.isArray(savedAnswer)) {
      if (qType === '多选题') {
        selectedAnswers = savedAnswer.map((x) => String(x)).filter(Boolean);
        userAnswerText = selectedAnswers.slice().sort().join('');
      } else if (qType === '选择题' || qType === '判断题') {
        selectedAnswer = savedAnswer.length > 0 ? String(savedAnswer[0]) : '';
        userAnswerText = selectedAnswer;
      } else if (qType === '填空题') {
        const trimmed = savedAnswer.map((x) => (x == null ? '' : String(x))).map((x) => x.trim());
        // 适配空数变化
        const filledCount = Math.max(blankCount, trimmed.length);
        const filled = Array.from({ length: filledCount }, (_, i) => trimmed[i] || '');
        blankCount = filledCount;
        blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
        nextBlankAnswers = filled.slice(0, filledCount);
        userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
      }
    } else if (typeof savedAnswer === 'string') {
      if (qType === '填空题') {
        const parts = savedAnswer.split(';;').map((x) => x.trim()).filter((x) => x.length > 0);
        const filledCount = Math.max(blankCount, parts.length);
        const filled = Array.from({ length: filledCount }, (_, i) => parts[i] || '');
        blankCount = filledCount;
        blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
        nextBlankAnswers = filled.slice(0, filledCount);
        userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
      } else {
        selectedAnswer = savedAnswer;
        userAnswerText = savedAnswer;
      }
    }

    // 仅自动判分题型恢复“已批改”状态
    if ((qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题') && (savedStatus === 'correct' || savedStatus === 'wrong')) {
      showAnswer = true;
      isCorrect = savedStatus === 'correct';
    }
    
    this.setData({
      currentIndex: index,
      currentQuestion: Object.assign({}, question, {
        displayContent,
        displayAnswer,
        options: normalizedOptions,
        isCode,
        explanationIsCode,
        displayExplanation
      }),
      selectedAnswer,
      selectedAnswers,
      blankCount,
      blankAnswers: nextBlankAnswers,
      blankIndexes,
      showAnswer,
      isJudgable: this.isAutoJudgable(qType),
      isCorrect,
      userAnswerText,
      isFavorite: question.is_fav === 1 || question.is_fav === true,
      showAIExplain: false,
      scrollIntoView: '',
      aiLoading: false,
      aiExplainText: '',
      aiExplainRichText: '',
      aiExplainError: '',
      aiExplainQuestionId: question.id || 0,
      progress: {
        current: index + 1,
        total: this.data.progress.total
      }
    }, () => {
      this.refreshDisplayOptions();
      this.updateSubmitState();
      this.saveProgressIndex(false);
    });
  },

  // 选择答案（单选题/判断题）
  onSelectAnswer(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return; // 已提交或背题模式不允许选择
    }
    
    const answer = (e.currentTarget.dataset.answer as string) || '';
    const { currentQuestion } = this.data;
    const qType: QuestionType = currentQuestion.q_type || '';
    
    // 多选题处理
    if (qType === '多选题') {
      const selectedAnswers = this.data.selectedAnswers.slice();
      const index = selectedAnswers.indexOf(answer);
      if (index > -1) {
        selectedAnswers.splice(index, 1); // 取消选择
      } else {
        selectedAnswers.push(answer); // 选择
      }
      this.setData({ selectedAnswers }, () => {
        this.refreshDisplayOptions();
        this.updateSubmitState();
        this.saveDraftAnswer();
      });
    } else {
      // 单选题/判断题
      this.setData({ selectedAnswer: answer }, () => {
        this.refreshDisplayOptions();
        this.updateSubmitState();

        // 选择题、判断题：点选即判
        if ((this.data.mode === 'quiz' || this.data.mode === 'reinforce') && !this.data.showAnswer && (qType === '选择题' || qType === '判断题')) {
          this.onSubmitAnswer();
        }
      });
    }
  },

  // 输入答案（主观题：问答/计算/简答）
  onInputAnswer(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return;
    }
    const cq = this.data.currentQuestion;
    const qType: QuestionType = (cq && cq.q_type) || '';
    if (qType === '填空题') {
      return;
    }
    this.setData({ selectedAnswer: e.detail.value }, () => {
      this.updateSubmitState();
      this.saveDraftAnswer();
    });
  },

  // 输入答案（填空题：多空）
  onBlankInput(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return;
    }
    const cq = this.data.currentQuestion;
    const qType: QuestionType = (cq && cq.q_type) || '';
    if (qType !== '填空题') {
      return;
    }
    const idx = Number(e.currentTarget.dataset.index);
    if (!isFinite(idx) || idx < 0) {
      return;
    }
    const next = this.data.blankAnswers.slice();
    next[idx] = e.detail.value;
    this.setData({ blankAnswers: next }, () => {
      this.updateSubmitState();
      this.saveDraftAnswer();
    });
  },

  // 提交答案（刷题模式）
  async onSubmitAnswer() {
    const { currentQuestion, selectedAnswer, selectedAnswers, mode, blankAnswers } = this.data;
    
    if (mode === 'memo') {
      return; // 背题模式不需要提交
    }
    
    if (!currentQuestion) {
      return;
    }
    
    const qType: QuestionType = currentQuestion.q_type || '';
    const isJudgable = this.isAutoJudgable(qType);

    // 检查是否已选择答案
    let userAnswer = '';
    let userAnswerText = '';

    if (qType === '多选题') {
      if (selectedAnswers.length === 0) {
        wx.showToast({ title: '请选择答案', icon: 'none' });
        return;
      }
      userAnswer = selectedAnswers.sort().join(''); // 排序后拼接
      userAnswerText = userAnswer;
    } else if (qType === '填空题') {
      const normalized = (blankAnswers || []).map((x) => (x || '').trim());
      if (normalized.length === 0 || normalized.some((x) => !x)) {
        wx.showToast({ title: '请填写所有空', icon: 'none' });
        return;
      }
      userAnswer = normalized.join(';;');
      userAnswerText = normalized.join(' / ');
    } else if (qType === '简答题' || qType === '计算题') {
      const t = (selectedAnswer || '').trim();
      if (!t) {
        wx.showToast({ title: '请输入答案', icon: 'none' });
        return;
      }
      userAnswer = t;
      userAnswerText = t;
    } else {
      if (!selectedAnswer) {
        wx.showToast({ title: '请选择或输入答案', icon: 'none' });
        return;
      }
      userAnswer = selectedAnswer.trim();
      userAnswerText = userAnswer;
    }
    
    // 验证答案
    const correctAnswer = currentQuestion.answer || '';
    const isCorrect = isJudgable ? this.checkAnswer(userAnswer, correctAnswer, qType) : false;
    
    // 更新进度缓存（answers/status/order/index）
    this.setProgressAnswerForIndex(this.data.currentIndex, qType);
    if (isJudgable) {
      this.progressStatusMap = this.progressStatusMap || {};
      this.progressStatusMap[String(this.data.currentIndex)] = isCorrect ? 'correct' : 'wrong';
    }

    this.patchData({
      showAnswer: true,
      isCorrect,
      isJudgable,
      userAnswerText
    }, () => {
      this.refreshDisplayOptions();
      this.updateSubmitState();
    });
    
    // 记录答题结果（主观题不自动判分，避免误记错题）
    if (isJudgable) {
      const nextRecords: any = Object.assign({}, this.data.answerRecords);
      nextRecords[currentQuestion.id] = {
        answered: true,
        isCorrect
      };
      this.patchData({
        answerRecords: nextRecords
      });
    }

    // 更新 questions 列表里的错题标记（保证“错题本”筛选能即时生效）
    if (isJudgable) {
      const questions = this.data.questions.map((q: any) => {
        if (q.id !== currentQuestion.id) return q;
        return Object.assign({}, q, { is_mistake: isCorrect ? 0 : 1 });
      });
      this.patchData({ questions });
    }

    // 重要操作：立即同步进度到云端
    this.saveProgressIndex(true);
    
    // 调用数据源适配器记录答题结果
    try {
      if (isJudgable && quizSource) {
        await quizSource.recordResult({
          questionId: currentQuestion.id,
          userAnswer: userAnswer,
          isCorrect: isCorrect
        });
      }
    } catch (err: any) {
      wx.showToast({ title: '记录结果失败，已忽略', icon: 'none' });
    }

    // 震动反馈（提交后）
    if (isJudgable && this.data.practiceSettings.vibrationFeedback) {
      try {
        const vibrateType = isCorrect ? 'medium' : 'heavy';
        // @ts-ignore - 部分基础库不支持 type 参数
        wx.vibrateShort({ type: vibrateType });
      } catch (e) {
        try {
          wx.vibrateShort();
        } catch (e2) {
          // ignore
        }
      }
    }

    // 做错自动收藏（仅在未收藏时触发）
    if (isJudgable && !isCorrect && this.data.practiceSettings.autoFavoriteOnWrong) {
      await this.autoFavoriteIfNeeded();
    }

    // 答对自动切题（给用户一点点反馈时间）
    if (isJudgable && isCorrect && this.data.practiceSettings.autoNextOnCorrect) {
      setTimeout(() => {
        // 仍在当前题且已展示答案时再切题
        if (this.data.showAnswer && this.data.currentQuestion && this.data.currentQuestion.id === currentQuestion.id) {
          this.onNextQuestion();
        }
      }, 650);
    }
  },

  async autoFavoriteIfNeeded() {
    const { currentQuestion, isFavorite } = this.data;
    if (!currentQuestion || isFavorite || !quizSource) return;

    try {
      await quizSource.toggleFavorite(currentQuestion.id);
      this.patchData({ isFavorite: true });
      const questions = this.data.questions.map((q: any) => {
        if (q.id === currentQuestion.id) return Object.assign({}, q, { is_fav: 1 });
        return q;
      });
      this.patchData({ questions });
    } catch (err: any) {
      wx.showToast({ title: '自动收藏失败', icon: 'none' });
    }
  },

  onToggleAIExplain() {
    const next = !this.data.showAIExplain;
    if (!next) {
      this.patchData({ showAIExplain: false, scrollIntoView: '' });
      return;
    }

    this.patchData({ showAIExplain: true, scrollIntoView: '' }, () => {
      this.loadAIExplain(false);
      setTimeout(() => {
        if (this.data.showAIExplain) {
          this.patchData({ scrollIntoView: 'aiExplainCard' });
        }
      }, 60);
    });
  },

  onRegenerateAIExplain() {
    this.loadAIExplain(true);
  },

  async loadAIExplain(force: boolean) {
    const cq = this.data.currentQuestion;
    if (!cq) return;

    const qid = Number(cq.id) || 0;
    if (!force && this.data.aiExplainText && this.data.aiExplainQuestionId === qid) {
      return;
    }

    if (!force && qid) {
      const cached = readAIExplainCache(qid);
      if (cached) {
        this.patchData({
          aiLoading: false,
          aiExplainError: '',
          aiExplainText: cached,
          aiExplainRichText: markdownToRichTextHtml(cached),
          aiExplainQuestionId: qid
        });
        return;
      }
    }

    const options = Array.isArray(cq.options)
      ? cq.options.map((x: any) => ({ key: x.key, value: x.value }))
      : undefined;

    this.patchData({ aiLoading: true, aiExplainError: '', aiExplainText: '', aiExplainRichText: '', aiExplainQuestionId: qid });
    try {
      const res: any = await api.aiExplain({
        question_id: qid || undefined,
        content: (cq.content || '').toString(),
        q_type: (cq.q_type || '').toString(),
        options
      });
      const text = (res && res.explain) ? String(res.explain) : '';
      const cleaned = (text || '').toString().trim();
      if (cleaned) {
        writeAIExplainCache(qid, cleaned);
      }
      const finalText = cleaned || '暂无解析内容';
      this.patchData({
        aiExplainText: finalText,
        aiExplainRichText: markdownToRichTextHtml(finalText),
        aiLoading: false
      });
    } catch (err: any) {
      this.patchData({ aiExplainError: err?.message || 'AI解析失败，请稍后重试', aiLoading: false });
    }
  },

  // 检查答案是否正确
  checkAnswer(userAnswer: string, correctAnswer: string, qType: string): boolean {
    if (qType === '多选题') {
      // 多选题：答案排序后比较
      const userAnswerSorted = userAnswer.split('').sort().join('');
      const correctAnswerSorted = correctAnswer.split('').sort().join('');
      return userAnswerSorted === correctAnswerSorted;
    } else if (qType === '填空题') {
      // 填空题：支持一题多空（;; 分隔），一空多答案（; 分隔）
      const userBlanks = userAnswer.split(';;').map((x) => x.trim());
      const normalizedCorrect = (correctAnswer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
      const correctBlanksRaw = normalizedCorrect.split(';;').map((x) => x.trim());
      const blankCount = Math.max(userBlanks.length, correctBlanksRaw.length, 1);

      for (let i = 0; i < blankCount; i++) {
        const userBlank = (userBlanks[i] || '').trim();
        const correctBlank = (correctBlanksRaw[i] || '').trim();
        if (!userBlank) {
          return false;
        }
        if (!correctBlank) {
          return false;
        }

        const correctAlternatives = correctBlank
          .split(';')
          .map((x) => x.trim())
          .filter(Boolean)
          .map((x) => x.toLowerCase());

        const u = userBlank.toLowerCase();
        if (correctAlternatives.length === 0) {
          if (u !== correctBlank.toLowerCase()) {
            return false;
          }
        } else {
          if (!correctAlternatives.includes(u)) {
            return false;
          }
        }
      }

      return true;
    } else {
      // 单选题/判断题/填空题：直接比较（忽略大小写和空格）
      const ua = userAnswer.trim().toLowerCase();
      const ca = (correctAnswer || '').toString().replace(/；/g, ';').trim().toLowerCase();

      // 支持单空多答案（; 分隔）
      if (ca.includes(';')) {
        const candidates = ca
          .split(';')
          .map((x) => x.trim())
          .filter(Boolean);
        return candidates.includes(ua);
      }

      return ua === ca;
    }
  },

  // 切换收藏（使用数据源适配器）
  async onToggleFavorite() {
    const { currentQuestion, isFavorite } = this.data;
    if (!currentQuestion || !quizSource) {
      return;
    }

    try {
      const result = await quizSource.toggleFavorite(currentQuestion.id);
      const newFavoriteState = result.is_favorite !== undefined ? result.is_favorite : !isFavorite;

      this.setData({
        isFavorite: newFavoriteState
      });

      // 更新题目数据
      const questions = this.data.questions.map((q: any) => {
        if (q.id === currentQuestion.id) {
          return Object.assign({}, q, { is_fav: newFavoriteState ? 1 : 0 });
        }
        return q;
      });

      this.setData({ questions });

      wx.showToast({
        title: newFavoriteState ? '已收藏' : '已取消收藏',
        icon: 'none',
        duration: 1500
      });
    } catch (err: any) {
      
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  // 上一题
  onPrevQuestion() {
    const { currentIndex } = this.data;
    if (currentIndex > 0) {
      this.loadQuestion(currentIndex - 1);
    }
  },

  // 下一题
  onNextQuestion() {
    const { currentIndex, questions, paginationEnabled, paginationHasMore } = this.data;
    if (currentIndex < questions.length - 1) {
      this.loadQuestion(currentIndex + 1);
    } else if (paginationEnabled && paginationHasMore) {
      // 分页模式：还有更多题目，加载后跳转
      wx.showLoading({ title: '加载中', mask: false });
      this.loadMoreQuestions().then(() => {
        wx.hideLoading();
        const updated = this.data.questions;
        if (currentIndex + 1 < updated.length) {
          this.loadQuestion(currentIndex + 1);
        } else {
          this.openQuizSettlement();
        }
      });
    } else {
      // 最后一题：进入结算页（替代答题结束弹窗）
      this.openQuizSettlement();
    }
  },

  // 打开题目列表抽屉
  onOpenQuestionList() {
    this.setData({ showQuestionList: true });
  },

  // 关闭题目列表抽屉
  onCloseQuestionList() {
    this.setData({ showQuestionList: false });
  },

  // 点击题目列表项
  onQuestionListItemTap(e: any) {
    const index = e.currentTarget.dataset.index;
    this.loadQuestion(index);
    this.onCloseQuestionList();
  },

  // 工具函数：打乱数组
  shuffleArray<T>(array: T[]): T[] {
    const shuffled = array.slice();
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = shuffled[i];
      shuffled[i] = shuffled[j];
      shuffled[j] = tmp;
    }
    return shuffled;
  },

  onQuestionImageError(e: any) {
    const idx = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.index) || -1);
    const q = this.data.currentQuestion;
    const urls = (q && q.image_urls) || [];
    if (!Array.isArray(urls) || urls.length === 0) return;
    if (!Number.isFinite(idx) || idx < 0 || idx >= urls.length) return;

    const url = String(urls[idx] || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) return;

    const self: any = this as any;
    self.__imgDlTried = self.__imgDlTried || {};
    const key = `${q && q.id ? q.id : 'q'}_${idx}_${url}`;
    if (self.__imgDlTried[key]) return;
    self.__imgDlTried[key] = true;

    wx.downloadFile({
      url,
      timeout: 15000,
      success: (res) => {
        const tempFilePath = String((res && (res as any).tempFilePath) || '').trim();
        if (!tempFilePath) return;

        const nextUrls = urls.slice();
        nextUrls[idx] = tempFilePath;
        const nextQuestion = Object.assign({}, q, { image_urls: nextUrls });

        const currentIndex = Number(this.data.currentIndex || 0);
        const nextQuestions = Array.isArray(this.data.questions) ? this.data.questions.slice() : [];
        if (currentIndex >= 0 && currentIndex < nextQuestions.length) {
          nextQuestions[currentIndex] = Object.assign({}, nextQuestions[currentIndex], { image_urls: nextUrls });
        }

        this.setData({ currentQuestion: nextQuestion, questions: nextQuestions });
      },
      fail: (err) => {
        // ignore
      }
    });
  },

  // 预览图片
  previewImage(e: any) {
    const idx = Number(e.currentTarget.dataset.index || 0);
    const urls = (this.data.currentQuestion && this.data.currentQuestion.image_urls) || [];
    if (!Array.isArray(urls) || urls.length === 0) return;
    const current = urls[Math.max(0, Math.min(idx, urls.length - 1))] || urls[0];
    wx.previewImage({ urls, current });
  },

  // 阻止事件冒泡（用于抽屉）
  stopPropagation() {
    // 空函数，用于阻止点击事件冒泡
  },

  // === 标签管理 ===
  async onOpenTagModal() {
    const { currentQuestion } = this.data;
    if (!currentQuestion) return;

    this.setData({ showTagModal: true, newTagName: '' });
    await this.loadAllTags();
    await this.loadQuestionTags();
  },

  onCloseTagModal() {
    this.setData({ showTagModal: false });
  },

  onTagNameInput(e: any) {
    this.setData({ newTagName: (e.detail.value || '').trim() });
  },

  async onCreateTag() {
    const { newTagName, sourceType, sourceId } = this.data;
    if (!newTagName) {
      wx.showToast({ title: '请输入标签名', icon: 'none' });
      return;
    }

    try {
      if (sourceType === 'bank') {
        await api.createBankTag(Number(sourceId), newTagName);
      } else {
        const subject = String(sourceId || '').trim();
        await api.createTag(newTagName, { subject });
      }
      this.setData({ newTagName: '' });
      await this.loadAllTags();
      wx.showToast({ title: '创建成功', icon: 'none' });
    } catch (err: any) {
      
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    }
  },

  async onToggleTagSelection(e: any) {
    const tagName = e.currentTarget.dataset.tag;
    if (!tagName) return;

    const { currentQuestion, allTags, currentQuestionTags, sourceType, sourceId } = this.data;
    if (!currentQuestion) return;

    const tagItem = allTags.find(t => t.name === tagName);
    if (!tagItem) return;

    const isSelected = tagItem.selected;
    let newTags: string[];

    if (isSelected) {
      // 取消选中
      newTags = currentQuestionTags.filter(t => t !== tagName);
    } else {
      // 选中
      newTags = [...currentQuestionTags, tagName];
    }

    try {
      if (sourceType === 'bank') {
        await api.setBankQuestionTags(Number(sourceId), currentQuestion.id, newTags);
      } else {
        await api.setQuestionTags(currentQuestion.id, newTags);
      }

      // 更新状态
      const updatedAllTags = allTags.map(t => ({
        ...t,
        selected: newTags.includes(t.name),
        count: t.name === tagName ? (isSelected ? t.count - 1 : t.count + 1) : t.count
      }));

      this.setData({
        currentQuestionTags: newTags,
        allTags: updatedAllTags
      });
    } catch (err: any) {
      
      wx.showToast({ title: err.message || '设置失败', icon: 'none' });
    }
  },

  async loadAllTags() {
    try {
      const { sourceType, sourceId } = this.data;
      let res: any;

      if (sourceType === 'bank') {
        res = await api.getBankTags(Number(sourceId));
      } else {
        const subject = String(sourceId || '').trim();
        res = await api.getTags({ subject });
      }

      const tags = res.tags || res || [];
      const { currentQuestionTags } = this.data;

      const allTags = tags.map((t: any) => ({
        name: t.name || t,
        count: t.count || 0,
        selected: currentQuestionTags.includes(t.name || t)
      }));

      this.setData({ allTags });
    } catch (err: any) {
      
    }
  },

  async loadQuestionTags() {
    const { currentQuestion, sourceType, sourceId } = this.data;
    if (!currentQuestion) return;

    try {
      let res: any;

      if (sourceType === 'bank') {
        res = await api.getBankQuestionTags(Number(sourceId), currentQuestion.id);
      } else {
        res = await api.getQuestionTags(currentQuestion.id);
      }

      const tags = res.tags || res || [];
      const tagNames = tags.map((t: any) => t.name || t);

      // 更新 allTags 的选中状态
      const { allTags } = this.data;
      const updatedAllTags = allTags.map(t => ({
        ...t,
        selected: tagNames.includes(t.name)
      }));

      this.setData({
        currentQuestionTags: tagNames,
        allTags: updatedAllTags
      });
    } catch (err: any) {
      
      this.setData({ currentQuestionTags: [] });
    }
  },

  // === 编辑题目 ===
  onEditQuestion() {
    const { currentQuestion, canEdit } = this.data;
    if (!currentQuestion || !canEdit) return;

    const qType = currentQuestion.q_type || '';
    const showOptions = qType === '选择题' || qType === '多选题' || qType === '判断题';

    // 格式化选项为文本
    let optionsText = '';
    if (showOptions && Array.isArray(currentQuestion.options)) {
      optionsText = currentQuestion.options
        .map((opt: any) => `${opt.key}. ${opt.value}`)
        .join('\n');
    }

    this.setData({
      showEditModal: true,
      editForm: {
        content: currentQuestion.content || '',
        options: optionsText,
        answer: currentQuestion.answer || '',
        explanation: currentQuestion.explanation || '',
        showOptions
      }
    });
  },

  onCloseEditModal() {
    this.setData({ showEditModal: false });
  },

  onEditContentInput(e: any) {
    this.setData({ 'editForm.content': e.detail.value });
  },

  onEditOptionsInput(e: any) {
    this.setData({ 'editForm.options': e.detail.value });
  },

  onEditAnswerInput(e: any) {
    this.setData({ 'editForm.answer': e.detail.value });
  },

  onEditExplanationInput(e: any) {
    this.setData({ 'editForm.explanation': e.detail.value });
  },

  async onSaveQuestion() {
    const { currentQuestion, editForm, editSaving, sourceType, sourceId } = this.data;
    if (!currentQuestion || editSaving) return;

    if (!editForm.content.trim()) {
      wx.showToast({ title: '题干不能为空', icon: 'none' });
      return;
    }

    if (!editForm.answer.trim()) {
      wx.showToast({ title: '答案不能为空', icon: 'none' });
      return;
    }

    this.setData({ editSaving: true });

    try {
      // 解析选项
      let options: Array<{ key: string; value: string }> | undefined;
      if (editForm.showOptions && editForm.options.trim()) {
        options = editForm.options
          .split('\n')
          .map(line => line.trim())
          .filter(line => line)
          .map(line => {
            const match = line.match(/^([A-Za-z0-9]{1,3})\s*[、.．:：]\s*(.+)$/);
            if (match) {
              return { key: match[1].toUpperCase(), value: match[2].trim() };
            }
            return { key: '', value: line };
          });
      }

      const updateData = {
        content: editForm.content.trim(),
        options,
        answer: editForm.answer.trim(),
        explanation: editForm.explanation.trim() || undefined
      };

      if (sourceType === 'bank') {
        await api.updateBankQuestion(Number(sourceId), currentQuestion.id, updateData);
      } else {
        await api.updateQuestion(currentQuestion.id, updateData);
      }

      // 更新当前题目数据
      const updatedQuestion = {
        ...currentQuestion,
        content: editForm.content.trim(),
        answer: editForm.answer.trim(),
        explanation: editForm.explanation.trim()
      };

      if (options) {
        updatedQuestion.options = options;
      }

      // 更新题目列表中的数据
      const questions = this.data.questions.map((q: any) => {
        if (q.id === currentQuestion.id) {
          return { ...q, ...updatedQuestion };
        }
        return q;
      });

      this.setData({
        currentQuestion: updatedQuestion,
        questions,
        showEditModal: false,
        editSaving: false
      });

      // 刷新显示
      this.refreshDisplayOptions();

      wx.showToast({ title: '保存成功', icon: 'success' });
    } catch (err: any) {
      
      this.setData({ editSaving: false });
      wx.showToast({ title: err.message || '保存失败', icon: 'none' });
    }
  },

  normalizeOptions(rawOptions: any, qType: string, correctAnswer?: string): OptionItem[] {
    let optList: any = rawOptions;

    if (typeof optList === 'string') {
      const s = optList.trim();
      if (!s) {
        optList = [];
      } else {
        try {
          optList = JSON.parse(s);
        } catch (e) {
          // ignore parse error and fallback to plain text
          optList = [s];
        }
      }
    }

    if (!Array.isArray(optList)) {
      optList = [];
    }

    if (qType === '判断题') {
      const ans = (correctAnswer || '').toString().trim();
      // 如果答案是字母（少数历史格式），优先使用题目自带 options
      if (!/^[A-Za-z]$/.test(ans)) {
        const normalized = ans.toLowerCase();
        let trueText = '正确';
        let falseText = '错误';

        if (normalized === '对' || normalized === '错') {
          trueText = '对';
          falseText = '错';
        } else if (normalized === '是' || normalized === '否') {
          trueText = '是';
          falseText = '否';
        } else if (normalized === 'true' || normalized === 'false') {
          trueText = 'True';
          falseText = 'False';
        }

        return [
          { key: 'A', value: trueText, answerValue: trueText },
          { key: 'B', value: falseText, answerValue: falseText }
        ];
      }
    }

    const options: OptionItem[] = [];
    for (const item of optList) {
      if (item && typeof item === 'object') {
        const rawKey = (item as any).key;
        const rawValue = (item as any).value;
        const key = String(rawKey == null ? '' : rawKey).trim();
        const value = stripHtmlToText(rawValue);
        if (key || value) {
          options.push({ key, value, answerValue: key || value });
        }
        continue;
      }

      const s = stripHtmlToText(item);
      if (!s) {
        continue;
      }

      // 解析 "A、xxx" / "A.xxx" / "A：xxx"
      const m = s.match(/^([A-Za-z0-9]{1,3})\s*[、.．:：]\s*(.+)$/);
      if (m) {
        const key = m[1].trim().slice(0, 1).toUpperCase();
        const value = m[2].trim();
        options.push({ key, value, answerValue: key });
        continue;
      }

      // 兜底：仅当更像“无分隔符的选项前缀”（如 A正确 / 1正确）时才把首字符当 key，避免把 Tony/Gaddis 误当 key
      const first = s.slice(0, 1).toUpperCase();
      const second = s.slice(1, 2);
      if (first && 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.includes(first) && second && !/[A-Za-z0-9]/.test(second)) {
        const value = s.slice(1).replace(/^[\s:：,，.．、\)\]]+/, '').trim();
        options.push({ key: first, value, answerValue: first });
        continue;
      }

      options.push({ key: '', value: s, answerValue: s });
    }

    // 如果 key 全为空，补 A/B/C...（仅用于展示，答题用 answerValue 仍保持原始 value）
    if (options.length > 0 && options.every((x) => !(x.key || '').trim())) {
      const seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      options.forEach((x, i) => {
        x.key = seed[i] || String(i + 1);
      });
    }

    return options;
  },

  refreshDisplayOptions() {
    const { currentQuestion, selectedAnswer, selectedAnswers, showAnswer, mode } = this.data;
    if (!currentQuestion) {
      this.setData({ displayOptions: [] });
      return;
    }

    const qType: QuestionType = currentQuestion.q_type || '';
    const correctAnswer = (currentQuestion.answer || '').toString();
    const correctAnswerNormalized = correctAnswer.trim().toLowerCase();
    const shouldShowResult = showAnswer || mode === 'memo';

    const normalizedOptions = this.normalizeOptions(currentQuestion.options, qType, currentQuestion.answer);

    const displayOptions: DisplayOption[] = normalizedOptions.map((opt) => {
      const isSelected =
        qType === '多选题' ? selectedAnswers.indexOf(opt.answerValue) > -1 : selectedAnswer === opt.answerValue;

      const isCorrect = shouldShowResult
        ? correctAnswerNormalized.indexOf(opt.answerValue.toString().trim().toLowerCase()) > -1
        : false;
      const isWrong = showAnswer ? isSelected && !isCorrect : false;

      const classParts: string[] = [];
      if (isSelected) classParts.push('selected');
      if (isCorrect) classParts.push('correct');
      if (isWrong) classParts.push('wrong');

      const displayValue = this.looksLikeCode(opt.value) ? this.preserveSpacesForCode(opt.value) : opt.value;

      return {
        key: opt.key,
        value: displayValue,
        answerValue: opt.answerValue,
        isSelected,
        isCorrect,
        isWrong,
        className: classParts.join(' ')
      };
    });

    this.setData({
      displayOptions,
      currentQuestion: Object.assign({}, currentQuestion, { options: normalizedOptions })
    });
  },

  isAutoJudgable(qType: QuestionType): boolean {
    return qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题';
  },

  updateSubmitState() {
    const { currentQuestion, mode, showAnswer, selectedAnswers, selectedAnswer, blankAnswers } = this.data;
    if (!currentQuestion || (mode !== 'quiz' && mode !== 'reinforce') || showAnswer) {
      this.setData({ showSubmitButton: false, submitDisabled: true });
      return;
    }

    const qType: QuestionType = currentQuestion.q_type || '';
    const showSubmit =
      qType === '多选题' || qType === '填空题' || qType === '简答题' || qType === '问答题' || qType === '计算题';

    let disabled = true;
    if (qType === '多选题') {
      disabled = selectedAnswers.length === 0;
    } else if (qType === '填空题') {
      disabled = !blankAnswers.length || blankAnswers.some((x) => !(x || '').trim());
    } else if (qType === '简答题' || qType === '问答题' || qType === '计算题') {
      disabled = !(selectedAnswer || '').trim();
    } else {
      disabled = true;
    }

    this.setData({ showSubmitButton: showSubmit, submitDisabled: showSubmit ? disabled : true });
  },

  initBlankState(
    qType: QuestionType,
    content: string,
    answer: string
  ): { blankCount: number; blankAnswers: string[]; blankIndexes: number[] } {
    if (qType !== '填空题') {
      return { blankCount: 0, blankAnswers: [], blankIndexes: [] };
    }

    const contentCount = (content.match(/__/g) || []).length;
    const normalizedAnswer = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
    const answerCount = normalizedAnswer.split(';;').length;
    const blankCount = Math.max(1, contentCount || 0, answerCount || 0);
    return {
      blankCount,
      blankAnswers: Array.from({ length: blankCount }, () => ''),
      blankIndexes: Array.from({ length: blankCount }, (_, i) => i)
    };
  },

  formatContentForDisplay(content: string): string {
    return stripHtmlToText(content);
  },

  looksLikeCode(text: string): boolean {
    const s = (text || '').toString();
    if (!s.includes('\n')) return false;
    const hasIndent = /(^|\n)[ \t]{2,}\S/.test(s);
    const hasCodeTokens =
      /\b(for|while|if|else|elif|def|class|print|return|break|continue|import|from|int|float|public|private|static|void|main)\b/.test(
        s
      );
    const hasSymbols = /[{}();=<>]/.test(s);
    return hasIndent || hasCodeTokens || hasSymbols;
  },

  preserveSpacesForCode(text: string): string {
    const s = (text || '').toString().replace(/\t/g, '  ');
    // 小程序 <text> 会折叠连续空格；代码场景将空格替换为 NBSP 保留缩进/对齐
    return s
      .split('\n')
      .map((line) => line.replace(/ /g, '\u00A0'))
      .join('\n');
  },

  formatAnswerForDisplay(qType: QuestionType, answer: string): string {
    const a = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
    if (qType === '填空题') {
      return a.replace(/;;/g, ' / ').replace(/;/g, ' 或 ');
    }
    return a;
  },

  buildProgressKey(): string {
    // 使用数据源适配器构建进度key
    if (quizSource) {
      return quizSource.buildProgressKey(this.data.mode as 'quiz' | 'memo' | 'reinforce', {
        type: this.data.qType,
        source: this.data.source,
        tag: this.data.tag,
        rk: this.data.reinforceKind,
        shuffleQuestions: this.data.shuffleQuestions,
        shuffleOptions: this.data.shuffleOptions
      });
    }

    // 兜底：手动构建（不应该到达这里）
    const userInfo = wx.getStorageSync('userInfo') || {};
    const uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';

    const mode = (this.data.mode || 'quiz').toString();
    const rawSourceId = String(this.data.sourceId || 'all');
    const sourceId = (this.data.sourceType === 'bank' && mode === 'reinforce') ? `bank_${rawSourceId}` : rawSourceId;
    const type = (this.data.qType || 'all').toString();

    const sourceParam = (this.data.source || '').toString();
    const dataScope = (sourceParam === 'favorites' || sourceParam === 'mistakes') ? sourceParam : 'all';
    const tag = (this.data.tag || '').toString();
    const tagPart = tag && tag.toLowerCase() !== 'all' ? `_tag${tag}` : '';

    const shuffleQ = this.data.shuffleQuestions ? '1' : '0';
    const shuffleO = this.data.shuffleOptions ? '1' : '0';

    const prefix = this.data.sourceType === 'bank' ? 'bank_quiz_progress' : 'quiz_progress';

    let rkPart = '';
    if (mode === 'reinforce') {
      const rk = String(this.data.reinforceKind || '').trim().toLowerCase();
      if (rk === 'wrong' || rk === 'similar') rkPart = `_rk${rk}`;
    }

    // reinforce 模式：对齐 Web 的 progressKey()（user_bank 也使用 quiz_progress）
    if (mode === 'reinforce') {
      return `quiz_progress_${uid}_${mode}_${sourceId}_${type}_${dataScope}${tagPart}${rkPart}_q${shuffleQ}_o${shuffleO}`;
    }

    return `${prefix}_${uid}_${mode}_${sourceId}_${type}_${dataScope}${tagPart}_q${shuffleQ}_o${shuffleO}`;
  },

  async loadProgressState(key: string): Promise<any | null> {
    if (!key) return null;

    const local = this.safeParseStorage(wx.getStorageSync(key));
    let remote: any = null;
    try {
      remote = await api.getProgress(key);
    } catch (e) {
      remote = null;
    }

    const merged = this.pickLatestProgress(local, remote);
    if (merged) {
      try {
        wx.setStorageSync(key, merged);
      } catch (e) {}
    }
    return merged;
  },

  safeParseStorage(val: any): any | null {
    if (!val) return null;
    if (typeof val === 'string') {
      try {
        return JSON.parse(val);
      } catch (e) {
        return null;
      }
    }
    if (typeof val === 'object') return val;
    return null;
  },

  pickLatestProgress(a: any, b: any): any | null {
    if (!a && !b) return null;
    if (a && !b) return a;
    if (!a && b) return b;

    const ta = Number(a && a.timestamp) || 0;
    const tb = Number(b && b.timestamp) || 0;
    return tb >= ta ? b : a;
  },

  applyQuestionOrder(questions: any[], order: any[]): any[] {
    try {
      const map = new Map<number, any>();
      questions.forEach((q: any) => {
        if (q && typeof q.id === 'number') map.set(q.id, q);
      });

      const ordered: any[] = [];
      order.forEach((id: any) => {
        const qid = Number(id);
        if (!isFinite(qid)) return;
        const hit = map.get(qid);
        if (hit) {
          ordered.push(hit);
          map.delete(qid);
        }
      });

      if (map.size > 0) {
        ordered.push(...Array.from(map.values()));
      }
      return ordered;
    } catch (e) {
      return questions;
    }
  },

  buildAnswerRecordsFromStatus(questions: any[], status: any): Record<number, { answered: boolean; isCorrect: boolean }> {
    const records: Record<number, { answered: boolean; isCorrect: boolean }> = {};
    if (!status || typeof status !== 'object') return records;

    Object.keys(status).forEach((k) => {
      const idx = Number(k);
      if (!isFinite(idx) || idx < 0 || idx >= questions.length) return;
      const v = status[k];
      if (v !== 'correct' && v !== 'wrong') return;
      const q = questions[idx];
      if (!q || typeof q.id !== 'number') return;
      records[q.id] = { answered: true, isCorrect: v === 'correct' };
    });

    return records;
  },

  getSavedAnswerForIndex(index: number): any {
    const map = this.progressAnswerMap;
    if (!map || typeof map !== 'object') return null;
    return map[String(index)];
  },

  getSavedStatusForIndex(index: number): any {
    const map = this.progressStatusMap;
    if (!map || typeof map !== 'object') return null;
    return map[String(index)];
  },

  setProgressAnswerForIndex(index: number, qType: QuestionType) {
    if (!this.progressAnswerMap || typeof this.progressAnswerMap !== 'object') {
      this.progressAnswerMap = {};
    }

    if (qType === '多选题') {
      this.progressAnswerMap[String(index)] = (this.data.selectedAnswers || []).slice();
      return;
    }
    if (qType === '选择题' || qType === '判断题') {
      const a = (this.data.selectedAnswer || '').trim();
      this.progressAnswerMap[String(index)] = a ? [a] : [];
      return;
    }
    if (qType === '填空题') {
      this.progressAnswerMap[String(index)] = (this.data.blankAnswers || []).slice();
      return;
    }

    // 问答/简答/计算
    this.progressAnswerMap[String(index)] = (this.data.selectedAnswer || '').toString();
  },

  saveDraftAnswer() {
    if ((this.data.mode !== 'quiz' && this.data.mode !== 'reinforce') || this.data.showAnswer) return;
    if (!this.data.currentQuestion) return;

    const qType: QuestionType = this.data.currentQuestion.q_type || '';
    this.setProgressAnswerForIndex(this.data.currentIndex, qType);
    this.saveProgressIndex(false);
  },

  saveProgressIndex(immediate: boolean) {
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    const payload: any = {
      index: this.data.currentIndex,
      status: this.progressStatusMap || {},
      answers: this.progressAnswerMap || {},
      timestamp: Date.now()
    };
    if (this.progressOrder) {
      payload.order = this.progressOrder;
    }

    this.saveProgressState(payload, immediate);
  },

  saveProgressState(payload: any, immediate: boolean) {
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    try {
      wx.setStorageSync(key, payload);
    } catch (e) {}

    this.lastSavedPayload = payload;
    this.syncPending = true;

    if (immediate) {
      if (this.saveProgressTimer) {
        clearTimeout(this.saveProgressTimer);
        this.saveProgressTimer = null;
      }
      this.syncToServer(payload);
      return;
    }

    if (this.saveProgressTimer) {
      clearTimeout(this.saveProgressTimer);
    }
    this.saveProgressTimer = setTimeout(() => {
      this.saveProgressTimer = null;
      this.syncToServer(payload);
    }, 200);
  },

  async syncToServer(payload: any) {
    if (!payload) return;
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    try {
      await api.saveProgress(key, payload);
      this.syncPending = false;
    } catch (e) {
      // 网络波动时保留本地进度即可
    }
  },

  // 保存"上次练习"指针（云端 + 本地），用于首页一键继续
  async saveLastSession(force = false) {
    const { sourceType, sourceId, displayName } = this.data;
    if (!sourceId) return;

    const payload: any = {
      source_type: sourceType,
      source_id: sourceId,
      display_name: displayName,
      mode: (this.data.mode || 'quiz').toString(),
      type: (this.data.qType || 'all').toString(),
      source: (this.data.source || 'all').toString(),
      shuffle_questions: this.data.shuffleQuestions ? 1 : 0,
      shuffle_options: this.data.shuffleOptions ? 1 : 0,
      progress_key: this.progressKey || this.buildProgressKey(),
      timestamp: Date.now()
    };

    // 兼容旧格式：如果是公有题库，仍保存 subject 字段
    if (sourceType === 'public') {
      payload.subject = String(sourceId);
    } else if (sourceType === 'bank') {
      payload.bank_id = Number(sourceId);
    }

    const key = 'last_practice_session';
    try {
      wx.setStorageSync(key, payload);
    } catch (e) {}

    // 避免频繁写云端：仅在强制 flush 时写一次
    if (!force) return;
    try {
      await api.saveProgress(key, payload);
    } catch (e) {}
  },

  onHide() {
    if (this.syncPending && this.lastSavedPayload) {
      this.saveProgressState(this.lastSavedPayload, true);
    }
    this.saveLastSession(true);
  },

  onUnload() {
    if (this.syncPending && this.lastSavedPayload) {
      this.saveProgressState(this.lastSavedPayload, true);
    }
    if (this.saveProgressTimer) {
      clearTimeout(this.saveProgressTimer);
      this.saveProgressTimer = null;
    }
    this.saveLastSession(true);
  },

  // === 滑屏切题 ===
  onTouchStart(e: any) {
    if (!e.touches || !e.touches.length) return;
    const touch = e.touches[0];
    this.setData({
      touchStartX: touch.clientX,
      touchStartY: touch.clientY
    });
  },

  onTouchEnd(e: any) {
    if (!e.changedTouches || !e.changedTouches.length) return;
    const touch = e.changedTouches[0];
    const { touchStartX, touchStartY, loading, currentQuestion } = this.data;

    // 未加载完成或无题目时不处理
    if (loading || !currentQuestion) return;

    const deltaX = touch.clientX - touchStartX;
    const deltaY = touch.clientY - touchStartY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    // 水平滑动距离 > 80px 且水平距离 > 垂直距离的 1.5 倍（避免误触）
    const swipeThreshold = 80;
    if (absDeltaX > swipeThreshold && absDeltaX > absDeltaY * 1.5) {
      if (deltaX > 0) {
        // 右滑 → 上一题
        this.onPrevQuestion();
      } else {
        // 左滑 → 下一题
        this.onNextQuestion();
      }
    }
  }
});


