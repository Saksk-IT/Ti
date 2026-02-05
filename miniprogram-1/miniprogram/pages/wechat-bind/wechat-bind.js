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
var nav_1 = require("../../utils/nav");
var HOME_URL = '/pages/hub-v2/hub-v2';
var PENDING_MINI_REDIRECT_KEY = 'pendingMiniRedirect';
function consumePendingMiniRedirect() {
    try {
        var raw = wx.getStorageSync(PENDING_MINI_REDIRECT_KEY);
        var url = String(raw || '').trim();
        if (!url)
            return '';
        wx.removeStorageSync(PENDING_MINI_REDIRECT_KEY);
        if (!url.startsWith('/'))
            return '';
        return url;
    }
    catch (e) {
        return '';
    }
}
function navigateAfterBind() {
    var next = consumePendingMiniRedirect();
    if (next) {
        (0, nav_1.safeNavigate)(next, 'redirectTo');
        return;
    }
    (0, nav_1.safeNavigate)(HOME_URL, 'switchTab');
}
Page({
    data: {
        step: 'choice',
        mode: 'password',
        wechatTempToken: '',
        account: '',
        password: '',
        email: '',
        code: '',
        loadingCreate: false,
        loadingBind: false,
        codeSending: false,
        loadingAny: false,
        actionDisabled: false,
        sendCodeDisabled: false,
        countdown: 60,
        error: ''
    },
    setLoading: function (partial) {
        var next = __assign(__assign({}, this.data), partial);
        var loadingAny = !!(next.loadingCreate || next.loadingBind || next.codeSending);
        var actionDisabled = !!(next.loadingCreate || next.loadingBind);
        var sendCodeDisabled = !!(next.loadingBind || next.codeSending);
        this.setData(__assign(__assign({}, partial), { loadingAny: loadingAny, actionDisabled: actionDisabled, sendCodeDisabled: sendCodeDisabled }));
    },
    onLoad: function () {
        var token = wx.getStorageSync('wechatTempToken') || '';
        if (!token) {
            this.setData({ error: '缺少临时票据，请重新登录' });
            return;
        }
        this.setData({ wechatTempToken: token });
    },
    setMode: function (e) {
        var mode = e.currentTarget.dataset.mode;
        if (mode !== 'password' && mode !== 'email_code')
            return;
        this.setData({ mode: mode, error: '' });
    },
    onGoBind: function () {
        this.setData({ step: 'bind', error: '' });
    },
    onBack: function () {
        this.setData({ step: 'choice', error: '' });
    },
    onAccount: function (e) {
        this.setData({ account: e.detail.value || '' });
    },
    onPassword: function (e) {
        this.setData({ password: e.detail.value || '' });
    },
    onEmail: function (e) {
        this.setData({ email: e.detail.value || '' });
    },
    onCode: function (e) {
        this.setData({ code: e.detail.value || '' });
    },
    onCreate: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, pending_1, e_1, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loadingCreate)
                            return [2 /*return*/];
                        this.setLoading({ loadingCreate: true, error: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.wechatCreate(this.data.wechatTempToken)];
                    case 2:
                        res = _a.sent();
                        if (!res || !res.token)
                            throw new Error('返回数据异常');
                        wx.setStorageSync('token', res.token);
                        if (res.user_info)
                            wx.setStorageSync('userInfo', res.user_info);
                        wx.removeStorageSync('wechatTempToken');
                        wx.showToast({ title: '已创建', icon: 'success' });
                        pending_1 = wx.getStorageSync('pendingWebLogin');
                        if (pending_1 && pending_1.sid && pending_1.nonce) {
                            setTimeout(function () {
                                return wx.reLaunch({
                                    url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(pending_1.sid), "&nonce=").concat(encodeURIComponent(pending_1.nonce))
                                });
                            }, 600);
                        }
                        else {
                            setTimeout(function () { return navigateAfterBind(); }, 600);
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        msg = (e_1 && (e_1.message || e_1.errMsg)) || '创建失败';
                        this.setData({ error: msg });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setLoading({ loadingCreate: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onSendCode: function () {
        return __awaiter(this, void 0, void 0, function () {
            var e_2, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.codeSending || this.data.loadingBind)
                            return [2 /*return*/];
                        if (!this.data.email) {
                            this.setData({ error: '请输入邮箱' });
                            return [2 /*return*/];
                        }
                        this.setData({ error: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.wechatBindSendCode(this.data.wechatTempToken, this.data.email)];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '已发送', icon: 'success' });
                        this.startCountdown();
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        msg = (e_2 && (e_2.message || e_2.errMsg)) || '发送失败';
                        this.setData({ error: msg });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    startCountdown: function () {
        var _this = this;
        this.setLoading({ codeSending: true, countdown: 60 });
        var timer = setInterval(function () {
            var next = (_this.data.countdown || 0) - 1;
            if (next <= 0) {
                clearInterval(timer);
                _this.setLoading({ codeSending: false, countdown: 60 });
                return;
            }
            _this.setData({ countdown: next });
        }, 1000);
    },
    onBind: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, pending_2, e_3, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loadingBind)
                            return [2 /*return*/];
                        // 先校验，避免校验失败后按钮被锁死
                        if (this.data.mode === 'password') {
                            if (!this.data.account || !this.data.password) {
                                this.setData({ error: '请输入账号和密码' });
                                return [2 /*return*/];
                            }
                        }
                        else {
                            if (!this.data.email || !this.data.code) {
                                this.setData({ error: '请输入邮箱和验证码' });
                                return [2 /*return*/];
                            }
                        }
                        this.setLoading({ loadingBind: true, error: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        res = void 0;
                        if (!(this.data.mode === 'password')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.wechatBindPassword(this.data.wechatTempToken, this.data.account, this.data.password)];
                    case 2:
                        res = _a.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.wechatBindEmailCode(this.data.wechatTempToken, this.data.email, this.data.code)];
                    case 4:
                        res = _a.sent();
                        _a.label = 5;
                    case 5:
                        if (!res || !res.token)
                            throw new Error('返回数据异常');
                        wx.setStorageSync('token', res.token);
                        if (res.user_info)
                            wx.setStorageSync('userInfo', res.user_info);
                        wx.removeStorageSync('wechatTempToken');
                        wx.showToast({ title: '已绑定', icon: 'success' });
                        pending_2 = wx.getStorageSync('pendingWebLogin');
                        if (pending_2 && pending_2.sid && pending_2.nonce) {
                            setTimeout(function () {
                                return wx.reLaunch({
                                    url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(pending_2.sid), "&nonce=").concat(encodeURIComponent(pending_2.nonce))
                                });
                            }, 600);
                        }
                        else {
                            setTimeout(function () { return navigateAfterBind(); }, 600);
                        }
                        return [3 /*break*/, 8];
                    case 6:
                        e_3 = _a.sent();
                        msg = (e_3 && (e_3.message || e_3.errMsg)) || '绑定失败';
                        this.setData({ error: msg });
                        return [3 /*break*/, 8];
                    case 7:
                        this.setLoading({ loadingBind: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    }
});
