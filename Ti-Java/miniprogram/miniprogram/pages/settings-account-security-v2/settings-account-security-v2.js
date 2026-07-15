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
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (key === 'about')
        return '/pages/settings-about-v2/settings-about-v2';
    return '/pages/settings-account-security-v2/settings-account-security-v2';
}
function accTo(key) {
    if (key === 'profile')
        return '/pages/settings-account-profile-v2/settings-account-profile-v2';
    if (key === 'bindings')
        return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
    return '/pages/settings-account-security-v2/settings-account-security-v2';
}
function isStrongPassword(pwd) {
    var v = String(pwd || '');
    if (v.length < 8)
        return false;
    return /[a-zA-Z]/.test(v) && /\d/.test(v);
}
Page({
    data: {
        navKey: 'account',
        accTab: 'security',
        loading: false,
        submitting: false,
        errorMsg: '',
        msg: '',
        hasPasswordSet: false,
        pwdChip: '-',
        pwdSub: '用于修改或设置登录密码。',
        submitText: '提交',
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
        showCurrent: false,
        showNew: false,
        showConfirm: false
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
        if (url === '/pages/settings-account-security-v2/settings-account-security-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onAccountSubTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = accTo(key);
        if (url === '/pages/settings-account-security-v2/settings-account-security-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onToggleShow: function (e) {
        var _a, _b;
        var target = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.target) || '');
        if (target === 'current')
            this.setData({ showCurrent: !this.data.showCurrent });
        if (target === 'new')
            this.setData({ showNew: !this.data.showNew });
        if (target === 'confirm')
            this.setData({ showConfirm: !this.data.showConfirm });
    },
    onCurrentInput: function (e) {
        var _a;
        this.setData({ currentPassword: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onNewInput: function (e) {
        var _a;
        this.setData({ newPassword: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onConfirmInput: function (e) {
        var _a;
        this.setData({ confirmPassword: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onReset: function () {
        if (this.data.submitting)
            return;
        this.setData({
            msg: '',
            errorMsg: '',
            currentPassword: '',
            newPassword: '',
            confirmPassword: ''
        });
    },
    onSubmit: function () {
        return __awaiter(this, void 0, void 0, function () {
            var isSetPassword, cur, nw, c, res, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.submitting)
                            return [2 /*return*/];
                        this.setData({ submitting: true, msg: '', errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        isSetPassword = !this.data.hasPasswordSet;
                        cur = String(this.data.currentPassword || '');
                        nw = String(this.data.newPassword || '');
                        c = String(this.data.confirmPassword || '');
                        if (!nw || !c)
                            throw new Error('请填写新密码');
                        if (nw !== c)
                            throw new Error('两次输入的密码不一致');
                        if (!isStrongPassword(nw))
                            throw new Error('密码至少 8 位且包含字母和数字');
                        if (isSetPassword && cur)
                            throw new Error('设置密码不需要输入当前密码');
                        if (!isSetPassword && !cur)
                            throw new Error('修改密码需要输入当前密码');
                        return [4 /*yield*/, api_1.api.updateProfilePassword({
                                current_password: cur,
                                new_password: nw,
                                is_set_password: isSetPassword
                            })];
                    case 2:
                        res = _a.sent();
                        if (!isSetPassword) return [3 /*break*/, 4];
                        wx.showToast({ title: (res === null || res === void 0 ? void 0 : res.message) || '密码设置成功', icon: 'none' });
                        this.setData({ currentPassword: '', newPassword: '', confirmPassword: '', msg: (res === null || res === void 0 ? void 0 : res.message) || '密码设置成功' });
                        return [4 /*yield*/, this.loadProfile(true)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                    case 4: return [4 /*yield*/, new Promise(function (resolve) {
                            wx.showModal({
                                title: '修改成功',
                                content: '为保证安全，需要重新登录。',
                                showCancel: false,
                                confirmText: '去登录',
                                success: function () { return resolve(); }
                            });
                        })];
                    case 5:
                        _a.sent();
                        (0, auth_1.logout)();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [3 /*break*/, 8];
                    case 6:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '操作失败，请稍后重试' });
                        return [3 /*break*/, 8];
                    case 7:
                        this.setData({ submitting: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    applyMode: function (hasPasswordSet) {
        var isSetPassword = !hasPasswordSet;
        this.setData({
            hasPasswordSet: hasPasswordSet,
            pwdChip: hasPasswordSet ? '已设置密码' : '未设置密码',
            pwdSub: hasPasswordSet ? '修改登录密码。修改成功后需要重新登录。' : '为账号设置登录密码（首次设置无需填写当前密码）。',
            submitText: isSetPassword ? '设置密码' : '修改密码'
        });
    },
    loadProfile: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, p, hasPasswordSet, e_2;
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
                        hasPasswordSet = !!(p === null || p === void 0 ? void 0 : p.has_password_set);
                        this.applyMode(hasPasswordSet);
                        return [3 /*break*/, 5];
                    case 3:
                        e_2 = _a.sent();
                        this.applyMode(false);
                        this.setData({ errorMsg: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '加载失败，请稍后重试' });
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
