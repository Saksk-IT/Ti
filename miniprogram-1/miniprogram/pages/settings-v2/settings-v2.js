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
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var user_settings_1 = require("../../utils/user-settings");
var theme_1 = require("../../utils/theme");
var PRACTICE_SETTINGS_KEY = 'quiz_practice_settings_v1';
function readPracticeSettings() {
    try {
        var raw = wx.getStorageSync(PRACTICE_SETTINGS_KEY);
        if (raw && typeof raw === 'object') {
            return {
                autoNextOnCorrect: !!raw.autoNextOnCorrect,
                autoFavoriteOnWrong: !!raw.autoFavoriteOnWrong,
                vibrationFeedback: !!raw.vibrationFeedback
            };
        }
    }
    catch (e) { }
    return { autoNextOnCorrect: false, autoFavoriteOnWrong: false, vibrationFeedback: false };
}
function writePracticeSettings(s) {
    try {
        wx.setStorageSync(PRACTICE_SETTINGS_KEY, s);
    }
    catch (e) { }
}
function getAppVersion() {
    var _a, _b;
    try {
        var info = wx.getAccountInfoSync ? wx.getAccountInfoSync() : null;
        var v = ((_a = info === null || info === void 0 ? void 0 : info.miniProgram) === null || _a === void 0 ? void 0 : _a.version) || ((_b = info === null || info === void 0 ? void 0 : info.miniProgram) === null || _b === void 0 ? void 0 : _b.envVersion);
        return v ? String(v) : '—';
    }
    catch (e) {
        return '—';
    }
}
function summarizeUser(userInfo) {
    var name = String((userInfo === null || userInfo === void 0 ? void 0 : userInfo.username) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.name) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.email) || '已登录');
    var parts = [];
    if (userInfo === null || userInfo === void 0 ? void 0 : userInfo.email)
        parts.push(String(userInfo.email));
    if ((userInfo === null || userInfo === void 0 ? void 0 : userInfo.id) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.user_id))
        parts.push("ID ".concat(userInfo.id || userInfo.user_id));
    if (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_admin)
        parts.push('管理员');
    if (userInfo === null || userInfo === void 0 ? void 0 : userInfo.is_subject_admin)
        parts.push('科目管理员');
    var meta = parts.length ? parts.join(' · ') : '已登录（JWT）';
    return { name: name, meta: meta };
}
Page({
    data: {
        drawerOpen: false,
        userName: '—',
        userMeta: '未登录',
        appVersion: '—',
        practiceSettings: readPracticeSettings()
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        var userInfo = wx.getStorageSync('userInfo') || {};
        var u = summarizeUser(userInfo);
        this.setData({
            userName: u.name,
            userMeta: u.meta,
            appVersion: getAppVersion(),
            practiceSettings: readPracticeSettings()
        });
    },
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
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a;
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
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
    onModeTap: function (e) {
        var _a, _b;
        var mode = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.mode) || 'system');
        if (mode !== 'light' && mode !== 'dark' && mode !== 'system')
            return;
        theme_1.themeManager.setMode(mode);
        this.setData(theme_1.themeManager.getPageData());
    },
    onStyleTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        style = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onPracticeSwitch: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        var value = !!(e && e.detail && e.detail.value);
        if (!key)
            return;
        var next = Object.assign({}, this.data.practiceSettings);
        next[key] = value;
        this.setData({ practiceSettings: next });
        writePracticeSettings(next);
    },
    onGoSubpage: function (e) {
        var _a, _b;
        var url = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.url) || '').trim();
        if (!url)
            return;
        wx.navigateTo({ url: url });
    },
    onGoMine: function () {
        wx.switchTab({ url: '/pages/mine/mine' });
    },
    onLogout: function () {
        try {
            wx.removeStorageSync('token');
            wx.removeStorageSync('userInfo');
        }
        catch (e) { }
        wx.reLaunch({ url: '/pages/login/login' });
    }
});
