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
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var avatar_1 = require("../../utils/avatar");
var hub_content_1 = require("./hub-content");
var SETUP_NICKNAME_RE = /^[\u4e00-\u9fffA-Za-z0-9]{1,8}$/;
var SETUP_NICKNAME_ERROR = '昵称只能使用汉字、字母、数字，最多8个字符';
var RANDOM_NICKNAME_PREFIXES = ['题友', '学友', '考友', '小题'];
function toSafeNumber(value) {
    var num = Number(value || 0);
    return Number.isFinite(num) ? num : 0;
}
function toSafeString(value, fallback) {
    if (fallback === void 0) { fallback = ''; }
    var text = String(value || '').trim();
    return text || fallback;
}
function padNumber(value, length) {
    var result = String(value);
    while (result.length < length) {
        result = "0".concat(result);
    }
    return result;
}
function createRandomNickname() {
    var prefix = RANDOM_NICKNAME_PREFIXES[Math.floor(Math.random() * RANDOM_NICKNAME_PREFIXES.length)] || '题友';
    var suffixLength = 8 - prefix.length;
    var suffixMax = Math.pow(10, suffixLength);
    var suffix = padNumber(Math.floor(Math.random() * suffixMax), suffixLength);
    return "".concat(prefix).concat(suffix);
}
function normalizeSetupNickname(value) {
    return String(value || '').trim();
}
function isValidSetupNickname(value) {
    return SETUP_NICKNAME_RE.test(value);
}
function formatTimeAgo(dateStr) {
    if (!dateStr)
        return '';
    try {
        var date = new Date(dateStr.replace(' ', 'T'));
        var now = new Date();
        var diffMs = now.getTime() - date.getTime();
        var diffMin = Math.floor(diffMs / 60000);
        var diffHour = Math.floor(diffMs / 3600000);
        var diffDay = Math.floor(diffMs / 86400000);
        if (diffMin < 1)
            return '刚刚';
        if (diffMin < 60)
            return "".concat(diffMin, "\u5206\u949F\u524D");
        if (diffHour < 24)
            return "".concat(diffHour, "\u5C0F\u65F6\u524D");
        if (diffDay < 7)
            return "".concat(diffDay, "\u5929\u524D");
        return dateStr.slice(0, 10);
    }
    catch (_a) {
        return '';
    }
}
/** 根据时间戳计算相对时间（避免时区问题） */
function formatTimeAgoFromTimestamp(timestamp) {
    if (!timestamp)
        return '';
    try {
        var now = Date.now();
        var diffMs = now - timestamp;
        var diffMin = Math.floor(diffMs / 60000);
        var diffHour = Math.floor(diffMs / 3600000);
        var diffDay = Math.floor(diffMs / 86400000);
        if (diffMin < 1)
            return '刚刚';
        if (diffMin < 60)
            return "".concat(diffMin, "\u5206\u949F\u524D");
        if (diffHour < 24)
            return "".concat(diffHour, "\u5C0F\u65F6\u524D");
        if (diffDay < 7)
            return "".concat(diffDay, "\u5929\u524D");
        // 超过7天显示日期
        var date = new Date(timestamp);
        var y = date.getFullYear();
        var m = String(date.getMonth() + 1).padStart(2, '0');
        var d = String(date.getDate()).padStart(2, '0');
        return "".concat(y, "-").concat(m, "-").concat(d);
    }
    catch (_a) {
        return '';
    }
}
/** 根据当前时间生成问候语 */
function getGreetingText() {
    var hour = new Date().getHours();
    if (hour >= 5 && hour < 9)
        return '早上好';
    if (hour >= 9 && hour < 12)
        return '上午好';
    if (hour >= 12 && hour < 14)
        return '中午好';
    if (hour >= 14 && hour < 18)
        return '下午好';
    if (hour >= 18 && hour < 22)
        return '晚上好';
    return '夜深了';
}
Page({
    data: {
        loading: false,
        inited: false,
        isLoggedIn: false, // 是否已登录
        // 用户信息
        userName: '',
        userAvatar: '',
        greetingText: '你好',
        // 签到
        checkin: {
            checked_in_today: false,
            streak_days: 0,
            total_days: 0,
        },
        // 继续练习
        lastPractice: {
            has_practice: false,
            last_at: null,
            subject_id: null,
            subject_name: null,
            path: null,
            last_at_display: '',
            source_type: '',
            source_id: '',
            display_name: '',
            mode: '',
            has_local_session: false,
        },
        // 薄弱环节（最多2条）
        weakness: [],
        // 学习统计
        stats: {
            answered: 0,
            accuracy: 0,
            favorites: 0,
            mistakes: 0,
        },
        // 首页扩展内容
        studyAdvice: [],
        recentBanks: [],
        weaknessEmptyActions: [],
        campusSummary: (0, hub_content_1.buildCampusSummary)(null, false),
        // 主题
        isDarkMode: false,
        themeClass: '',
        themeStyle: 'default',
        themeStyleClass: '',
        themeMode: 'light',
        // 页面进入动画
        pageVisible: false,
        // 新用户资料设置弹窗
        showProfileSetupModal: false,
        setupStep: 'profile',
        setupAvatarTempPath: '',
        setupNickName: '',
        savingProfile: false,
        requiresNicknameSetup: false,
        needsPasswordSetup: false,
        // 昵称检查状态
        usernameStatus: '',
        usernameStatusText: '',
        usernameCheckTimer: null,
        // 密码设置
        setupPassword: '',
        setupPasswordConfirm: '',
        showPassword: false,
        savingPassword: false,
    },
    onLoad: function () {
        var _this = this;
        // 初始化主题
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        // 设置问候语
        this.setData({ greetingText: getGreetingText() });
        // 页面进入动画：延迟触发，防止白屏
        setTimeout(function () {
            _this.setData({ pageVisible: true });
        }, 50);
    },
    onShow: function () {
        var isLoggedIn = (0, auth_1.checkLogin)();
        this.setData({ isLoggedIn: isLoggedIn });
        // 更新主题
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        // 更新问候语（可能跨时段）
        this.setData({ greetingText: getGreetingText() });
        // 加载数据（无论是否登录都加载，但内容不同）
        this.loadAllData();
        // 检查是否为新用户，显示资料设置引导
        this.checkNewUserSetup();
    },
    loadAllData: function () {
        return __awaiter(this, void 0, void 0, function () {
            var isLoggedIn, _a, profile, checkinStatus, lastPractice, homeStats, campusStatus, nextAvatar, self, localSession, data, weaknessRows, e_1, errorMsg;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, 4, 5]);
                        isLoggedIn = this.data.isLoggedIn;
                        // 未登录时显示默认信息
                        if (!isLoggedIn) {
                            this.setData({
                                userName: '游客',
                                userAvatar: '',
                                checkin: { checked_in_today: false, streak_days: 0, total_days: 0 },
                                lastPractice: { has_practice: false, last_at: null, subject_id: null, subject_name: null, path: null, last_at_display: '' },
                                stats: { answered: 0, accuracy: 0, favorites: 0, mistakes: 0 },
                                weakness: [],
                                campusSummary: (0, hub_content_1.buildCampusSummary)(null, false),
                                inited: true,
                                loading: false,
                            });
                            this.refreshHubContent();
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getProfile().catch(function () { return null; }),
                                api_1.api.getCheckinStatus().catch(function () { return null; }),
                                api_1.api.getLastPractice().catch(function () { return null; }),
                                api_1.api.getDataCenter(30).catch(function () { return api_1.api.getHistoryStats(30).catch(function () { return null; }); }),
                                api_1.api.getEduScheduleStatus().catch(function (error) { return ({ error: error }); }),
                            ])];
                    case 2:
                        _a = _b.sent(), profile = _a[0], checkinStatus = _a[1], lastPractice = _a[2], homeStats = _a[3], campusStatus = _a[4];
                        // 用户信息
                        if (profile) {
                            nextAvatar = profile.avatar ? (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(profile.avatar)) : '';
                            self = this;
                            self.__userAvatarDlTried = false;
                            this.setData({
                                userName: profile.username || '用户',
                                userAvatar: nextAvatar,
                            });
                            this.maybePromptAccountSetup(profile);
                        }
                        // 签到状态
                        if (checkinStatus) {
                            this.setData({
                                checkin: {
                                    checked_in_today: checkinStatus.checked_in_today || false,
                                    streak_days: checkinStatus.streak_days || 0,
                                    total_days: checkinStatus.total_days || 0,
                                },
                            });
                        }
                        localSession = this.getLocalLastSession();
                        if (localSession && localSession.has_practice) {
                            // 本地有精确会话信息，优先使用
                            this.setData({
                                lastPractice: localSession,
                            });
                        }
                        else if (lastPractice && lastPractice.has_practice) {
                            // 兜底：使用服务端返回的数据
                            this.setData({
                                lastPractice: {
                                    has_practice: true,
                                    last_at: lastPractice.last_at,
                                    subject_id: lastPractice.subject_id,
                                    subject_name: lastPractice.subject_name,
                                    path: lastPractice.path,
                                    last_at_display: formatTimeAgo(lastPractice.last_at),
                                    has_local_session: false,
                                },
                            });
                        }
                        // 学习统计 + 薄弱环节
                        if (homeStats) {
                            data = homeStats;
                            this.setData({
                                stats: (0, hub_content_1.normalizeHubStats)(data),
                            });
                            weaknessRows = Array.isArray(data.weakness_rows) ? data.weakness_rows.slice(0, 2) : [];
                            this.setData({ weakness: weaknessRows });
                        }
                        this.setData({ campusSummary: (0, hub_content_1.buildCampusSummary)(campusStatus, true) });
                        this.setData({ inited: true });
                        this.refreshHubContent();
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _b.sent();
                        console.error('加载首页数据失败:', e_1);
                        errorMsg = (e_1 && e_1.message) || '';
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期') || errorMsg.includes('unauthorized')) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            this.setData({
                                isLoggedIn: false,
                                userName: '游客',
                                userAvatar: '',
                                campusSummary: (0, hub_content_1.buildCampusSummary)(null, false),
                            });
                            this.refreshHubContent();
                        }
                        else {
                            wx.showToast({ title: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '加载失败', icon: 'none' });
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    refreshHubContent: function () {
        var _a = this.data, stats = _a.stats, weakness = _a.weakness, lastPractice = _a.lastPractice, isLoggedIn = _a.isLoggedIn;
        this.rememberRecentBank(lastPractice);
        var storedRecentBanks = this.getStoredRecentBanks();
        this.setData({
            studyAdvice: (0, hub_content_1.buildStudyAdvice)(stats, weakness, lastPractice, isLoggedIn),
            recentBanks: (0, hub_content_1.buildRecentBanks)(lastPractice, storedRecentBanks),
            weaknessEmptyActions: (0, hub_content_1.buildWeaknessEmptyActions)(isLoggedIn, stats),
        });
    },
    getStoredRecentBanks: function () {
        try {
            var raw = wx.getStorageSync('hub_recent_banks_v1');
            if (Array.isArray(raw))
                return raw;
            if (typeof raw === 'string' && raw.trim()) {
                var parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed : [];
            }
            return [];
        }
        catch (e) {
            return [];
        }
    },
    rememberRecentBank: function (lastPractice) {
        if (!lastPractice || !lastPractice.has_practice)
            return;
        var sourceId = lastPractice.source_id || lastPractice.subject_id || '';
        var title = toSafeString(lastPractice.subject_name || lastPractice.display_name);
        if (!sourceId || !title)
            return;
        var sourceType = toSafeString(lastPractice.source_type, lastPractice.subject_id ? 'public' : '');
        var current = {
            key: "".concat(sourceType || 'practice', "-").concat(String(sourceId)),
            title: title,
            meta: toSafeString(lastPractice.last_at_display, '最近练习'),
            source_type: sourceType,
            source_id: sourceId,
            target: 'stored',
            mode: toSafeString(lastPractice.mode),
        };
        try {
            var existing = this.getStoredRecentBanks()
                .filter(function (row) { return row && typeof row === 'object'; })
                .map(function (row, index) {
                var item = row;
                return {
                    key: toSafeString(item.key, "stored-".concat(index)),
                    title: toSafeString(item.title || item.name || item.display_name || item.subject_name),
                    meta: toSafeString(item.meta || item.last_at_display || item.subtitle, '最近使用'),
                    source_type: toSafeString(item.source_type),
                    source_id: toSafeString(item.source_id || item.subject_id || item.bank_id),
                    target: toSafeString(item.target, 'stored'),
                    mode: toSafeString(item.mode),
                };
            })
                .filter(function (row) { return !!row.title && !!row.source_id; });
            var nextRows = [current]
                .concat(existing)
                .filter(function (row, index, rows) {
                if (!row)
                    return false;
                var key = "".concat(toSafeString(row.source_type, 'unknown'), ":").concat(toSafeString(row.source_id, row.title));
                return rows.findIndex(function (candidate) {
                    if (!candidate)
                        return false;
                    var candidateKey = "".concat(toSafeString(candidate.source_type, 'unknown'), ":").concat(toSafeString(candidate.source_id, candidate.title));
                    return candidateKey === key;
                }) === index;
            })
                .slice(0, 6);
            wx.setStorageSync('hub_recent_banks_v1', nextRows);
        }
        catch (e) { }
    },
    // 签到
    onCheckinTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var result, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        // 未登录时提示登录
                        if (!this.data.isLoggedIn) {
                            this.showLoginPrompt('登录后可签到');
                            return [2 /*return*/];
                        }
                        if (this.data.checkin.checked_in_today) {
                            wx.showToast({ title: '今日已签到', icon: 'none' });
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.doCheckin()];
                    case 2:
                        result = _a.sent();
                        this.setData({
                            checkin: {
                                checked_in_today: true,
                                streak_days: result.streak_days || 1,
                                total_days: result.total_days || 1,
                            },
                        });
                        if (result.just_checked_in) {
                            wx.showToast({ title: '签到成功', icon: 'success' });
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        wx.showToast({ title: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '签到失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 继续练习
    onContinuePractice: function () {
        // 未登录时提示登录
        if (!this.data.isLoggedIn) {
            this.showLoginPrompt('登录后可查看练习记录');
            return;
        }
        var lp = this.data.lastPractice;
        // 优先使用本地精确会话构建完整路径
        if (lp.has_local_session && lp.source_type && lp.source_id) {
            var params = [];
            if (lp.source_type === 'bank') {
                params.push("bank_id=".concat(lp.source_id));
            }
            else {
                params.push("subject=".concat(lp.source_id));
            }
            if (lp.mode)
                params.push("mode=".concat(lp.mode));
            var path = "/pages/quiz/quiz?".concat(params.join('&'));
            (0, nav_1.safeNavigate)(path, 'redirectTo');
            return;
        }
        // 兜底：使用服务端返回的 path
        if (lp.path) {
            (0, nav_1.safeNavigate)(lp.path, 'redirectTo');
        }
        else {
            (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
        }
    },
    // 显示登录提示
    showLoginPrompt: function (message) {
        wx.showModal({
            title: '提示',
            content: message,
            confirmText: '去登录',
            cancelText: '取消',
            success: function (res) {
                if (res.confirm) {
                    wx.navigateTo({ url: '/pages/login/login' });
                }
            }
        });
    },
    // 跳转登录页
    onGoLoginTap: function () {
        wx.navigateTo({ url: '/pages/login/login' });
    },
    onAdviceTap: function (e) {
        var _a, _b;
        var target = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.target) || '');
        this.routeHubTarget(target);
    },
    onRecentBankTap: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var target = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.target) || '');
        if (target === 'continue') {
            this.onContinuePractice();
            return;
        }
        var sourceType = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.sourceType) || '');
        var sourceId = (_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.sourceId;
        if (sourceType === 'bank' && sourceId) {
            (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?bank_id=".concat(encodeURIComponent(String(sourceId))), 'navigateTo');
            return;
        }
        if (sourceType === 'public' && sourceId) {
            (0, nav_1.safeNavigate)("/pages/subject-detail-v2/subject-detail-v2?subject=".concat(encodeURIComponent(String(sourceId))), 'navigateTo');
            return;
        }
        this.onGoPublicBank();
    },
    onWeaknessEmptyActionTap: function (e) {
        var _a, _b;
        var target = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.target) || '');
        this.routeHubTarget(target);
    },
    routeHubTarget: function (target) {
        switch (target) {
            case 'login':
                this.onGoLoginTap();
                break;
            case 'continue':
                this.onContinuePractice();
                break;
            case 'weakness':
                this.onGoHistory();
                break;
            case 'review':
                this.onGoReview();
                break;
            case 'favorites':
                this.onGoFavorites();
                break;
            case 'publicBank':
                this.onGoPublicBank();
                break;
            default:
                this.onGoPublicBank();
                break;
        }
    },
    refreshCampusSummary: function () {
        return __awaiter(this, void 0, void 0, function () {
            var data, error_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.data.isLoggedIn) {
                            this.setData({ campusSummary: (0, hub_content_1.buildCampusSummary)(null, false) });
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getEduScheduleStatus()];
                    case 2:
                        data = _a.sent();
                        this.setData({ campusSummary: (0, hub_content_1.buildCampusSummary)(data, true) });
                        wx.showToast({ title: '校园状态已同步', icon: 'success' });
                        return [3 /*break*/, 4];
                    case 3:
                        error_1 = _a.sent();
                        this.setData({ campusSummary: (0, hub_content_1.buildCampusSummary)({ error: error_1 }, true) });
                        wx.showToast({ title: '同步失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    openCampus: function (mode) {
        if (mode === 'schedule') {
            (0, nav_1.safeNavigate)('/pages/campus-schedule/campus-schedule', 'navigateTo');
            return;
        }
        if (mode === 'grades') {
            (0, nav_1.safeNavigate)('/pages/campus-grades/campus-grades', 'navigateTo');
            return;
        }
        (0, nav_1.safeNavigate)('/pages/campus/campus', 'switchTab');
    },
    onGoCampus: function () {
        this.openCampus();
    },
    onCampusPrimaryAction: function () {
        var summary = this.data.campusSummary;
        if (!this.data.isLoggedIn) {
            this.onGoLoginTap();
            return;
        }
        if (summary.statusLabel === '待绑定') {
            (0, nav_1.safeNavigate)('/pages/settings-account-bindings-v2/settings-account-bindings-v2', 'navigateTo');
            return;
        }
        this.openCampus(summary.statusLabel === '已绑定' ? 'schedule' : undefined);
    },
    onCampusSecondaryAction: function () {
        var summary = this.data.campusSummary;
        if (!this.data.isLoggedIn) {
            this.openCampus();
            return;
        }
        if (summary.statusLabel === '同步失败') {
            this.refreshCampusSummary();
            return;
        }
        this.openCampus(summary.statusLabel === '已绑定' ? 'grades' : undefined);
    },
    // 获取本地保存的上次练习会话
    getLocalLastSession: function () {
        try {
            var raw = wx.getStorageSync('last_practice_session');
            if (!raw || typeof raw !== 'object')
                return null;
            var session = raw;
            var sourceType = toSafeString(session.source_type);
            var sourceId = session.source_id || session.subject || session.bank_id;
            if (!sourceType || !sourceId)
                return null;
            // 计算时间显示（直接用时间戳计算，避免时区问题）
            var timestamp = toSafeNumber(session.timestamp);
            var lastAtDisplay = '';
            if (timestamp) {
                lastAtDisplay = formatTimeAgoFromTimestamp(timestamp);
            }
            // 直接使用保存的显示名称，无名称时使用默认
            var subjectName = toSafeString(session.display_name, sourceType === 'bank' ? '个人题库' : '公共题库');
            var normalizedSourceType = sourceType === 'bank' || sourceType === 'public' ? sourceType : '';
            return {
                has_practice: true,
                last_at: timestamp ? new Date(timestamp).toISOString() : null,
                subject_id: sourceType === 'public' ? Number(sourceId) : null,
                subject_name: subjectName,
                path: null, // 由 onContinuePractice 动态构建
                last_at_display: lastAtDisplay,
                source_type: normalizedSourceType,
                source_id: sourceId,
                display_name: subjectName,
                mode: toSafeString(session.mode),
                has_local_session: true,
            };
        }
        catch (e) {
            return null;
        }
    },
    // 薄弱环节点击
    onWeaknessItemTap: function (e) {
        var item = e.currentTarget.dataset.item;
        if (!item)
            return;
        // 跳转到对应科目的练习页
        (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
    },
    // 主题切换
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    // 快捷入口
    onGoPublicBank: function () {
        (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
    },
    onGoMyBanks: function () {
        (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
    },
    onGoFavorites: function () {
        (0, nav_1.safeNavigate)('/pages/favorites-v2/favorites-v2', 'redirectTo');
    },
    onGoHistory: function () {
        (0, nav_1.safeNavigate)('/packages/data/pages/data-center-v2/data-center-v2', 'redirectTo');
    },
    onGoReview: function () {
        (0, nav_1.safeNavigate)('/pages/review-hub-v3/review-hub-v3', 'redirectTo');
    },
    onGoExamCenter: function () {
        (0, nav_1.safeNavigate)('/pages/exams-select-v2/exams-select-v2', 'redirectTo');
    },
    onAboutTap: function () {
        (0, nav_1.safeNavigate)('/pages/settings-about-v2/settings-about-v2', 'redirectTo');
    },
    // 头像点击 - 跳转个人资料
    onAvatarTap: function () {
        (0, nav_1.safeNavigate)('/pages/profile-view-v2/profile-view-v2', 'navigateTo');
    },
    onUserAvatarError: function () {
        var _this = this;
        var url = String(this.data.userAvatar || '').trim();
        if (!url || !/^https?:\/\//i.test(url)) {
            this.setData({ userAvatar: '' });
            return;
        }
        var self = this;
        if (self.__userAvatarDlTried) {
            this.setData({ userAvatar: '' });
            return;
        }
        self.__userAvatarDlTried = true;
        wx.downloadFile({
            url: url,
            timeout: 15000,
            success: function (res) {
                var tempFilePath = String((res && res.tempFilePath) || '').trim();
                _this.setData({ userAvatar: tempFilePath || '' });
            },
            fail: function () {
                _this.setData({ userAvatar: '' });
            }
        });
    },
    // 通知
    onGoNotifications: function () {
        (0, nav_1.safeNavigate)('/pages/notifications-v2/notifications-v2', 'navigateTo');
    },
    // 设置
    onGoSettings: function () {
        (0, nav_1.safeNavigate)('/pages/settings-account-profile-v2/settings-account-profile-v2', 'redirectTo');
    },
    // 检查是否为新用户，显示资料设置引导
    checkNewUserSetup: function () {
        var _this = this;
        var isNewUser = wx.getStorageSync('isNewUser');
        if (isNewUser && this.data.isLoggedIn) {
            // 延迟显示弹窗，等页面加载完成
            setTimeout(function () {
                if (!_this.data.isLoggedIn || _this.data.showProfileSetupModal)
                    return;
                var setupNickName = isValidSetupNickname(normalizeSetupNickname(_this.data.setupNickName))
                    ? normalizeSetupNickname(_this.data.setupNickName)
                    : createRandomNickname();
                _this.setData({
                    showProfileSetupModal: true,
                    setupStep: 'profile',
                    setupNickName: setupNickName,
                    requiresNicknameSetup: true,
                    needsPasswordSetup: true,
                    usernameStatus: '',
                    usernameStatusText: '',
                });
            }, 500);
        }
    },
    // 登录后自动检测：历史微信昵称需先设置昵称；未设置密码则进入密码步骤
    maybePromptAccountSetup: function (profile) {
        if (!this.data.isLoggedIn || !profile)
            return;
        var needsNicknameSetup = !!profile.needs_nickname_setup;
        var needsPasswordSetup = !profile.has_password_set;
        if (this.data.showProfileSetupModal) {
            this.setData({ needsPasswordSetup: needsPasswordSetup });
            return;
        }
        if (!needsNicknameSetup && !needsPasswordSetup)
            return;
        var nextData = {
            showProfileSetupModal: true,
            setupStep: needsNicknameSetup ? 'profile' : 'password',
            requiresNicknameSetup: needsNicknameSetup,
            needsPasswordSetup: needsPasswordSetup,
            setupPassword: '',
            setupPasswordConfirm: '',
        };
        if (needsNicknameSetup) {
            nextData.setupNickName = createRandomNickname();
            nextData.usernameStatus = '';
            nextData.usernameStatusText = '';
        }
        this.setData(__assign({}, nextData));
    },
    // 选择头像回调
    onSetupChooseAvatar: function (e) {
        var _a;
        var avatarUrl = ((_a = e.detail) === null || _a === void 0 ? void 0 : _a.avatarUrl) || '';
        if (avatarUrl) {
            this.setData({ setupAvatarTempPath: avatarUrl });
        }
    },
    // 昵称实时输入回调（用于防抖检查）
    onSetupNickNameInput: function (e) {
        var _this = this;
        var _a;
        var nickName = normalizeSetupNickname((_a = e.detail) === null || _a === void 0 ? void 0 : _a.value);
        this.setData({ setupNickName: nickName });
        // 清除之前的定时器
        if (this.data.usernameCheckTimer) {
            clearTimeout(this.data.usernameCheckTimer);
        }
        if (!nickName) {
            this.setData({ usernameStatus: '', usernameStatusText: '' });
            return;
        }
        if (!isValidSetupNickname(nickName)) {
            this.setData({ usernameStatus: 'error', usernameStatusText: SETUP_NICKNAME_ERROR });
            return;
        }
        // 防抖检查用户名
        this.setData({ usernameStatus: 'checking', usernameStatusText: '检查中...' });
        var timer = setTimeout(function () {
            _this.checkUsernameAvailable(nickName);
        }, 500);
        this.setData({ usernameCheckTimer: timer });
    },
    // 昵称输入完成回调
    onSetupNickNameChange: function (e) {
        var _a;
        var nickName = normalizeSetupNickname((_a = e.detail) === null || _a === void 0 ? void 0 : _a.value);
        this.setData({ setupNickName: nickName });
        if (nickName && isValidSetupNickname(nickName)) {
            this.checkUsernameAvailable(nickName);
        }
    },
    onRefreshSetupNickname: function () {
        if (this.data.savingProfile)
            return;
        var setupNickName = createRandomNickname();
        this.setData({
            setupNickName: setupNickName,
            usernameStatus: '',
            usernameStatusText: '',
        });
        this.checkUsernameAvailable(setupNickName);
    },
    validateSetupNickname: function (username) {
        if (!username) {
            this.setData({ usernameStatus: 'error', usernameStatusText: SETUP_NICKNAME_ERROR });
            return false;
        }
        if (!isValidSetupNickname(username)) {
            this.setData({ usernameStatus: 'error', usernameStatusText: SETUP_NICKNAME_ERROR });
            return false;
        }
        return true;
    },
    // 检查用户名是否可用
    checkUsernameAvailable: function (username) {
        return __awaiter(this, void 0, void 0, function () {
            var res, err_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.validateSetupNickname(username))
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.checkUsername(username, true)];
                    case 2:
                        res = _a.sent();
                        if (normalizeSetupNickname(this.data.setupNickName) !== username)
                            return [2 /*return*/];
                        if (res.available) {
                            this.setData({ usernameStatus: 'ok', usernameStatusText: '可以使用' });
                        }
                        else {
                            this.setData({ usernameStatus: 'error', usernameStatusText: res.message || '已被使用' });
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        this.setData({ usernameStatus: 'error', usernameStatusText: (err_1 === null || err_1 === void 0 ? void 0 : err_1.message) || '检查失败' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 关闭资料设置弹窗
    onCloseProfileSetupModal: function () {
        if (this.data.requiresNicknameSetup) {
            wx.showToast({ title: '请先设置昵称', icon: 'none' });
            return;
        }
        this.setData({ showProfileSetupModal: false });
        wx.removeStorageSync('isNewUser');
    },
    // 阻止事件冒泡
    preventBubble: function () {
        // 空函数
    },
    // 跳过资料设置
    onSkipProfileSetup: function () {
        if (this.data.requiresNicknameSetup) {
            wx.showToast({ title: '请先设置昵称', icon: 'none' });
            return;
        }
        this.setData({ showProfileSetupModal: false });
        wx.removeStorageSync('isNewUser');
        wx.showToast({ title: '可在设置中修改', icon: 'none' });
    },
    // 保存资料设置
    onSaveProfileSetup: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, setupAvatarTempPath, usernameStatus, requiresNicknameSetup, needsPasswordSetup, setupNickName, uploadRes, cachedUserInfo, uploadErr_1, cachedUserInfo, nicknameErr_1, e_3;
            var _this = this;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.savingProfile)
                            return [2 /*return*/];
                        _a = this.data, setupAvatarTempPath = _a.setupAvatarTempPath, usernameStatus = _a.usernameStatus, requiresNicknameSetup = _a.requiresNicknameSetup, needsPasswordSetup = _a.needsPasswordSetup;
                        setupNickName = normalizeSetupNickname(this.data.setupNickName);
                        if (requiresNicknameSetup && !this.validateSetupNickname(setupNickName)) {
                            wx.showToast({ title: SETUP_NICKNAME_ERROR, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (!requiresNicknameSetup && !setupAvatarTempPath && !setupNickName) {
                            wx.showToast({ title: '请选择头像或输入昵称', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (setupNickName && !this.validateSetupNickname(setupNickName)) {
                            wx.showToast({ title: SETUP_NICKNAME_ERROR, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (setupNickName && usernameStatus === 'checking') {
                            wx.showToast({ title: '昵称检查中，请稍候', icon: 'none' });
                            return [2 /*return*/];
                        }
                        // 如果有昵称但检查未通过
                        if (setupNickName && usernameStatus === 'error') {
                            wx.showToast({ title: '请修改昵称后再保存', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ savingProfile: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 10, , 11]);
                        if (!setupAvatarTempPath) return [3 /*break*/, 5];
                        _b.label = 2;
                    case 2:
                        _b.trys.push([2, 4, , 5]);
                        return [4 /*yield*/, api_1.api.uploadProfileAvatar(setupAvatarTempPath)];
                    case 3:
                        uploadRes = _b.sent();
                        if (uploadRes && uploadRes.avatar_url) {
                            this.setData({ userAvatar: (0, api_1.resolveUploadUrl)(uploadRes.avatar_url) });
                            cachedUserInfo = wx.getStorageSync('userInfo') || {};
                            wx.setStorageSync('userInfo', __assign(__assign({}, cachedUserInfo), { avatar: uploadRes.avatar_url }));
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        uploadErr_1 = _b.sent();
                        console.warn('头像上传失败:', (uploadErr_1 === null || uploadErr_1 === void 0 ? void 0 : uploadErr_1.message) || uploadErr_1);
                        return [3 /*break*/, 5];
                    case 5:
                        if (!setupNickName) return [3 /*break*/, 9];
                        _b.label = 6;
                    case 6:
                        _b.trys.push([6, 8, , 9]);
                        return [4 /*yield*/, api_1.api.updateProfile({ username: setupNickName, strict_nickname: true })];
                    case 7:
                        _b.sent();
                        this.setData({ userName: setupNickName });
                        cachedUserInfo = wx.getStorageSync('userInfo') || {};
                        wx.setStorageSync('userInfo', __assign(__assign({}, cachedUserInfo), { username: setupNickName, needs_nickname_setup: false }));
                        return [3 /*break*/, 9];
                    case 8:
                        nicknameErr_1 = _b.sent();
                        wx.showToast({ title: (nicknameErr_1 === null || nicknameErr_1 === void 0 ? void 0 : nicknameErr_1.message) || '昵称设置失败', icon: 'none' });
                        this.setData({ savingProfile: false });
                        return [2 /*return*/];
                    case 9:
                        wx.showToast({ title: '资料已保存', icon: 'success' });
                        setTimeout(function () {
                            if (needsPasswordSetup) {
                                _this.setData({
                                    setupStep: 'password',
                                    savingProfile: false,
                                    requiresNicknameSetup: false,
                                });
                                return;
                            }
                            _this.setData({
                                showProfileSetupModal: false,
                                setupStep: 'profile',
                                savingProfile: false,
                                requiresNicknameSetup: false,
                                needsPasswordSetup: false,
                                usernameStatus: '',
                                usernameStatusText: '',
                            });
                            wx.removeStorageSync('isNewUser');
                        }, 500);
                        return [3 /*break*/, 11];
                    case 10:
                        e_3 = _b.sent();
                        wx.showToast({ title: (e_3 === null || e_3 === void 0 ? void 0 : e_3.message) || '保存失败', icon: 'none' });
                        this.setData({ savingProfile: false });
                        return [3 /*break*/, 11];
                    case 11: return [2 /*return*/];
                }
            });
        });
    },
    // 密码输入
    onSetupPasswordInput: function (e) {
        var _a;
        this.setData({ setupPassword: ((_a = e.detail) === null || _a === void 0 ? void 0 : _a.value) || '' });
    },
    // 确认密码输入
    onSetupPasswordConfirmInput: function (e) {
        var _a;
        this.setData({ setupPasswordConfirm: ((_a = e.detail) === null || _a === void 0 ? void 0 : _a.value) || '' });
    },
    // 切换密码显示
    onToggleShowPassword: function () {
        this.setData({ showPassword: !this.data.showPassword });
    },
    // 跳过密码设置
    onSkipPasswordSetup: function () {
        this.setData({ showProfileSetupModal: false });
        wx.removeStorageSync('isNewUser');
        wx.showToast({ title: '可在设置中设置密码', icon: 'none' });
    },
    // 保存密码设置
    onSavePasswordSetup: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, setupPassword, setupPasswordConfirm, hasLetter, hasDigit, cachedUserInfo, e_4;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.savingPassword)
                            return [2 /*return*/];
                        _a = this.data, setupPassword = _a.setupPassword, setupPasswordConfirm = _a.setupPasswordConfirm;
                        if (!setupPassword) {
                            wx.showToast({ title: '请输入密码', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (setupPassword.length < 8) {
                            wx.showToast({ title: '密码至少8位', icon: 'none' });
                            return [2 /*return*/];
                        }
                        hasLetter = /[a-zA-Z]/.test(setupPassword);
                        hasDigit = /\d/.test(setupPassword);
                        if (!hasLetter || !hasDigit) {
                            wx.showToast({ title: '密码必须包含字母和数字', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (setupPassword !== setupPasswordConfirm) {
                            wx.showToast({ title: '两次密码不一致', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ savingPassword: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.updateProfilePassword({
                                new_password: setupPassword,
                                is_set_password: true
                            })];
                    case 2:
                        _b.sent();
                        wx.showToast({ title: '密码设置成功', icon: 'success' });
                        cachedUserInfo = wx.getStorageSync('userInfo') || {};
                        wx.setStorageSync('userInfo', __assign(__assign({}, cachedUserInfo), { has_password_set: true }));
                        this.setData({
                            showProfileSetupModal: false,
                            setupStep: 'profile',
                            needsPasswordSetup: false,
                            setupPassword: '',
                            setupPasswordConfirm: '',
                            showPassword: false
                        });
                        wx.removeStorageSync('isNewUser');
                        return [3 /*break*/, 5];
                    case 3:
                        e_4 = _b.sent();
                        wx.showToast({ title: (e_4 === null || e_4 === void 0 ? void 0 : e_4.message) || '设置失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ savingPassword: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
});
