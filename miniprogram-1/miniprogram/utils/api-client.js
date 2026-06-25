"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.request = request;
exports.unwrapApiEnvelopeMaybe = unwrapApiEnvelopeMaybe;
exports.normalizeDataCenterContext = normalizeDataCenterContext;
// HTTP 客户端核心（从 api-endpoints.ts 提取）
var config_1 = require("./config");
var url_utils_1 = require("./url-utils");
var hasShownDevHostHint = false;
function maybeShowDevHostHint(apiBaseUrl, message) {
    if (hasShownDevHostHint)
        return;
    var msg = String(message || '');
    try {
        var envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
        if (envVersion !== 'develop')
            return;
    }
    catch (e) { }
    var isDevtools = false;
    try {
        var platform = (0, config_1.getWxPlatform)();
        isDevtools = platform === 'devtools';
    }
    catch (e) { }
    var isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
    if (!isLocalhost)
        return;
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
    catch (e) { }
}
function request(url, method, data) {
    if (method === void 0) { method = 'GET'; }
    return new Promise(function (resolve, reject) {
        var apiBaseUrl = (0, url_utils_1.getApiBaseUrl)();
        var token = wx.getStorageSync('token') || '';
        var tokenAtRequest = token;
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
                    var latestToken = wx.getStorageSync('token') || '';
                    if (latestToken && latestToken !== tokenAtRequest) {
                        var err_1 = new Error(errorMsg);
                        err_1.statusCode = 401;
                        err_1.response = res.data;
                        reject(err_1);
                        return;
                    }
                    var pages = getCurrentPages();
                    var currentPage = pages[pages.length - 1];
                    var currentRoute_1 = currentPage ? currentPage.route : '';
                    wx.removeStorageSync('token');
                    wx.removeStorageSync('userInfo');
                    var guestAllowedPages = ['pages/hub-v2/hub-v2', 'pages/index-v2/index-v2', 'pages/subjects/subjects'];
                    var isGuestAllowedPage = guestAllowedPages.some(function (p) { return currentRoute_1.includes(p); });
                    if (!currentRoute_1.includes('login') && !isGuestAllowedPage) {
                        wx.reLaunch({ url: '/pages/login/login' });
                    }
                    var err = new Error(errorMsg);
                    err.statusCode = 401;
                    err.response = res.data;
                    reject(err);
                }
                else if (res.statusCode === 429) {
                    reject(new Error('请求过于频繁，请稍后再试'));
                }
                else {
                    var errorData = res.data;
                    var errorMsg = (errorData && (errorData.message || errorData.error)) || "\u8BF7\u6C42\u5931\u8D25: ".concat(res.statusCode);
                    reject(new Error(errorMsg));
                }
            },
            fail: function (err) {
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
