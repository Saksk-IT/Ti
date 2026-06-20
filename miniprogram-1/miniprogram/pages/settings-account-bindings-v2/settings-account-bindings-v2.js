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
    if (key === 'practice')
        return '/pages/settings-practice-v2/settings-practice-v2';
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (key === 'about')
        return '/pages/settings-about-v2/settings-about-v2';
    return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
}
function accTo(key) {
    if (key === 'profile')
        return '/pages/settings-account-profile-v2/settings-account-profile-v2';
    if (key === 'security')
        return '/pages/settings-account-security-v2/settings-account-security-v2';
    return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
}
function validateEmail(email) {
    var v = String(email || '').trim();
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!v)
        return { ok: false, msg: '请输入邮箱地址' };
    if (!emailRegex.test(v))
        return { ok: false, msg: '邮箱格式不正确' };
    return { ok: true, value: v };
}
Page({
    data: {
        navKey: 'account',
        accTab: 'bindings',
        loading: false,
        errorMsg: '',
        msg: '',
        emailChip: '-',
        emailDesc: '加载中…',
        emailActionText: '绑定',
        emailFormOpen: false,
        bindEmail: '',
        bindCode: '',
        sendingCode: false,
        countdown: 0,
        sendCodeText: '发送验证码',
        sendCodeDisabled: false,
        bindingEmail: false,
        wechatBound: false,
        wechatChip: '-',
        wechatDesc: '加载中…',
        bindingWechat: false,
        unbindingWechat: false
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
    onUnload: function () {
        this.clearCountdown();
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
        if (url === '/pages/settings-account-bindings-v2/settings-account-bindings-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onAccountSubTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = accTo(key);
        if (url === '/pages/settings-account-bindings-v2/settings-account-bindings-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onEmailActionTap: function () {
        if (this.data.loading)
            return;
        this.setData({
            msg: '',
            errorMsg: '',
            emailFormOpen: true
        });
    },
    onCloseEmailFormTap: function () {
        if (this.data.bindingEmail)
            return;
        this.clearCountdown();
        this.setData({
            emailFormOpen: false,
            bindEmail: '',
            bindCode: ''
        });
    },
    onBindEmailInput: function (e) {
        var _a;
        this.setData({ bindEmail: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onBindCodeInput: function (e) {
        var _a;
        this.setData({ bindCode: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    getSendCodeText: function () {
        if (this.data.sendingCode)
            return '发送中…';
        if (this.data.countdown > 0)
            return "\u91CD\u53D1(".concat(this.data.countdown, "s)");
        return '发送验证码';
    },
    refreshSendCodeUi: function () {
        this.setData({
            sendCodeText: this.getSendCodeText(),
            sendCodeDisabled: this.data.sendingCode || this.data.countdown > 0
        });
    },
    clearCountdown: function () {
        var self = this;
        if (self.__countdownTimer) {
            clearTimeout(self.__countdownTimer);
            self.__countdownTimer = null;
        }
        this.setData({ countdown: 0, sendingCode: false });
        this.refreshSendCodeUi();
    },
    tickCountdown: function () {
        var _this = this;
        var self = this;
        var next = Math.max(0, Number(this.data.countdown || 0) - 1);
        this.setData({ countdown: next });
        this.refreshSendCodeUi();
        if (next <= 0) {
            self.__countdownTimer = null;
            return;
        }
        self.__countdownTimer = setTimeout(function () { return _this.tickCountdown(); }, 1000);
    },
    onSendCodeTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var v, res, tip, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.sendingCode || this.data.countdown > 0)
                            return [2 /*return*/];
                        v = validateEmail(this.data.bindEmail);
                        if (!v.ok) {
                            this.setData({ errorMsg: v.msg || '邮箱格式不正确' });
                            return [2 /*return*/];
                        }
                        this.setData({ sendingCode: true, msg: '', errorMsg: '' });
                        this.refreshSendCodeUi();
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.sendEmailBindCode(v.value)];
                    case 2:
                        res = _a.sent();
                        tip = String((res === null || res === void 0 ? void 0 : res.message) || '验证码已发送');
                        wx.showToast({ title: tip, icon: 'none' });
                        this.setData({ msg: tip, countdown: 60 });
                        this.refreshSendCodeUi();
                        this.tickCountdown();
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '发送失败，请稍后重试' });
                        this.clearCountdown();
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ sendingCode: false });
                        this.refreshSendCodeUi();
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onBindEmailTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var v, code, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.bindingEmail)
                            return [2 /*return*/];
                        v = validateEmail(this.data.bindEmail);
                        if (!v.ok) {
                            this.setData({ errorMsg: v.msg || '邮箱格式不正确' });
                            return [2 /*return*/];
                        }
                        code = String(this.data.bindCode || '').trim();
                        if (!code || code.length !== 6) {
                            this.setData({ errorMsg: '请输入 6 位验证码' });
                            return [2 /*return*/];
                        }
                        this.setData({ bindingEmail: true, msg: '', errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.bindEmail(v.value, code)];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '邮箱绑定成功', icon: 'none' });
                        this.clearCountdown();
                        this.setData({ emailFormOpen: false, bindEmail: '', bindCode: '', msg: '邮箱绑定成功' });
                        return [4 /*yield*/, this.loadProfile(true)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        e_2 = _a.sent();
                        this.setData({ errorMsg: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '绑定失败，请稍后重试' });
                        return [3 /*break*/, 6];
                    case 5:
                        this.setData({ bindingEmail: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onWechatBindTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var code, res, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.bindingWechat)
                            return [2 /*return*/];
                        this.setData({ bindingWechat: true, msg: '', errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 5, 6, 7]);
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.login({
                                    success: function (res) { return resolve(String((res === null || res === void 0 ? void 0 : res.code) || '')); },
                                    fail: function () { return resolve(''); }
                                });
                            })];
                    case 2:
                        code = _a.sent();
                        if (!code)
                            throw new Error('获取微信登录 code 失败');
                        return [4 /*yield*/, api_1.api.miniWechatBind(code)];
                    case 3:
                        res = _a.sent();
                        if (res && res.token)
                            wx.setStorageSync('token', res.token);
                        if (res && res.user_info)
                            wx.setStorageSync('userInfo', res.user_info);
                        wx.showToast({ title: '绑定成功', icon: 'none' });
                        this.setData({ msg: '绑定成功' });
                        return [4 /*yield*/, this.loadProfile(true)];
                    case 4:
                        _a.sent();
                        return [3 /*break*/, 7];
                    case 5:
                        e_3 = _a.sent();
                        this.setData({ errorMsg: (e_3 === null || e_3 === void 0 ? void 0 : e_3.message) || '绑定失败，请稍后重试' });
                        return [3 /*break*/, 7];
                    case 6:
                        this.setData({ bindingWechat: false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    onWechatUnbindTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var emailChip, hasEmail, ok, e_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.unbindingWechat)
                            return [2 /*return*/];
                        emailChip = this.data.emailChip || '';
                        hasEmail = emailChip.includes('已绑定');
                        if (!hasEmail) {
                            wx.showModal({
                                title: '无法解绑',
                                content: '请先绑定邮箱后再解绑微信，否则账号将无法登录。',
                                showCancel: false,
                                confirmText: '去绑定邮箱'
                            });
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '确认解绑微信',
                                    content: '解绑后将无法使用微信一键登录。为保证安全，需要重新登录。',
                                    confirmText: '解绑',
                                    cancelText: '取消',
                                    success: function (res) { return resolve(!!res.confirm); },
                                    fail: function () { return resolve(false); }
                                });
                            })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        this.setData({ unbindingWechat: true, msg: '', errorMsg: '' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 5, 6, 7]);
                        return [4 /*yield*/, api_1.api.wechatUnbind()];
                    case 3:
                        _a.sent();
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '解绑成功',
                                    content: '需要重新登录。',
                                    showCancel: false,
                                    confirmText: '去登录',
                                    success: function () { return resolve(); }
                                });
                            })];
                    case 4:
                        _a.sent();
                        (0, auth_1.logout)();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [3 /*break*/, 7];
                    case 5:
                        e_4 = _a.sent();
                        this.setData({ errorMsg: (e_4 === null || e_4 === void 0 ? void 0 : e_4.message) || '解绑失败，请稍后重试' });
                        return [3 /*break*/, 7];
                    case 6:
                        this.setData({ unbindingWechat: false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    applyProfile: function (p) {
        var email = String((p === null || p === void 0 ? void 0 : p.email) || '').trim();
        var verified = !!(p === null || p === void 0 ? void 0 : p.email_verified);
        var emailChip = email ? (verified ? '已绑定' : '已绑定(未验证)') : '未绑定';
        var emailDesc = email ? "\u5F53\u524D\u90AE\u7BB1\uFF1A".concat(email).concat(verified ? '' : '（未验证）') : '绑定邮箱用于接收验证码与找回账号。';
        var emailActionText = email ? '更换' : '绑定';
        var wechatBound = !!(p === null || p === void 0 ? void 0 : p.wechat_bound);
        var wechatChip = wechatBound ? '已绑定' : '未绑定';
        var wechatDesc = wechatBound ? '已绑定微信，可使用微信一键登录。' : '绑定微信后可使用微信一键登录。';
        this.setData({
            wechatBound: wechatBound,
            emailChip: emailChip,
            emailDesc: emailDesc,
            emailActionText: emailActionText,
            wechatChip: wechatChip,
            wechatDesc: wechatDesc
        });
    },
    loadProfile: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, p, e_5;
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
                        this.applyProfile(p);
                        this.refreshSendCodeUi();
                        return [3 /*break*/, 5];
                    case 3:
                        e_5 = _a.sent();
                        this.applyProfile({});
                        this.setData({ errorMsg: (e_5 === null || e_5 === void 0 ? void 0 : e_5.message) || '加载失败，请稍后重试' });
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
