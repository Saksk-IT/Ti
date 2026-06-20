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
function pickDaily(res) {
    if (Array.isArray(res === null || res === void 0 ? void 0 : res.all_daily) && res.all_daily.length)
        return res.all_daily;
    if (Array.isArray(res === null || res === void 0 ? void 0 : res.daily) && res.daily.length)
        return res.daily;
    return [];
}
function buildHistoryPatch(res) {
    var _a, _b, _c, _d;
    var allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
    var bankSummary = (res === null || res === void 0 ? void 0 : res.bank_summary) || {};
    var totalQuestions = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.total_questions);
    var answeredCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.answered);
    var correctCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.correct);
    var accuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
    var completion = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.completion);
    var favoritesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.favorites);
    var mistakesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
    var mistakesTimes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes_times);
    var streakDays = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.streak_days);
    var lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
    var lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
    var publicAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.answered_count);
    var bankAnswered = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.answered);
    var windowAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.window_answered);
    var windowAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.window_accuracy);
    var dailySource = pickDaily(res);
    var dailyMax = Math.max((0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.all_daily_max), (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.daily_max), 1);
    var trendBars = (0, data_center_1.buildTrendBars)(dailySource, dailyMax);
    var heatmapRows = (0, data_center_1.buildHeatmapGrid)((_a = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _a === void 0 ? void 0 : _a.all, (_b = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _b === void 0 ? void 0 : _b.max);
    var abilityList = (Array.isArray(res === null || res === void 0 ? void 0 : res.ability_radar) ? res.ability_radar : []).map(function (a) { return ({
        name: String((a === null || a === void 0 ? void 0 : a.name) || ''),
        value: (0, data_center_1.pct1)(a === null || a === void 0 ? void 0 : a.value)
    }); });
    var topMixRaw = (0, data_center_1.buildTopMix)((res === null || res === void 0 ? void 0 : res.subject_rows) || [], (res === null || res === void 0 ? void 0 : res.bank_rows) || [], 8);
    var topMax = Math.max.apply(Math, __spreadArray([1], topMixRaw.map(function (it) { return (0, data_center_1.toInt)(it.answered); }), false));
    var topMix = topMixRaw.map(function (it) { return ({
        name: it.name,
        answered: (0, data_center_1.toInt)(it.answered),
        accuracy: (0, data_center_1.pct1)(it.accuracy),
        barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(it.answered) * 100) / topMax)
    }); });
    var nextActions = Array.isArray(res === null || res === void 0 ? void 0 : res.next_actions) ? res.next_actions : [];
    var weaknessRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [];
    var weaknessRows = weaknessRaw.map(function (w) { return ({
        key: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), "__").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
        subject: String((w === null || w === void 0 ? void 0 : w.subject) || ''),
        q_type: String((w === null || w === void 0 ? void 0 : w.q_type) || ''),
        answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered),
        accuracy: (0, data_center_1.pct1)(w === null || w === void 0 ? void 0 : w.accuracy)
    }); });
    return {
        inited: true,
        totalQuestions: totalQuestions,
        answeredCount: answeredCount,
        correctCount: correctCount,
        accuracy: accuracy,
        completion: completion,
        favoritesCount: favoritesCount,
        mistakesCount: mistakesCount,
        mistakesTimes: mistakesTimes,
        streakDays: streakDays,
        lastActivityText: lastActivityText,
        publicAnswered: publicAnswered,
        bankAnswered: bankAnswered,
        windowAnswered: windowAnswered,
        windowAccuracy: windowAccuracy,
        trendBars: trendBars,
        heatmapRows: heatmapRows,
        abilityList: abilityList,
        topMix: topMix,
        nextActions: nextActions,
        weaknessRows: weaknessRows
    };
}
Page({
    data: {
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        activeTab: 'overview',
        totalQuestions: 0,
        answeredCount: 0,
        correctCount: 0,
        accuracy: 0,
        completion: 0,
        favoritesCount: 0,
        mistakesCount: 0,
        mistakesTimes: 0,
        streakDays: 0,
        lastActivityText: '—',
        publicAnswered: 0,
        bankAnswered: 0,
        windowAnswered: 0,
        windowAccuracy: 0,
        trendBars: [],
        heatmapRows: [],
        abilityList: [],
        topMix: [],
        nextActions: [],
        weaknessRows: []
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
                    __assign(patch, buildHistoryPatch(cached), { errorMsg: '' });
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
    onDayBarTap: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var day = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.day) || '');
        var total = (0, data_center_1.toInt)((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.total);
        var accuracy = (0, data_center_1.pct1)((_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.accuracy);
        if (!day)
            return;
        wx.showToast({ title: "".concat(day, "\uFF1A").concat(total, "\u9898\uFF0C\u6B63\u786E\u7387 ").concat(accuracy, "%"), icon: 'none' });
    },
    onGoQuiz: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var subject = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subject) || 'all');
        var type = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.type) || 'all');
        var source = String(((_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.source) || 'all');
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
            var self, now, lastAt, res, allSummary, bankSummary, totalQuestions, answeredCount, correctCount, accuracy, completion, favoritesCount, mistakesCount, mistakesTimes, streakDays, lastActivityRaw, lastActivityText, publicAnswered, bankAnswered, windowAnswered, windowAccuracy, dailySource, dailyMax, trendBars, heatmapRows, abilityList, topMixRaw, topMax_1, topMix, nextActions, weaknessRaw, weaknessRows, e_1;
            var _a, _b;
            if (force === void 0) { force = false; }
            return __generator(this, function (_c) {
                switch (_c.label) {
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
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataCenter(this.data.days)];
                    case 2:
                        res = _c.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(this.data.days, res);
                        }
                        catch (e) { }
                        allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
                        bankSummary = (res === null || res === void 0 ? void 0 : res.bank_summary) || {};
                        totalQuestions = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.total_questions);
                        answeredCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.answered);
                        correctCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.correct);
                        accuracy = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.accuracy);
                        completion = (0, data_center_1.pct1)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.completion);
                        favoritesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.favorites);
                        mistakesCount = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes);
                        mistakesTimes = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.mistakes_times);
                        streakDays = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.streak_days);
                        lastActivityRaw = (allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity) ? String(allSummary.last_activity) : '';
                        lastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 10) : '—';
                        publicAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.answered_count);
                        bankAnswered = (0, data_center_1.toInt)(bankSummary === null || bankSummary === void 0 ? void 0 : bankSummary.answered);
                        windowAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.window_answered);
                        windowAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.window_accuracy);
                        dailySource = pickDaily(res);
                        dailyMax = Math.max((0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.all_daily_max), (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.daily_max), 1);
                        trendBars = (0, data_center_1.buildTrendBars)(dailySource, dailyMax);
                        heatmapRows = (0, data_center_1.buildHeatmapGrid)((_a = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _a === void 0 ? void 0 : _a.all, (_b = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _b === void 0 ? void 0 : _b.max);
                        abilityList = (Array.isArray(res === null || res === void 0 ? void 0 : res.ability_radar) ? res.ability_radar : []).map(function (a) { return ({
                            name: String((a === null || a === void 0 ? void 0 : a.name) || ''),
                            value: (0, data_center_1.pct1)(a === null || a === void 0 ? void 0 : a.value)
                        }); });
                        topMixRaw = (0, data_center_1.buildTopMix)((res === null || res === void 0 ? void 0 : res.subject_rows) || [], (res === null || res === void 0 ? void 0 : res.bank_rows) || [], 8);
                        topMax_1 = Math.max.apply(Math, __spreadArray([1], topMixRaw.map(function (it) { return (0, data_center_1.toInt)(it.answered); }), false));
                        topMix = topMixRaw.map(function (it) { return ({
                            name: it.name,
                            answered: (0, data_center_1.toInt)(it.answered),
                            accuracy: (0, data_center_1.pct1)(it.accuracy),
                            barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(it.answered) * 100) / topMax_1)
                        }); });
                        nextActions = Array.isArray(res === null || res === void 0 ? void 0 : res.next_actions) ? res.next_actions : [];
                        weaknessRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [];
                        weaknessRows = weaknessRaw.map(function (w) { return ({
                            key: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), "__").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
                            subject: String((w === null || w === void 0 ? void 0 : w.subject) || ''),
                            q_type: String((w === null || w === void 0 ? void 0 : w.q_type) || ''),
                            answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered),
                            accuracy: (0, data_center_1.pct1)(w === null || w === void 0 ? void 0 : w.accuracy)
                        }); });
                        this.setData({
                            inited: true,
                            totalQuestions: totalQuestions,
                            answeredCount: answeredCount,
                            correctCount: correctCount,
                            accuracy: accuracy,
                            completion: completion,
                            favoritesCount: favoritesCount,
                            mistakesCount: mistakesCount,
                            mistakesTimes: mistakesTimes,
                            streakDays: streakDays,
                            lastActivityText: lastActivityText,
                            publicAnswered: publicAnswered,
                            bankAnswered: bankAnswered,
                            windowAnswered: windowAnswered,
                            windowAccuracy: windowAccuracy,
                            trendBars: trendBars,
                            heatmapRows: heatmapRows,
                            abilityList: abilityList,
                            topMix: topMix,
                            nextActions: nextActions,
                            weaknessRows: weaknessRows
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _c.sent();
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
