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
var theme_1 = require("../../utils/theme");
var avatar_1 = require("../../utils/avatar");
function maskEmail(email) {
    var s = (email == null) ? '' : String(email).trim();
    if (!s || !s.includes('@'))
        return s || '未绑定';
    var parts = s.split('@');
    if (parts.length < 2)
        return s;
    var name = parts[0] || '';
    var domain = parts.slice(1).join('@') || '';
    if (!name)
        return "***@".concat(domain);
    if (name.length === 1)
        return "".concat(name, "***@").concat(domain);
    return "".concat(name.slice(0, 2), "***@").concat(domain);
}
Page({
    data: {
        loading: false,
        errorMsg: '',
        username: '—',
        avatarUrl: '',
        avatarInitial: 'U',
        roleText: '普通用户',
        createdAtText: '—',
        wechatBound: false,
        wechatBadge: '微信未绑定',
        emailRaw: '',
        emailMasked: '未绑定',
        emailBadge: '未绑定',
        collegeRaw: '',
        contactRaw: '',
        signatureRaw: '',
        collegeText: '未设置',
        contactText: '未设置',
        signatureText: '未设置',
        streakDays: 0,
        totalAnswered: 0,
        accuracyText: '0%',
        mistakesCount: 0,
        favoritesCount: 0
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
        if (!this.data.loading)
            this.loadProfile(false);
    },
    onPullDownRefresh: function () {
        var _this = this;
        Promise.resolve()
            .then(function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.loadProfile(true)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); })
            .finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onEditProfile: function () {
        wx.navigateTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=account&accTab=profile&edit=1' });
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
    },
    onAvatarTap: function () {
        var url = String(this.data.avatarUrl || '').trim();
        if (url) {
            wx.previewImage({ urls: [url], current: url });
            return;
        }
        this.onEditProfile();
    },
    onAvatarError: function () {
        var _this = this;
        var url = String(this.data.avatarUrl || '').trim();
        if (!url || !/^https?:\/\//i.test(url)) {
            this.setData({ avatarUrl: '' });
            return;
        }
        var self = this;
        if (self.__avatarDlTried) {
            this.setData({ avatarUrl: '' });
            return;
        }
        self.__avatarDlTried = true;
        wx.downloadFile({
            url: url,
            timeout: 15000,
            success: function (res) {
                var tempFilePath = String((res && res.tempFilePath) || '').trim();
                _this.setData({ avatarUrl: tempFilePath || '' });
            },
            fail: function () {
                _this.setData({ avatarUrl: '' });
            }
        });
    },
    onGoHistory: function () {
        wx.navigateTo({ url: '/packages/data/pages/data-center-v2/data-center-v2' });
    },
    onGoMistakes: function () {
        wx.navigateTo({ url: '/pages/mistakes-v2/mistakes-v2' });
    },
    onGoFavorites: function () {
        wx.navigateTo({ url: '/pages/favorites-v2/favorites-v2' });
    },
    onCopy: function (e) {
        var _a, _b;
        var value = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.value) || '').trim();
        if (!value) {
            wx.showToast({ title: '无可复制内容', icon: 'none' });
            return;
        }
        wx.setClipboardData({
            data: value,
            success: function () { return wx.showToast({ title: '已复制', icon: 'none' }); },
            fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
        });
    },
    loadProfile: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, p, username, avatar, isAdmin, createdAtText, college, contact, signature, streakDays, totalAnswered, accuracy, mistakesCount, favoritesCount, emailRaw, emailMasked, emailVerified, emailBadge, wechatBound, wechatBadge, e_1;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 8000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getProfile()];
                    case 2:
                        p = _a.sent();
                        username = String((p === null || p === void 0 ? void 0 : p.username) || '用户');
                        avatar = (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(p === null || p === void 0 ? void 0 : p.avatar));
                        isAdmin = !!(p === null || p === void 0 ? void 0 : p.is_admin);
                        createdAtText = (p === null || p === void 0 ? void 0 : p.created_at) ? "\u52A0\u5165 ".concat(String(p.created_at)) : '加入时间 —';
                        college = String((p === null || p === void 0 ? void 0 : p.college) || '');
                        contact = String((p === null || p === void 0 ? void 0 : p.contact) || '');
                        signature = String((p === null || p === void 0 ? void 0 : p.signature) || '');
                        streakDays = Number((p === null || p === void 0 ? void 0 : p.streak_days) || 0) || 0;
                        totalAnswered = Number((p === null || p === void 0 ? void 0 : p.total_answered) || 0) || 0;
                        accuracy = Number((p === null || p === void 0 ? void 0 : p.accuracy) || 0) || 0;
                        mistakesCount = Number((p === null || p === void 0 ? void 0 : p.mistakes_count) || 0) || 0;
                        favoritesCount = Number((p === null || p === void 0 ? void 0 : p.favorites_count) || 0) || 0;
                        emailRaw = String((p === null || p === void 0 ? void 0 : p.email) || '').trim();
                        emailMasked = maskEmail(emailRaw);
                        emailVerified = !!(p === null || p === void 0 ? void 0 : p.email_verified);
                        emailBadge = emailRaw ? (emailVerified ? '已验证' : '未验证') : '未绑定';
                        wechatBound = !!(p === null || p === void 0 ? void 0 : p.wechat_bound);
                        wechatBadge = wechatBound ? '微信已绑定' : '微信未绑定';
                        this.setData({
                            username: username,
                            avatarUrl: avatar || '/images/default-avatar.png',
                            avatarInitial: (username || 'U').charAt(0).toUpperCase(),
                            roleText: isAdmin ? '管理员' : '普通用户',
                            createdAtText: createdAtText,
                            wechatBound: wechatBound,
                            wechatBadge: wechatBadge,
                            emailRaw: emailRaw,
                            emailMasked: emailMasked || '未绑定',
                            emailBadge: emailBadge,
                            collegeRaw: college,
                            contactRaw: contact,
                            signatureRaw: signature,
                            collegeText: college ? college : '未设置',
                            contactText: contact ? contact : '未设置',
                            signatureText: signature ? signature : '未设置',
                            streakDays: streakDays,
                            totalAnswered: totalAnswered,
                            accuracyText: "".concat(accuracy, "%"),
                            mistakesCount: mistakesCount,
                            favoritesCount: favoritesCount
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '加载失败，请稍后重试' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
