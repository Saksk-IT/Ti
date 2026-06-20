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
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var data_center_1 = require("../../packages/data/utils/data-center");
var data_center_cache_1 = require("../../packages/data/utils/data-center-cache");
function buildBanksPatch(res) {
    var allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
    var bankSummary = (res === null || res === void 0 ? void 0 : res.bank_summary) || {};
    var lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
    var lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
    var bankTotal = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.bank_total);
    var bankTotalQuestions = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.total_questions);
    var bankAnswered = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.answered);
    var bankAccuracy = (0, data_center_1.pct1)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.accuracy);
    var bankCompletion = (0, data_center_1.pct1)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.completion);
    var publicAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.answered_count);
    var publicAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.accuracy);
    var allAccuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
    var allFavorites = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.favorites);
    var allMistakes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
    var answeredTotal = publicAnswered + bankAnswered;
    var sharePublicPct = answeredTotal > 0 ? (0, data_center_1.pct1)((publicAnswered * 100) / answeredTotal) : 0;
    var shareBankPct = answeredTotal > 0 ? (0, data_center_1.pct1)((bankAnswered * 100) / answeredTotal) : 0;
    var catRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_category_rows) ? res.bank_category_rows : [];
    var catMax = Math.max.apply(Math, __spreadArray([1], catRaw.map(function (c) { return (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered); }), false));
    var categoryRows = catRaw.map(function (c) { return ({
        category_id: (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.category_id),
        category_name: String((c === null || c === void 0 ? void 0 : c.category_name) || '未分类'),
        answered: (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered),
        accuracy: (0, data_center_1.pct1)(c === null || c === void 0 ? void 0 : c.accuracy),
        barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered) * 100) / catMax)
    }); });
    var bankRows = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_rows) ? res.bank_rows : [];
    var topMax = Math.max.apply(Math, __spreadArray([1], bankRows.map(function (b) { return (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered); }), false));
    var bankTopRows = bankRows
        .map(function (b) { return ({
        bank_id: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.bank_id),
        name: String((b === null || b === void 0 ? void 0 : b.name) || ''),
        answered: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered),
        accuracy: (0, data_center_1.pct1)(b === null || b === void 0 ? void 0 : b.accuracy),
        barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered) * 100) / topMax)
    }); })
        .sort(function (a, b) { return b.answered - a.answered; })
        .slice(0, 10);
    return {
        inited: true,
        lastActivityText: lastActivityText,
        bankTotal: bankTotal,
        bankTotalQuestions: bankTotalQuestions,
        bankAnswered: bankAnswered,
        bankAccuracy: bankAccuracy,
        bankCompletion: bankCompletion,
        publicAnswered: publicAnswered,
        publicAccuracy: publicAccuracy,
        allAccuracy: allAccuracy,
        allFavorites: allFavorites,
        allMistakes: allMistakes,
        sharePublicPct: sharePublicPct,
        shareBankPct: shareBankPct,
        categoryRows: categoryRows,
        bankTopRows: bankTopRows,
        bankRows: bankRows
    };
}
Page({
    data: {
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        lastActivityText: '—',
        bankTotal: 0,
        bankTotalQuestions: 0,
        bankAnswered: 0,
        bankAccuracy: 0,
        bankCompletion: 0,
        publicAnswered: 0,
        publicAccuracy: 0,
        allAccuracy: 0,
        allFavorites: 0,
        allMistakes: 0,
        sharePublicPct: 0,
        shareBankPct: 0,
        categoryRows: [],
        bankTopRows: [],
        bankRows: []
    },
    onLoad: function (options) {
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        this.setData({ days: days });
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var patch = {};
        var hydrated = false;
        try {
            __assign(patch, theme_1.themeManager.getPageData());
        }
        catch (e) { }
        if (!this.data.inited) {
            try {
                var cached = (0, data_center_cache_1.getCachedDataCenter)(this.data.days);
                if (cached) {
                    __assign(patch, buildBanksPatch(cached), { errorMsg: '' });
                    this.__lastLoadedAt = Date.now();
                    hydrated = true;
                }
            }
            catch (e) { }
        }
        try {
            if (Object.keys(patch).length)
                this.setData(patch);
        }
        catch (e) { }
        if (!hydrated && !this.data.inited && !this.data.loading) {
            this.loadStats(true);
        }
    },
    onPullDownRefresh: function () {
        this.loadStats(true).finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    onDaysTap: function (e) {
        var _this = this;
        var _a, _b;
        var days = (0, data_center_1.normalizeDays)((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.days);
        if (days === this.data.days)
            return;
        this.setData({ days: days }, function () {
            _this.loadStats(true);
        });
    },
    onTabTap: function (e) {
        var _a, _b;
        var tab = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '');
        var days = this.data.days;
        var map = {
            overview: '/pages/history-v2/history-v2',
            banks: '/pages/data-banks-v2/data-banks-v2',
            trend: '/pages/data-trend-v2/data-trend-v2',
            ai: '/pages/data-ai-v2/data-ai-v2'
        };
        if (!map[tab])
            return;
        (0, nav_1.safeNavigate)("".concat(map[tab], "?days=").concat(days), 'reLaunch');
    },
    onGoBankPractice: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!bankId)
            return;
        wx.navigateTo({ url: "/pages/bank-detail/bank-detail?bank_id=".concat(bankId) });
    },
    onGoBankManage: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!bankId)
            return;
        wx.navigateTo({ url: "/pages/bank-detail/bank-detail?bank_id=".concat(bankId, "&tab=manage") });
    },
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, res, allSummary, bankSummary, lastActivityRaw, lastActivityText, bankTotal, bankTotalQuestions, bankAnswered, bankAccuracy, bankCompletion, publicAnswered, publicAccuracy, allAccuracy, allFavorites, allMistakes, answeredTotal, sharePublicPct, shareBankPct, catRaw, catMax_1, categoryRows, bankRows, topMax_1, bankTopRows, e_1;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 10000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataCenter(this.data.days)];
                    case 2:
                        res = _a.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(this.data.days, res);
                        }
                        catch (e) { }
                        allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
                        bankSummary = (res === null || res === void 0 ? void 0 : res.bank_summary) || {};
                        lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
                        lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
                        bankTotal = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.bank_total);
                        bankTotalQuestions = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.total_questions);
                        bankAnswered = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.answered);
                        bankAccuracy = (0, data_center_1.pct1)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.accuracy);
                        bankCompletion = (0, data_center_1.pct1)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.completion);
                        publicAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.answered_count);
                        publicAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.accuracy);
                        allAccuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
                        allFavorites = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.favorites);
                        allMistakes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
                        answeredTotal = publicAnswered + bankAnswered;
                        sharePublicPct = answeredTotal > 0 ? (0, data_center_1.pct1)((publicAnswered * 100) / answeredTotal) : 0;
                        shareBankPct = answeredTotal > 0 ? (0, data_center_1.pct1)((bankAnswered * 100) / answeredTotal) : 0;
                        catRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_category_rows) ? res.bank_category_rows : [];
                        catMax_1 = Math.max.apply(Math, __spreadArray([1], catRaw.map(function (c) { return (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered); }), false));
                        categoryRows = catRaw.map(function (c) { return ({
                            category_id: (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.category_id),
                            category_name: String((c === null || c === void 0 ? void 0 : c.category_name) || '未分类'),
                            answered: (0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered),
                            accuracy: (0, data_center_1.pct1)(c === null || c === void 0 ? void 0 : c.accuracy),
                            barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(c === null || c === void 0 ? void 0 : c.answered) * 100) / catMax_1)
                        }); });
                        bankRows = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_rows) ? res.bank_rows : [];
                        topMax_1 = Math.max.apply(Math, __spreadArray([1], bankRows.map(function (b) { return (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered); }), false));
                        bankTopRows = bankRows
                            .map(function (b) { return ({
                            bank_id: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.bank_id),
                            name: String((b === null || b === void 0 ? void 0 : b.name) || ''),
                            answered: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered),
                            accuracy: (0, data_center_1.pct1)(b === null || b === void 0 ? void 0 : b.accuracy),
                            barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered) * 100) / topMax_1)
                        }); })
                            .sort(function (a, b) { return b.answered - a.answered; })
                            .slice(0, 10);
                        this.setData({
                            inited: true,
                            lastActivityText: lastActivityText,
                            bankTotal: bankTotal,
                            bankTotalQuestions: bankTotalQuestions,
                            bankAnswered: bankAnswered,
                            bankAccuracy: bankAccuracy,
                            bankCompletion: bankCompletion,
                            publicAnswered: publicAnswered,
                            publicAccuracy: publicAccuracy,
                            allAccuracy: allAccuracy,
                            allFavorites: allFavorites,
                            allMistakes: allMistakes,
                            sharePublicPct: sharePublicPct,
                            shareBankPct: shareBankPct,
                            categoryRows: categoryRows,
                            bankTopRows: bankTopRows,
                            bankRows: bankRows
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '加载失败，请稍后再试。' });
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
