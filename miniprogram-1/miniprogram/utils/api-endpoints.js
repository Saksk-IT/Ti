"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.api = void 0;
exports.getApiOrigin = getApiOrigin;
exports.resolveUploadUrl = resolveUploadUrl;
exports.normalizeImageUrls = normalizeImageUrls;
exports.request = request;
// API基础配置
// 从 config.ts 导入配置，支持自动检测开发/生产环境
var config_1 = require("./config");
var memory_cache_1 = require("./memory-cache");
function getApiBaseUrl() {
    return config_1.config.getApiUrl();
}
function getApiOriginFromBaseUrl(apiBaseUrl) {
    return apiBaseUrl.replace(/\/api\/?$/, '');
}
function getApiOrigin() {
    return getApiOriginFromBaseUrl(getApiBaseUrl());
}
function isPrivateHostname(hostname) {
    var h = String(hostname || '').trim().toLowerCase();
    if (!h)
        return true;
    if (h === 'localhost')
        return true;
    if (h.endsWith('.local'))
        return true;
    var m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (!m)
        return false;
    var a = Number(m[1]);
    var b = Number(m[2]);
    var c = Number(m[3]);
    var d = Number(m[4]);
    if (![a, b, c, d].every(function (n) { return Number.isFinite(n) && n >= 0 && n <= 255; }))
        return false;
    if (a === 127)
        return true;
    if (a === 10)
        return true;
    if (a === 192 && b === 168)
        return true;
    if (a === 172 && b >= 16 && b <= 31)
        return true;
    if (a === 169 && b === 254)
        return true;
    return false;
}
function maybeUpgradeToHttps(url) {
    var raw = String(url || '').trim();
    if (!/^http:\/\//i.test(raw))
        return raw;
    // 避免影响开发者工具本地调试（常用 http + 局域网/localhost）
    try {
        if (getWxPlatform() === 'devtools')
            return raw;
    }
    catch (e) {
        // ignore
    }
    var noScheme = raw.replace(/^http:\/\//i, '');
    var slashIdx = noScheme.indexOf('/');
    var hostPort = slashIdx === -1 ? noScheme : noScheme.slice(0, slashIdx);
    var rest = slashIdx === -1 ? '' : noScheme.slice(slashIdx);
    if (!hostPort)
        return raw;
    // 注意：这里不处理 IPv6（当前项目场景基本用不到）
    var parts = hostPort.split(':');
    var host = String(parts[0] || '').trim();
    var portRaw = parts.length > 1 ? String(parts[1] || '').trim() : '';
    var portNum = portRaw ? Number(portRaw) : NaN;
    var port = Number.isFinite(portNum) && portNum > 0 && portNum <= 65535 ? Math.floor(portNum) : undefined;
    if (!host)
        return raw;
    if (isPrivateHostname(host))
        return raw;
    // 避免把 http://example.com:5000 盲目改成 https://example.com:5000
    if (typeof port === 'number' && port !== 80)
        return raw;
    var finalHostPort = typeof port === 'number' && port === 80 ? host : hostPort;
    return "https://".concat(finalHostPort).concat(rest);
}
// 将后端存储的相对路径（如 question_images/xxx.png）转换为可访问的完整 URL
function resolveUploadUrl(input) {
    var API_ORIGIN = maybeUpgradeToHttps(getApiOrigin());
    if (input == null)
        return '';
    var raw = String(input).trim();
    if (!raw || raw === '[]')
        return '';
    if (/^https?:\/\//i.test(raw))
        return maybeUpgradeToHttps(raw);
    if (raw.startsWith('/uploads/'))
        return "".concat(API_ORIGIN).concat(raw);
    if (raw.startsWith('uploads/'))
        return "".concat(API_ORIGIN, "/").concat(raw);
    if (raw.startsWith('/'))
        return "".concat(API_ORIGIN).concat(raw);
    // 默认认为存放在 /uploads 下（如 question_images/...）
    return "".concat(API_ORIGIN, "/uploads/").concat(raw);
}
function normalizeImagePathList(input) {
    if (Array.isArray(input)) {
        return input
            .map(function (p) { return resolveUploadUrl(p); })
            .filter(function (p) { return typeof p === 'string' && p.length > 0; });
    }
    if (input && typeof input === 'object') {
        var content = input.content || input.question || input.stem || input.images;
        return normalizeImagePathList(content);
    }
    if (typeof input === 'string') {
        var url_1 = resolveUploadUrl(input);
        return url_1 ? [url_1] : [];
    }
    return [];
}
// 兼容 image_path 可能为：单路径字符串、JSON 数组字符串、JSON 对象字符串、数组
function normalizeImageUrls(imagePath) {
    if (imagePath == null)
        return [];
    if (Array.isArray(imagePath)) {
        return normalizeImagePathList(imagePath);
    }
    var raw = String(imagePath).trim();
    if (!raw || raw === '[]')
        return [];
    if (raw.startsWith('[') || raw.startsWith('{')) {
        try {
            var parsed = JSON.parse(raw);
            return normalizeImagePathList(parsed);
        }
        catch (e) {
            // 忽略 JSON 解析失败，走单路径兜底
        }
    }
    var url = resolveUploadUrl(raw);
    return url ? [url] : [];
}
function getWxPlatform() {
    try {
        var info = wx.getDeviceInfo ? wx.getDeviceInfo() : null;
        var p = info && info.platform;
        if (p)
            return String(p);
    }
    catch (e) { }
    try {
        var p = wx.getSystemInfoSync().platform;
        if (p)
            return String(p);
    }
    catch (e) { }
    return '';
}
var hasShownDevHostHint = false;
function maybeShowDevHostHint(apiBaseUrl, message) {
    if (hasShownDevHostHint)
        return;
    var msg = String(message || '');
    // 仅对「开发版 + localhost」给出引导，避免干扰正常错误处理
    try {
        var envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
        if (envVersion !== 'develop')
            return;
    }
    catch (e) {
        // 获取失败时不拦截
    }
    var isDevtools = false;
    try {
        var platform = getWxPlatform();
        isDevtools = platform === 'devtools';
    }
    catch (e) {
        // 忽略
    }
    var isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
    if (!isLocalhost)
        return;
    // 真机/部分环境会带 ERR_CONNECTION_REFUSED；开发者工具有时只给 request:fail
    var isConnRefused = msg.includes('ERR_CONNECTION_REFUSED') ||
        msg.includes('errcode:-102') ||
        msg.includes('cronet_error_code:-102') ||
        msg.toLowerCase().includes('connection refused');
    var isGenericRequestFail = msg.trim() === 'request:fail';
    if (!isConnRefused && !(isDevtools && isGenericRequestFail))
        return;
    hasShownDevHostHint = true;
    var content = isDevtools
        ? "\u5F53\u524D API \u5730\u5740\u4E3A\uFF1A".concat(apiBaseUrl, "\n\n") +
            '开发者工具访问本机 127.0.0.1/localhost 没问题，但现在连接失败，通常是后端未启动或端口不一致。\n' +
            '请先在后端项目根目录运行：python run.py（默认监听 0.0.0.0:5000），然后重试。\n' +
            '如后端在其它 Host/Port，可到「开发设置」修改并点击「测试连接」。'
        : "\u5F53\u524D API \u5730\u5740\u4E3A\uFF1A".concat(apiBaseUrl, "\n\n") +
            '真机预览无法访问电脑的 localhost/127.0.0.1。\n' +
            '请将 API Host 设置为电脑的局域网 IP（如 192.168.1.100），并确保后端已启动（python run.py，监听 0.0.0.0:5000）。';
    wx.showModal({
        title: '无法连接后端',
        content: content,
        confirmText: '去设置',
        cancelText: '知道了',
        success: function (res) {
            if (!res.confirm)
                return;
            wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
        }
    });
}
// 请求封装
function shouldUseSummaryLog(data) {
    if (!data || typeof data !== 'object')
        return false;
    if (!Object.prototype.hasOwnProperty.call(data, 'data'))
        return false;
    var payload = data.data;
    if (Array.isArray(payload))
        return payload.length > 50;
    if (payload && typeof payload === 'object')
        return Object.keys(payload).length > 30;
    return false;
}
function buildResponseLogSummary(data) {
    if (!data || typeof data !== 'object')
        return data;
    var out = {};
    if (Object.prototype.hasOwnProperty.call(data, 'status'))
        out.status = data.status;
    if (Object.prototype.hasOwnProperty.call(data, 'code'))
        out.code = data.code;
    if (Object.prototype.hasOwnProperty.call(data, 'request_id'))
        out.request_id = data.request_id;
    if (Object.prototype.hasOwnProperty.call(data, 'message'))
        out.message = data.message;
    if (Object.prototype.hasOwnProperty.call(data, 'data')) {
        var payload = data.data;
        if (Array.isArray(payload))
            out.data = "Array(".concat(payload.length, ")");
        else if (payload && typeof payload === 'object')
            out.data = "Object(keys=".concat(Object.keys(payload).length, ")");
        else
            out.data = payload;
    }
    return out;
}
function isApiLogEnabled() {
    try {
        var raw = wx.getStorageSync('__api_debug_log__');
        return raw === '1' || raw === 1 || raw === true;
    }
    catch (e) {
        return false;
    }
}
function safeLogApiResponse(method, url, statusCode, data) {
    if (!isApiLogEnabled())
        return;
    try {
        if (shouldUseSummaryLog(data)) {
            console.log("API\u8BF7\u6C42 ".concat(method, " ").concat(url, ":"), statusCode, buildResponseLogSummary(data));
            return;
        }
        console.log("API\u8BF7\u6C42 ".concat(method, " ").concat(url, ":"), statusCode, data);
    }
    catch (e) {
        // ignore
    }
}
function request(url, method, data) {
    if (method === void 0) { method = 'GET'; }
    return new Promise(function (resolve, reject) {
        var apiBaseUrl = getApiBaseUrl();
        // 获取token
        var token = wx.getStorageSync('token') || '';
        // 记录本次请求使用的 token，避免“旧请求的 401 把新 token 清掉”导致登录循环
        var tokenAtRequest = token;
        // GET请求将data作为query参数（微信小程序会自动处理，但为了明确性我们也可以手动处理）
        wx.request({
            url: "".concat(apiBaseUrl).concat(url),
            method: method,
            data: data,
            header: {
                'Content-Type': 'application/json',
                'Authorization': tokenAtRequest ? "Bearer ".concat(tokenAtRequest) : ''
            },
            success: function (res) {
                safeLogApiResponse(method, url, res.statusCode, res.data);
                if (res.statusCode === 200) {
                    var result = res.data;
                    // 兼容两种响应格式：
                    // 1) { status: 'success', data?: ... }  （quiz/exam 等）
                    // 2) { code: 0, data?: ... }            （user_bank 等）
                    var isStatusSuccess = result && result.status === 'success';
                    var hasCodeField = result && Object.prototype.hasOwnProperty.call(result, 'code');
                    var isCodeSuccess = hasCodeField && Number(result.code) === 0;
                    if (isStatusSuccess || isCodeSuccess) {
                        if (result.data !== undefined) {
                            resolve(result.data);
                            return;
                        }
                        var rest = Object.assign({}, result);
                        delete rest.status;
                        resolve(rest);
                        return;
                    }
                    reject(new Error((result && (result.message || result.msg)) || '请求失败'));
                }
                else if (res.statusCode === 401) {
                    var errorData = res.data;
                    var errorMsg = (errorData && (errorData.message || errorData.error)) || '登录已过期';
                    // 如果本次请求使用的是旧 token，而当前 storage 里已经是新 token，则认为是"旧请求 401"
                    // 此时不要清 token / 不要跳转，避免把新 token 清掉导致"始终登录不上"
                    var latestToken = wx.getStorageSync('token') || '';
                    if (latestToken && latestToken !== tokenAtRequest) {
                        var err_1 = new Error(errorMsg);
                        err_1.statusCode = 401;
                        err_1.response = res.data;
                        reject(err_1);
                        return;
                    }
                    // 先检查当前页面，避免循环跳转
                    var pages = getCurrentPages();
                    var currentPage = pages[pages.length - 1];
                    var currentRoute_1 = currentPage ? currentPage.route : '';
                    // 清理本地登录态（token 已经无效）
                    wx.removeStorageSync('token');
                    wx.removeStorageSync('userInfo');
                    // 允许游客浏览的页面：不自动跳转登录页，让页面自行处理
                    var guestAllowedPages = ['pages/hub-v2/hub-v2', 'pages/index-v2/index-v2', 'pages/subjects/subjects'];
                    var isGuestAllowedPage = guestAllowedPages.some(function (p) { return currentRoute_1.includes(p); });
                    // 如果不在登录页且不在游客允许页面，跳转到登录页
                    if (!currentRoute_1.includes('login') && !isGuestAllowedPage) {
                        wx.reLaunch({ url: '/pages/login/login' });
                    }
                    var err = new Error(errorMsg);
                    err.statusCode = 401;
                    err.response = res.data;
                    reject(err);
                }
                else if (res.statusCode === 429) {
                    // 请求过于频繁
                    var errorMsg = '请求过于频繁，请稍后再试';
                    reject(new Error(errorMsg));
                }
                else {
                    // 尝试获取错误信息
                    var errorData = res.data;
                    var errorMsg = (errorData && (errorData.message || errorData.error)) || "\u8BF7\u6C42\u5931\u8D25: ".concat(res.statusCode);
                    reject(new Error(errorMsg));
                }
            },
            fail: function (err) {
                // 处理网络错误
                var errorMsg = err.errMsg || err.message || '网络请求失败，请检查网络连接';
                maybeShowDevHostHint(apiBaseUrl, errorMsg);
                reject(new Error(errorMsg));
            }
        });
    });
}
function unwrapApiEnvelopeMaybe(input) {
    if (!input || typeof input !== 'object')
        return input;
    var hasStatus = typeof input.status === 'string';
    var hasCode = Object.prototype.hasOwnProperty.call(input, 'code');
    if ((hasStatus || hasCode) && Object.prototype.hasOwnProperty.call(input, 'data')) {
        return input.data;
    }
    return input;
}
function shallowCloneObject(input) {
    if (!input || typeof input !== 'object')
        return {};
    var out = {};
    for (var k in input) {
        if (!Object.prototype.hasOwnProperty.call(input, k))
            continue;
        out[k] = input[k];
    }
    return out;
}
function normalizeDataCenterContext(input) {
    var maybeUnwrapped = unwrapApiEnvelopeMaybe(input);
    var ctx = maybeUnwrapped && typeof maybeUnwrapped === 'object' ? maybeUnwrapped : {};
    var out = shallowCloneObject(ctx);
    // 兼容：后端/中间层可能返回不同命名或再次套 envelope
    var nested = unwrapApiEnvelopeMaybe(out);
    var base = nested && typeof nested === 'object' ? nested : out;
    if (!base.all_summary && base.allSummary)
        base.all_summary = base.allSummary;
    if (!base.all_summary && base.all)
        base.all_summary = base.all;
    if (!base.all_summary && base.summary)
        base.all_summary = base.summary;
    if (!base.all_summary && base.public_summary)
        base.all_summary = base.public_summary;
    if (!base.window_days && base.windowDays)
        base.window_days = base.windowDays;
    // 兼容：all_summary 内部字段 camelCase
    if (base.all_summary && typeof base.all_summary === 'object') {
        var s = base.all_summary;
        if (!s.last_activity && s.lastActivity)
            s.last_activity = s.lastActivity;
        if (!s.total_questions && s.totalQuestions)
            s.total_questions = s.totalQuestions;
        if (!s.mistakes_times && s.mistakesTimes)
            s.mistakes_times = s.mistakesTimes;
        if (!s.streak_days && s.streakDays)
            s.streak_days = s.streakDays;
    }
    if (!base.all_summary || typeof base.all_summary !== 'object') {
        throw new Error('数据中心接口返回异常：缺少 all_summary（请检查后端是否已部署 /api/data/center，或确认小程序 API 地址配置正确）');
    }
    return base;
}
// 导出API方法
exports.api = {
    // 微信登录
    wechatLogin: function (code, userInfo, allowCreate) {
        if (allowCreate === void 0) { allowCreate = true; }
        return request('/wechat/login', 'POST', { code: code, user_info: userInfo, allow_create: allowCreate });
    },
    // 微信：未绑定时创建新账号
    wechatCreate: function (wechatTempToken, userInfo) {
        return request('/wechat/create', 'POST', { wechat_temp_token: wechatTempToken, user_info: userInfo });
    },
    // 微信：绑定已有账号（邮箱验证码）
    wechatBindSendCode: function (wechatTempToken, email) {
        return request('/wechat/bind/send_code', 'POST', { wechat_temp_token: wechatTempToken, email: email });
    },
    wechatBindPassword: function (wechatTempToken, account, password) {
        return request('/wechat/bind', 'POST', {
            wechat_temp_token: wechatTempToken,
            bind_mode: 'password',
            account: account,
            password: password
        });
    },
    wechatBindEmailCode: function (wechatTempToken, email, code) {
        return request('/wechat/bind', 'POST', {
            wechat_temp_token: wechatTempToken,
            bind_mode: 'email_code',
            email: email,
            code: code
        });
    },
    // Web 扫码登录：小程序确认
    webLoginConfirm: function (sid, nonce) {
        return request('/web_login/confirm', 'POST', { sid: sid, nonce: nonce });
    },
    // 小程序：获取用于 web-view 打开「Web 前台」的一次性登录跳转
    getMiniWebViewUrl: function (next) {
        if (next === void 0) { next = '/hub'; }
        return request('/web_login/mini_webview_url', 'POST', { next: next });
    },
    // Web 账号管理：绑定微信（小程序确认，使用 wx.login code）
    webWechatBindConfirm: function (sid, nonce, code) {
        return request('/wechat/bind_confirm', 'POST', { sid: sid, nonce: nonce, code: code });
    },
    // === 小程序：邮箱/手机号 + 密码登录（JWT） ===
    miniPasswordLogin: function (account, password) {
        return request('/mini/login', 'POST', { account: account, password: password });
    },
    miniSendEmailLoginCode: function (email) {
        return request('/mini/email/send-login-code', 'POST', { email: email });
    },
    miniEmailLogin: function (email, code) {
        return request('/mini/email/login', 'POST', { email: email, code: code });
    },
    // 小程序：已登录用户绑定微信（密码/邮箱登录后引导绑定）
    miniWechatBind: function (code) {
        return request('/mini/wechat/bind', 'POST', { code: code });
    },
    getAuthLoginMethods: function () {
        return request('/auth/login-methods', 'GET');
    },
    // 获取科目列表
    getSubjects: function () { return request('/quiz/subjects', 'GET'); },
    // 获取科目元信息（id/name/题量）
    getSubjectsMeta: function () {
        return request('/quiz/subjects/meta', 'GET');
    },
    // 题库广场：公开题库列表（系统题库 + 用户公开题库）
    getPublicBanks: function (params) {
        return request('/public/banks', 'GET', params || {});
    },
    getPublicBankCard: function (sourceType, bankId) {
        return request("/public/banks/card/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId))), 'GET');
    },
    joinPublicBank: function (sourceType, bankId) {
        return request("/public/banks/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId)), "/join"), 'POST', {});
    },
    leavePublicBank: function (sourceType, bankId) {
        return request("/public/banks/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId)), "/join"), 'DELETE', {});
    },
    // 获取题目列表
    getQuestions: function (params) { return request('/quiz/questions', 'GET', params); },
    // 获取题目详情
    getQuestionDetail: function (id) { return request("/quiz/questions/".concat(id), 'GET'); },
    // 搜索题目（用于小程序搜索页）
    searchQuestions: function (params) { return request('/quiz/search', 'GET', params); },
    // 记录答题结果
    recordResult: function (questionId, isCorrect) {
        return request('/quiz/record_result', 'POST', {
            question_id: questionId,
            is_correct: isCorrect
        });
    },
    // 主观题判分（公共题库与个人题库共用）
    gradeSubjective: function (payload) { return request('/quiz/grade_subjective', 'POST', payload); },
    // 切换收藏
    toggleFavorite: function (questionId) {
        return request('/quiz/favorite', 'POST', { question_id: questionId });
    },
    // AI 解析（占位/可替换为真实 AI）
    aiExplain: function (payload) {
        return request('/quiz/ai/explain', 'POST', payload);
    },
    // 获取科目详情信息
    getSubjectInfo: function (subject) {
        return request("/quiz/subjects/".concat(encodeURIComponent(subject), "/info"), 'GET');
    },
    // 科目统计详情（用于题库详情页-统计子页面）
    getSubjectStatsDetail: function (subject, daysOrParams) {
        if (daysOrParams === void 0) { daysOrParams = 14; }
        var params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
        return request("/quiz/subjects/".concat(encodeURIComponent(subject), "/stats"), 'GET', params);
    },
    // 科目题目列表（用于统计页：错题/收藏列表与图表）
    getSubjectQuestions: function (subject, params) { return request("/quiz/subjects/".concat(encodeURIComponent(subject), "/questions"), 'GET', params || {}); },
    // 科目收藏新增趋势（按收藏创建时间聚合）
    getSubjectFavoritesTrend: function (subject, days) {
        if (days === void 0) { days = 30; }
        return request("/quiz/subjects/".concat(encodeURIComponent(subject), "/favorites/trend"), 'GET', { days: days });
    },
    // 获取题目数量统计（支持范围和题型筛选）
    getQuestionsCount: function (params) { return request('/quiz/questions/count', 'GET', params || {}); },
    // 获取用户收藏和错题数量（支持题型筛选）
    getUserCounts: function (params) { return request('/quiz/questions/user_counts', 'GET', params); },
    // 学习统计（对齐 Web /history）
    getHistoryStats: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("history:".concat(days), 15 * 1000, function () { return request('/quiz/history', 'GET', { days: days }); });
    },
    // 数据中心聚合（对齐 Web /api/data/center）
    getDataCenter: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("data-center:".concat(days), 15 * 1000, function () {
            return request('/data/center', 'GET', { days: days }).then(normalizeDataCenterContext);
        });
    },
    // 数据中心：标签聚合统计（对齐 Web /api/data/tags）
    getDataTags: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("data-tags:".concat(days), 15 * 1000, function () { return request('/data/tags', 'GET', { days: days }); });
    },
    // 数据中心 AI 建议（对齐 Web /api/data/ai-advice）
    getDataAiAdvice: function (prompt, days) {
        if (days === void 0) { days = 30; }
        return request('/data/ai-advice', 'POST', { prompt: prompt, days: days });
    },
    // 获取云端进度（与 Web 端 /api/progress 互通）
    getProgress: function (key) { return request('/progress', 'GET', { key: key }); },
    // 保存云端进度（与 Web 端 /api/progress 互通）
    saveProgress: function (key, data) { return request('/progress', 'POST', { key: key, data: data }); },
    // 删除云端进度（与 Web 端 /api/progress 互通）
    deleteProgress: function (key) { return request("/progress?key=".concat(encodeURIComponent(key)), 'DELETE'); },
    // 加强训练（错题/相似题，对齐 Web /api/quiz/reinforce）
    getQuizReinforce: function (params) { return request('/quiz/reinforce', 'GET', params || {}); },
    // === 模拟考试（与 Web /api/exams 互通） ===
    createExam: function (data) { return request('/exams/create', 'POST', data); },
    getExam: function (examId) { return request("/exams/".concat(examId), 'GET'); },
    deleteExam: function (examId) { return request("/exams/".concat(examId), 'DELETE'); },
    // 考试记录（对齐 Web /exams?tab=records）
    getExamRecords: function (params) { return request('/exams/records', 'GET', params || {}); },
    // 考试数据（对齐 Web /exams?tab=data）
    getExamStats: function (params) {
        return request('/exams/stats', 'GET', params || {});
    },
    saveExamDraft: function (examId, answers) {
        return request('/exams/save_draft', 'POST', { exam_id: examId, answers: answers });
    },
    submitExam: function (examId, answers) {
        return request('/exams/submit', 'POST', { exam_id: examId, answers: answers });
    },
    examToMistakes: function (examId) { return request("/exams/".concat(examId, "/mistakes"), 'POST', {}); },
    getExamTemplates: function () { return request('/exams/templates', 'GET'); },
    createExamTemplate: function (data) {
        return request('/exams/templates', 'POST', data);
    },
    deleteExamTemplate: function (templateId) { return request("/exams/templates/".concat(templateId), 'DELETE'); },
    // === 通知（与 Web /api/notifications 互通） ===
    getNotifications: function (params) {
        return request('/notifications', 'GET', params || {});
    },
    getNotificationDetail: function (id, params) {
        return request("/notifications/".concat(id), 'GET', params || {});
    },
    markNotificationRead: function (id) { return request("/notifications/".concat(id, "/read"), 'POST', {}); },
    dismissNotification: function (id) { return request("/notifications/".concat(id, "/dismiss"), 'POST', {}); },
    getUnreadNotificationCount: function () { return request('/notifications/unread_count', 'GET'); },
    // === 账号资料/设置（与 Web /api/profile /api/settings/about 互通） ===
    getProfile: function () {
        return request('/profile', 'GET');
    },
    updateProfile: function (data) {
        return request('/profile/update', 'POST', data);
    },
    checkUsername: function (username, strictNickname) {
        if (strictNickname === void 0) { strictNickname = false; }
        return request('/profile/check-username', 'POST', { username: username, strict_nickname: strictNickname });
    },
    updateProfilePassword: function (data) {
        return request('/profile/password', 'POST', {
            current_password: data.current_password || '',
            new_password: data.new_password,
            is_set_password: !!data.is_set_password
        });
    },
    sendEmailBindCode: function (email) {
        return request('/email/send-bind-code', 'POST', { email: email });
    },
    bindEmail: function (email, code) {
        return request('/email/bind', 'POST', { email: email, code: code });
    },
    wechatUnbind: function () { return request('/wechat/unbind', 'POST', {}); },
    getEduScheduleStatus: function () {
        return request('/edu-schedule/status', 'GET');
    },
    queryEduSchedule: function (payload) {
        return request('/edu-schedule/query', 'POST', payload);
    },
    queryEduGrades: function (payload) {
        return request('/edu-schedule/grades/query', 'POST', payload);
    },
    saveEduCredentials: function (username, password) {
        return request('/edu-schedule/credentials', 'POST', { username: username, password: password });
    },
    deleteEduCredentials: function () {
        return request('/edu-schedule/credentials', 'DELETE');
    },
    uploadProfileAvatar: function (filePath) {
        return new Promise(function (resolve, reject) {
            var apiBaseUrl = getApiBaseUrl();
            var token = wx.getStorageSync('token') || '';
            if (!token) {
                reject(new Error('请先登录'));
                return;
            }
            wx.uploadFile({
                url: "".concat(apiBaseUrl, "/profile/avatar"),
                filePath: filePath,
                name: 'avatar',
                header: {
                    'Authorization': token ? "Bearer ".concat(token) : ''
                },
                success: function (res) {
                    var _a;
                    try {
                        var raw = res.data;
                        var js = typeof raw === 'string' ? JSON.parse(raw) : raw;
                        var ok = Number(res.statusCode) === 200 && js && js.status === 'success';
                        if (!ok) {
                            var msg = (js && (js.message || js.error)) || "\u4E0A\u4F20\u5931\u8D25: ".concat(res.statusCode);
                            reject(new Error(msg));
                            return;
                        }
                        var avatarUrl = (js.avatar_url || ((_a = js.data) === null || _a === void 0 ? void 0 : _a.avatar_url) || '').toString();
                        if (!avatarUrl) {
                            reject(new Error('上传失败：缺少 avatar_url'));
                            return;
                        }
                        resolve({ avatar_url: avatarUrl });
                    }
                    catch (e) {
                        reject(new Error((e === null || e === void 0 ? void 0 : e.message) || '上传失败：响应解析异常'));
                    }
                },
                fail: function (err) {
                    var errorMsg = (err === null || err === void 0 ? void 0 : err.errMsg) || (err === null || err === void 0 ? void 0 : err.message) || '网络异常：上传失败';
                    maybeShowDevHostHint(apiBaseUrl, errorMsg);
                    reject(new Error(errorMsg));
                }
            });
        });
    },
    // === 签到（与 Web 端 /api/user/checkin 互通） ===
    getCheckinStatus: function () {
        return request('/user/checkin/status', 'GET');
    },
    doCheckin: function () {
        return request('/user/checkin', 'POST');
    },
    // === 继续练习（获取最近一次练习记录） ===
    getLastPractice: function () {
        return request('/user/last-practice', 'GET');
    },
    getSettingsAbout: function () {
        return request('/settings/about', 'GET');
    },
    // === 用户题库（个人题库） ===
    // 创建题库
    createBank: function (data) {
        return request('/user/banks/api', 'POST', data);
    },
    // 获取我的题库列表
    getMyBanks: function (params) {
        return request('/user/banks/api/list', 'GET', params || {});
    },
    // 获取我的题库融合视图（我创建 + 公开加入 + 分享加入，对齐 Web /user/banks）
    getMyBankOverview: function (params) {
        return request('/user/banks/api/overview', 'GET', params || {});
    },
    // 获取收到的分享题库列表
    getSharedBanks: function () { return request('/user/banks/api/shared', 'GET'); },
    // 获取题库详情
    getBankDetail: function (bankId) { return request("/user/banks/api/".concat(bankId), 'GET'); },
    // 设置题库公开/私有
    setBankPublic: function (bankId, data) {
        return request("/user/banks/api/".concat(bankId, "/public"), 'POST', data);
    },
    // 获取题库题目列表
    getBankQuestions: function (bankId, params) { return request("/user/banks/api/".concat(bankId, "/questions"), 'GET', params || {}); },
    // 获取题库题目详情（单题）
    getBankQuestionDetail: function (bankId, questionId) {
        return request("/user/banks/api/".concat(bankId, "/questions/").concat(questionId), 'GET');
    },
    // 获取题库刷题题目
    getBankQuizQuestions: function (bankId, params) { return request("/user/banks/api/".concat(bankId, "/quiz"), 'GET', params || {}); },
    // 记录题库答题结果
    recordBankQuizResult: function (bankId, data) { return request("/user/banks/api/".concat(bankId, "/quiz/record"), 'POST', data); },
    // 切换题库题目收藏状态
    toggleBankFavorite: function (bankId, questionId) {
        return request("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/favorite"), 'POST');
    },
    // 获取题库答题统计
    getBankMyStats: function (bankId) { return request("/user/banks/api/".concat(bankId, "/my-stats"), 'GET'); },
    // 题库统计详情（用于题库详情页-统计子页面）
    getBankStatsDetail: function (bankId, daysOrParams) {
        if (daysOrParams === void 0) { daysOrParams = 14; }
        var params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
        var key = "bank-stats:".concat(bankId, ":").concat(JSON.stringify(params));
        return memory_cache_1.memoryCache.remember(key, 15 * 1000, function () { return request("/user/banks/api/".concat(bankId, "/stats"), 'GET', params); });
    },
    // 题库收藏新增趋势（按收藏创建时间聚合）
    getBankFavoritesTrend: function (bankId, days) {
        if (days === void 0) { days = 30; }
        return request("/user/banks/api/".concat(bankId, "/favorites/trend"), 'GET', { days: days });
    },
    // 获取题库用户统计（总数、收藏数、错题数，支持题型和来源筛选）
    getBankUserCounts: function (bankId, params) { return request("/user/banks/api/".concat(bankId, "/user-counts"), 'GET', params || {}); },
    // 通过分享码加入题库
    joinBankByCode: function (shareCode) {
        return request('/user/banks/api/join', 'POST', { share_code: shareCode });
    },
    // 通过分享链接token加入题库
    joinBankByToken: function (token) {
        return request('/user/banks/api/join', 'POST', { token: token });
    },
    // 预览加入题库（不写入记录，用于“加入确认页”）
    previewJoinBank: function (params) {
        return request('/user/banks/api/join/preview', 'GET', params || {});
    },
    // 获取题库分享列表
    getBankShares: function (bankId) {
        return request("/user/banks/api/".concat(bankId, "/shares"), 'GET');
    },
    // 获取题库使用人数（仅创建者可见）
    getBankUsageStats: function (bankId) {
        return request("/user/banks/api/".concat(bankId, "/usage-stats"), 'GET');
    },
    // 创建题库分享
    createBankShare: function (bankId, data) { return request("/user/banks/api/".concat(bankId, "/shares"), 'POST', data); },
    // 删除/撤销题库分享
    deleteBankShare: function (bankId, shareId) {
        return request("/user/banks/api/".concat(bankId, "/shares/").concat(shareId), 'DELETE');
    },
    // 搜索题库题目
    searchBankQuestions: function (bankId, params) { return request("/user/banks/api/".concat(bankId, "/questions"), 'GET', params); },
    // === 题目标签（公有题库） ===
    // 获取用户所有标签
    getTags: function (params) { return request('/quiz/tags', 'GET', params || {}); },
    // 创建新标签
    createTag: function (name, params) {
        return request('/quiz/tags', 'POST', __assign({ name: name }, (params || {})));
    },
    // 删除标签（仅删除当前用户 + 当前科目下的标签与绑定）
    deleteTag: function (name, params) {
        return request('/quiz/tags', 'DELETE', __assign({ name: name }, (params || {})));
    },
    // 获取题目标签
    getQuestionTags: function (questionId) { return request("/quiz/questions/".concat(questionId, "/tags"), 'GET'); },
    // 设置题目标签
    setQuestionTags: function (questionId, tags) {
        return request("/quiz/questions/".concat(questionId, "/tags"), 'POST', { tags: tags });
    },
    // === 编辑题目（公有题库，需要管理员权限） ===
    updateQuestion: function (questionId, data) { return request("/quiz/questions/".concat(questionId), 'PUT', data); },
    // === 题目标签（个人题库） ===
    // 获取题库标签
    getBankTags: function (bankId) { return request("/user/banks/api/".concat(bankId, "/tags"), 'GET'); },
    // 创建题库标签
    createBankTag: function (bankId, name) {
        return request("/user/banks/api/".concat(bankId, "/tags"), 'POST', { name: name });
    },
    // 删除题库标签（仅删除当前用户 + 当前题库下的标签与绑定）
    deleteBankTag: function (bankId, name) {
        return request("/user/banks/api/".concat(bankId, "/tags"), 'DELETE', { name: name });
    },
    // 获取题库题目标签
    getBankQuestionTags: function (bankId, questionId) {
        return request("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/tags"), 'GET');
    },
    // 设置题库题目标签
    setBankQuestionTags: function (bankId, questionId, tags) {
        return request("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/tags"), 'POST', { tags: tags });
    },
    // === 编辑题目（个人题库） ===
    updateBankQuestion: function (bankId, questionId, data) { return request("/user/banks/api/".concat(bankId, "/questions/").concat(questionId), 'PUT', data); }
};
