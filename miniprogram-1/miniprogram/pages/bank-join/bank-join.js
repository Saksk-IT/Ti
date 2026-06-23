"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var api_endpoints_1 = require("../../utils/api-endpoints");
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
        catch (e) {
            return tokenMatch[1];
        }
    }
    return '';
}

function normalizeSourceType(input) {
    return String(input || '').trim() === 'system' ? 'system' : 'user';
}

function joinedBankDetailUrl(bankId, source) {
    var id = encodeURIComponent(String(bankId));
    return "/pages/bank-detail/bank-detail?id=".concat(id, "&source_type=user&source=").concat(source, "&relation=").concat(source);
}

function joinLabel(mode) {
    var value = String(mode || 'free').trim().toLowerCase();
    if (value === 'member')
        return '会员加入';
    if (value === 'paid')
        return '付费加入';
    if (value === 'approval')
        return '申请加入';
    return '免费加入';
}

function formatText(input, fallback) {
    if (fallback === void 0) { fallback = '-'; }
    var raw = String(input || '').trim();
    return raw || fallback;
}

function buildPublicBankCard(raw, sourceType) {
    var coverUrl = (0, api_endpoints_1.resolveUploadUrl)(raw && raw.cover_image);
    var joinMode = String((raw && raw.join_mode) || 'free').trim().toLowerCase() || 'free';
    var isJoined = !!(raw && raw.relation && raw.relation.is_joined);
    return {
        id: Number((raw && raw.id) || 0) || 0,
        sourceType: sourceType,
        name: formatText(raw && raw.name, '未命名题库'),
        description: formatText(raw && raw.description, '暂无题库简介'),
        coverUrl: coverUrl,
        hasCover: !!coverUrl,
        sourceLabel: formatText(raw && raw.source_label, sourceType === 'system' ? '系统题库' : '用户公开'),
        ownerLabel: formatText(raw && raw.owner_label, sourceType === 'system' ? '系统题库' : '匿名用户'),
        boardLabel: formatText(raw && raw.board && raw.board.name, '未分板块'),
        questionCount: Number((raw && raw.question_count) || 0) || 0,
        participantsTotal: Number((raw && raw.participants_total) || 0) || 0,
        activeUsers7d: Number((raw && raw.answer_users_7d) || 0) || 0,
        publishedAt: formatText(raw && raw.published_at),
        lastActivityAt: formatText(raw && raw.last_activity_at),
        joinMode: joinMode,
        joinModeLabel: joinLabel(joinMode),
        joinNote: formatText(raw && raw.join_note, joinMode === 'free' ? '确认加入后，该题库会进入“我的题库”。' : '当前加入方式暂未在小程序开放。'),
        allowCopy: !!(raw && raw.allow_copy),
        isOwner: !!(raw && raw.is_owner),
        isJoined: isJoined
    };
}

Page({
    data: {
        mode: 'code',
        token: '',
        shareCode: '',
        sourceType: 'user',
        bankId: 0,
        card: null,
        loading: false,
        joining: false,
        errorMsg: ''
    },

    onLoad: function (options) {
        var _this = this;
        var sourceType = normalizeSourceType((options && (options.source_type || options.sourceType || options.type)) || '');
        var bankId = Number((options && (options.bank_id || options.bankId || options.id)) || 0);
        if (Number.isFinite(bankId) && bankId > 0) {
            this.setData({ mode: 'public', sourceType: sourceType, bankId: bankId });
            this.loadPublicCard(sourceType, bankId);
            return;
        }

        var rawToken = (options && (options.token || options.share_token)) || '';
        var token = normalizeTokenFromShareLink(rawToken);
        if (!token) {
            var scene = String((options && options.scene) || '').trim();
            if (scene) {
                try {
                    token = normalizeTokenFromShareLink(decodeURIComponent(scene)) || normalizeTokenFromShareLink(scene);
                }
                catch (e) {
                    token = normalizeTokenFromShareLink(scene);
                }
            }
        }
        var shareCode = String((options && (options.share_code || options.code)) || '').trim().toUpperCase();
        var mode = token ? 'token' : 'code';
        this.setData({ mode: mode, token: token, shareCode: shareCode });
        if (token) {
            this.autoJoinByToken(token);
            return;
        }
        if (shareCode && shareCode.length === 6) {
            this.joinByCode(shareCode);
        }
    },

    loadPublicCard: function (sourceType, bankId) {
        var _this = this;
        if (this.data.loading)
            return;
        this.setData({ loading: true, errorMsg: '' });
        api_1.api.getPublicBankCard(sourceType, bankId).then(function (raw) {
            var card = buildPublicBankCard(raw, sourceType);
            if (!card.id)
                throw new Error('题库信息异常');
            _this.setData({ card: card, sourceType: sourceType, bankId: card.id });
        }).catch(function (e) {
            var msg = (e && e.message) ? String(e.message) : '加载失败';
            _this.setData({ errorMsg: msg, card: null });
        }).finally(function () {
            _this.setData({ loading: false });
        });
    },

    onShareCodeInput: function (e) {
        var v = String((e && e.detail && e.detail.value) || '').trim().toUpperCase();
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

    onConfirmPublicJoin: function () {
        var _this = this;
        if (this.data.joining)
            return;
        var sourceType = normalizeSourceType(this.data.sourceType);
        var bankId = Number(this.data.bankId || 0);
        var card = this.data.card;
        if (!bankId || !card)
            return;
        if (card.isOwner || card.isJoined) {
            this.goPublicPractice();
            return;
        }
        if (card.joinMode !== 'free') {
            wx.showToast({ title: "".concat(card.joinModeLabel, "\u6682\u672A\u5F00\u653E"), icon: 'none' });
            return;
        }
        var nextUrl = "/pages/bank-join/bank-join?source_type=".concat(encodeURIComponent(sourceType), "&bank_id=").concat(encodeURIComponent(String(bankId)));
        this.ensureLoggedIn(nextUrl).then(function (ok) {
            if (!ok)
                return;
            _this.setData({ joining: true, errorMsg: '' });
            wx.showLoading({ title: '加入中...' });
            return api_1.api.joinPublicBank(sourceType, bankId).then(function () {
                wx.showToast({ title: '已加入', icon: 'success' });
                _this.loadPublicCard(sourceType, bankId);
            }).catch(function (e) {
                var msg = (e && e.message) ? String(e.message) : '加入失败';
                _this.setData({ errorMsg: msg });
                wx.showToast({ title: msg, icon: 'none' });
            }).finally(function () {
                wx.hideLoading();
                _this.setData({ joining: false });
            });
        });
    },

    goPublicPractice: function () {
        var sourceType = normalizeSourceType(this.data.sourceType);
        var bankId = Number(this.data.bankId || 0);
        var card = this.data.card;
        if (!bankId)
            return;
        if (sourceType === 'system') {
            var params = ["id=".concat(encodeURIComponent(String(bankId)))];
            if (card && card.name)
                params.push("subject=".concat(encodeURIComponent(card.name)));
            (0, nav_1.safeNavigate)("/pages/subject-detail-v2/subject-detail-v2?".concat(params.join('&')), 'redirectTo');
            return;
        }
    (0, nav_1.safeNavigate)(joinedBankDetailUrl(bankId, 'public'), 'redirectTo');
    },

    onPublicRetry: function () {
        var sourceType = normalizeSourceType(this.data.sourceType);
        var bankId = Number(this.data.bankId || 0);
        if (!bankId)
            return;
        this.loadPublicCard(sourceType, bankId);
    },

    autoJoinByToken: function (token) {
        var _this = this;
        var t = String(token || '').trim();
        if (!t || this.data.loading)
            return;
        var nextUrl = "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(t));
        this.ensureLoggedIn(nextUrl).then(function (ok) {
            if (!ok)
                return;
            _this.setData({ loading: true, errorMsg: '' });
            wx.showLoading({ title: '加入中...' });
            return api_1.api.joinBankByToken(t).then(function (res) {
                var bankId = Number((res && res.bank_id) || 0);
                var bankName = String((res && res.bank_name) || '').trim();
                wx.showToast({ title: bankName ? "\u5DF2\u52A0\u5165\u300C".concat(bankName, "\u300D") : '已加入', icon: 'success' });
                clearPendingMiniRedirect();
                if (bankId > 0) {
                    (0, nav_1.safeNavigate)(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
                }
                else {
                    (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                }
            }).catch(function (e) {
                var msg = (e && e.message) ? String(e.message) : '加入失败';
                _this.setData({ errorMsg: msg });
            }).finally(function () {
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
            return api_1.api.joinBankByCode(c).then(function (res) {
                var bankId = Number((res && res.bank_id) || 0);
                var bankName = String((res && res.bank_name) || '').trim();
                wx.showToast({ title: bankName ? "\u5DF2\u52A0\u5165\u300C".concat(bankName, "\u300D") : '已加入', icon: 'success' });
                clearPendingMiniRedirect();
                if (bankId > 0) {
                    (0, nav_1.safeNavigate)(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
                }
                else {
                    (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                }
            }).catch(function (e) {
                var msg = (e && e.message) ? String(e.message) : '加入失败';
                _this.setData({ errorMsg: msg });
            }).finally(function () {
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
        if (this.data.mode === 'public') {
            this.onPublicRetry();
            return;
        }
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
