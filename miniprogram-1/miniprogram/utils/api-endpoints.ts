// API 端点定义（基础设施已提取到 api-client.ts 和 url-utils.ts）
import { request, normalizeDataCenterContext } from './api-client';
import { getApiBaseUrl, getApiOrigin, resolveUploadUrl, normalizeImageUrls } from './url-utils';
import { getWxPlatform } from './config';
import { memoryCache } from './memory-cache';

// 保持向后兼容的导出
export { getApiOrigin, resolveUploadUrl, normalizeImageUrls };
export { request };

let hasShownUploadDevHostHint = false;
function maybeShowUploadDevHostHint(apiBaseUrl: string, message: string): void {
  if (hasShownUploadDevHostHint) return;

  const msg = String(message || '');
  try {
    const envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
    if (envVersion !== 'develop') return;
  } catch (e) {}

  let isDevtools = false;
  try {
    isDevtools = getWxPlatform() === 'devtools';
  } catch (e) {}

  const isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
  if (!isLocalhost) return;

  const normalizedMsg = msg.toLowerCase();
  const isConnRefused =
    msg.includes('ERR_CONNECTION_REFUSED') ||
    msg.includes('errcode:-102') ||
    msg.includes('cronet_error_code:-102') ||
    normalizedMsg.includes('connection refused');
  const isGenericUploadFail = msg.trim() === 'uploadFile:fail' || msg.trim() === 'request:fail';
  if (!isConnRefused && !(isDevtools && isGenericUploadFail)) return;

  hasShownUploadDevHostHint = true;
  wx.showModal({
    title: '无法连接后端',
    content: `当前 API 地址为：${apiBaseUrl}\n\n请确认 Docker 开发服务正在运行，或到「开发设置」调整 API Host/Port 后重试。`,
    confirmText: '去设置',
    cancelText: '知道了',
    success: (res) => {
      if (!res.confirm) return;
      wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
    }
  });
}

// 导出API方法
export const api = {
  // 微信登录
  wechatLogin: (code: string, userInfo?: any, allowCreate: boolean = true) =>
    request('/wechat/login', 'POST', { code, user_info: userInfo, allow_create: allowCreate }),

  // 微信：未绑定时创建新账号
  wechatCreate: (wechatTempToken: string, userInfo?: { avatarUrl?: string | null; nickName?: string | null }) =>
    request('/wechat/create', 'POST', { wechat_temp_token: wechatTempToken, user_info: userInfo }),

  // 微信：绑定已有账号（邮箱验证码）
  wechatBindSendCode: (wechatTempToken: string, email: string) =>
    request('/wechat/bind/send_code', 'POST', { wechat_temp_token: wechatTempToken, email }),

  wechatBindPassword: (wechatTempToken: string, account: string, password: string) =>
    request('/wechat/bind', 'POST', {
      wechat_temp_token: wechatTempToken,
      bind_mode: 'password',
      account,
      password
    }),

  wechatBindEmailCode: (wechatTempToken: string, email: string, code: string) =>
    request('/wechat/bind', 'POST', {
      wechat_temp_token: wechatTempToken,
      bind_mode: 'email_code',
      email,
      code
    }),

  // Web 扫码登录：小程序确认
  webLoginConfirm: (sid: string, nonce: string) =>
    request('/web_login/confirm', 'POST', { sid, nonce }),

  // 小程序：获取用于 web-view 打开「Web 前台」的一次性登录跳转
  getMiniWebViewUrl: (next: string = '/hub') =>
    request('/web_login/mini_webview_url', 'POST', { next }) as Promise<{ path: string; token_expires_at?: number }>,

  // Web 账号管理：绑定微信（小程序确认，使用 wx.login code）
  webWechatBindConfirm: (sid: string, nonce: string, code: string) =>
    request('/wechat/bind_confirm', 'POST', { sid, nonce, code }),

  // === 小程序：邮箱/手机号 + 密码登录（JWT） ===
  miniPasswordLogin: (account: string, password: string) =>
    request('/mini/login', 'POST', { account, password }),

  miniSendEmailLoginCode: (email: string) =>
    request('/mini/email/send-login-code', 'POST', { email }),

  miniEmailLogin: (email: string, code: string) =>
    request('/mini/email/login', 'POST', { email, code }),

  // 小程序：已登录用户绑定微信（密码/邮箱登录后引导绑定）
  miniWechatBind: (code: string) =>
    request('/mini/wechat/bind', 'POST', { code }),

  getAuthLoginMethods: () =>
    request('/auth/login-methods', 'GET') as Promise<{
      phone_login_enabled: boolean;
      wechat_login_enabled: boolean;
      default_mode: 'phone' | 'qr' | 'password' | 'code';
    }>,

  // 小程序：忘记密码 — 发送验证码
  miniSendForgotPasswordCode: (email: string) =>
    request('/mini/forgot-password/send-code', 'POST', { email }),

  // 小程序：忘记密码 — 重置密码
  miniResetPassword: (email: string, code: string, new_password: string) =>
    request('/mini/forgot-password/reset', 'POST', { email, code, new_password }),
  
  // 获取科目列表
  getSubjects: () => request('/quiz/subjects', 'GET'),

  // 获取科目元信息（id/name/题量）
  getSubjectsMeta: () =>
    request('/quiz/subjects/meta', 'GET') as Promise<{
      subjects: Array<{ id: number; name: string; question_count: number }>;
      quiz_count: number;
    }>,

  // 题库广场：公开题库列表（系统题库 + 用户公开题库）
  getPublicBanks: (params?: {
    page?: number;
    per_page?: number;
    sort?: 'newest' | 'popular' | 'questions';
    keyword?: string;
    type?: '' | 'system' | 'user';
  }) =>
    request('/public/banks', 'GET', params || {}) as Promise<{
      banks: Array<{
        id: number;
        name: string;
        description?: string;
        question_count?: number;
        use_count?: number;
        allow_copy?: number;
        is_shared?: number | boolean;
        cover_image?: string | null;
        public_at?: string;
        created_at?: string;
        owner_id?: number | null;
        owner_nickname?: string;
        owner_avatar?: string;
        join_mode?: 'free' | 'member' | 'paid' | 'approval' | string;
        join_note?: string;
        relation?: {
          joined_via?: string;
          is_joined?: boolean;
        };
        source_type?: string;
        source_label?: string;
        participants_total?: number;
        answer_users_7d?: number;
        bank_type: 'system' | 'user';
      }>;
      total: number;
      page: number;
    }>,

  getPublicBankCard: (sourceType: 'system' | 'user', bankId: number) =>
    request(`/public/banks/card/${encodeURIComponent(sourceType)}/${encodeURIComponent(String(bankId))}`, 'GET') as Promise<{
      id: number;
      bank_type: 'system' | 'user';
      source_type?: string;
      source_label?: string;
      name: string;
      description?: string;
      cover_image?: string | null;
      owner_label?: string;
      owner_avatar?: string | null;
      question_count?: number;
      participants_total?: number;
      answer_users_7d?: number;
      published_at?: string;
      last_activity_at?: string;
      join_mode?: 'free' | 'member' | 'paid' | 'approval' | string;
      join_note?: string;
      allow_copy?: boolean;
      is_owner?: boolean;
      relation?: {
        joined_via?: string;
        is_joined?: boolean;
      };
      board?: {
        id?: number | null;
        slug?: string | null;
        name?: string | null;
      };
      practice_url?: string;
      detail_url?: string;
    }>,

  joinPublicBank: (sourceType: 'system' | 'user', bankId: number) =>
    request(`/public/banks/${encodeURIComponent(sourceType)}/${encodeURIComponent(String(bankId))}/join`, 'POST', {}) as Promise<{
      joined?: boolean;
      self_owned?: boolean;
      source_type?: string;
    }>,

  leavePublicBank: (sourceType: 'system' | 'user', bankId: number) =>
    request(`/public/banks/${encodeURIComponent(sourceType)}/${encodeURIComponent(String(bankId))}/join`, 'DELETE', {}) as Promise<{
      joined?: boolean;
      source_type?: string;
    }>,
  
  // 获取题目列表
  getQuestions: (params: {
    subject?: string;
    q_type?: string;
    mode?: string;
    tag?: string;
    source?: string;
    shuffle_questions?: string | number;
    shuffle_options?: string | number;
    full_load?: string | number;
    load_all?: string | number;
    page?: number;
    per_page?: number;
  }) => request('/quiz/questions', 'GET', params),
  
  // 获取题目详情
  getQuestionDetail: (id: number) => request(`/quiz/questions/${id}`, 'GET'),

  // 搜索题目（用于小程序搜索页）
  searchQuestions: (params: {
    keyword: string;
    subject?: string;
    q_type?: string;
    type?: string; // 兼容字段
    source?: string;
    tag?: string;
    page?: number;
    per_page?: number;
  }) => request('/quiz/search', 'GET', params),
  
  // 记录答题结果
  recordResult: (questionId: number, isCorrect: boolean) =>
    request('/quiz/record_result', 'POST', {
      question_id: questionId,
      is_correct: isCorrect
    }),

  // 主观题判分（公共题库与个人题库共用）
  gradeSubjective: (payload: {
    question_id: number | string;
    user_answer: string;
    grading_mode?: 'auto_full' | 'ai' | 'manual' | string;
    source?: 'user_bank' | 'bank' | 'public' | string;
    bank_id?: number | string | null;
  }) => request('/quiz/grade_subjective', 'POST', payload),
  
  // 切换收藏
  toggleFavorite: (questionId: number) =>
    request('/quiz/favorite', 'POST', { question_id: questionId }),

  // AI 解析（占位/可替换为真实 AI）
  aiExplain: (payload: { question_id?: number; content?: string; q_type?: string; options?: any }) =>
    request('/quiz/ai/explain', 'POST', payload),
  
  // 获取科目详情信息
  getSubjectInfo: (subject: string) =>
    request(`/quiz/subjects/${encodeURIComponent(subject)}/info`, 'GET'),

  // 科目统计详情（用于题库详情页-统计子页面）
  getSubjectStatsDetail: (
    subject: string,
    daysOrParams:
      | number
      | { days?: number; source?: string; q_type?: string; type?: string; tag?: string } = 14
  ) => {
    const params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
    return request(`/quiz/subjects/${encodeURIComponent(subject)}/stats`, 'GET', params);
  },

  // 科目题目列表（用于统计页：错题/收藏列表与图表）
  getSubjectQuestions: (
    subject: string,
    params?: {
      page?: number;
      per_page?: number;
      source?: string; // all/favorites/mistakes
      q_type?: string;
      type?: string; // 兼容字段
      tag?: string;
    }
  ) => request(`/quiz/subjects/${encodeURIComponent(subject)}/questions`, 'GET', params || {}),

  // 科目收藏新增趋势（按收藏创建时间聚合）
  getSubjectFavoritesTrend: (subject: string, days: number = 30) =>
    request(`/quiz/subjects/${encodeURIComponent(subject)}/favorites/trend`, 'GET', { days }),
  
  // 获取题目数量统计（支持范围和题型筛选）
  getQuestionsCount: (params?: {
    subject?: string;
    type?: string;
    source?: string;
    tag?: string;
  }) => request('/quiz/questions/count', 'GET', params || {}),
  
  // 获取用户收藏和错题数量（支持题型筛选）
  getUserCounts: (params: {
    subject?: string;
    type?: string;
    tag?: string;
  }) => request('/quiz/questions/user_counts', 'GET', params),

  // 学习统计（对齐 Web /history）
  getHistoryStats: (days: number = 30) =>
    memoryCache.remember(`history:${days}`, 15 * 1000, () => request('/quiz/history', 'GET', { days })),

  // 数据中心聚合（对齐 Web /api/data/center）
  getDataCenter: (days: number = 30) =>
    memoryCache.remember(`data-center:${days}`, 15 * 1000, () =>
      request('/data/center', 'GET', { days }).then(normalizeDataCenterContext)
    ),

  // 数据中心：标签聚合统计（对齐 Web /api/data/tags）
  getDataTags: (days: number = 30) =>
    memoryCache.remember(`data-tags:${days}`, 15 * 1000, () => request('/data/tags', 'GET', { days })),

  // 数据中心 AI 建议（对齐 Web /api/data/ai-advice）
  getDataAiAdvice: (prompt: string, days: number = 30) =>
    request('/data/ai-advice', 'POST', { prompt, days }),

  // 获取云端进度（与 Web 端 /api/progress 互通）
  getProgress: (key: string) => request('/progress', 'GET', { key }),

  // 保存云端进度（与 Web 端 /api/progress 互通）
  saveProgress: (key: string, data: any) => request('/progress', 'POST', { key, data }),

  // 删除云端进度（与 Web 端 /api/progress 互通）
  deleteProgress: (key: string) => request(`/progress?key=${encodeURIComponent(key)}`, 'DELETE'),

  // 加强训练（错题/相似题，对齐 Web /api/quiz/reinforce）
  getQuizReinforce: (params: {
    source: 'public' | 'user_bank';
    bank_id?: number;
    subject_id?: number;
    include?: string;
    wrong_n?: number;
    seed_n?: number;
    per_seed?: number;
    similar_n?: number;
    wrong_list_n?: number;
    pairs_n?: number;
    similar_mode?: string;
  }) => request('/quiz/reinforce', 'GET', params || {}),

  // === 模拟考试（与 Web /api/exams 互通） ===
  createExam: (data: {
    subject: string;
    duration: number;
    types: Record<string, number>;
    scores?: Record<string, number>;
    source?: 'public' | 'user_bank';
    bank_id?: number | string | null;
  }) => request('/exams/create', 'POST', data),

  getExam: (examId: number) => request(`/exams/${examId}`, 'GET'),

  deleteExam: (examId: number) => request(`/exams/${examId}`, 'DELETE'),

  // 考试记录（对齐 Web /exams?tab=records）
  getExamRecords: (params?: {
    source?: 'all' | 'public' | 'user_bank';
    subject?: string;
    bank_id?: number | null;
    page?: number;
    size?: number;
  }) => request('/exams/records', 'GET', params || {}),

  // 考试数据（对齐 Web /exams?tab=data）
  getExamStats: (params?: { source?: 'all' | 'public' | 'user_bank'; subject?: string; bank_id?: number | null }) =>
    request('/exams/stats', 'GET', params || {}),

  saveExamDraft: (examId: number, answers: Array<{ question_id: number; user_answer: string }>) =>
    request('/exams/save_draft', 'POST', { exam_id: examId, answers }),

  submitExam: (examId: number, answers: Array<{ question_id: number; user_answer: string }>) =>
    request('/exams/submit', 'POST', { exam_id: examId, answers }),

  examToMistakes: (examId: number) => request(`/exams/${examId}/mistakes`, 'POST', {}),

  getExamTemplates: () => request('/exams/templates', 'GET') as Promise<Array<{
    id: number;
    title: string;
    config: any;
    created_at?: string;
    updated_at?: string;
  }>>,

  createExamTemplate: (data: { title: string; config: any }) =>
    request('/exams/templates', 'POST', data) as Promise<{ id: number }>,

  deleteExamTemplate: (templateId: number) => request(`/exams/templates/${templateId}`, 'DELETE'),

  // === 通知（与 Web /api/notifications 互通） ===
  getNotifications: (params?: { include_dismissed?: number | string; limit?: number }) =>
    request('/notifications', 'GET', params || {}) as Promise<
      Array<{
        id: number;
        title: string;
        content: string;
        n_type?: string;
        priority?: number;
        start_at?: string | null;
        end_at?: string | null;
        created_at?: string;
        is_read?: number | boolean;
      }>
    >,

  getNotificationDetail: (id: number, params?: { include_dismissed?: number | string }) =>
    request(`/notifications/${id}`, 'GET', params || {}),

  markNotificationRead: (id: number) => request(`/notifications/${id}/read`, 'POST', {}),

  dismissNotification: (id: number) => request(`/notifications/${id}/dismiss`, 'POST', {}),

  getUnreadNotificationCount: () => request('/notifications/unread_count', 'GET'),

  // === 账号资料/设置（与 Web /api/profile /api/settings/about 互通） ===
  getProfile: () =>
    request('/profile', 'GET') as Promise<{
      username: string;
      avatar?: string;
      contact?: string;
      college?: string;
      signature?: string;
      email?: string | null;
      email_verified?: boolean;
      wechat_bound?: boolean;
      created_at?: string;
      is_admin?: boolean;
      has_password_set?: boolean;
      needs_nickname_setup?: boolean;
      streak_days?: number;
      total_answered?: number;
      correct_answered?: number;
      accuracy?: number;
      favorites_count?: number;
      mistakes_count?: number;
    }>,

  updateProfile: (data: { username?: string; avatar?: string; contact?: string; college?: string; signature?: string; strict_nickname?: boolean; nickname_setup?: boolean }) =>
    request('/profile/update', 'POST', data) as Promise<{ message?: string }>,

  checkUsername: (username: string, strictNickname = false) =>
    request('/profile/check-username', 'POST', { username, strict_nickname: strictNickname }) as Promise<{ available: boolean; message?: string }>,

  updateProfilePassword: (data: { current_password?: string; new_password: string; is_set_password: boolean }) =>
    request('/profile/password', 'POST', {
      current_password: data.current_password || '',
      new_password: data.new_password,
      is_set_password: !!data.is_set_password
    }) as Promise<{ message?: string }>,

  sendEmailBindCode: (email: string) =>
    request('/email/send-bind-code', 'POST', { email }) as Promise<{ message?: string }>,

  bindEmail: (email: string, code: string) =>
    request('/email/bind', 'POST', { email, code }),

  wechatUnbind: () => request('/wechat/unbind', 'POST', {}) as Promise<{ message?: string }>,

  uploadProfileAvatar: (filePath: string) =>
    new Promise<{ avatar_url: string }>((resolve, reject) => {
      const apiBaseUrl = getApiBaseUrl();
      const token = wx.getStorageSync('token') || '';
      if (!token) {
        reject(new Error('请先登录'));
        return;
      }
      wx.uploadFile({
        url: `${apiBaseUrl}/profile/avatar`,
        filePath,
        name: 'avatar',
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          try {
            const raw: any = res.data;
            const js: any = typeof raw === 'string' ? JSON.parse(raw) : raw;
            const ok = Number(res.statusCode) === 200 && js && js.status === 'success';
            if (!ok) {
              const msg = (js && (js.message || js.error)) || `上传失败: ${res.statusCode}`;
              reject(new Error(msg));
              return;
            }
            const avatarUrl = (js.avatar_url || js.data?.avatar_url || '').toString();
            if (!avatarUrl) {
              reject(new Error('上传失败：缺少 avatar_url'));
              return;
            }
            resolve({ avatar_url: avatarUrl });
          } catch (e: any) {
            reject(new Error(e?.message || '上传失败：响应解析异常'));
          }
        },
        fail: (err: any) => {
          const errorMsg = err?.errMsg || err?.message || '网络异常：上传失败';
          maybeShowUploadDevHostHint(apiBaseUrl, errorMsg);
          reject(new Error(errorMsg));
        }
      });
    }),

  // === 签到（与 Web 端 /api/user/checkin 互通） ===
  getCheckinStatus: () =>
    request('/user/checkin/status', 'GET') as Promise<{
      today: string;
      checked_in_today: boolean;
      checked_in_at: string | null;
      streak_days: number;
      total_days: number;
    }>,

  doCheckin: () =>
    request('/user/checkin', 'POST') as Promise<{
      today: string;
      checked_in_today: boolean;
      checked_in_at: string;
      streak_days: number;
      total_days: number;
      just_checked_in: boolean;
    }>,

  // === 继续练习（获取最近一次练习记录） ===
  getLastPractice: () =>
    request('/user/last-practice', 'GET') as Promise<{
      has_practice: boolean;
      last_at: string | null;
      subject_id: number | null;
      subject_name: string | null;
      question_id: number | null;
      path: string | null;
    }>,

  getSettingsAbout: () =>
    request('/settings/about', 'GET') as Promise<{
      admin_available: boolean;
      admin_username?: string;
      admin_email?: string;
      admin_wechat?: string;
      chat_disabled?: boolean;
      chat_disabled_reason?: string;
    }>,

  // === 用户题库（个人题库） ===
  // 创建题库
  createBank: (data: { name: string; description?: string; category_id?: number | null }) =>
    request('/user/banks/api', 'POST', data) as Promise<{ id: number; name: string }>,

  // 获取我的题库列表
  getMyBanks: (params?: { category_id?: number; is_public?: number }) =>
    request('/user/banks/api/list', 'GET', params || {}),

  // 获取我的题库融合视图（我创建 + 公开加入 + 分享加入，对齐 Web /user/banks）
  getMyBankOverview: (params?: {
    scope?: 'all' | 'created' | 'public' | 'shared';
    keyword?: string;
    page?: number;
    per_page?: number;
  }) =>
    request('/user/banks/api/overview', 'GET', params || {}) as Promise<{
      items: Array<{
        id: number;
        kind?: 'created' | 'joined' | string;
        relation?: 'created' | 'public' | 'shared' | 'both' | string;
        source_type?: 'user' | 'system' | string;
        source_label?: string;
        visibility_label?: string;
        name: string;
        description?: string;
        cover_image?: string | null;
        owner_label?: string;
        owner_avatar?: string | null;
        question_count?: number;
        participants_total?: number;
        answer_users_7d?: number;
        is_featured?: boolean;
        updated_at?: string;
        last_joined_at?: string;
        last_activity_at?: string;
      }>;
      total: number;
      page: number;
      per_page: number;
      scope: 'all' | 'created' | 'public' | 'shared';
      counts?: {
        all?: number;
        created?: number;
        public?: number;
        shared?: number;
      };
    }>,

  // 获取收到的分享题库列表
  getSharedBanks: () => request('/user/banks/api/shared', 'GET'),

  // 获取题库详情
  getBankDetail: (bankId: number) => request(`/user/banks/api/${bankId}`, 'GET'),

  // 设置题库公开/私有
  setBankPublic: (bankId: number, data: { is_public: boolean; public_description?: string }) =>
    request(`/user/banks/api/${bankId}/public`, 'POST', data),

  // 获取题库题目列表
  getBankQuestions: (bankId: number, params?: {
    page?: number;
    per_page?: number;
    q_type?: string;
    keyword?: string;
    source?: string; // all/favorites/mistakes
    tag?: string;
  }) => request(`/user/banks/api/${bankId}/questions`, 'GET', params || {}),

  // 获取题库题目详情（单题）
  getBankQuestionDetail: (bankId: number, questionId: number) =>
    request(`/user/banks/api/${bankId}/questions/${questionId}`, 'GET') as Promise<any>,

  // 获取题库刷题题目
  getBankQuizQuestions: (bankId: number, params?: {
    mode?: string;  // 'all' | 'wrong' | 'random'
    ids?: string;   // 指定题目ID列表（用于加强训练等）
    question_ids?: string; // 兼容字段
    limit?: number;
    page?: number;
    per_page?: number;
    full_load?: string | number;
    load_all?: string | number;
    q_type?: string; // 题型筛选
    tag?: string;    // 题库标签筛选（用户私有）
  }) => request(`/user/banks/api/${bankId}/quiz`, 'GET', params || {}),

  // 记录题库答题结果
  recordBankQuizResult: (bankId: number, data: {
    question_id: number;
    user_answer: string;
    is_correct: boolean;
  }) => request(`/user/banks/api/${bankId}/quiz/record`, 'POST', data),

  // 切换题库题目收藏状态
  toggleBankFavorite: (bankId: number, questionId: number) =>
    request(`/user/banks/api/${bankId}/questions/${questionId}/favorite`, 'POST'),

  // 获取题库答题统计
  getBankMyStats: (bankId: number) => request(`/user/banks/api/${bankId}/my-stats`, 'GET'),

  // 题库统计详情（用于题库详情页-统计子页面）
  getBankStatsDetail: (
    bankId: number,
    daysOrParams: number | { days?: number; source?: string; q_type?: string; tag?: string } = 14
  ) => {
    const params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
    const key = `bank-stats:${bankId}:${JSON.stringify(params)}`;
    return memoryCache.remember(key, 15 * 1000, () => request(`/user/banks/api/${bankId}/stats`, 'GET', params));
  },

  // 题库收藏新增趋势（按收藏创建时间聚合）
  getBankFavoritesTrend: (bankId: number, days: number = 30) =>
    request(`/user/banks/api/${bankId}/favorites/trend`, 'GET', { days }),

  // 获取题库用户统计（总数、收藏数、错题数，支持题型和来源筛选）
  getBankUserCounts: (bankId: number, params?: {
    q_type?: string;   // 题型筛选
    source?: string;   // 来源筛选（all/favorites/mistakes）
    tag?: string;      // 题库标签筛选（用户私有）
  }) => request(`/user/banks/api/${bankId}/user-counts`, 'GET', params || {}),

  // 通过分享码加入题库
  joinBankByCode: (shareCode: string) =>
    request('/user/banks/api/join', 'POST', { share_code: shareCode }),

  // 通过分享链接token加入题库
  joinBankByToken: (token: string) =>
    request('/user/banks/api/join', 'POST', { token }),

  // 预览加入题库（不写入记录，用于“加入确认页”）
  previewJoinBank: (params: { token?: string; share_code?: string }) =>
    request('/user/banks/api/join/preview', 'GET', params || {}),

  // 获取题库分享列表
  getBankShares: (bankId: number) =>
    request(`/user/banks/api/${bankId}/shares`, 'GET'),

  // 获取题库使用人数（仅创建者可见）
  getBankUsageStats: (bankId: number) =>
    request(`/user/banks/api/${bankId}/usage-stats`, 'GET'),

  // 创建题库分享
  createBankShare: (bankId: number, data: {
    type?: string;        // 'code' 或 'link'
    permission?: string;  // 'read' 或 'copy'
    expires_in?: number | null;  // 有效天数，null为永久
    max_uses?: number;
  }) => request(`/user/banks/api/${bankId}/shares`, 'POST', data),

  // 删除/撤销题库分享
  deleteBankShare: (bankId: number, shareId: number) =>
    request(`/user/banks/api/${bankId}/shares/${shareId}`, 'DELETE'),

  // 搜索题库题目
  searchBankQuestions: (bankId: number, params: {
    keyword: string;
    q_type?: string;
    source?: string;
    tag?: string;
    page?: number;
    per_page?: number;
  }) => request(`/user/banks/api/${bankId}/questions`, 'GET', params),

  // === 题目标签（公有题库） ===
  // 获取用户所有标签
  getTags: (params?: { subject?: string }) => request('/quiz/tags', 'GET', params || {}),

  // 创建新标签
  createTag: (name: string, params?: { subject?: string; subject_id?: number }) =>
    request('/quiz/tags', 'POST', { name, ...(params || {}) }),

  // 删除标签（仅删除当前用户 + 当前科目下的标签与绑定）
  deleteTag: (name: string, params?: { subject?: string; subject_id?: number }) =>
    request('/quiz/tags', 'DELETE', { name, ...(params || {}) }),

  // 获取题目标签
  getQuestionTags: (questionId: number) => request(`/quiz/questions/${questionId}/tags`, 'GET'),

  // 设置题目标签
  setQuestionTags: (questionId: number, tags: string[]) =>
    request(`/quiz/questions/${questionId}/tags`, 'POST', { tags }),

  // === 编辑题目（公有题库，需要管理员权限） ===
  updateQuestion: (questionId: number, data: {
    content?: string;
    options?: Array<{ key: string; value: string }>;
    answer?: string;
    explanation?: string;
  }) => request(`/quiz/questions/${questionId}`, 'PUT', data),

  // === 题目标签（个人题库） ===
  // 获取题库标签
  getBankTags: (bankId: number) => request(`/user/banks/api/${bankId}/tags`, 'GET'),

  // 创建题库标签
  createBankTag: (bankId: number, name: string) =>
    request(`/user/banks/api/${bankId}/tags`, 'POST', { name }),

  // 删除题库标签（仅删除当前用户 + 当前题库下的标签与绑定）
  deleteBankTag: (bankId: number, name: string) =>
    request(`/user/banks/api/${bankId}/tags`, 'DELETE', { name }),

  // 获取题库题目标签
  getBankQuestionTags: (bankId: number, questionId: number) =>
    request(`/user/banks/api/${bankId}/questions/${questionId}/tags`, 'GET'),

  // 设置题库题目标签
  setBankQuestionTags: (bankId: number, questionId: number, tags: string[]) =>
    request(`/user/banks/api/${bankId}/questions/${questionId}/tags`, 'POST', { tags }),

  // === 编辑题目（个人题库） ===
  updateBankQuestion: (bankId: number, questionId: number, data: {
    content?: string;
    options?: Array<{ key: string; value: string }>;
    answer?: string;
    explanation?: string;
  }) => request(`/user/banks/api/${bankId}/questions/${questionId}`, 'PUT', data)
};
