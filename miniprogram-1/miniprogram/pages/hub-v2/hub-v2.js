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
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
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
var user_settings_1 = require("../../utils/user-settings");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
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
            return "".concat(diffMin, "分钟前");
        if (diffHour < 24)
            return "".concat(diffHour, "小时前");
        if (diffDay < 7)
            return "".concat(diffDay, "天前");
        return dateStr.slice(0, 10);
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
        drawerOpen: false,
        loading: false,
        inited: false,
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
        // 主题
        isDarkMode: false,
        themeClass: '',
        themeStyle: 'default',
        themeStyleClass: '',
        themeMode: 'light',
        // 页面进入动画
        pageVisible: false,
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
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        // 隐藏tabBar
        try {
            wx.hideTabBar({ animation: false });
        }
        catch (e) { }
        // 更新主题
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        // 更新问候语（可能跨时段）
        this.setData({ greetingText: getGreetingText() });
        // 加载数据
        this.loadAllData();
    },
    onHide: function () {
        try {
            wx.showTabBar({ animation: false });
        }
        catch (e) { }
    },
    onUnload: function () {
        try {
            wx.showTabBar({ animation: false });
        }
        catch (e) { }
    },
    loadAllData: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, profile, checkinStatus, lastPractice, historyStats, data, weaknessRows, e_1;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getProfile().catch(function () { return null; }),
                                api_1.api.getCheckinStatus().catch(function () { return null; }),
                                api_1.api.getLastPractice().catch(function () { return null; }),
                                api_1.api.getHistoryStats(30).catch(function () { return null; }),
                            ])];
                    case 2:
                        _a = _b.sent(), profile = _a[0], checkinStatus = _a[1], lastPractice = _a[2], historyStats = _a[3];
                        // 用户信息
                        if (profile) {
                            this.setData({
                                userName: profile.username || '用户',
                                userAvatar: profile.avatar ? (0, api_1.resolveUploadUrl)(profile.avatar) : '',
                            });
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
                        // 继续练习
                        if (lastPractice && lastPractice.has_practice) {
                            this.setData({
                                lastPractice: {
                                    has_practice: true,
                                    last_at: lastPractice.last_at,
                                    subject_id: lastPractice.subject_id,
                                    subject_name: lastPractice.subject_name,
                                    path: lastPractice.path,
                                    last_at_display: formatTimeAgo(lastPractice.last_at),
                                },
                            });
                        }
                        // 学习统计 + 薄弱环节
                        if (historyStats) {
                            data = historyStats;
                            this.setData({
                                stats: {
                                    answered: data.answered_count || 0,
                                    accuracy: data.accuracy || 0,
                                    favorites: data.favorites_count || 0,
                                    mistakes: data.mistakes_count || 0,
                                },
                            });
                            weaknessRows = (data.weakness_rows || []).slice(0, 2);
                            this.setData({ weakness: weaknessRows });
                        }
                        this.setData({ inited: true });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _b.sent();
                        console.error('加载首页数据失败:', e_1);
                        wx.showToast({ title: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    // 签到
    onCheckinTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var result, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
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
        var path = this.data.lastPractice.path;
        if (path) {
            (0, nav_1.safeNavigate)(path, 'redirectTo');
        }
        else {
            (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
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
    // 侧边栏
    onHamburgerTap: function () {
        this.setData({ drawerOpen: true });
    },
    onDrawerClose: function () {
        this.setData({ drawerOpen: false });
    },
    onDrawerNavigate: function (e) {
        var _a, _b;
        var url = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.url;
        var navType = (_b = e === null || e === void 0 ? void 0 : e.detail) === null || _b === void 0 ? void 0 : _b.navType;
        this.setData({ drawerOpen: false });
        if (!url)
            return;
        (0, nav_1.safeNavigate)(url, navType);
    },
    onDrawerSelectStyle: function (e) {
        var _a;
        return __awaiter(this, void 0, void 0, function () {
            var style;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        style = (((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        this.setData({ drawerOpen: false });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    // 主题切换
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
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
        (0, nav_1.safeNavigate)('/pages/settings-center-v2/settings-center-v2?navKey=about', 'redirectTo');
    },
    // 头像点击 - 跳转个人资料
    onAvatarTap: function () {
        (0, nav_1.safeNavigate)('/pages/profile-view-v2/profile-view-v2', 'navigateTo');
    },
    // 通知
    onGoNotifications: function () {
        (0, nav_1.safeNavigate)('/pages/notifications-v2/notifications-v2', 'navigateTo');
    },
    // 设置
    onGoSettings: function () {
        (0, nav_1.safeNavigate)('/pages/settings-center-v2/settings-center-v2', 'redirectTo');
    },
});
