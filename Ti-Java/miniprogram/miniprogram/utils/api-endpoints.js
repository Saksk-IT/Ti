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
exports.api = exports.request = exports.normalizeImageUrls = exports.resolveUploadUrl = exports.getApiOrigin = void 0;
// API 端点定义（基础设施已提取到 api-client.ts 和 url-utils.ts）
var api_client_1 = require("./api-client");
Object.defineProperty(exports, "request", { enumerable: true, get: function () { return api_client_1.request; } });
var url_utils_1 = require("./url-utils");
Object.defineProperty(exports, "getApiOrigin", { enumerable: true, get: function () { return url_utils_1.getApiOrigin; } });
Object.defineProperty(exports, "resolveUploadUrl", { enumerable: true, get: function () { return url_utils_1.resolveUploadUrl; } });
Object.defineProperty(exports, "normalizeImageUrls", { enumerable: true, get: function () { return url_utils_1.normalizeImageUrls; } });
var config_1 = require("./config");
var memory_cache_1 = require("./memory-cache");
var hasShownUploadDevHostHint = false;
function maybeShowUploadDevHostHint(apiBaseUrl, message) {
    if (hasShownUploadDevHostHint)
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
        isDevtools = (0, config_1.getWxPlatform)() === 'devtools';
    }
    catch (e) { }
    var isLocalhost = /^http:\/\/(127\.0\.0\.1|localhost)(:|\/)/i.test(apiBaseUrl);
    if (!isLocalhost)
        return;
    var normalizedMsg = msg.toLowerCase();
    var isConnRefused = msg.includes('ERR_CONNECTION_REFUSED') ||
        msg.includes('errcode:-102') ||
        msg.includes('cronet_error_code:-102') ||
        normalizedMsg.includes('connection refused');
    var isGenericUploadFail = msg.trim() === 'uploadFile:fail' || msg.trim() === 'request:fail';
    if (!isConnRefused && !(isDevtools && isGenericUploadFail))
        return;
    hasShownUploadDevHostHint = true;
    wx.showModal({
        title: '无法连接后端',
        content: "\u5F53\u524D API \u5730\u5740\u4E3A\uFF1A".concat(apiBaseUrl, "\n\n\u8BF7\u786E\u8BA4 Docker \u5F00\u53D1\u670D\u52A1\u6B63\u5728\u8FD0\u884C\uFF0C\u6216\u5230\u300C\u5F00\u53D1\u8BBE\u7F6E\u300D\u8C03\u6574 API Host/Port \u540E\u91CD\u8BD5\u3002"),
        confirmText: '去设置',
        cancelText: '知道了',
        success: function (res) {
            if (!res.confirm)
                return;
            wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
        }
    });
}
// 导出API方法
exports.api = {
    // 微信登录
    wechatLogin: function (code, userInfo, allowCreate) {
        if (allowCreate === void 0) { allowCreate = true; }
        return (0, api_client_1.request)('/wechat/login', 'POST', { code: code, user_info: userInfo, allow_create: allowCreate });
    },
    // 微信：未绑定时创建新账号
    wechatCreate: function (wechatTempToken, userInfo) {
        return (0, api_client_1.request)('/wechat/create', 'POST', { wechat_temp_token: wechatTempToken, user_info: userInfo });
    },
    // 微信：绑定已有账号（邮箱验证码）
    wechatBindSendCode: function (wechatTempToken, email) {
        return (0, api_client_1.request)('/wechat/bind/send_code', 'POST', { wechat_temp_token: wechatTempToken, email: email });
    },
    wechatBindPassword: function (wechatTempToken, account, password) {
        return (0, api_client_1.request)('/wechat/bind', 'POST', {
            wechat_temp_token: wechatTempToken,
            bind_mode: 'password',
            account: account,
            password: password
        });
    },
    wechatBindEmailCode: function (wechatTempToken, email, code) {
        return (0, api_client_1.request)('/wechat/bind', 'POST', {
            wechat_temp_token: wechatTempToken,
            bind_mode: 'email_code',
            email: email,
            code: code
        });
    },
    // Web 扫码登录：小程序确认
    webLoginConfirm: function (sid, nonce) {
        return (0, api_client_1.request)('/web_login/confirm', 'POST', { sid: sid, nonce: nonce });
    },
    // 小程序：获取用于 web-view 打开「Web 前台」的一次性登录跳转
    getMiniWebViewUrl: function (next) {
        if (next === void 0) { next = '/hub'; }
        return (0, api_client_1.request)('/web_login/mini_webview_url', 'POST', { next: next });
    },
    // Web 账号管理：绑定微信（小程序确认，使用 wx.login code）
    webWechatBindConfirm: function (sid, nonce, code) {
        return (0, api_client_1.request)('/wechat/bind_confirm', 'POST', { sid: sid, nonce: nonce, code: code });
    },
    // === 小程序：邮箱/手机号 + 密码登录（JWT） ===
    miniPasswordLogin: function (account, password) {
        return (0, api_client_1.request)('/mini/login', 'POST', { account: account, password: password });
    },
    miniSendEmailLoginCode: function (email) {
        return (0, api_client_1.request)('/mini/email/send-login-code', 'POST', { email: email });
    },
    miniEmailLogin: function (email, code) {
        return (0, api_client_1.request)('/mini/email/login', 'POST', { email: email, code: code });
    },
    // 小程序：已登录用户绑定微信（密码/邮箱登录后引导绑定）
    miniWechatBind: function (code) {
        return (0, api_client_1.request)('/mini/wechat/bind', 'POST', { code: code });
    },
    getAuthLoginMethods: function () {
        return (0, api_client_1.request)('/auth/login-methods', 'GET');
    },
    // 小程序：忘记密码 — 发送验证码
    miniSendForgotPasswordCode: function (email) {
        return (0, api_client_1.request)('/mini/forgot-password/send-code', 'POST', { email: email });
    },
    // 小程序：忘记密码 — 重置密码
    miniResetPassword: function (email, code, new_password) {
        return (0, api_client_1.request)('/mini/forgot-password/reset', 'POST', { email: email, code: code, new_password: new_password });
    },
    // 获取科目列表
    getSubjects: function () { return (0, api_client_1.request)('/quiz/subjects', 'GET'); },
    // 获取科目元信息（id/name/题量）
    getSubjectsMeta: function () {
        return (0, api_client_1.request)('/quiz/subjects/meta', 'GET');
    },
    // 题库广场：公开题库列表（系统题库 + 用户公开题库）
    getPublicBanks: function (params) {
        return (0, api_client_1.request)('/public/banks', 'GET', params || {});
    },
    getPublicBankCard: function (sourceType, bankId) {
        return (0, api_client_1.request)("/public/banks/card/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId))), 'GET');
    },
    joinPublicBank: function (sourceType, bankId) {
        return (0, api_client_1.request)("/public/banks/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId)), "/join"), 'POST', {});
    },
    leavePublicBank: function (sourceType, bankId) {
        return (0, api_client_1.request)("/public/banks/".concat(encodeURIComponent(sourceType), "/").concat(encodeURIComponent(String(bankId)), "/join"), 'DELETE', {});
    },
    // 获取题目列表
    getQuestions: function (params) { return (0, api_client_1.request)('/quiz/questions', 'GET', params); },
    // 获取题目详情
    getQuestionDetail: function (id) { return (0, api_client_1.request)("/quiz/questions/".concat(id), 'GET'); },
    // 搜索题目（用于小程序搜索页）
    searchQuestions: function (params) { return (0, api_client_1.request)('/quiz/search', 'GET', params); },
    // 记录答题结果
    recordResult: function (questionId, isCorrect) {
        return (0, api_client_1.request)('/quiz/record_result', 'POST', {
            question_id: questionId,
            is_correct: isCorrect
        });
    },
    // 主观题判分（公共题库与个人题库共用）
    gradeSubjective: function (payload) { return (0, api_client_1.request)('/quiz/grade_subjective', 'POST', payload); },
    // 切换收藏
    toggleFavorite: function (questionId) {
        return (0, api_client_1.request)('/quiz/favorite', 'POST', { question_id: questionId });
    },
    // AI 解析（占位/可替换为真实 AI）
    aiExplain: function (payload) {
        return (0, api_client_1.request)('/quiz/ai/explain', 'POST', payload);
    },
    // 获取科目详情信息
    getSubjectInfo: function (subject) {
        return (0, api_client_1.request)("/quiz/subjects/".concat(encodeURIComponent(subject), "/info"), 'GET');
    },
    // 科目统计详情（用于题库详情页-统计子页面）
    getSubjectStatsDetail: function (subject, daysOrParams) {
        if (daysOrParams === void 0) { daysOrParams = 14; }
        var params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
        return (0, api_client_1.request)("/quiz/subjects/".concat(encodeURIComponent(subject), "/stats"), 'GET', params);
    },
    // 科目题目列表（用于统计页：错题/收藏列表与图表）
    getSubjectQuestions: function (subject, params) { return (0, api_client_1.request)("/quiz/subjects/".concat(encodeURIComponent(subject), "/questions"), 'GET', params || {}); },
    // 科目收藏新增趋势（按收藏创建时间聚合）
    getSubjectFavoritesTrend: function (subject, days) {
        if (days === void 0) { days = 30; }
        return (0, api_client_1.request)("/quiz/subjects/".concat(encodeURIComponent(subject), "/favorites/trend"), 'GET', { days: days });
    },
    // 获取题目数量统计（支持范围和题型筛选）
    getQuestionsCount: function (params) { return (0, api_client_1.request)('/quiz/questions/count', 'GET', params || {}); },
    // 获取用户收藏和错题数量（支持题型筛选）
    getUserCounts: function (params) { return (0, api_client_1.request)('/quiz/questions/user_counts', 'GET', params); },
    // 学习统计（对齐 Web /history）
    getHistoryStats: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("history:".concat(days), 15 * 1000, function () { return (0, api_client_1.request)('/quiz/history', 'GET', { days: days }); });
    },
    // 数据中心聚合（对齐 Web /api/data/center）
    getDataCenter: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("data-center:".concat(days), 15 * 1000, function () {
            return (0, api_client_1.request)('/data/center', 'GET', { days: days }).then(api_client_1.normalizeDataCenterContext);
        });
    },
    // 数据中心：标签聚合统计（对齐 Web /api/data/tags）
    getDataTags: function (days) {
        if (days === void 0) { days = 30; }
        return memory_cache_1.memoryCache.remember("data-tags:".concat(days), 15 * 1000, function () { return (0, api_client_1.request)('/data/tags', 'GET', { days: days }); });
    },
    // 数据中心 AI 建议（对齐 Web /api/data/ai-advice）
    getDataAiAdvice: function (prompt, days) {
        if (days === void 0) { days = 30; }
        return (0, api_client_1.request)('/data/ai-advice', 'POST', { prompt: prompt, days: days });
    },
    // 获取云端进度（与 Web 端 /api/progress 互通）
    getProgress: function (key) { return (0, api_client_1.request)('/progress', 'GET', { key: key }); },
    // 保存云端进度（与 Web 端 /api/progress 互通）
    saveProgress: function (key, data) { return (0, api_client_1.request)('/progress', 'POST', { key: key, data: data }); },
    // 删除云端进度（与 Web 端 /api/progress 互通）
    deleteProgress: function (key) { return (0, api_client_1.request)("/progress?key=".concat(encodeURIComponent(key)), 'DELETE'); },
    // 加强训练（错题/相似题，对齐 Web /api/quiz/reinforce）
    getQuizReinforce: function (params) { return (0, api_client_1.request)('/quiz/reinforce', 'GET', params || {}); },
    // === 模拟考试（与 Web /api/exams 互通） ===
    createExam: function (data) { return (0, api_client_1.request)('/exams/create', 'POST', data); },
    getExam: function (examId) { return (0, api_client_1.request)("/exams/".concat(examId), 'GET'); },
    deleteExam: function (examId) { return (0, api_client_1.request)("/exams/".concat(examId), 'DELETE'); },
    // 考试记录（对齐 Web /exams?tab=records）
    getExamRecords: function (params) { return (0, api_client_1.request)('/exams/records', 'GET', params || {}); },
    // 考试数据（对齐 Web /exams?tab=data）
    getExamStats: function (params) {
        return (0, api_client_1.request)('/exams/stats', 'GET', params || {});
    },
    saveExamDraft: function (examId, answers) {
        return (0, api_client_1.request)('/exams/save_draft', 'POST', { exam_id: examId, answers: answers });
    },
    submitExam: function (examId, answers) {
        return (0, api_client_1.request)('/exams/submit', 'POST', { exam_id: examId, answers: answers });
    },
    examToMistakes: function (examId) { return (0, api_client_1.request)("/exams/".concat(examId, "/mistakes"), 'POST', {}); },
    getExamTemplates: function () { return (0, api_client_1.request)('/exams/templates', 'GET'); },
    createExamTemplate: function (data) {
        return (0, api_client_1.request)('/exams/templates', 'POST', data);
    },
    deleteExamTemplate: function (templateId) { return (0, api_client_1.request)("/exams/templates/".concat(templateId), 'DELETE'); },
    // === 通知（与 Web /api/notifications 互通） ===
    getNotifications: function (params) {
        return (0, api_client_1.request)('/notifications', 'GET', params || {});
    },
    getNotificationDetail: function (id, params) {
        return (0, api_client_1.request)("/notifications/".concat(id), 'GET', params || {});
    },
    markNotificationRead: function (id) { return (0, api_client_1.request)("/notifications/".concat(id, "/read"), 'POST', {}); },
    dismissNotification: function (id) { return (0, api_client_1.request)("/notifications/".concat(id, "/dismiss"), 'POST', {}); },
    getUnreadNotificationCount: function () { return (0, api_client_1.request)('/notifications/unread_count', 'GET'); },
    // === 账号资料/设置（与 Web /api/profile /api/settings/about 互通） ===
    getProfile: function () {
        return (0, api_client_1.request)('/profile', 'GET');
    },
    updateProfile: function (data) {
        return (0, api_client_1.request)('/profile/update', 'POST', data);
    },
    checkUsername: function (username, strictNickname) {
        if (strictNickname === void 0) { strictNickname = false; }
        return (0, api_client_1.request)('/profile/check-username', 'POST', { username: username, strict_nickname: strictNickname });
    },
    updateProfilePassword: function (data) {
        return (0, api_client_1.request)('/profile/password', 'POST', {
            current_password: data.current_password || '',
            new_password: data.new_password,
            is_set_password: !!data.is_set_password
        });
    },
    sendEmailBindCode: function (email) {
        return (0, api_client_1.request)('/email/send-bind-code', 'POST', { email: email });
    },
    bindEmail: function (email, code) {
        return (0, api_client_1.request)('/email/bind', 'POST', { email: email, code: code });
    },
    wechatUnbind: function () { return (0, api_client_1.request)('/wechat/unbind', 'POST', {}); },
    getEduScheduleStatus: function () {
        return (0, api_client_1.request)('/edu-schedule/status', 'GET');
    },
    queryEduSchedule: function (payload) {
        return (0, api_client_1.request)('/edu-schedule/query', 'POST', payload);
    },
    queryEduGrades: function (payload) {
        return (0, api_client_1.request)('/edu-schedule/grades/query', 'POST', payload);
    },
    getEduQueryTask: function (taskId) {
        return (0, api_client_1.request)("/edu-schedule/query-tasks/".concat(encodeURIComponent(taskId)), 'GET');
    },
    cancelEduQueryTask: function (taskId) {
        return (0, api_client_1.request)("/edu-schedule/query-tasks/".concat(encodeURIComponent(taskId), "/cancel"), 'POST', {});
    },
    completeEduWebvpnSession: function (challengeId, captchaCode) {
        return (0, api_client_1.request)('/edu-schedule/webvpn-session/complete', 'POST', {
            challenge_id: challengeId,
            captcha_code: captchaCode,
        });
    },
    saveEduCredentials: function (username, password) {
        return (0, api_client_1.request)('/edu-schedule/credentials', 'POST', { username: username, password: password });
    },
    deleteEduCredentials: function () {
        return (0, api_client_1.request)('/edu-schedule/credentials', 'DELETE');
    },
    uploadProfileAvatar: function (filePath) {
        return new Promise(function (resolve, reject) {
            var apiBaseUrl = (0, url_utils_1.getApiBaseUrl)();
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
                    maybeShowUploadDevHostHint(apiBaseUrl, errorMsg);
                    reject(new Error(errorMsg));
                }
            });
        });
    },
    // === 签到（与 Web 端 /api/user/checkin 互通） ===
    getCheckinStatus: function () {
        return (0, api_client_1.request)('/user/checkin/status', 'GET');
    },
    doCheckin: function () {
        return (0, api_client_1.request)('/user/checkin', 'POST');
    },
    // === 继续练习（获取最近一次练习记录） ===
    getLastPractice: function () {
        return (0, api_client_1.request)('/user/last-practice', 'GET');
    },
    getSettingsAbout: function () {
        return (0, api_client_1.request)('/settings/about', 'GET');
    },
    // === 用户题库（个人题库） ===
    // 创建题库
    createBank: function (data) {
        return (0, api_client_1.request)('/user/banks/api', 'POST', data);
    },
    // 获取我的题库列表
    getMyBanks: function (params) {
        return (0, api_client_1.request)('/user/banks/api/list', 'GET', params || {});
    },
    // 获取我的题库融合视图（我创建 + 公开加入 + 分享加入，对齐 Web /user/banks）
    getMyBankOverview: function (params) {
        return (0, api_client_1.request)('/user/banks/api/overview', 'GET', params || {});
    },
    // 获取收到的分享题库列表
    getSharedBanks: function () { return (0, api_client_1.request)('/user/banks/api/shared', 'GET'); },
    // 获取题库详情
    getBankDetail: function (bankId) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId), 'GET'); },
    // 设置题库公开/私有
    setBankPublic: function (bankId, data) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/public"), 'POST', data);
    },
    // 获取题库题目列表
    getBankQuestions: function (bankId, params) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions"), 'GET', params || {}); },
    // 获取题库题目详情（单题）
    getBankQuestionDetail: function (bankId, questionId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId), 'GET');
    },
    // 获取题库刷题题目
    getBankQuizQuestions: function (bankId, params) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/quiz"), 'GET', params || {}); },
    // 记录题库答题结果
    recordBankQuizResult: function (bankId, data) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/quiz/record"), 'POST', data); },
    // 切换题库题目收藏状态
    toggleBankFavorite: function (bankId, questionId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/favorite"), 'POST');
    },
    // 获取题库答题统计
    getBankMyStats: function (bankId) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/my-stats"), 'GET'); },
    // 题库统计详情（用于题库详情页-统计子页面）
    getBankStatsDetail: function (bankId, daysOrParams) {
        if (daysOrParams === void 0) { daysOrParams = 14; }
        var params = typeof daysOrParams === 'number' ? { days: daysOrParams } : (daysOrParams || {});
        var key = "bank-stats:".concat(bankId, ":").concat(JSON.stringify(params));
        return memory_cache_1.memoryCache.remember(key, 15 * 1000, function () { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/stats"), 'GET', params); });
    },
    // 题库收藏新增趋势（按收藏创建时间聚合）
    getBankFavoritesTrend: function (bankId, days) {
        if (days === void 0) { days = 30; }
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/favorites/trend"), 'GET', { days: days });
    },
    // 获取题库用户统计（总数、收藏数、错题数，支持题型和来源筛选）
    getBankUserCounts: function (bankId, params) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/user-counts"), 'GET', params || {}); },
    // 通过分享码加入题库
    joinBankByCode: function (shareCode) {
        return (0, api_client_1.request)('/user/banks/api/join', 'POST', { share_code: shareCode });
    },
    // 通过分享链接token加入题库
    joinBankByToken: function (token) {
        return (0, api_client_1.request)('/user/banks/api/join', 'POST', { token: token });
    },
    // 预览加入题库（不写入记录，用于“加入确认页”）
    previewJoinBank: function (params) {
        return (0, api_client_1.request)('/user/banks/api/join/preview', 'GET', params || {});
    },
    // 获取题库分享列表
    getBankShares: function (bankId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/shares"), 'GET');
    },
    // 获取题库使用人数（仅创建者可见）
    getBankUsageStats: function (bankId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/usage-stats"), 'GET');
    },
    // 创建题库分享
    createBankShare: function (bankId, data) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/shares"), 'POST', data); },
    // 删除/撤销题库分享
    deleteBankShare: function (bankId, shareId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/shares/").concat(shareId), 'DELETE');
    },
    // 搜索题库题目
    searchBankQuestions: function (bankId, params) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions"), 'GET', params); },
    // === 题目标签（公有题库） ===
    // 获取用户所有标签
    getTags: function (params) { return (0, api_client_1.request)('/quiz/tags', 'GET', params || {}); },
    // 创建新标签
    createTag: function (name, params) {
        return (0, api_client_1.request)('/quiz/tags', 'POST', __assign({ name: name }, (params || {})));
    },
    // 删除标签（仅删除当前用户 + 当前科目下的标签与绑定）
    deleteTag: function (name, params) {
        return (0, api_client_1.request)('/quiz/tags', 'DELETE', __assign({ name: name }, (params || {})));
    },
    // 获取题目标签
    getQuestionTags: function (questionId) { return (0, api_client_1.request)("/quiz/questions/".concat(questionId, "/tags"), 'GET'); },
    // 设置题目标签
    setQuestionTags: function (questionId, tags) {
        return (0, api_client_1.request)("/quiz/questions/".concat(questionId, "/tags"), 'POST', { tags: tags });
    },
    // === 编辑题目（公有题库，需要管理员权限） ===
    updateQuestion: function (questionId, data) { return (0, api_client_1.request)("/quiz/questions/".concat(questionId), 'PUT', data); },
    // === 题目标签（个人题库） ===
    // 获取题库标签
    getBankTags: function (bankId) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/tags"), 'GET'); },
    // 创建题库标签
    createBankTag: function (bankId, name) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/tags"), 'POST', { name: name });
    },
    // 删除题库标签（仅删除当前用户 + 当前题库下的标签与绑定）
    deleteBankTag: function (bankId, name) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/tags"), 'DELETE', { name: name });
    },
    // 获取题库题目标签
    getBankQuestionTags: function (bankId, questionId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/tags"), 'GET');
    },
    // 设置题库题目标签
    setBankQuestionTags: function (bankId, questionId, tags) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId, "/tags"), 'POST', { tags: tags });
    },
    // === 编辑题目（个人题库） ===
    updateBankQuestion: function (bankId, questionId, data) { return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId), 'PUT', data); },
    // 删除题库题目（个人题库创建者）
    deleteBankQuestion: function (bankId, questionId) {
        return (0, api_client_1.request)("/user/banks/api/".concat(bankId, "/questions/").concat(questionId), 'DELETE', {});
    }
};
