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
// 登录页面
var auth_1 = require("../../utils/auth");
var api_1 = require("../../utils/api");
var config_1 = require("../../utils/config");
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
function navigateAfterLogin() {
    var next = consumePendingMiniRedirect();
    if (next) {
        (0, nav_1.safeNavigate)(next, 'redirectTo');
        return;
    }
    (0, nav_1.safeNavigate)(HOME_URL, 'switchTab');
}
function isConnectionRefusedMessage(message) {
    var msg = String(message || '');
    return (msg.includes('ERR_CONNECTION_REFUSED') ||
        msg.includes('errcode:-102') ||
        msg.includes('cronet_error_code:-102') ||
        msg.toLowerCase().includes('connection refused'));
}
function isDevEnv() {
    try {
        return wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
    }
    catch (e) {
        return false;
    }
}
Page({
    data: {
        mode: 'wechat',
        loading: false,
        username: '',
        password: '',
        email: '',
        code: '',
        codeSending: false,
        countdown: 20,
        showDevTools: false,
        apiUrl: ''
    },
    onLoad: function () {
        return __awaiter(this, void 0, void 0, function () {
            var token, err_1, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        this.refreshApiInfo();
                        token = wx.getStorageSync('token');
                        if (!token)
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSubjects()];
                    case 2:
                        _a.sent();
                        navigateAfterLogin();
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        // 401：token 无效，清理后留在登录页
                        if (err_1 && err_1.statusCode === 401) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            return [2 /*return*/];
                        }
                        msg = (err_1 && err_1.message) || '';
                        if (isConnectionRefusedMessage(msg)) {
                            wx.showModal({
                                title: '无法连接后端',
                                content: "\u5F53\u524D API \u5730\u5740\u4E3A\uFF1A".concat(config_1.config.getApiUrl(), "\n\n") +
                                    '请到「开发设置」切换到“自定义”，填写电脑局域网 IP（如 192.168.1.100）或粘贴完整 URL，并点击“保存并启用自定义”。\n\n' +
                                        '同时确保后端已启动（python run.py）。',
                                confirmText: '去设置',
                                cancelText: '知道了',
                                success: function (res) {
                                    if (!res.confirm)
                                        return;
                                    wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
                                }
                            });
                            return [2 /*return*/];
                        }
                        // 其它错误：不阻塞用户（可能是网络波动），仍按“已登录”处理
                        navigateAfterLogin();
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onShow: function () {
        this.refreshApiInfo();
    },
    refreshApiInfo: function () {
        this.setData({
            showDevTools: isDevEnv(),
            apiUrl: config_1.config.getApiUrl()
        });
    },
    onOpenDevSettingsTap: function () {
        wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
    },
    onCopyApiTap: function () {
        var data = String(this.data.apiUrl || '').trim();
        if (!data)
            return;
        wx.setClipboardData({
            data: data,
            success: function () { return wx.showToast({ title: '已复制', icon: 'success' }); },
            fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
        });
    },
    promptBindWechatIfNeeded: function (loginData) {
        return __awaiter(this, void 0, void 0, function () {
            var userInfo, wechatBound, modalRes, code, bindRes, e_1, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        userInfo = (loginData && loginData.user_info) || wx.getStorageSync('userInfo') || null;
                        wechatBound = !!(userInfo && (userInfo.wechat_bound || userInfo.wechatBound));
                        if (wechatBound)
                            return [2 /*return*/];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '绑定微信',
                                    content: '绑定后可使用微信快捷登录',
                                    confirmText: '绑定',
                                    cancelText: '稍后',
                                    success: resolve
                                });
                            })];
                    case 1:
                        modalRes = _a.sent();
                        if (!modalRes || !modalRes.confirm)
                            return [2 /*return*/];
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 5, , 6]);
                        return [4 /*yield*/, new Promise(function (resolve, reject) {
                                wx.login({
                                    success: function (res) {
                                        if (res.code)
                                            resolve(res.code);
                                        else
                                            reject(new Error('获取微信登录code失败'));
                                    },
                                    fail: function (err) { return reject(err); }
                                });
                            })];
                    case 3:
                        code = _a.sent();
                        return [4 /*yield*/, api_1.api.miniWechatBind(code)];
                    case 4:
                        bindRes = _a.sent();
                        if (bindRes && bindRes.token)
                            wx.setStorageSync('token', bindRes.token);
                        if (bindRes && bindRes.user_info)
                            wx.setStorageSync('userInfo', bindRes.user_info);
                        wx.showToast({ title: '微信已绑定', icon: 'success' });
                        return [3 /*break*/, 6];
                    case 5:
                        e_1 = _a.sent();
                        msg = (e_1 && (e_1.message || e_1.errMsg)) || '绑定失败';
                        wx.showToast({ title: msg, icon: 'none' });
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    // 微信登录
    handleLogin: function () {
        return __awaiter(this, void 0, void 0, function () {
            var result, pending_1, err_2, errorMsg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, (0, auth_1.wechatLogin)()];
                    case 2:
                        result = _a.sent();
                        if (result === 'need_bind') {
                            wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: '登录成功', icon: 'success' });
                        pending_1 = wx.getStorageSync('pendingWebLogin');
                        if (pending_1 && pending_1.sid && pending_1.nonce) {
                            setTimeout(function () {
                                wx.reLaunch({
                                    url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(pending_1.sid), "&nonce=").concat(encodeURIComponent(pending_1.nonce))
                                });
                            }, 600);
                            return [2 /*return*/];
                        }
                        // 跳转到首页，使用reLaunch确保页面重新加载
                        setTimeout(function () {
                            navigateAfterLogin();
                        }, 600);
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _a.sent();
                        console.error('登录失败:', err_2);
                        errorMsg = (err_2 && (err_2.message || err_2.errMsg)) || '登录失败，请稍后重试';
                        wx.showToast({
                            title: errorMsg,
                            icon: 'none',
                            duration: 3000
                        });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 手动登录按钮
    onLoginTap: function () {
        this.handleLogin();
    },
    onSwitchMode: function (e) {
        var mode = e.currentTarget.dataset.mode;
        if (mode !== 'wechat' && mode !== 'password' && mode !== 'email')
            return;
        this.setData({ mode: mode });
    },
    onUsernameInput: function (e) {
        this.setData({ username: e.detail.value || '' });
    },
    onPasswordInput: function (e) {
        this.setData({ password: e.detail.value || '' });
    },
    onEmailInput: function (e) {
        this.setData({ email: e.detail.value || '' });
    },
    onCodeInput: function (e) {
        this.setData({ code: e.detail.value || '' });
    },
    onPasswordLoginTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var username, password, isEmail, isPhone, data, pending_2, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        username = (this.data.username || '').trim();
                        password = this.data.password || '';
                        isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(username);
                        isPhone = /^1[3-9]\d{9}$/.test(username);
                        if (!username || !password) {
                            wx.showToast({ title: '请输入邮箱/手机号和密码', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (!isEmail && !isPhone) {
                            wx.showToast({ title: '仅支持邮箱或手机号登录', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, api_1.api.miniPasswordLogin(username, password)];
                    case 2:
                        data = _a.sent();
                        if (!data || !data.token)
                            throw new Error('登录返回异常');
                        wx.setStorageSync('token', data.token);
                        if (data.user_info)
                            wx.setStorageSync('userInfo', data.user_info);
                        return [4 /*yield*/, this.promptBindWechatIfNeeded(data)];
                    case 3:
                        _a.sent();
                        wx.showToast({ title: '登录成功', icon: 'success' });
                        pending_2 = wx.getStorageSync('pendingWebLogin');
                        if (pending_2 && pending_2.sid && pending_2.nonce) {
                            setTimeout(function () {
                                wx.reLaunch({
                                    url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(pending_2.sid), "&nonce=").concat(encodeURIComponent(pending_2.nonce))
                                });
                            }, 600);
                            return [2 /*return*/];
                        }
                        setTimeout(function () { return navigateAfterLogin(); }, 600);
                        return [3 /*break*/, 5];
                    case 4:
                        e_2 = _a.sent();
                        wx.showToast({ title: (e_2 && (e_2.message || e_2.errMsg)) || '登录失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onSendCodeTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var email, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.codeSending || this.data.loading)
                            return [2 /*return*/];
                        email = (this.data.email || '').trim();
                        if (!email) {
                            wx.showToast({ title: '请输入邮箱', icon: 'none' });
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.miniSendEmailLoginCode(email)];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '已发送', icon: 'success' });
                        this.startCountdown();
                        return [3 /*break*/, 4];
                    case 3:
                        e_3 = _a.sent();
                        wx.showToast({ title: (e_3 && (e_3.message || e_3.errMsg)) || '发送失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    startCountdown: function () {
        var _this = this;
        this.setData({ codeSending: true, countdown: 20 });
        var timer = setInterval(function () {
            var next = (_this.data.countdown || 0) - 1;
            if (next <= 0) {
                clearInterval(timer);
                _this.setData({ codeSending: false, countdown: 20 });
                return;
            }
            _this.setData({ countdown: next });
        }, 1000);
    },
    onEmailLoginTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var email, code, data, pending_3, e_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        email = (this.data.email || '').trim();
                        code = (this.data.code || '').trim();
                        if (!email || !code) {
                            wx.showToast({ title: '请输入邮箱和验证码', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, api_1.api.miniEmailLogin(email, code)];
                    case 2:
                        data = _a.sent();
                        if (!data || !data.token)
                            throw new Error('登录返回异常');
                        wx.setStorageSync('token', data.token);
                        if (data.user_info)
                            wx.setStorageSync('userInfo', data.user_info);
                        return [4 /*yield*/, this.promptBindWechatIfNeeded(data)];
                    case 3:
                        _a.sent();
                        wx.showToast({ title: '登录成功', icon: 'success' });
                        pending_3 = wx.getStorageSync('pendingWebLogin');
                        if (pending_3 && pending_3.sid && pending_3.nonce) {
                            setTimeout(function () {
                                wx.reLaunch({
                                    url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(pending_3.sid), "&nonce=").concat(encodeURIComponent(pending_3.nonce))
                                });
                            }, 600);
                            return [2 /*return*/];
                        }
                        setTimeout(function () { return navigateAfterLogin(); }, 600);
                        return [3 /*break*/, 5];
                    case 4:
                        e_4 = _a.sent();
                        wx.showToast({ title: (e_4 && (e_4.message || e_4.errMsg)) || '登录失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
