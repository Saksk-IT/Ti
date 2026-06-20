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
var api_1 = require("../../../../utils/api");
var auth_1 = require("../../../../utils/auth");
var nav_1 = require("../../../../utils/nav");
var theme_1 = require("../../../../utils/theme");
var data_center_1 = require("../../utils/data-center");
var data_center_cache_1 = require("../../utils/data-center-cache");
function resolveDataTabUrl(tab) {
    var map = {
        global: '/packages/data/pages/data-global-v2/data-global-v2',
        bank: '/packages/data/pages/data-bank-v2/data-bank-v2',
        mistakes: '/packages/data/pages/data-mistakes-v2/data-mistakes-v2',
        favorites: '/packages/data/pages/data-favorites-v2/data-favorites-v2',
        tags: '/packages/data/pages/data-tags-v2/data-tags-v2'
    };
    return map[tab];
}
function clamp100(v) {
    var n = Number(v);
    if (!Number.isFinite(n))
        return 0;
    return Math.max(0, Math.min(100, n));
}
function buildMistakesViewData(res) {
    var allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
    var lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
    var lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
    var answeredCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.answered);
    var accuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
    var mistakesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
    var mistakesTimes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes_times);
    var mistakeRate = answeredCount > 0 ? (0, data_center_1.pct1)((mistakesTimes * 100) / answeredCount) : 0;
    var mistakeDepth = mistakesCount > 0 ? (0, data_center_1.pct1)((mistakesTimes * 100) / mistakesCount) : 0;
    var weaknessRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [];
    var weaknessRows = weaknessRaw.map(function (w) { return ({
        key: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), "__").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
        subject: String((w === null || w === void 0 ? void 0 : w.subject) || ''),
        q_type: String((w === null || w === void 0 ? void 0 : w.q_type) || ''),
        answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered),
        accuracy: (0, data_center_1.pct1)(clamp100(w === null || w === void 0 ? void 0 : w.accuracy)),
        mistakes: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.mistakes)
    }); });
    var subjectRows = Array.isArray(res === null || res === void 0 ? void 0 : res.subject_rows) ? res.subject_rows : [];
    var topSubjectsRaw = subjectRows
        .map(function (s) { return ({ name: String((s === null || s === void 0 ? void 0 : s.subject) || ''), total: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.mistakes) }); })
        .filter(function (x) { return x.total > 0; })
        .sort(function (a, b) { return b.total - a.total; })
        .slice(0, 10);
    var subMax = Math.max.apply(Math, __spreadArray([1], topSubjectsRaw.map(function (x) { return x.total; }), false));
    var topSubjectMistakes = topSubjectsRaw.map(function (x) { return ({
        key: "sub_".concat(x.name),
        name: x.name,
        total: x.total,
        barPct: (0, data_center_1.pct1)((x.total * 100) / subMax),
        meta: "\u9519\u9898 ".concat(x.total)
    }); });
    var bankRows = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_rows) ? res.bank_rows : [];
    var topBanksRaw = bankRows
        .map(function (b) { return ({
        bank_id: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.bank_id),
        name: String((b === null || b === void 0 ? void 0 : b.name) || ''),
        total: (0, data_center_1.toInt)((b === null || b === void 0 ? void 0 : b.mistakes_times) || (b === null || b === void 0 ? void 0 : b.mistakes))
    }); })
        .filter(function (x) { return x.total > 0; })
        .sort(function (a, b) { return b.total - a.total; })
        .slice(0, 10);
    var bankMax = Math.max.apply(Math, __spreadArray([1], topBanksRaw.map(function (x) { return x.total; }), false));
    var topBankMistakes = topBanksRaw.map(function (x) { return ({
        key: "bank_".concat(x.bank_id),
        name: x.name,
        total: x.total,
        barPct: (0, data_center_1.pct1)((x.total * 100) / bankMax),
        meta: "\u7D2F\u8BA1\u9519 ".concat(x.total, " \u6B21")
    }); });
    var recentRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.recent_mistakes) ? res.recent_mistakes : [];
    var recentMistakes = recentRaw.map(function (m, idx) { return ({
        key: "m_".concat(idx, "_").concat(String((m === null || m === void 0 ? void 0 : m.question_id) || '')),
        subject: String((m === null || m === void 0 ? void 0 : m.subject) || '未分类'),
        q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || '未知'),
        difficulty: (0, data_center_1.toInt)((m === null || m === void 0 ? void 0 : m.difficulty) || 1),
        snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || ''),
        wrong_count: (m === null || m === void 0 ? void 0 : m.wrong_count) == null ? null : (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.wrong_count)
    }); });
    return {
        inited: true,
        errorMsg: '',
        lastActivityText: lastActivityText,
        answeredCount: answeredCount,
        accuracy: accuracy,
        mistakesCount: mistakesCount,
        mistakesTimes: mistakesTimes,
        mistakeRate: mistakeRate,
        mistakeDepth: mistakeDepth,
        weaknessRows: weaknessRows,
        topSubjectMistakes: topSubjectMistakes,
        topBankMistakes: topBankMistakes,
        recentMistakes: recentMistakes
    };
}
Page({
    data: __assign(__assign({}, theme_1.themeManager.getPageData()), {
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        lastActivityText: '—',
        answeredCount: 0,
        accuracy: 0,
        mistakesCount: 0,
        mistakesTimes: 0,
        mistakeRate: 0,
        mistakeDepth: 0,
        weaknessRows: [],
        topSubjectMistakes: [],
        topBankMistakes: [],
        recentMistakes: []
    }),
    onLoad: function (options) {
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        var url = "/packages/data/pages/data-center-v2/data-center-v2?tab=mistakes&days=".concat(encodeURIComponent(String(days)));
        wx.redirectTo({
            url: url,
            fail: function () {
                this.setData({ days: days, window_days: days });
            }.bind(this)
        });
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
                    this.__lastLoadedAt = Date.now();
                    __assign(patch, buildMistakesViewData(cached));
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
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
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
        var raw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '');
        var tab = raw === 'global' || raw === 'bank' || raw === 'favorites' || raw === 'tags' ? raw : 'mistakes';
        var days = this.data.days;
        var base = resolveDataTabUrl(tab);
        (0, nav_1.safeNavigate)("".concat(base, "?days=").concat(encodeURIComponent(String(days))), 'redirectTo');
    },
    onGoQuiz: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var subject = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subject) || 'all');
        var type = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.type) || 'all');
        var source = String(((_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.source) || 'mistakes');
        var params = [];
        params.push("subject=".concat(encodeURIComponent(subject)));
        params.push('mode=quiz');
        params.push("source=".concat(encodeURIComponent(source)));
        if (type && type !== 'all')
            params.push("type=".concat(encodeURIComponent(type)));
        wx.navigateTo({ url: "/pages/quiz/quiz?".concat(params.join('&')) });
    },
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, res, allSummary, lastActivityRaw, lastActivityText, answeredCount, accuracy, mistakesCount, mistakesTimes, mistakeRate, mistakeDepth, weaknessRaw, weaknessRows, subjectRows, topSubjectsRaw, subMax_1, topSubjectMistakes, bankRows, topBanksRaw, bankMax_1, topBankMistakes, recentRaw, recentMistakes, e_1;
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
                        lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
                        lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
                        answeredCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.answered);
                        accuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
                        mistakesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
                        mistakesTimes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes_times);
                        mistakeRate = answeredCount > 0 ? (0, data_center_1.pct1)((mistakesTimes * 100) / answeredCount) : 0;
                        mistakeDepth = mistakesCount > 0 ? (0, data_center_1.pct1)((mistakesTimes * 100) / mistakesCount) : 0;
                        weaknessRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [];
                        weaknessRows = weaknessRaw.map(function (w) { return ({
                            key: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), "__").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
                            subject: String((w === null || w === void 0 ? void 0 : w.subject) || ''),
                            q_type: String((w === null || w === void 0 ? void 0 : w.q_type) || ''),
                            answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered),
                            accuracy: (0, data_center_1.pct1)(clamp100(w === null || w === void 0 ? void 0 : w.accuracy)),
                            mistakes: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.mistakes)
                        }); });
                        subjectRows = Array.isArray(res === null || res === void 0 ? void 0 : res.subject_rows) ? res.subject_rows : [];
                        topSubjectsRaw = subjectRows
                            .map(function (s) { return ({ name: String((s === null || s === void 0 ? void 0 : s.subject) || ''), total: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.mistakes) }); })
                            .filter(function (x) { return x.total > 0; })
                            .sort(function (a, b) { return b.total - a.total; })
                            .slice(0, 10);
                        subMax_1 = Math.max.apply(Math, __spreadArray([1], topSubjectsRaw.map(function (x) { return x.total; }), false));
                        topSubjectMistakes = topSubjectsRaw.map(function (x) { return ({
                            key: "sub_".concat(x.name),
                            name: x.name,
                            total: x.total,
                            barPct: (0, data_center_1.pct1)((x.total * 100) / subMax_1),
                            meta: "\u9519\u9898 ".concat(x.total)
                        }); });
                        bankRows = Array.isArray(res === null || res === void 0 ? void 0 : res.bank_rows) ? res.bank_rows : [];
                        topBanksRaw = bankRows
                            .map(function (b) { return ({
                            bank_id: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.bank_id),
                            name: String((b === null || b === void 0 ? void 0 : b.name) || ''),
                            total: (0, data_center_1.toInt)((b === null || b === void 0 ? void 0 : b.mistakes_times) || (b === null || b === void 0 ? void 0 : b.mistakes))
                        }); })
                            .filter(function (x) { return x.total > 0; })
                            .sort(function (a, b) { return b.total - a.total; })
                            .slice(0, 10);
                        bankMax_1 = Math.max.apply(Math, __spreadArray([1], topBanksRaw.map(function (x) { return x.total; }), false));
                        topBankMistakes = topBanksRaw.map(function (x) { return ({
                            key: "bank_".concat(x.bank_id),
                            name: x.name,
                            total: x.total,
                            barPct: (0, data_center_1.pct1)((x.total * 100) / bankMax_1),
                            meta: "\u7D2F\u8BA1\u9519 ".concat(x.total, " \u6B21")
                        }); });
                        recentRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.recent_mistakes) ? res.recent_mistakes : [];
                        recentMistakes = recentRaw.map(function (m, idx) { return ({
                            key: "m_".concat(idx, "_").concat(String((m === null || m === void 0 ? void 0 : m.question_id) || '')),
                            subject: String((m === null || m === void 0 ? void 0 : m.subject) || '未分类'),
                            q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || '未知'),
                            difficulty: (0, data_center_1.toInt)((m === null || m === void 0 ? void 0 : m.difficulty) || 1),
                            snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || ''),
                            wrong_count: (m === null || m === void 0 ? void 0 : m.wrong_count) == null ? null : (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.wrong_count)
                        }); });
                        this.setData({
                            inited: true,
                            lastActivityText: lastActivityText,
                            answeredCount: answeredCount,
                            accuracy: accuracy,
                            mistakesCount: mistakesCount,
                            mistakesTimes: mistakesTimes,
                            mistakeRate: mistakeRate,
                            mistakeDepth: mistakeDepth,
                            weaknessRows: weaknessRows,
                            topSubjectMistakes: topSubjectMistakes,
                            topBankMistakes: topBankMistakes,
                            recentMistakes: recentMistakes
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
