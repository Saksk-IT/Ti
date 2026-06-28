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
// mine.ts - 我的
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var avatar_1 = require("../../utils/avatar");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var font_1 = require("../../utils/font");
function toSafeNumber(value) {
    var num = Number(value || 0);
    return Number.isFinite(num) ? num : 0;
}
function canShowAdmin(userInfo) {
    return !!((userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_admin) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_subject_admin) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_notification_admin));
}
Page({
    data: {
        userInfo: null,
        canShowAdmin: false,
        stats: {
            favorites: 0,
            mistakes: 0
        },
        loading: false
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var userInfo = wx.getStorageSync('userInfo');
        try {
            this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), font_1.fontManager.getPageData()));
        }
        catch (e) { }
        // 将相对路径的 avatar 转为完整 URL
        if (userInfo && (userInfo.avatar || userInfo.avatar_url)) {
            var rawAvatar = userInfo.avatar || userInfo.avatar_url;
            var fullUrl = (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(rawAvatar));
            userInfo.avatar = fullUrl;
            userInfo.avatar_url = fullUrl;
        }
        this.setData({ userInfo: userInfo, canShowAdmin: canShowAdmin(userInfo) });
        this.loadStats();
    },
    loadStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var data, summary, err_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getDataCenter(30)];
                    case 2:
                        data = _a.sent();
                        summary = data && typeof data === 'object' && data.all_summary
                            ? data.all_summary
                            : {};
                        this.setData({
                            stats: {
                                favorites: toSafeNumber(summary.favorites),
                                mistakes: toSafeNumber(summary.mistakes)
                            },
                            loading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载用户统计失败:', err_1);
                        wx.showToast({ title: (err_1 && err_1.message) || '加载失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onGoFavoritesTap: function () {
        (0, nav_1.safeNavigate)('/pages/favorites-v2/favorites-v2', 'navigateTo');
    },
    onGoMistakesTap: function () {
        (0, nav_1.safeNavigate)('/pages/mistakes-v2/mistakes-v2', 'navigateTo');
    },
    onGoProfileTap: function () {
        (0, nav_1.safeNavigate)('/pages/profile-view-v2/profile-view-v2', 'navigateTo');
    },
    onGoAccountTap: function () {
        (0, nav_1.safeNavigate)('/pages/settings-account-security-v2/settings-account-security-v2', 'navigateTo');
    },
    onGoReviewTap: function () {
        (0, nav_1.safeNavigate)('/pages/review-hub-v3/review-hub-v3', 'navigateTo');
    },
    onGoDataTap: function () {
        (0, nav_1.safeNavigate)('/packages/data/pages/data-center-v2/data-center-v2', 'navigateTo');
    },
    onGoExamTap: function () {
        (0, nav_1.safeNavigate)('/pages/exams-select-v2/exams-select-v2', 'navigateTo');
    },
    onGoCodingTap: function () {
        (0, nav_1.safeNavigate)('/pages/coding-v2/coding-v2', 'navigateTo');
    },
    onGoNotificationsTap: function () {
        (0, nav_1.safeNavigate)('/pages/notifications-v2/notifications-v2', 'navigateTo');
    },
    onGoThemeTap: function () {
        (0, nav_1.safeNavigate)('/pages/settings-theme-v2/settings-theme-v2', 'navigateTo');
    },
    onGoAdminTap: function () {
        if (!this.data.canShowAdmin)
            return;
        (0, nav_1.safeNavigate)('/pages/admin-v2/admin-v2', 'navigateTo');
    },
    onLogoutTap: function () {
        wx.showModal({
            title: '退出登录',
            content: '确定要退出登录吗？',
            confirmText: '退出',
            confirmColor: '#FF3B30',
            success: function (res) {
                if (!res.confirm)
                    return;
                (0, auth_1.logout)();
                wx.reLaunch({ url: '/pages/login/login' });
            }
        });
    }
});
