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
var last_practice_1 = require("../../utils/last-practice");
var theme_1 = require("../../utils/theme");
function navTo(key) {
    if (key === 'account')
        return '/pages/settings-account-profile-v2/settings-account-profile-v2';
    if (key === 'practice')
        return '/pages/settings-practice-v2/settings-practice-v2';
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    return '/pages/settings-about-v2/settings-about-v2';
}
function summarizeUsername() {
    var userInfo = wx.getStorageSync('userInfo') || {};
    var name = String((userInfo === null || userInfo === void 0 ? void 0 : userInfo.username) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.name) || (userInfo === null || userInfo === void 0 ? void 0 : userInfo.email) || '').trim();
    return name || '已登录';
}
Page({
    data: {
        navKey: 'about',
        aboutTab: 'app',
        contactOpen: false,
        currentUsername: '—',
        adminUsername: '',
        adminEmail: '',
        adminWechat: '',
        chatDisabled: true,
        chatDisabledReason: '',
        errorMsg: ''
    },
    onLoad: function (options) {
        var tab = String((options === null || options === void 0 ? void 0 : options.aboutTab) || (options === null || options === void 0 ? void 0 : options.about) || '').toLowerCase();
        if (tab === 'legal')
            this.setData({ aboutTab: 'legal' });
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
        this.setData({ currentUsername: summarizeUsername() });
        this.loadAboutInfo();
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onContinueLast: function () {
        var url = (0, last_practice_1.buildLastPracticeUrl)();
        if (!url) {
            wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
            return;
        }
        wx.navigateTo({ url: url });
    },
    onSettingsNavTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = navTo(key);
        if (url === '/pages/settings-about-v2/settings-about-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onAboutTabTap: function (e) {
        var _a, _b;
        var tab = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '').toLowerCase();
        var next = tab === 'legal' ? 'legal' : 'app';
        if (next === this.data.aboutTab)
            return;
        this.setData({ aboutTab: next });
    },
    onToggleContact: function () {
        this.setData({ contactOpen: !this.data.contactOpen });
    },
    loadAboutInfo: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        this.setData({ errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSettingsAbout()];
                    case 2:
                        res = _a.sent();
                        this.setData({
                            adminUsername: String((res === null || res === void 0 ? void 0 : res.admin_username) || ''),
                            adminEmail: String((res === null || res === void 0 ? void 0 : res.admin_email) || ''),
                            adminWechat: String((res === null || res === void 0 ? void 0 : res.admin_wechat) || ''),
                            chatDisabled: !!(res === null || res === void 0 ? void 0 : res.chat_disabled),
                            chatDisabledReason: String((res === null || res === void 0 ? void 0 : res.chat_disabled_reason) || '')
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '加载失败，请稍后重试' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onGoProfile: function () {
        wx.redirectTo({ url: '/pages/settings-account-profile-v2/settings-account-profile-v2' });
    },
    onContactChat: function () {
        if (this.data.chatDisabled) {
            wx.showToast({ title: this.data.chatDisabledReason || '暂不可用', icon: 'none' });
            return;
        }
        wx.showToast({ title: '小程序暂不支持站内聊天，请在 Web 端打开 /contact_admin', icon: 'none' });
    },
    onCopy: function (e) {
        var _a, _b;
        var v = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.value) || '').trim();
        if (!v)
            return;
        wx.setClipboardData({
            data: v,
            success: function () { return wx.showToast({ title: '已复制', icon: 'none' }); },
            fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
        });
    },
    onOpenTerms: function () {
        wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /terms', icon: 'none' });
    },
    onOpenPrivacy: function () {
        wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /privacy', icon: 'none' });
    }
});
