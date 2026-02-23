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
var PENDING_MINI_REDIRECT_KEY = 'pendingMiniRedirect';
function setPendingMiniRedirect(url) {
    try {
        var s = String(url || '').trim();
        if (!s)
            return;
        wx.setStorageSync(PENDING_MINI_REDIRECT_KEY, s);
    }
    catch (e) { }
}
function clearPendingMiniRedirect() {
    try {
        wx.removeStorageSync(PENDING_MINI_REDIRECT_KEY);
    }
    catch (e) { }
}
function normalizeTokenFromShareLink(input) {
    var s = String(input || '').trim();
    if (!s)
        return '';
    if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?'))
        return s;
    var tokenMatch = s.match(/[?&]token=([^&#]+)/i);
    if (tokenMatch && tokenMatch[1]) {
        try {
            return decodeURIComponent(tokenMatch[1]);
        }
        catch (_a) {
            return tokenMatch[1];
        }
    }
    return '';
}
Page({
    data: {
        mode: 'code',
        token: '',
        shareCode: '',
        loading: false,
        errorMsg: ''
    },
    onLoad: function (options) {
        return __awaiter(this, void 0, void 0, function () {
            var rawToken, token, scene, shareCode, mode;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        rawToken = (options === null || options === void 0 ? void 0 : options.token) || (options === null || options === void 0 ? void 0 : options.share_token) || '';
                        token = normalizeTokenFromShareLink(rawToken);
                        // 兼容：扫码/二维码场景可能走 scene 参数
                        if (!token) {
                            scene = String((options === null || options === void 0 ? void 0 : options.scene) || '').trim();
                            if (scene) {
                                try {
                                    token = normalizeTokenFromShareLink(decodeURIComponent(scene)) || normalizeTokenFromShareLink(scene);
                                }
                                catch (_b) {
                                    token = normalizeTokenFromShareLink(scene);
                                }
                            }
                        }
                        shareCode = String((options === null || options === void 0 ? void 0 : options.share_code) || (options === null || options === void 0 ? void 0 : options.code) || '').trim().toUpperCase();
                        mode = token ? 'token' : 'code';
                        this.setData({ mode: mode, token: token, shareCode: shareCode });
                        if (!token) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.autoJoinByToken(token)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
                        if (!(shareCode && shareCode.length === 6)) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.joinByCode(shareCode)];
                    case 3:
                        _a.sent();
                        _a.label = 4;
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onShareCodeInput: function (e) {
        var _a;
        var v = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '').trim().toUpperCase();
        this.setData({ shareCode: v, errorMsg: '' });
    },
    ensureLoggedIn: function (nextUrl) {
        return __awaiter(this, void 0, Promise, function () {
            var result, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if ((0, auth_1.checkLogin)())
                            return [2 /*return*/, true];
                        setPendingMiniRedirect(nextUrl);
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, (0, auth_1.wechatLogin)()];
                    case 2:
                        result = _a.sent();
                        if (result === 'success')
                            return [2 /*return*/, true];
                        if (result === 'need_bind') {
                            wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
                            return [2 /*return*/, false];
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        e_1 = _a.sent();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [2 /*return*/, false];
                    case 4:
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [2 /*return*/, false];
                }
            });
        });
    },
    autoJoinByToken: function (token) {
        return __awaiter(this, void 0, void 0, function () {
            var t, nextUrl, ok, res, bankId, bankName, e_2, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        t = String(token || '').trim();
                        if (!t)
                            return [2 /*return*/];
                        if (this.data.loading)
                            return [2 /*return*/];
                        nextUrl = "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(t));
                        return [4 /*yield*/, this.ensureLoggedIn(nextUrl)];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        this.setData({ loading: true, errorMsg: '' });
                        wx.showLoading({ title: '加入中...' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.joinBankByToken(t)];
                    case 3:
                        res = _a.sent();
                        bankId = Number((res === null || res === void 0 ? void 0 : res.bank_id) || 0);
                        bankName = String((res === null || res === void 0 ? void 0 : res.bank_name) || '').trim();
                        wx.showToast({ title: bankName ? "\u5DF2\u52A0\u5165\u300C".concat(bankName, "\u300D") : '已加入', icon: 'success' });
                        clearPendingMiniRedirect();
                        if (bankId > 0) {
                            (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
                        }
                        else {
                            (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                        }
                        return [3 /*break*/, 6];
                    case 4:
                        e_2 = _a.sent();
                        msg = (e_2 && e_2.message) ? String(e_2.message) : '加入失败';
                        this.setData({ errorMsg: msg });
                        return [3 /*break*/, 6];
                    case 5:
                        wx.hideLoading();
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    joinByCode: function (code) {
        return __awaiter(this, void 0, void 0, function () {
            var c, nextUrl, ok, res, bankId, bankName, e_3, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        c = String(code || '').trim().toUpperCase();
                        if (!c || c.length !== 6) {
                            wx.showToast({ title: '请输入6位分享码', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (this.data.loading)
                            return [2 /*return*/];
                        nextUrl = "/pages/bank-join/bank-join?share_code=".concat(encodeURIComponent(c));
                        return [4 /*yield*/, this.ensureLoggedIn(nextUrl)];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        this.setData({ loading: true, errorMsg: '' });
                        wx.showLoading({ title: '加入中...' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.joinBankByCode(c)];
                    case 3:
                        res = _a.sent();
                        bankId = Number((res === null || res === void 0 ? void 0 : res.bank_id) || 0);
                        bankName = String((res === null || res === void 0 ? void 0 : res.bank_name) || '').trim();
                        wx.showToast({ title: bankName ? "\u5DF2\u52A0\u5165\u300C".concat(bankName, "\u300D") : '已加入', icon: 'success' });
                        clearPendingMiniRedirect();
                        if (bankId > 0) {
                            (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
                        }
                        else {
                            (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                        }
                        return [3 /*break*/, 6];
                    case 4:
                        e_3 = _a.sent();
                        msg = (e_3 && e_3.message) ? String(e_3.message) : '加入失败';
                        this.setData({ errorMsg: msg });
                        return [3 /*break*/, 6];
                    case 5:
                        wx.hideLoading();
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onJoinByCodeTap: function () {
        var code = String(this.data.shareCode || '').trim().toUpperCase();
        this.joinByCode(code);
    },
    onRetry: function () {
        if (this.data.mode === 'token') {
            this.autoJoinByToken(String(this.data.token || ''));
            return;
        }
        this.joinByCode(String(this.data.shareCode || ''));
    },
    onSwitchToCode: function () {
        this.setData({ mode: 'code', token: '', errorMsg: '' });
    },
    onCancel: function () {
        // 分享打开的页面通常是页面栈第一个，无法 navigateBack，直接跳首页
        var pages = getCurrentPages();
        if (pages.length <= 1) {
            (0, nav_1.safeNavigate)('/pages/hub-v2/hub-v2', 'switchTab');
            return;
        }
        wx.navigateBack({
            delta: 1,
            fail: function () {
                (0, nav_1.safeNavigate)('/pages/hub-v2/hub-v2', 'switchTab');
            }
        });
    }
});
