/**
 * quiz-source.ts - 统一数据源适配器
 *
 * 将公有题库(subject)和个人题库(bank)统一为相同的接口，
 * 使页面代码可以复用，只需传入不同的数据源即可。
 */

import { api } from './api';

// ============================================
// 类型定义
// ============================================

/** 题目结构 */
export interface Question {
  id: number;
  content: string;
  q_type: string;
  options?: string | any[];
  answer?: string;
  explanation?: string;
  difficulty?: number;
  image_path?: string;
  subject?: string;
  bank_id?: number;
  [key: string]: any;
}

/** 用户统计 */
export interface UserCounts {
  total: number;
  favorites: number;
  mistakes: number;
}

/** 我的统计 */
export interface MyStats {
  total_answered: number;
  correct_count: number;
  wrong_count: number;
  accuracy: number;
}

/** 筛选参数 */
export interface FilterParams {
  type?: string;      // 题型
  source?: string;    // 来源：all/favorites/mistakes
}

/** 题目请求参数 */
export interface QuestionParams {
  mode?: string;              // quiz/memo
  source?: string;            // all/favorites/mistakes
  type?: string;              // 题型
  tag?: string;               // 标签（用户私有）
  shuffle_questions?: boolean;
  shuffle_options?: boolean;
  ids?: number[];             // 指定题目ID列表（用于加强训练等）
  page?: number;
  per_page?: number;
  limit?: number;
}

/** 搜索参数 */
export interface SearchParams {
  keyword: string;
  type?: string;
  source?: string;   // all/favorites/mistakes（公有题库可用；个人题库由后端支持）
  tag?: string;      // 标签筛选（用户私有）
  page?: number;
  per_page?: number;
}

/** 答题记录参数 */
export interface RecordParams {
  questionId: number;
  userAnswer?: string;
  isCorrect: boolean;
}

// ============================================
// 数据源接口
// ============================================

export interface IQuizSource {
  /** 数据源类型 */
  readonly sourceType: 'public' | 'bank';
  /** 标识符：subject名称 或 bank_id */
  readonly sourceId: string | number;
  /** 显示名称 */
  readonly displayName: string;

  /** 获取信息（名称、题型列表等） */
  getInfo(): Promise<{
    name: string;
    available_types: string[];
    question_count?: number;
    [key: string]: any;
  }>;

  /** 获取用户统计（总数、收藏数、错题数） */
  getUserCounts(params?: FilterParams): Promise<UserCounts>;

  /** 获取题目列表（用于刷题） */
  getQuestions(params?: QuestionParams): Promise<{
    questions: Question[];
    total: number;
  }>;

  /** 记录答题结果 */
  recordResult(params: RecordParams): Promise<void>;

  /** 切换收藏 */
  toggleFavorite(questionId: number): Promise<{ is_favorite: boolean }>;

  /** 搜索题目 */
  searchQuestions(params: SearchParams): Promise<{
    questions: Question[];
    total: number;
  }>;

  /** 获取我的答题统计 */
  getMyStats(): Promise<MyStats>;

  /** 删除刷题进度 */
  deleteProgress(key: string): Promise<void>;

  /** 构建进度存储key */
  buildProgressKey(mode: 'quiz' | 'memo' | 'reinforce', options: {
    type?: string;
    source?: string;
    tag?: string;
    rk?: 'wrong' | 'similar' | '';
    shuffleQuestions?: boolean;
    shuffleOptions?: boolean;
  }): string;
}

// ============================================
// 公有题库数据源
// ============================================

export class PublicQuizSource implements IQuizSource {
  readonly sourceType = 'public' as const;
  readonly sourceId: string;
  displayName: string = '';

  constructor(subject: string) {
    this.sourceId = subject;
    this.displayName = subject;
  }

  async getInfo() {
    const res: any = await api.getSubjectInfo(this.sourceId);
    const info = res.data || res || {};
    this.displayName = info.name || this.sourceId;
    return {
      name: info.name || this.sourceId,
      available_types: Array.isArray(info.available_types) ? info.available_types : [],
      question_count: info.question_count || 0,
      ...info
    };
  }

  async getUserCounts(params?: FilterParams): Promise<UserCounts> {
    const { type, source } = params || {};

    // 获取总题数（基于当前范围和题型）
    const countParams: any = { subject: this.sourceId };
    if (type && type !== 'all') {
      countParams.type = type;
    }
    if (source && source !== 'all') {
      countParams.source = source;
    }
    const totalRes = await api.getQuestionsCount(countParams);

    // 获取用户收藏和错题数量（基于当前题型）
    const userRes = await api.getUserCounts({
      subject: this.sourceId,
      type: type && type !== 'all' ? type : undefined
    });

    return {
      total: (totalRes as any).count || 0,
      favorites: (userRes as any).favorites || 0,
      mistakes: (userRes as any).mistakes || 0
    };
  }

  async getQuestions(params?: QuestionParams) {
    const apiParams: any = {
      subject: this.sourceId
    };

    if (params?.type && params.type !== 'all') {
      apiParams.q_type = params.type;
    }
    if (params?.tag && params.tag !== 'all') {
      apiParams.tag = params.tag;
    }
    if (params?.source && params.source !== 'all') {
      apiParams.source = params.source;
    }
    if (params?.mode) {
      apiParams.mode = params.mode;
    }
    if (params?.shuffle_questions) {
      apiParams.shuffle_questions = 1;
    }
    if (params?.shuffle_options) {
      apiParams.shuffle_options = 1;
    }
    // Reinforce / 指定题目：按 ids 拉题（与 Web /quiz?ids=... 对齐）
    if (params?.ids && Array.isArray(params.ids) && params.ids.length > 0) {
      const ids = params.ids
        .map((x) => Number(x))
        .filter((n) => Number.isFinite(n) && n > 0)
        .map((n) => Math.floor(n));
      apiParams.ids = ids.join(',');
    }
    if (params?.page) {
      apiParams.page = params.page;
    }
    if (params?.per_page) {
      apiParams.per_page = params.per_page;
    }

    const res: any = await api.getQuestions(apiParams);
    return {
      questions: res.questions || res || [],
      total: res.total || (res.questions || res || []).length
    };
  }

  async recordResult(params: RecordParams) {
    await api.recordResult(params.questionId, params.isCorrect);
  }

  async toggleFavorite(questionId: number) {
    const res: any = await api.toggleFavorite(questionId);
    return { is_favorite: res.is_favorite ?? true };
  }

  async searchQuestions(params: SearchParams) {
    const apiParams: any = {
      keyword: params.keyword,
      subject: this.sourceId
    };
    if (params.type && params.type !== 'all') {
      apiParams.q_type = params.type;
    }
    if (params.source && params.source !== 'all') {
      apiParams.source = params.source;
    }
    if (params.tag && params.tag !== 'all') {
      apiParams.tag = params.tag;
    }
    if (params.page) {
      apiParams.page = params.page;
    }
    if (params.per_page) {
      apiParams.per_page = params.per_page;
    }

    const res: any = await api.searchQuestions(apiParams);
    return {
      questions: res.questions || res || [],
      total: res.total || (res.questions || res || []).length
    };
  }

  async getMyStats(): Promise<MyStats> {
    // 公有题库暂无独立的统计接口，返回默认值
    // 可以通过 getUserCounts 获取部分数据
    const counts = await this.getUserCounts();
    return {
      total_answered: 0,  // 需要后端支持
      correct_count: 0,
      wrong_count: counts.mistakes,
      accuracy: 0
    };
  }

  async deleteProgress(key: string) {
    await api.deleteProgress(key);
  }

  buildProgressKey(mode: 'quiz' | 'memo' | 'reinforce', options: {
    type?: string;
    source?: string;
    tag?: string;
    rk?: 'wrong' | 'similar' | '';
    shuffleQuestions?: boolean;
    shuffleOptions?: boolean;
  }): string {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const uid = (userInfo.id || userInfo.user_id) ? String(userInfo.id || userInfo.user_id) : 'guest';

    const subject = this.sourceId || 'all';
    const type = options.type || 'all';
    const dataScope = (options.source === 'favorites' || options.source === 'mistakes') ? options.source : 'all';
    const tag = (options.tag || '').toString();
    const tagPart = tag && tag.toLowerCase() !== 'all' ? `_tag${tag}` : '';
    const shuffleQ = options.shuffleQuestions ? '1' : '0';
    const shuffleO = options.shuffleOptions ? '1' : '0';
    let rkPart = '';
    if (mode === 'reinforce') {
      const rk = String(options.rk || '').trim().toLowerCase();
      if (rk === 'wrong' || rk === 'similar') rkPart = `_rk${rk}`;
    }

    return `quiz_progress_${uid}_${mode}_${subject}_${type}_${dataScope}${tagPart}${rkPart}_q${shuffleQ}_o${shuffleO}`;
  }
}

// ============================================
// 个人题库数据源
// ============================================

export class BankQuizSource implements IQuizSource {
  readonly sourceType = 'bank' as const;
  readonly sourceId: number;
  displayName: string = '';

  constructor(bankId: number) {
    this.sourceId = bankId;
  }

  async getInfo() {
    const res: any = await api.getBankDetail(this.sourceId);
    const info = res.data || res || {};
    this.displayName = info.name || `题库${this.sourceId}`;
    return {
      name: info.name || `题库${this.sourceId}`,
      available_types: Array.isArray(info.available_types) ? info.available_types : [],
      question_count: info.question_count || 0,
      permission: info.permission,
      access_type: info.access_type,
      ...info
    };
  }

  async getUserCounts(params?: FilterParams): Promise<UserCounts> {
    const apiParams: any = {};
    if (params?.type && params.type !== 'all') {
      apiParams.q_type = params.type;
    }
    if (params?.source && params.source !== 'all') {
      apiParams.source = params.source;
    }

    const res: any = await api.getBankUserCounts(this.sourceId, apiParams);
    const data = res.data || res || {};
    return {
      total: data.total || 0,
      favorites: data.favorites || 0,
      mistakes: data.mistakes || 0
    };
  }

  async getQuestions(params?: QuestionParams) {
    const apiParams: any = {};

    // 个人题库使用不同的模式映射
    if (params?.source === 'mistakes') {
      apiParams.mode = 'wrong';
    } else if (params?.source === 'favorites') {
      apiParams.mode = 'favorites';
    } else {
      apiParams.mode = 'all';
    }

    // 加强训练等：指定题目列表优先
    if (params?.ids && Array.isArray(params.ids) && params.ids.length > 0) {
      const ids = params.ids
        .map((x) => Number(x))
        .filter((n) => Number.isFinite(n) && n > 0)
        .map((n) => Math.floor(n));
      apiParams.ids = ids.join(',');
    }

    // 题型/标签筛选（与公共题库参数保持一致）
    if (params?.type && params.type !== 'all') {
      apiParams.q_type = params.type;
    }
    if (params?.tag && params.tag !== 'all') {
      apiParams.tag = params.tag;
    }

    // 兼容 quiz 页面传 per_page=1000 的用法
    const limit = params?.limit || params?.per_page || 1000;
    if (limit) {
      apiParams.limit = limit;
    }

    const res: any = await api.getBankQuizQuestions(this.sourceId, apiParams);
    let questions = res.questions || res || [];

    // 如果需要打乱题目
    if (params?.shuffle_questions && Array.isArray(questions)) {
      questions = [...questions].sort(() => Math.random() - 0.5);
    }

    // 如果需要打乱选项（仅选择题/多选题）
    if (params?.shuffle_options && Array.isArray(questions)) {
      const optionTypes = new Set(['选择题', '多选题']);
      questions = questions.map((q: Question) => {
        if (!optionTypes.has((q as any).q_type || '')) return q;
        if (q.options) {
          let opts = q.options;
          if (typeof opts === 'string') {
            try {
              opts = JSON.parse(opts);
            } catch (e) {
              opts = [];
            }
          }
          if (Array.isArray(opts) && opts.length > 0) {
            const shuffled = [...opts].sort(() => Math.random() - 0.5);
            return { ...q, options: shuffled };
          }
        }
        return q;
      });
    }

    return {
      questions,
      total: res.total || questions.length
    };
  }

  async recordResult(params: RecordParams) {
    await api.recordBankQuizResult(this.sourceId, {
      question_id: params.questionId,
      user_answer: params.userAnswer || '',
      is_correct: params.isCorrect
    });
  }

  async toggleFavorite(questionId: number) {
    const res: any = await api.toggleBankFavorite(this.sourceId, questionId);
    return { is_favorite: res.is_favorite ?? false };
  }

  async searchQuestions(params: SearchParams) {
    const apiParams: any = {
      keyword: params.keyword
    };
    if (params.type && params.type !== 'all') {
      apiParams.q_type = params.type;
    }
    if (params.source && params.source !== 'all') {
      apiParams.source = params.source;
    }
    if (params.tag && params.tag !== 'all') {
      apiParams.tag = params.tag;
    }
    if (params.page) {
      apiParams.page = params.page;
    }
    if (params.per_page) {
      apiParams.per_page = params.per_page;
    }

    const res: any = await api.searchBankQuestions(this.sourceId, apiParams);
    const data = res.data || res || {};
    return {
      questions: data.questions || [],
      total: data.total || (data.questions || []).length
    };
  }

  async getMyStats(): Promise<MyStats> {
    const res: any = await api.getBankMyStats(this.sourceId);
    const data = res.data || res || {};
    return {
      total_answered: data.total_answered || 0,
      correct_count: data.correct_count || 0,
      wrong_count: data.wrong_count || 0,
      accuracy: data.accuracy || 0
    };
  }

  async deleteProgress(key: string) {
    await api.deleteProgress(key);
  }

  buildProgressKey(mode: 'quiz' | 'memo' | 'reinforce', options: {
    type?: string;
    source?: string;
    tag?: string;
    rk?: 'wrong' | 'similar' | '';
    shuffleQuestions?: boolean;
    shuffleOptions?: boolean;
  }): string {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const uid = (userInfo.id || userInfo.user_id) ? String(userInfo.id || userInfo.user_id) : 'guest';

    const bankId = this.sourceId || 0;
    const subject = bankId ? `bank_${bankId}` : 'all';
    const type = options.type || 'all';
    const dataScope = (options.source === 'favorites' || options.source === 'mistakes') ? options.source : 'all';
    const tag = (options.tag || '').toString();
    const tagPart = tag && tag.toLowerCase() !== 'all' ? `_tag${tag}` : '';
    const shuffleQ = options.shuffleQuestions ? '1' : '0';
    const shuffleO = options.shuffleOptions ? '1' : '0';
    let rkPart = '';
    if (mode === 'reinforce') {
      const rk = String(options.rk || '').trim().toLowerCase();
      if (rk === 'wrong' || rk === 'similar') rkPart = `_rk${rk}`;
    }

    // reinforce 模式：对齐 Web 的 progressKey()（subject=bank_<id>，prefix=quiz_progress）
    if (mode === 'reinforce') {
      return `quiz_progress_${uid}_${mode}_${subject}_${type}_${dataScope}${tagPart}${rkPart}_q${shuffleQ}_o${shuffleO}`;
    }

    return `bank_quiz_progress_${uid}_${mode}_${bankId}_${type}_${dataScope}${tagPart}_q${shuffleQ}_o${shuffleO}`;
  }
}

// ============================================
// 工厂函数
// ============================================

export interface SourceOptions {
  subject?: string;
  bankId?: number;
}

/**
 * 创建数据源
 * @param options.subject - 公有题库科目名
 * @param options.bankId - 个人题库ID
 */
export function createQuizSource(options: SourceOptions): IQuizSource {
  if (options.bankId) {
    return new BankQuizSource(options.bankId);
  }
  if (options.subject) {
    return new PublicQuizSource(options.subject);
  }
  throw new Error('必须提供 subject 或 bankId');
}

/**
 * 从页面参数创建数据源
 * @param options - 页面 onLoad 的 options 参数
 */
export function createSourceFromOptions(options: {
  subject?: string;
  bank_id?: string | number;
  bankId?: string | number;
}): IQuizSource | null {
  const bankId = options.bank_id || options.bankId;
  if (bankId) {
    return new BankQuizSource(Number(bankId));
  }
  if (options.subject) {
    try {
      return new PublicQuizSource(decodeURIComponent(options.subject));
    } catch {
      return new PublicQuizSource(options.subject);
    }
  }
  return null;
}

/**
 * 获取数据源的显示标签
 */
export function getSourceLabel(source: IQuizSource): string {
  if (source.sourceType === 'bank') {
    return '个人题库';
  }
  return '公有题库';
}
