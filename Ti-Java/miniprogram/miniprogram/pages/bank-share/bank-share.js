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
// bank-share.ts - 个人题库分享设置页面
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        bankId: 0,
        bankInfo: {
            name: '',
            question_count: 0
        },
        shares: [],
        loading: false,
        wechatShareToken: '',
        wechatShareReady: false,
        wechatSharePreparing: false,
        showCodeModal: false,
        generatedCode: ''
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var bankId = Number(options.bank_id || 0);
        if (!bankId) {
            wx.showToast({ title: '题库参数缺失', icon: 'none' });
            setTimeout(function () { return wx.navigateBack(); }, 1500);
            return;
        }
        this.setData({ bankId: bankId });
        wx.showShareMenu({ withShareTicket: true });
        this.loadData();
    },
    loadData: function () {
        return __awaiter(this, void 0, void 0, function () {
            var results, detailRes, sharesRes, bankData, sharesData, shares, err_1;
            var _this = this;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        this.setData({ loading: true });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getBankDetail(this.data.bankId),
                                api_1.api.getBankShares(this.data.bankId)
                            ])];
                    case 2:
                        results = _c.sent();
                        detailRes = results[0];
                        sharesRes = results[1];
                        bankData = detailRes.data || detailRes || {};
                        sharesData = sharesRes.data || sharesRes || {};
                        shares = (sharesData.shares || [])
                            .filter(function (s) { return !!(s === null || s === void 0 ? void 0 : s.is_active); })
                            .map(function (s) {
                            return Object.assign({}, s, {
                                expires_at_display: s.expires_at ? _this.formatDate(s.expires_at) : ''
                            });
                        });
                        this.setData({
                            bankInfo: {
                                name: bankData.name || '未知题库',
                                question_count: bankData.question_count || 0
                            },
                            shares: shares,
                            loading: false,
                            wechatShareToken: this.pickShareTokenFromShares(shares),
                            wechatShareReady: !!this.pickShareTokenFromShares(shares)
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _c.sent();
                        console.error('加载数据失败:', err_1);
                        if (((_a = err_1.message) === null || _a === void 0 ? void 0 : _a.includes('401')) || ((_b = err_1.message) === null || _b === void 0 ? void 0 : _b.includes('登录'))) {
                            wx.reLaunch({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: err_1.message || '加载失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    isExpiredIso: function (expiresAt) {
        var s = String(expiresAt || '').trim();
        if (!s)
            return false;
        var d = new Date(s);
        var ts = d.getTime();
        return !Number.isFinite(ts) || ts < Date.now();
    },
    pickShareTokenFromShares: function (shares) {
        var list = Array.isArray(shares) ? shares : [];
        for (var _i = 0, list_1 = list; _i < list_1.length; _i++) {
            var s = list_1[_i];
            if (!s || !s.is_active)
                continue;
            var token = String(s.share_token || '').trim();
            if (!token)
                continue;
            if (s.expires_at && this.isExpiredIso(s.expires_at))
                continue;
            return token;
        }
        return '';
    },
    extractTokenFromShareLink: function (input) {
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
            catch (_a) {
                return m[1];
            }
        }
        return '';
    },
    ensureWechatShareToken: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var bankId, currentToken, token, created;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/, ''];
                        currentToken = String(this.data.wechatShareToken || '').trim();
                        if (!force && this.data.wechatShareReady && currentToken)
                            return [2 /*return*/, currentToken];
                        if (this.data.wechatSharePreparing)
                            return [2 /*return*/, currentToken];
                        this.setData({ wechatSharePreparing: true, wechatShareReady: false });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, , 7, 8]);
                        return [4 /*yield*/, this.loadData()];
                    case 2:
                        _a.sent();
                        token = String(this.data.wechatShareToken || '').trim();
                        if (!!token) return [3 /*break*/, 4];
                        return [4 /*yield*/, api_1.api.createBankShare(bankId, {
                                type: 'link',
                                permission: 'read',
                                expires_in: null
                            })];
                    case 3:
                        created = _a.sent();
                        token = String((created === null || created === void 0 ? void 0 : created.share_token) || '').trim() || this.extractTokenFromShareLink(created === null || created === void 0 ? void 0 : created.share_link);
                        _a.label = 4;
                    case 4:
                        this.setData({ wechatShareToken: token, wechatShareReady: !!token });
                        if (!token) return [3 /*break*/, 6];
                        return [4 /*yield*/, this.loadData()];
                    case 5:
                        _a.sent();
                        _a.label = 6;
                    case 6: return [2 /*return*/, token];
                    case 7:
                        this.setData({ wechatSharePreparing: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    formatDate: function (dateStr) {
        try {
            var date = new Date(dateStr);
            var month = String(date.getMonth() + 1).padStart(2, '0');
            var day = String(date.getDate()).padStart(2, '0');
            return "".concat(month, "-").concat(day);
        }
        catch (_a) {
            return '';
        }
    },
    onCreateShare: function (_e) {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, res, shareData, err_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = this.data.bankId;
                        wx.showLoading({ title: '创建中...' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createBankShare(bankId, {
                                type: 'code',
                                permission: 'read',
                                expires_in: null
                            })];
                    case 2:
                        res = _a.sent();
                        wx.hideLoading();
                        shareData = res.data || res || {};
                        if (shareData.share_code) {
                            this.setData({
                                showCodeModal: true,
                                generatedCode: shareData.share_code
                            });
                        }
                        // 刷新列表
                        this.loadData();
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _a.sent();
                        wx.hideLoading();
                        wx.showToast({ title: err_2.message || '创建失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onCloseCodeModal: function () {
        this.setData({ showCodeModal: false });
    },
    onCopyGeneratedCode: function () {
        var _this = this;
        wx.setClipboardData({
            data: this.data.generatedCode,
            success: function () {
                wx.showToast({ title: '已复制', icon: 'success' });
                _this.setData({ showCodeModal: false });
            }
        });
    },
    onCopyCode: function (e) {
        var code = e.currentTarget.dataset.code;
        if (!code) {
            wx.showToast({ title: '暂无分享码', icon: 'none' });
            return;
        }
        wx.setClipboardData({
            data: code,
            success: function () {
                wx.showToast({ title: '已复制', icon: 'success' });
            }
        });
    },
    onDeleteShare: function (e) {
        var _this = this;
        var shareId = e.currentTarget.dataset.id;
        wx.showModal({
            title: '确认撤销',
            content: '撤销后，使用此分享码加入的用户将无法继续访问',
            confirmColor: '#FF3B30',
            success: function (res) { return __awaiter(_this, void 0, void 0, function () {
                var err_3;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (!res.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '撤销中...' });
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.deleteBankShare(this.data.bankId, shareId)];
                        case 2:
                            _a.sent();
                            wx.hideLoading();
                            wx.showToast({ title: '已撤销', icon: 'success' });
                            this.loadData();
                            return [3 /*break*/, 4];
                        case 3:
                            err_3 = _a.sent();
                            wx.hideLoading();
                            wx.showToast({ title: err_3.message || '撤销失败', icon: 'none' });
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    onWechatShareTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var token, err_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.wechatSharePreparing)
                            return [2 /*return*/];
                        wx.showLoading({ title: '准备分享...' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, this.ensureWechatShareToken(false)];
                    case 2:
                        token = _a.sent();
                        if (!token)
                            throw new Error('微信分享准备失败');
                        wx.showToast({ title: '已准备好，请再次点击微信分享', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 3:
                        err_4 = _a.sent();
                        wx.showToast({ title: (err_4 && err_4.message) ? String(err_4.message) : '分享失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        wx.hideLoading();
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onShareAppMessage: function () {
        var bankInfo = this.data.bankInfo;
        var token = String(this.data.wechatShareToken || '').trim();
        return {
            title: "\u9080\u8BF7\u4F60\u52A0\u5165\u9898\u5E93\uFF1A".concat(bankInfo.name),
            path: token
                ? "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(token))
                : '/pages/my-banks-v2/my-banks-v2'
        };
    }
});
