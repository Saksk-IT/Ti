// HTTP 客户端核心（从 api-endpoints.ts 提取）
import { getWxPlatform } from './config';
import { getApiBaseUrl } from './url-utils';

let hasShownDevHostHint = false;
function maybeShowDevHostHint(apiBaseUrl: string, message: string): void {
  if (hasShownDevHostHint) return;

  const msg = String(message || '');

  try {
    const envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
    if (envVersion !== 'develop') return;
  } catch (e) {}

  let isDevtools = false;
  try {
    const platform = getWxPlatform();
    isDevtools = platform === 'devtools';
  } catch (e) {}

  const isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
  if (!isLocalhost) return;

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

function isApiLogEnabled(): boolean {
  try {
    const raw = wx.getStorageSync('__api_debug_log__');
    return raw === '1' || raw === 1 || raw === true;
  } catch (e) {
    return false;
  }
}

function safeLogApiResponse(method: string, url: string, statusCode: number, data: any): void {
  if (!isApiLogEnabled()) return;
  try {
    if (shouldUseSummaryLog(data)) {
      console.log(`API请求 ${method} ${url}:`, statusCode, buildResponseLogSummary(data));
      return;
    }
    console.log(`API请求 ${method} ${url}:`, statusCode, data);
  } catch (e) {}
}

export function request<T = any>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: any
): Promise<T> {
  return new Promise((resolve, reject) => {
    const apiBaseUrl = getApiBaseUrl();
    const token = wx.getStorageSync('token') || '';
    const tokenAtRequest = token;

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

          reject(new Error((result && (result.message || result.msg)) || '请求失败'));
        } else if (res.statusCode === 401) {
          const errorData = res.data as { message?: string; error?: string; [key: string]: any };
          const errorMsg = (errorData && (errorData.message || errorData.error)) || '登录已过期';

          const latestToken = wx.getStorageSync('token') || '';
          if (latestToken && latestToken !== tokenAtRequest) {
            const err: any = new Error(errorMsg);
            err.statusCode = 401;
            err.response = res.data;
            reject(err);
            return;
          }
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];
          const currentRoute = currentPage ? currentPage.route : '';

          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');

          const guestAllowedPages = ['pages/hub-v2/hub-v2', 'pages/index-v2/index-v2', 'pages/subjects/subjects'];
          const isGuestAllowedPage = guestAllowedPages.some(p => currentRoute.includes(p));

          if (!currentRoute.includes('login') && !isGuestAllowedPage) {
            wx.reLaunch({ url: '/pages/login/login' });
          }

          const err: any = new Error(errorMsg);
          err.statusCode = 401;
          err.response = res.data;
          reject(err);
        } else if (res.statusCode === 429) {
          reject(new Error('请求过于频繁，请稍后再试'));
        } else {
          const errorData = res.data as { message?: string; error?: string };
          const errorMsg =
            (errorData && (errorData.message || errorData.error)) || `请求失败: ${res.statusCode}`;
          reject(new Error(errorMsg));
        }
      },
      fail: (err: any) => {
        const errorMsg = err.errMsg || err.message || '网络请求失败，请检查网络连接';
        maybeShowDevHostHint(apiBaseUrl, errorMsg);
        reject(new Error(errorMsg));
      }
    });
  });
}

export function unwrapApiEnvelopeMaybe(input: any): any {
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

export function normalizeDataCenterContext(input: any): any {
  const maybeUnwrapped = unwrapApiEnvelopeMaybe(input);
  const ctx = maybeUnwrapped && typeof maybeUnwrapped === 'object' ? (maybeUnwrapped as any) : {};
  const out: any = shallowCloneObject(ctx);

  const nested = unwrapApiEnvelopeMaybe(out);
  const base = nested && typeof nested === 'object' ? nested : out;

  if (!base.all_summary && base.allSummary) base.all_summary = base.allSummary;
  if (!base.all_summary && base.all) base.all_summary = base.all;
  if (!base.all_summary && base.summary) base.all_summary = base.summary;
  if (!base.all_summary && base.public_summary) base.all_summary = base.public_summary;
  if (!base.window_days && base.windowDays) base.window_days = base.windowDays;

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
