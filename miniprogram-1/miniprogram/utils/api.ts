// API基础配置
// 从 config.ts 导入配置，支持自动检测开发/生产环境
import { config } from './config';

function getApiBaseUrl(): string {
  return config.getApiUrl();
}

function getApiOriginFromBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/api\/?$/, '');
}

export function getApiOrigin(): string {
  return getApiOriginFromBaseUrl(getApiBaseUrl());
}

function isPrivateHostname(hostname: string): boolean {
  const h = String(hostname || '').trim().toLowerCase();
  if (!h) return true;
  if (h === 'localhost') return true;
  if (h.endsWith('.local')) return true;

  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const a = Number(m[1]);
  const b = Number(m[2]);
  const c = Number(m[3]);
  const d = Number(m[4]);
  if (![a, b, c, d].every((n) => Number.isFinite(n) && n >= 0 && n <= 255)) return false;

  if (a === 127) return true;
  if (a === 10) return true;
  if (a === 192 && b === 168) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 169 && b === 254) return true;
  return false;
}

function maybeUpgradeToHttps(url: string): string {
  const raw = String(url || '').trim();
  if (!/^http:\/\//i.test(raw)) return raw;

  // 避免影响开发者工具本地调试（常用 http + 局域网/localhost）
  try {
    if (getWxPlatform() === 'devtools') return raw;
  } catch (e) {
    // ignore
  }

  const noScheme = raw.replace(/^http:\/\//i, '');
  const slashIdx = noScheme.indexOf('/');
  const hostPort = slashIdx === -1 ? noScheme : noScheme.slice(0, slashIdx);
  const rest = slashIdx === -1 ? '' : noScheme.slice(slashIdx);
  if (!hostPort) return raw;

  // 注意：这里不处理 IPv6（当前项目场景基本用不到）
  const parts = hostPort.split(':');
  const host = String(parts[0] || '').trim();
  const portRaw = parts.length > 1 ? String(parts[1] || '').trim() : '';
  const portNum = portRaw ? Number(portRaw) : NaN;
  const port =
    Number.isFinite(portNum) && portNum > 0 && portNum <= 65535 ? Math.floor(portNum) : undefined;

  if (!host) return raw;
  if (isPrivateHostname(host)) return raw;

  // 避免把 http://example.com:5000 盲目改成 https://example.com:5000
  if (typeof port === 'number' && port !== 80) return raw;

  const finalHostPort = typeof port === 'number' && port === 80 ? host : hostPort;
  return `https://${finalHostPort}${rest}`;
}

// 将后端存储的相对路径（如 question_images/xxx.png）转换为可访问的完整 URL
export function resolveUploadUrl(input: any): string {
  const API_ORIGIN = maybeUpgradeToHttps(getApiOrigin());
  if (input == null) return '';
  const raw = String(input).trim();
  if (!raw || raw === '[]') return '';
  if (/^https?:\/\//i.test(raw)) return maybeUpgradeToHttps(raw);

  if (raw.startsWith('/uploads/')) return `${API_ORIGIN}${raw}`;
  if (raw.startsWith('uploads/')) return `${API_ORIGIN}/${raw}`;
  if (raw.startsWith('/')) return `${API_ORIGIN}${raw}`;

  // 默认认为存放在 /uploads 下（如 question_images/...）
  return `${API_ORIGIN}/uploads/${raw}`;
}

// 兼容 image_path 可能为：单路径字符串、JSON 数组字符串、数组
export function normalizeImageUrls(imagePath: any): string[] {
  if (imagePath == null) return [];

  if (Array.isArray(imagePath)) {
    return imagePath
      .map((p) => resolveUploadUrl(p))
      .filter((p) => typeof p === 'string' && p.length > 0);
  }

  const raw = String(imagePath).trim();
  if (!raw || raw === '[]') return [];

  if (raw.startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed
          .map((p) => resolveUploadUrl(p))
          .filter((p) => typeof p === 'string' && p.length > 0);
      }
      if (typeof parsed === 'string') {
        const url = resolveUploadUrl(parsed);
        return url ? [url] : [];
      }
    } catch (e) {
      // 忽略 JSON 解析失败，走单路径兜底
    }
  }

  const url = resolveUploadUrl(raw);
  return url ? [url] : [];
}

function getWxPlatform(): string {
  try {
    const info = (wx as any).getDeviceInfo ? (wx as any).getDeviceInfo() : null;
    const p = info && (info as any).platform;
    if (p) return String(p);
  } catch (e) {}

  try {
    const p = wx.getSystemInfoSync().platform;
    if (p) return String(p);
  } catch (e) {}

  return '';
}

let hasShownDevHostHint = false;
function maybeShowDevHostHint(apiBaseUrl: string, message: string): void {
  if (hasShownDevHostHint) return;

  const msg = String(message || '');

  // 仅对「开发版 + localhost」给出引导，避免干扰正常错误处理
  try {
    const envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
    if (envVersion !== 'develop') return;
  } catch (e) {
    // 获取失败时不拦截
  }

  let isDevtools = false;
  try {
    const platform = getWxPlatform();
    isDevtools = platform === 'devtools';
  } catch (e) {
    // 忽略
  }

  const isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
  if (!isLocalhost) return;

  // 真机/部分环境会带 ERR_CONNECTION_REFUSED；开发者工具有时只给 request:fail
  const isConnRefused =
    msg.includes('ERR_CONNECTION_REFUSED') ||
    msg.includes('errcode:-102') ||
    msg.includes('cronet_error_code:-102') ||
    msg.toLowerCase().includes('connection refused');
  const isGenericRequestFail = msg.trim() === 'request:fail';
  if (!isConnRefused && !(isDevtools && isGenericRequestFail)) return;

  hasShownDevHostHint = true;
  const content = isDevtools
    ? `当前 API 地址为：${apiBaseUrl}\n\n` +
      '开发者工具访问本机 127.0.0.1/localhost 没问题，但现在连接失败，通常是后端未启动或端口不一致。\n' +
      '请先在后端项目根目录运行：python run.py（默认监听 0.0.0.0:5000），然后重试。\n' +
      '如后端在其它 Host/Port，可到「开发设置」修改并点击「测试连接」。'
    : `当前 API 地址为：${apiBaseUrl}\n\n` +
      '真机预览无法访问电脑的 localhost/127.0.0.1。\n' +
      '请将 API Host 设置为电脑的局域网 IP（如 192.168.1.100），并确保后端已启动（python run.py，监听 0.0.0.0:5000）。';
  wx.showModal({
    title: '无法连接后端',
    content,
    confirmText: '去设置',
    cancelText: '知道了',
    success: (res) => {
      if (!res.confirm) return;
      wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
    }
  });
}

// 请求封装
function shouldUseSummaryLog(data: any): boolean {
  if (!data || typeof data !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(data, 'data')) return false;
  const payload = (data as any).data;
  if (Array.isArray(payload)) return payload.length > 50;
  if (payload && typeof payload === 'object') return Object.keys(payload).length > 30;
  return false;
}

function buildResponseLogSummary(data: any): any {
  if (!data || typeof data !== 'object') return data;
  const out: any = {};
  if (Object.prototype.hasOwnProperty.call(data, 'status')) out.status = (data as any).status;
  if (Object.prototype.hasOwnProperty.call(data, 'code')) out.code = (data as any).code;
  if (Object.prototype.hasOwnProperty.call(data, 'request_id')) out.request_id = (data as any).request_id;
  if (Object.prototype.hasOwnProperty.call(data, 'message')) out.message = (data as any).message;
  if (Object.prototype.hasOwnProperty.call(data, 'data')) {
    const payload = (data as any).data;
    if (Array.isArray(payload)) out.data = `Array(${payload.length})`;
    else if (payload && typeof payload === 'object') out.data = `Object(keys=${Object.keys(payload).length})`;
    else out.data = payload;
  }
  return out;
}

function safeLogApiResponse(method: string, url: string, statusCode: number, data: any): void {
  try {
    if (shouldUseSummaryLog(data)) {
      console.log(`API请求 ${method} ${url}:`, statusCode, buildResponseLogSummary(data));
      return;
    }
    console.log(`API请求 ${method} ${url}:`, statusCode, data);
  } catch (e) {
    try {
      console.log(`API请求 ${method} ${url}:`, statusCode, '[log skipped]');
    } catch (e2) {}
  }
}

function request<T = any>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: any
): Promise<T> {
  return new Promise((resolve, reject) => {
    const apiBaseUrl = getApiBaseUrl();
    // 获取token
    const token = wx.getStorageSync('token') || '';
    // 记录本次请求使用的 token，避免“旧请求的 401 把新 token 清掉”导致登录循环
    const tokenAtRequest = token;
    
    // 调试日志
    if (url.includes('/quiz/subjects')) {
      console.log('API请求token状态:', token ? `有token(${token.substring(0, 20)}...)` : '无token');
    }
    
    // GET请求将data作为query参数（微信小程序会自动处理，但为了明确性我们也可以手动处理）
    wx.request({
      url: `${apiBaseUrl}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': tokenAtRequest ? `Bearer ${tokenAtRequest}` : ''
      },
      success: (res) => {
        safeLogApiResponse(method, url, res.statusCode, res.data);
        if (res.statusCode === 200) {
          const result: any = res.data;

          // 兼容两种响应格式：
          // 1) { status: 'success', data?: ... }  （quiz/exam 等）
          // 2) { code: 0, data?: ... }            （user_bank 等）
          const isStatusSuccess = result && result.status === 'success';
          const hasCodeField = result && Object.prototype.hasOwnProperty.call(result, 'code');
          const isCodeSuccess = hasCodeField && Number(result.code) === 0;

          if (isStatusSuccess || isCodeSuccess) {
            if (result.data !== undefined) {
              resolve(result.data as T);
              return;
            }
            const rest: any = Object.assign({}, result);
            delete rest.status;
            resolve(rest as T);
            return;
          }

          console.error('API返回错误状态:', result);
          reject(new Error((result && (result.message || result.msg)) || '请求失败'));
        } else if (res.statusCode === 401) {
          const errorData = res.data as { message?: string; error?: string; [key: string]: any };
          const errorMsg = (errorData && (errorData.message || errorData.error)) || '登录已过期';

          // 如果本次请求使用的是旧 token，而当前 storage 里已经是新 token，则认为是"旧请求 401"
          // 此时不要清 token / 不要跳转，避免把新 token 清掉导致"始终登录不上"
          const latestToken = wx.getStorageSync('token') || '';
          if (latestToken && latestToken !== tokenAtRequest) {
            console.warn('401来自旧请求，忽略登出:', url);
            const err: any = new Error(errorMsg);
            err.statusCode = 401;
            err.response = res.data;
            reject(err);
            return;
          }

          // 先检查当前页面，避免循环跳转
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];
          const currentRoute = currentPage ? currentPage.route : '';

          // 清理本地登录态（token 已经无效）
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');

          // 允许游客浏览的页面：不自动跳转登录页，让页面自行处理
          const guestAllowedPages = ['pages/hub-v2/hub-v2', 'pages/index/index', 'pages/subjects/subjects'];
          const isGuestAllowedPage = guestAllowedPages.some(p => currentRoute.includes(p));

          // 如果不在登录页且不在游客允许页面，跳转到登录页
          if (!currentRoute.includes('login') && !isGuestAllowedPage) {
            console.log('401错误，清除token并跳转到登录页');
            wx.reLaunch({ url: '/pages/login/login' });
          }

          const err: any = new Error(errorMsg);
          err.statusCode = 401;
          err.response = res.data;
          reject(err);
        } else if (res.statusCode === 429) {
          // 请求过于频繁
          const errorMsg = '请求过于频繁，请稍后再试';
          console.error('API请求限流:', res.statusCode);
          reject(new Error(errorMsg));
        } else {
          // 尝试获取错误信息
          const errorData = res.data as { message?: string; error?: string };
          const errorMsg =
            (errorData && (errorData.message || errorData.error)) || `请求失败: ${res.statusCode}`;
          console.error('API请求失败:', res.statusCode, errorMsg);
          reject(new Error(errorMsg));
        }
      },
      fail: (err: any) => {
        console.error('网络请求失败:', err);
        // 处理网络错误
        const errorMsg = err.errMsg || err.message || '网络请求失败，请检查网络连接';
        maybeShowDevHostHint(apiBaseUrl, errorMsg);
        reject(new Error(errorMsg));
      }
    });
  });
}

function unwrapApiEnvelopeMaybe(input: any): any {
  if (!input || typeof input !== 'object') return input;
  const hasStatus = typeof (input as any).status === 'string';
  const hasCode = Object.prototype.hasOwnProperty.call(input, 'code');
  if ((hasStatus || hasCode) && Object.prototype.hasOwnProperty.call(input, 'data')) {
    return (input as any).data;
  }
  return input;
}

function shallowCloneObject(input: any): any {
  if (!input || typeof input !== 'object') return {};
  const out: any = {};
  for (const k in input) {
    if (!Object.prototype.hasOwnProperty.call(input, k)) continue;
    out[k] = input[k];
  }
  return out;
}

function normalizeDataCenterContext(input: any): any {
  const maybeUnwrapped = unwrapApiEnvelopeMaybe(input);
  const ctx = maybeUnwrapped && typeof maybeUnwrapped === 'object' ? (maybeUnwrapped as any) : {};
  const out: any = shallowCloneObject(ctx);

  // 兼容：后端/中间层可能返回不同命名或再次套 envelope
  const nested = unwrapApiEnvelopeMaybe(out);
  const base = nested && typeof nested === 'object' ? nested : out;

  if (!base.all_summary && base.allSummary) base.all_summary = base.allSummary;
  if (!base.all_summary && base.all) base.all_summary = base.all;
  if (!base.all_summary && base.summary) base.all_summary = base.summary;
  if (!base.all_summary && base.public_summary) base.all_summary = base.public_summary;
  if (!base.window_days && base.windowDays) base.window_days = base.windowDays;

  // 兼容：all_summary 内部字段 camelCase
  if (base.all_summary && typeof base.all_summary === 'object') {
    const s: any = base.all_summary;
    if (!s.last_activity && s.lastActivity) s.last_activity = s.lastActivity;
    if (!s.total_questions && s.totalQuestions) s.total_questions = s.totalQuestions;
    if (!s.mistakes_times && s.mistakesTimes) s.mistakes_times = s.mistakesTimes;
    if (!s.streak_days && s.streakDays) s.streak_days = s.streakDays;
  }

  if (!base.all_summary || typeof base.all_summary !== 'object') {
    throw new Error('数据中心接口返回异常：缺少 all_summary（请检查后端是否已部署 /api/data/center，或确认小程序 API 地址配置正确）');
  }

  return base;
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

  // === 小程序：账号登录（JWT） ===
  miniPasswordLogin: (username: string, password: string) =>
    request('/mini/login', 'POST', { username, password }),

  miniSendEmailLoginCode: (email: string) =>
    request('/mini/email/send-login-code', 'POST', { email }),

  miniEmailLogin: (email: string, code: string) =>
    request('/mini/email/login', 'POST', { email, code }),

  // 小程序：已登录用户绑定微信（密码/邮箱登录后引导绑定）
  miniWechatBind: (code: string) =>
    request('/mini/wechat/bind', 'POST', { code }),
  
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
        public_at?: string;
        created_at?: string;
        owner_id?: number | null;
        owner_nickname?: string;
        owner_avatar?: string;
        bank_type: 'system' | 'user';
      }>;
      total: number;
      page: number;
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
  getHistoryStats: (days: number = 30) => request('/quiz/history', 'GET', { days }),

  // 数据中心聚合（对齐 Web /api/data/center）
  getDataCenter: (days: number = 30) => request('/data/center', 'GET', { days }).then(normalizeDataCenterContext),

  // 数据中心：标签聚合统计（对齐 Web /api/data/tags）
  getDataTags: (days: number = 30) => request('/data/tags', 'GET', { days }),

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
      streak_days?: number;
      total_answered?: number;
      correct_answered?: number;
      accuracy?: number;
      favorites_count?: number;
      mistakes_count?: number;
    }>,

  updateProfile: (data: { username?: string; avatar?: string; contact?: string; college?: string; signature?: string }) =>
    request('/profile/update', 'POST', data) as Promise<{ message?: string }>,

  checkUsername: (username: string) =>
    request('/profile/check-username', 'POST', { username }) as Promise<{ available: boolean; message?: string }>,

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
          maybeShowDevHostHint(apiBaseUrl, errorMsg);
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
    return request(`/user/banks/api/${bankId}/stats`, 'GET', params);
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
