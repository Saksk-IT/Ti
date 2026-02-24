"use strict";
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
var auth_1 = require("../../utils/auth");
var theme_1 = require("../../utils/theme");
var font_1 = require("../../utils/font");
var user_settings_1 = require("../../utils/user-settings");
var api_endpoints_1 = require("../../utils/api-endpoints");
var avatar_1 = require("../../utils/avatar");
function summarizeUserName(userInfo) {
    var raw = (userInfo === null || userInfo === void 0 ? void 0 : userInfo.username) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.name) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.nickname) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.email);
    var name = (raw == null) ? '' : String(raw).trim();
    return name || '未登录';
}
function summarizeUserAvatar(userInfo) {
    var raw = (userInfo === null || userInfo === void 0 ? void 0 : userInfo.avatar) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.avatar_url) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.avatarUrl);
    var full = (0, avatar_1.decorateAvatarUrl)((0, api_endpoints_1.resolveUploadUrl)(raw));
    return full || '/images/default-avatar.png';
}
function resolveCanShowAdmin(userInfo) {
    return !!((userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_admin) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_subject_admin) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_notification_admin));
}
Component({
    properties: {
        open: {
            type: Boolean,
            value: false,
            observer: function (v) {
                if (v) {
                    this.refreshUnreadCount(false);
                    this.refreshUserName();
                    this.refreshThemeData();
                    return;
                }
                this.closeQuickMenus();
            }
        },
        themeStyle: { type: String, value: 'default' },
        activeKey: { type: String, value: '' }
    },
    data: {
        searchKeyword: '',
        unreadNotiCount: 0,
        unreadNotiText: '',
        userName: '未登录',
        userAvatar: '/images/default-avatar.png',
        canShowAdmin: false,
        actionMenuOpen: false,
        themeMenuOpen: false,
        fontMenuOpen: false,
        themeMode: 'system',
        fontStyle: 'modern',
        isDarkMode: false,
        themeClass: 'theme-light',
        themeStyleClass: ''
    },
    lifetimes: {
        attached: function () {
            var _this = this;
            this.refreshUserName();
            this.refreshThemeData();
            try {
                var off = theme_1.themeManager.onThemeChange(function () {
                    _this.refreshThemeData();
                });
                this.__offThemeChange = off;
            }
            catch (e) { }
        },
        detached: function () {
            try {
                if (typeof this.__offThemeChange === 'function')
                    this.__offThemeChange();
            }
            catch (e) { }
            this.__offThemeChange = null;
        }
    },
    methods: {
        onClose: function () {
            this.closeQuickMenus();
            this.triggerEvent('close');
        },
        stopTap: function () { },
        closeQuickMenus: function () {
            if (!this.data.actionMenuOpen && !this.data.themeMenuOpen && !this.data.fontMenuOpen)
                return;
            this.setData({ actionMenuOpen: false, themeMenuOpen: false, fontMenuOpen: false });
        },
        refreshThemeData: function () {
            try {
                var p = theme_1.themeManager.getPageData();
                var f = font_1.fontManager.getPageData();
                this.setData({
                    themeMode: (p === null || p === void 0 ? void 0 : p.themeMode) || theme_1.themeManager.getMode(),
                    fontStyle: (f === null || f === void 0 ? void 0 : f.fontStyle) || font_1.fontManager.getStyle(),
                    isDarkMode: !!(p === null || p === void 0 ? void 0 : p.isDarkMode),
                    themeClass: String((p === null || p === void 0 ? void 0 : p.themeClass) || ''),
                    themeStyleClass: String((p === null || p === void 0 ? void 0 : p.themeStyleClass) || '')
                });
            }
            catch (e) { }
        },
        refreshUserName: function () {
            try {
                var userInfo = wx.getStorageSync('userInfo') || {};
                this.setData({
                    userName: summarizeUserName(userInfo),
                    userAvatar: summarizeUserAvatar(userInfo),
                    canShowAdmin: resolveCanShowAdmin(userInfo)
                });
            }
            catch (e) {
                this.setData({
                    userName: '未登录',
                    userAvatar: '/images/default-avatar.png',
                    canShowAdmin: false
                });
            }
        },
        onProfileAvatarError: function () {
            this.setData({ userAvatar: '/images/default-avatar.png' });
        },
        refreshUnreadCount: function () {
            return __awaiter(this, arguments, void 0, function (force) {
                var token, self, now, lastAt, res, count, text, e_1;
                if (force === void 0) { force = false; }
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            token = wx.getStorageSync('token') || '';
                            if (!token) {
                                this.setData({ unreadNotiCount: 0, unreadNotiText: '' });
                                return [2 /*return*/];
                            }
                            self = this;
                            now = Date.now();
                            lastAt = Number(self.__unreadFetchedAt || 0) || 0;
                            if (!force && now - lastAt < 15000)
                                return [2 /*return*/];
                            self.__unreadFetchedAt = now;
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.getUnreadNotificationCount()];
                        case 2:
                            res = _a.sent();
                            count = Number((res === null || res === void 0 ? void 0 : res.count) || 0) || 0;
                            text = count > 99 ? '99+' : String(count);
                            this.setData({ unreadNotiCount: count, unreadNotiText: count > 0 ? text : '' });
                            return [3 /*break*/, 4];
                        case 3:
                            e_1 = _a.sent();
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            });
        },
        onNavTap: function (e) {
            var _a, _b, _c, _d;
            var url = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.url;
            var navType = (_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.navType;
            this.triggerEvent('navigate', { url: url, navType: navType });
        },
        onMoreTap: function () {
            var opened = !!this.data.actionMenuOpen;
            this.setData({ actionMenuOpen: !opened, themeMenuOpen: false, fontMenuOpen: false });
            if (!opened)
                this.refreshThemeData();
        },
        onQuickMenuMaskTap: function () {
            this.closeQuickMenus();
        },
        onQuickNavTap: function (e) {
            var _a, _b, _c, _d;
            var url = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.url;
            var navType = (_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.navType;
            this.closeQuickMenus();
            this.triggerEvent('navigate', { url: url, navType: navType });
        },
        onOpenThemeMenu: function () {
            this.setData({ actionMenuOpen: false, themeMenuOpen: true, fontMenuOpen: false });
            this.refreshThemeData();
        },
        onOpenFontMenu: function () {
            this.setData({ actionMenuOpen: false, themeMenuOpen: false, fontMenuOpen: true });
            this.refreshThemeData();
        },
        onBackToQuickMenu: function () {
            this.setData({ actionMenuOpen: true, themeMenuOpen: false, fontMenuOpen: false });
        },
        onThemeModeTap: function (e) {
            var _a, _b, _c, _d;
            var mode = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.mode) || 'system');
            if (mode !== 'light' && mode !== 'dark' && mode !== 'system')
                return;
            theme_1.themeManager.setMode(mode);
            this.setData({ themeMode: theme_1.themeManager.getMode() });
            this.closeQuickMenus();
        },
        onThemeStyleTap: function (e) {
            return __awaiter(this, void 0, void 0, function () {
                var _a, _b, _c, _d, style;
                return __generator(this, function (_e) {
                    switch (_e.label) {
                        case 0:
                            style = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.style) || 'default');
                            theme_1.themeManager.setStyle(style);
                            this.closeQuickMenus();
                            return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                        case 1:
                            _e.sent();
                            return [2 /*return*/];
                    }
                });
            });
        },
        onFontStyleTap: function (e) {
            var _this = this;
            return __awaiter(this, void 0, void 0, function () {
                var style;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            style = String((e === null || e === void 0 ? void 0 : e.currentTarget.dataset.style) || 'system');
                            return [4 /*yield*/, font_1.fontManager.setStyle(style)];
                        case 1:
                            _a.sent();
                            _this.refreshThemeData();
                            _this.closeQuickMenus();
                            return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                        case 2:
                            _a.sent();
                            return [2 /*return*/];
                    }
                });
            });
        },
        onLogoutTap: function () {
            var _this = this;
            this.closeQuickMenus();
            wx.showModal({
                title: '退出登录',
                content: '确定要退出登录吗？',
                confirmText: '退出',
                confirmColor: '#FF3B30',
                success: function (r) {
                    if (!r.confirm)
                        return;
                    try {
                        (0, auth_1.logout)();
                    }
                    catch (e) { }
                    _this.triggerEvent('navigate', { url: '/pages/login/login', navType: 'reLaunch' });
                }
            });
        },
        onStyleTap: function (e) {
            var _a, _b;
            var style = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.style;
            this.triggerEvent('selectstyle', { style: style });
        },
        onSearchInput: function (e) {
            var v = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
            this.setData({ searchKeyword: v });
        },
        onSearchSubmit: function () {
            var kw = String(this.data.searchKeyword || '').trim();
            if (!kw) {
                this.triggerEvent('navigate', { url: '/pages/search-v2/search-v2', navType: 'navigateTo' });
                return;
            }
            var url = "/pages/search-v2/search-v2?keyword=".concat(encodeURIComponent(kw));
            this.triggerEvent('navigate', { url: url, navType: 'navigateTo' });
        }
    }
});
