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
function normalizeDays(input) {
    var n = Number(input || 14);
    if (n === 7 || n === 14 || n === 30 || n === 90)
        return n;
    return 14;
}
function clampPct(v) {
    if (!Number.isFinite(v))
        return 0;
    return Math.max(0, Math.min(100, v));
}
function formatDateTime(raw) {
    var s = String(raw || '').trim();
    if (!s)
        return '-';
    try {
        var iso = s.includes('T') ? s : s.replace(' ', 'T');
        var d = new Date(iso);
        if (isNaN(d.getTime()))
            return s;
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        return "".concat(y, "-").concat(m, "-").concat(day, " ").concat(hh, ":").concat(mm);
    }
    catch (_a) {
        return s;
    }
}
Page({
    data: {
        inited: false,
        loading: false,
        subjectId: 0,
        subjectName: '',
        dataSubTab: 'favorites',
        detailTab: 'stats',
        statsDays: 14,
        statsLoadedDays: 0,
        statsLoading: false,
        statsError: '',
        statsOverview: {
            total: 0,
            answered: 0,
            correct: 0,
            wrong: 0,
            favorites: 0,
            mistakes: 0,
            mistakeTimes: 0,
            accuracy: 0,
            completion: 0,
            accuracyText: '0.0%',
            completionText: '0.0%',
            streakDays: 0,
            lastText: '-'
        },
        statsTrend: [],
        statsByType: [],
        statsAdvice: [],
        ringAccuracy: 0,
        ringCompletion: 0,
        ringActive: 0,
        activeDaysRate: 0,
        favMistakeRateText: '0%',
        heatCells: [],
        displayTypes: []
    },
    onLoad: function (options) {
        var _a, _b;
        var sidRaw = (_b = (_a = options === null || options === void 0 ? void 0 : options.id) !== null && _a !== void 0 ? _a : options === null || options === void 0 ? void 0 : options.subject_id) !== null && _b !== void 0 ? _b : options === null || options === void 0 ? void 0 : options.subjectId;
        var subjectId = Number(sidRaw || 0);
        var subjectName = (options === null || options === void 0 ? void 0 : options.subject) ? String(options.subject) : '';
        if (subjectName) {
            try {
                subjectName = decodeURIComponent(subjectName);
            }
            catch (e) { }
        }
        var days = normalizeDays(options === null || options === void 0 ? void 0 : options.days);
        this.setData({
            subjectId: Number.isFinite(subjectId) ? subjectId : 0,
            subjectName: subjectName,
            statsDays: days
        });
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        if (!this.data.inited && !this.data.loading) {
            this.bootstrap();
        }
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onDetailTabTap: function (e) {
        var _a, _b, _c, _d;
        var raw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || 'practice').trim().toLowerCase();
        var tab = raw === 'exam' || raw === 'search' || raw === 'share'
            ? raw
            : raw === 'stats'
                ? 'stats'
                : 'practice';
        if (tab === 'stats')
            return;
        var subjectId = Number(this.data.subjectId || 0);
        var subject = String(this.data.subjectName || '').trim();
        var params = [];
        if (subjectId)
            params.push("id=".concat(encodeURIComponent(String(subjectId))));
        if (subject)
            params.push("subject=".concat(encodeURIComponent(subject)));
        var pages = getCurrentPages();
        var prev = pages.length >= 2 ? pages[pages.length - 2] : null;
        var prevRoute = prev === null || prev === void 0 ? void 0 : prev.route;
        var prevId = Number(((_c = prev === null || prev === void 0 ? void 0 : prev.data) === null || _c === void 0 ? void 0 : _c.subjectId) || 0);
        var prevName = String(((_d = prev === null || prev === void 0 ? void 0 : prev.data) === null || _d === void 0 ? void 0 : _d.subjectName) || '').trim();
        var returnKey = subjectId ? "subject_".concat(subjectId, "_return_tab") : subject ? "subject_".concat(subject, "_return_tab") : '';
        if (returnKey && prevRoute === 'pages/subject-detail-v2/subject-detail-v2' && ((subjectId && prevId === subjectId) || (subject && prevName === subject))) {
            try {
                wx.setStorageSync(returnKey, tab);
            }
            catch (err) { }
            wx.navigateBack({ delta: 1 });
            return;
        }
        if (returnKey) {
            try {
                wx.setStorageSync(returnKey, '');
            }
            catch (err) { }
        }
        var url = params.length
            ? "/pages/subject-detail-v2/subject-detail-v2?".concat(params.join('&'), "&tab=").concat(encodeURIComponent(tab))
            : "/pages/subject-detail-v2/subject-detail-v2?tab=".concat(encodeURIComponent(tab));
        (0, nav_1.safeNavigate)(url, 'redirectTo');
    },
    onDataTabTap: function (e) {
        var _a, _b;
        var raw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subtab) || 'global');
        var subtab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
        if (subtab === this.data.dataSubTab)
            return;
        var subjectId = Number(this.data.subjectId || 0);
        var subject = String(this.data.subjectName || '').trim();
        var params = [];
        if (subjectId)
            params.push("id=".concat(encodeURIComponent(String(subjectId))));
        if (subject)
            params.push("subject=".concat(encodeURIComponent(subject)));
        var days = Number(this.data.statsDays || 14) || 14;
        if ([7, 14, 30, 90].includes(days))
            params.push("days=".concat(encodeURIComponent(String(days))));
        var base = subtab === 'mistakes'
            ? '/pages/subject-data-mistakes/subject-data-mistakes'
            : subtab === 'favorites'
                ? '/pages/subject-data-favorites/subject-data-favorites'
                : '/pages/subject-data-global/subject-data-global';
        var url = params.length ? "".concat(base, "?").concat(params.join('&')) : base;
        (0, nav_1.safeNavigate)(url, 'redirectTo');
    },
    onStatsDaysTap: function (e) {
        var _this = this;
        var _a, _b;
        var days = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.days) || 14);
        if (![7, 14, 30, 90].includes(days))
            return;
        if (days === this.data.statsDays)
            return;
        this.setData({ statsDays: days, statsLoadedDays: 0 }, function () { return _this.loadStatsDetail(days); });
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, 5, 6]);
                        return [4 /*yield*/, this.resolveSubject()];
                    case 2:
                        _a.sent();
                        this.setData({ inited: true });
                        return [4 /*yield*/, this.loadStatsDetail(this.data.statsDays)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        e_1 = _a.sent();
                        wx.showToast({ title: (e_1 && e_1.message) ? String(e_1.message) : '数据加载失败', icon: 'none' });
                        return [3 /*break*/, 6];
                    case 5:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    resolveSubject: function () {
        return __awaiter(this, void 0, void 0, function () {
            var subjectName, subjectId, meta, metaObj, subjects, subject;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        subjectName = String(this.data.subjectName || '').trim();
                        subjectId = Number(this.data.subjectId || 0);
                        if (subjectName)
                            return [2 /*return*/];
                        if (!subjectId) {
                            throw new Error('缺少题库信息');
                        }
                        return [4 /*yield*/, api_1.api.getSubjectsMeta()];
                    case 1:
                        meta = _a.sent();
                        metaObj = (meta && typeof meta === 'object' ? meta : {});
                        subjects = Array.isArray(metaObj === null || metaObj === void 0 ? void 0 : metaObj.subjects) ? metaObj.subjects : [];
                        subject = subjects.find(function (s) { return Number(s === null || s === void 0 ? void 0 : s.id) === subjectId; });
                        if (!subject)
                            throw new Error('题库不存在或无权限');
                        this.setData({ subjectName: String((subject === null || subject === void 0 ? void 0 : subject.name) || '').trim() });
                        return [2 /*return*/];
                }
            });
        });
    },
    buildStatsView: function (data) {
        var total = Number((data === null || data === void 0 ? void 0 : data.total_count) || 0) || 0;
        var answered = Number((data === null || data === void 0 ? void 0 : data.answered) || 0) || 0;
        var correct = Number((data === null || data === void 0 ? void 0 : data.correct) || 0) || 0;
        var wrong = Number((data === null || data === void 0 ? void 0 : data.wrong) || 0) || 0;
        var favorites = Number((data === null || data === void 0 ? void 0 : data.favorites) || 0) || 0;
        var mistakes = Number((data === null || data === void 0 ? void 0 : data.mistakes) || 0) || 0;
        var mistakeTimes = Number((data === null || data === void 0 ? void 0 : data.mistakes_times) || 0) || 0;
        var accuracy = Number((data === null || data === void 0 ? void 0 : data.accuracy) || 0) || 0;
        var completion = Number((data === null || data === void 0 ? void 0 : data.completion) || 0) || 0;
        var streakDays = Number((data === null || data === void 0 ? void 0 : data.streak_days) || 0) || 0;
        var lastText = formatDateTime(data === null || data === void 0 ? void 0 : data.last_activity);
        var overview = {
            total: total,
            answered: answered,
            correct: correct,
            wrong: wrong,
            favorites: favorites,
            mistakes: mistakes,
            mistakeTimes: mistakeTimes,
            accuracy: accuracy,
            completion: completion,
            accuracyText: "".concat(accuracy.toFixed(1), "%"),
            completionText: "".concat(completion.toFixed(1), "%"),
            streakDays: streakDays,
            lastText: lastText
        };
        var rawTrend = Array.isArray(data === null || data === void 0 ? void 0 : data.trend) ? data.trend : [];
        var maxAnswered = rawTrend.reduce(function (m, it) { return Math.max(m, Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0); }, 0) || 0;
        var trend = rawTrend.map(function (it) {
            var day = String((it === null || it === void 0 ? void 0 : it.day) || '');
            var label = day ? day.slice(5) : '';
            var a = Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0;
            var c = Number((it === null || it === void 0 ? void 0 : it.correct) || 0) || 0;
            var w = Number((it === null || it === void 0 ? void 0 : it.wrong) || 0) || Math.max(0, a - c);
            var answeredPct = maxAnswered > 0 ? clampPct((a / maxAnswered) * 100) : 0;
            var correctPctInAnswered = a > 0 ? clampPct((Math.min(a, c) / a) * 100) : 0;
            return { day: day, label: label, answered: a, correct: Math.min(a, c), wrong: w, answeredPct: answeredPct, correctPctInAnswered: correctPctInAnswered };
        });
        var rawByType = Array.isArray(data === null || data === void 0 ? void 0 : data.by_type) ? data.by_type : [];
        var byType = rawByType.map(function (it) {
            var q_type = String((it === null || it === void 0 ? void 0 : it.q_type) || '未知');
            var t = Number((it === null || it === void 0 ? void 0 : it.total) || 0) || 0;
            var a = Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0;
            var c = Number((it === null || it === void 0 ? void 0 : it.correct) || 0) || 0;
            var w = Number((it === null || it === void 0 ? void 0 : it.wrong) || 0) || Math.max(0, a - c);
            var fav = Number((it === null || it === void 0 ? void 0 : it.favorites) || 0) || 0;
            var mis = Number((it === null || it === void 0 ? void 0 : it.mistakes) || 0) || 0;
            var acc = Number((it === null || it === void 0 ? void 0 : it.accuracy) || 0) || 0;
            var comp = Number((it === null || it === void 0 ? void 0 : it.completion) || 0) || 0;
            var completionWidth = clampPct(comp);
            return {
                q_type: q_type,
                total: t,
                answered: a,
                correct: c,
                wrong: w,
                favorites: fav,
                mistakes: mis,
                accuracyText: "".concat(acc.toFixed(1), "%"),
                completionText: "".concat(comp.toFixed(1), "%"),
                completionWidth: completionWidth,
                metaText: "\u6536\u85CF ".concat(fav, " \u00B7 \u5DF2\u505A ").concat(a, "/").concat(t, " \u00B7 \u6B63\u786E\u7387 ").concat(acc.toFixed(1), "% \u00B7 \u8986\u76D6\u7387 ").concat(comp.toFixed(1), "%")
            };
        });
        var advice = Array.isArray(data === null || data === void 0 ? void 0 : data.advice) ? data.advice : [];
        return { overview: overview, trend: trend, byType: byType, advice: advice };
    },
    buildHeatCells: function (trend) {
        var slice = trend.slice(-28);
        var maxAnswered = slice.reduce(function (m, it) { return Math.max(m, it.answered || 0); }, 0) || 0;
        var cells = slice.map(function (it) {
            if (!maxAnswered)
                return { level: 0 };
            var pct = it.answered / maxAnswered;
            var level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
            return { level: level };
        });
        var pad = 28 - cells.length;
        if (pad > 0) {
            return Array.from({ length: pad }, function () { return ({ level: 0 }); }).concat(cells);
        }
        return cells;
    },
    loadStatsDetail: function (days) {
        return __awaiter(this, void 0, void 0, function () {
            var subject, data, view, activeDays, activeDaysRate, favMistakeRate, sortedTypes, err_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        subject = String(this.data.subjectName || '').trim();
                        if (!subject)
                            return [2 /*return*/];
                        if (this.data.statsLoading)
                            return [2 /*return*/];
                        this.setData({ statsLoading: true, statsError: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSubjectStatsDetail(subject, { days: days, source: 'favorites' })];
                    case 2:
                        data = _a.sent();
                        view = this.buildStatsView(data || {});
                        activeDays = view.trend.filter(function (it) { return it.answered > 0; }).length;
                        activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
                        favMistakeRate = view.overview.total > 0 ? clampPct((view.overview.mistakes / view.overview.total) * 100) : 0;
                        sortedTypes = __spreadArray([], view.byType, true).sort(function (a, b) { return b.favorites - a.favorites; });
                        this.setData({
                            statsLoadedDays: days,
                            statsLoading: false,
                            statsOverview: view.overview,
                            statsTrend: view.trend,
                            statsByType: view.byType,
                            statsAdvice: view.advice,
                            ringAccuracy: clampPct(view.overview.accuracy),
                            ringCompletion: clampPct(view.overview.completion),
                            ringActive: clampPct(activeDaysRate),
                            activeDaysRate: activeDaysRate,
                            favMistakeRateText: "".concat(favMistakeRate.toFixed(0), "%"),
                            heatCells: this.buildHeatCells(view.trend),
                            displayTypes: sortedTypes
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        this.setData({
                            statsLoading: false,
                            statsError: (err_1 && err_1.message) ? String(err_1.message) : '统计加载失败'
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    }
});
