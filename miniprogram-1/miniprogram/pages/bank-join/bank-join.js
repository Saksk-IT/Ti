var api_1 = require("../../utils/api");
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
    var m = s.match(/[?&]token=([^&#]+)/i);
    if (m && m[1]) {
        try {
            return decodeURIComponent(m[1]);
        }
        catch (e) {
            return m[1];
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
        var _a;
        var rawToken = (options === null || options === void 0 ? void 0 : options.token) || (options === null || options === void 0 ? void 0 : options.share_token) || '';
        var token = normalizeTokenFromShareLink(rawToken);
        if (!token) {
            var scene = String((options === null || options === void 0 ? void 0 : options.scene) || '').trim();
            if (scene) {
                try {
                    token = normalizeTokenFromShareLink(decodeURIComponent(scene)) || normalizeTokenFromShareLink(scene);
                }
                catch (e) {
                    token = normalizeTokenFromShareLink(scene);
                }
            }
        }
        var shareCode = String(((_a = options) === null || _a === void 0 ? void 0 : _a.share_code) || (options === null || options === void 0 ? void 0 : options.code) || '').trim().toUpperCase();
        var mode = token ? 'token' : 'code';
        this.setData({ mode: mode, token: token, shareCode: shareCode });
        // 打开分享即加入，不再走“预览/确认”
        if (token) {
            this.autoJoinByToken(token);
            return;
        }
        if (shareCode && shareCode.length === 6) {
            this.joinByCode(shareCode);
        }
    },
    onShareCodeInput: function (e) {
        var v = String((e === null || e === void 0 ? void 0 : e.detail) && e.detail.value || '').trim().toUpperCase();
        this.setData({ shareCode: v, errorMsg: '' });
    },
    ensureLoggedIn: function (nextUrl) {
        if ((0, auth_1.checkLogin)())
            return Promise.resolve(true);
        setPendingMiniRedirect(nextUrl);
        return (0, auth_1.wechatLogin)().then(function (result) {
            if (result === 'success')
                return true;
            if (result === 'need_bind') {
                wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
                return false;
            }
            wx.redirectTo({ url: '/pages/login/login' });
            return false;
        }).catch(function () {
            wx.redirectTo({ url: '/pages/login/login' });
            return false;
        });
    },
    autoJoinByToken: function (token) {
        var _this = this;
        var t = String(token || '').trim();
        if (!t)
            return;
        if (this.data.loading)
            return;
        var nextUrl = "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(t));
        this.ensureLoggedIn(nextUrl).then(function (ok) {
            if (!ok)
                return;
            _this.setData({ loading: true, errorMsg: '' });
            wx.showLoading({ title: '加入中...' });
            api_1.api.joinBankByToken(t)
                .then(function (res) {
                var bankId = Number((res && res.bank_id) || 0);
                var bankName = String((res && res.bank_name) || '').trim();
                wx.showToast({ title: bankName ? "已加入「".concat(bankName, "」") : '已加入', icon: 'success' });
                clearPendingMiniRedirect();
                if (bankId > 0) {
                    (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
                }
                else {
                    (0, nav_1.safeNavigate)('/pages/my-banks/my-banks', 'switchTab');
                }
            })
                .catch(function (e) {
                var msg = (e && e.message) ? String(e.message) : '加入失败';
                _this.setData({ errorMsg: msg });
            })
                .finally(function () {
                wx.hideLoading();
                _this.setData({ loading: false });
            });
        });
    },
    joinByCode: function (code) {
        var _this = this;
        var c = String(code || '').trim().toUpperCase();
        if (!c || c.length !== 6) {
            wx.showToast({ title: '请输入6位分享码', icon: 'none' });
            return;
        }
        if (this.data.loading)
            return;
        var nextUrl = "/pages/bank-join/bank-join?share_code=".concat(encodeURIComponent(c));
        this.ensureLoggedIn(nextUrl).then(function (ok) {
            if (!ok)
                return;
            _this.setData({ loading: true, errorMsg: '' });
            wx.showLoading({ title: '加入中...' });
            api_1.api.joinBankByCode(c)
                .then(function (res) {
                var bankId = Number((res && res.bank_id) || 0);
                var bankName = String((res && res.bank_name) || '').trim();
                wx.showToast({ title: bankName ? "已加入「".concat(bankName, "」") : '已加入', icon: 'success' });
                clearPendingMiniRedirect();
                if (bankId > 0) {
                    (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
                }
                else {
                    (0, nav_1.safeNavigate)('/pages/my-banks/my-banks', 'switchTab');
                }
            })
                .catch(function (e) {
                var msg = (e && e.message) ? String(e.message) : '加入失败';
                _this.setData({ errorMsg: msg });
            })
                .finally(function () {
                wx.hideLoading();
                _this.setData({ loading: false });
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
