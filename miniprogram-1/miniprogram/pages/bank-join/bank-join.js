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
        catch (_a) {
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
    var _a, _b;
    var coverUrl = (0, api_endpoints_1.resolveUploadUrl)(raw === null || raw === void 0 ? void 0 : raw.cover_image);
    var joinMode = String((raw === null || raw === void 0 ? void 0 : raw.join_mode) || 'free').trim().toLowerCase() || 'free';
    var isJoined = !!((_a = raw === null || raw === void 0 ? void 0 : raw.relation) === null || _a === void 0 ? void 0 : _a.is_joined);
    return {
        id: Number((raw === null || raw === void 0 ? void 0 : raw.id) || 0) || 0,
        sourceType: sourceType,
        name: formatText(raw === null || raw === void 0 ? void 0 : raw.name, '未命名题库'),
        description: formatText(raw === null || raw === void 0 ? void 0 : raw.description, '暂无题库简介'),
        coverUrl: coverUrl,
        hasCover: !!coverUrl,
        sourceLabel: formatText(raw === null || raw === void 0 ? void 0 : raw.source_label, sourceType === 'system' ? '系统题库' : '用户公开'),
        ownerLabel: formatText(raw === null || raw === void 0 ? void 0 : raw.owner_label, sourceType === 'system' ? '系统题库' : '匿名用户'),
        boardLabel: formatText((_b = raw === null || raw === void 0 ? void 0 : raw.board) === null || _b === void 0 ? void 0 : _b.name, '未分板块'),
        questionCount: Number((raw === null || raw === void 0 ? void 0 : raw.question_count) || 0) || 0,
        participantsTotal: Number((raw === null || raw === void 0 ? void 0 : raw.participants_total) || 0) || 0,
        activeUsers7d: Number((raw === null || raw === void 0 ? void 0 : raw.answer_users_7d) || 0) || 0,
        publishedAt: formatText(raw === null || raw === void 0 ? void 0 : raw.published_at),
        lastActivityAt: formatText(raw === null || raw === void 0 ? void 0 : raw.last_activity_at),
        joinMode: joinMode,
        joinModeLabel: joinLabel(joinMode),
        joinNote: formatText(raw === null || raw === void 0 ? void 0 : raw.join_note, joinMode === 'free' ? '确认加入后，该题库会进入“我的题库”。' : '当前加入方式暂未在小程序开放。'),
        allowCopy: !!(raw === null || raw === void 0 ? void 0 : raw.allow_copy),
        isOwner: !!(raw === null || raw === void 0 ? void 0 : raw.is_owner),
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
        return __awaiter(this, void 0, void 0, function () {
            var sourceType, bankId, rawToken, token, scene, shareCode, mode;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        sourceType = normalizeSourceType((options === null || options === void 0 ? void 0 : options.source_type) || (options === null || options === void 0 ? void 0 : options.sourceType) || (options === null || options === void 0 ? void 0 : options.type));
                        bankId = Number((options === null || options === void 0 ? void 0 : options.bank_id) || (options === null || options === void 0 ? void 0 : options.bankId) || (options === null || options === void 0 ? void 0 : options.id) || 0);
                        if (!(Number.isFinite(bankId) && bankId > 0)) return [3 /*break*/, 2];
                        this.setData({ mode: 'public', sourceType: sourceType, bankId: bankId });
                        return [4 /*yield*/, this.loadPublicCard(sourceType, bankId)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
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
                        if (!token) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.autoJoinByToken(token)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                    case 4:
                        if (!(shareCode && shareCode.length === 6)) return [3 /*break*/, 6];
                        return [4 /*yield*/, this.joinByCode(shareCode)];
                    case 5:
                        _a.sent();
                        _a.label = 6;
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    loadPublicCard: function (sourceType, bankId) {
        return __awaiter(this, void 0, void 0, function () {
            var raw, card, e_1, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getPublicBankCard(sourceType, bankId)];
                    case 2:
                        raw = _a.sent();
                        card = buildPublicBankCard(raw, sourceType);
                        if (!card.id)
                            throw new Error('题库信息异常');
                        this.setData({ card: card, sourceType: sourceType, bankId: card.id });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        msg = (e_1 && e_1.message) ? String(e_1.message) : '加载失败';
                        this.setData({ errorMsg: msg, card: null });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
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
        return __awaiter(this, void 0, void 0, function () {
            var result, e_2;
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
                        e_2 = _a.sent();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [2 /*return*/, false];
                    case 4:
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [2 /*return*/, false];
                }
            });
        });
    },
    onConfirmPublicJoin: function () {
        return __awaiter(this, void 0, void 0, function () {
            var sourceType, bankId, card, nextUrl, ok, e_3, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.joining)
                            return [2 /*return*/];
                        sourceType = normalizeSourceType(this.data.sourceType);
                        bankId = Number(this.data.bankId || 0);
                        card = this.data.card;
                        if (!bankId || !card)
                            return [2 /*return*/];
                        if (card.isOwner || card.isJoined) {
                            this.goPublicPractice();
                            return [2 /*return*/];
                        }
                        if (card.joinMode !== 'free') {
                            wx.showToast({ title: "".concat(card.joinModeLabel, "\u6682\u672A\u5F00\u653E"), icon: 'none' });
                            return [2 /*return*/];
                        }
                        nextUrl = "/pages/bank-join/bank-join?source_type=".concat(encodeURIComponent(sourceType), "&bank_id=").concat(encodeURIComponent(String(bankId)));
                        return [4 /*yield*/, this.ensureLoggedIn(nextUrl)];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        this.setData({ joining: true, errorMsg: '' });
                        wx.showLoading({ title: '加入中...' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 5, 6, 7]);
                        return [4 /*yield*/, api_1.api.joinPublicBank(sourceType, bankId)];
                    case 3:
                        _a.sent();
                        wx.showToast({ title: '已加入', icon: 'success' });
                        return [4 /*yield*/, this.loadPublicCard(sourceType, bankId)];
                    case 4:
                        _a.sent();
                        return [3 /*break*/, 7];
                    case 5:
                        e_3 = _a.sent();
                        msg = (e_3 && e_3.message) ? String(e_3.message) : '加入失败';
                        this.setData({ errorMsg: msg });
                        wx.showToast({ title: msg, icon: 'none' });
                        return [3 /*break*/, 7];
                    case 6:
                        wx.hideLoading();
                        this.setData({ joining: false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
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
            if (card === null || card === void 0 ? void 0 : card.name)
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
        return __awaiter(this, void 0, void 0, function () {
            var t, nextUrl, ok, res, bankId, bankName, e_4, msg;
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
                            (0, nav_1.safeNavigate)(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
                        }
                        else {
                            (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                        }
                        return [3 /*break*/, 6];
                    case 4:
                        e_4 = _a.sent();
                        msg = (e_4 && e_4.message) ? String(e_4.message) : '加入失败';
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
            var c, nextUrl, ok, res, bankId, bankName, e_5, msg;
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
                            (0, nav_1.safeNavigate)(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
                        }
                        else {
                            (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'switchTab');
                        }
                        return [3 /*break*/, 6];
                    case 4:
                        e_5 = _a.sent();
                        msg = (e_5 && e_5.message) ? String(e_5.message) : '加入失败';
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
