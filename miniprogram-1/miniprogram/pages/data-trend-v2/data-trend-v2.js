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
function buildTrendPatch(res) {
    var _a, _b, _c, _d, _e;
    var windowAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.window_answered);
    var windowAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.window_accuracy);
    var dailySource = pickDaily(res);
    var dailyMax = Math.max((0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.all_daily_max), (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.daily_max), 1);
    var trendBars = (0, data_center_1.buildTrendBars)(dailySource, dailyMax);
    var heatmapRows = (0, data_center_1.buildHeatmapGrid)((_a = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _a === void 0 ? void 0 : _a.all, (_b = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _b === void 0 ? void 0 : _b.max);
    var hourlyRaw = Array.isArray((_c = res === null || res === void 0 ? void 0 : res.activity_hourly) === null || _c === void 0 ? void 0 : _c.all) ? res.activity_hourly.all : [];
    var hourlyMax = Math.max((0, data_center_1.toInt)((_d = res === null || res === void 0 ? void 0 : res.activity_hourly) === null || _d === void 0 ? void 0 : _d.max), 1);
    var hourlyBars = hourlyRaw.map(function (h) { return ({
        hour: (0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.hour),
        total: (0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.total),
        barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.total) * 100) / hourlyMax)
    }); });
    var daySums = [0, 0, 0, 0, 0, 0, 0];
    var heatmapAll = Array.isArray((_e = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _e === void 0 ? void 0 : _e.all) ? res.activity_heatmap.all : [];
    heatmapAll.forEach(function (it) {
        if (!it || it.length < 3)
            return;
        var day = (0, data_center_1.toInt)(it[0]);
        var val = (0, data_center_1.toInt)(it[2]);
        if (day < 0 || day > 6)
            return;
        daySums[day] += val;
    });
    var dayMax = Math.max.apply(Math, __spreadArray([1], daySums, false));
    var dayNames = ['鍛ㄤ竴', '鍛ㄤ簩', '鍛ㄤ笁', '鍛ㄥ洓', '鍛ㄤ簲', '鍛ㄥ叚', '鍛ㄦ棩'];
    var weekdayBars = daySums.map(function (val, idx) { return ({
        name: dayNames[idx],
        total: val,
        barPct: (0, data_center_1.pct1)((val * 100) / dayMax)
    }); });
    var typeRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.type_rows) ? res.type_rows : []).map(function (t) { return ({
        q_type: String((t === null || t === void 0 ? void 0 : t.q_type) || ''),
        answered: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.answered),
        accuracy: (0, data_center_1.pct1)(t === null || t === void 0 ? void 0 : t.accuracy)
    }); });
    var difficultyRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.difficulty_rows) ? res.difficulty_rows : []).map(function (d) { return ({
        difficulty: (0, data_center_1.toInt)(d === null || d === void 0 ? void 0 : d.difficulty),
        label: String((d === null || d === void 0 ? void 0 : d.label) || ''),
        answered: (0, data_center_1.toInt)(d === null || d === void 0 ? void 0 : d.answered),
        accuracy: (0, data_center_1.pct1)(d === null || d === void 0 ? void 0 : d.accuracy)
    }); });
    return {
        inited: true,
        windowAnswered: windowAnswered,
        windowAccuracy: windowAccuracy,
        trendBars: trendBars,
        hourlyBars: hourlyBars,
        weekdayBars: weekdayBars,
        heatmapRows: heatmapRows,
        typeRows: typeRows,
        difficultyRows: difficultyRows
    };
}
Page({
    data: {
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        windowAnswered: 0,
        windowAccuracy: 0,
        trendBars: [],
        hourlyBars: [],
        weekdayBars: [],
        heatmapRows: [],
        typeRows: [],
        difficultyRows: []
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
            Object.assign(patch, theme_1.themeManager.getPageData());
        }
        catch (e) { }
        if (!this.data.inited) {
            try {
                var cached = (0, data_center_cache_1.getCachedDataCenter)(this.data.days);
                if (cached) {
                    Object.assign(patch, buildTrendPatch(cached), { errorMsg: '' });
                    var self = this;
                    self.__lastLoadedAt = Date.now();
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
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, res, windowAnswered, windowAccuracy, dailySource, dailyMax, trendBars, heatmapRows, hourlyRaw, hourlyMax_1, hourlyBars, daySums_1, heatmapAll, dayMax_1, dayNames_1, weekdayBars, typeRows, difficultyRows, e_1;
            var _a, _b, _c, _d, _e;
            if (force === void 0) { force = false; }
            return __generator(this, function (_f) {
                switch (_f.label) {
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
                        _f.label = 1;
                    case 1:
                        _f.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataCenter(this.data.days)];
                    case 2:
                        res = _f.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(this.data.days, res);
                        }
                        catch (e) { }
                        windowAnswered = (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.window_answered);
                        windowAccuracy = (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.window_accuracy);
                        dailySource = pickDaily(res);
                        dailyMax = Math.max((0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.all_daily_max), (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.daily_max), 1);
                        trendBars = (0, data_center_1.buildTrendBars)(dailySource, dailyMax);
                        heatmapRows = (0, data_center_1.buildHeatmapGrid)((_a = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _a === void 0 ? void 0 : _a.all, (_b = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _b === void 0 ? void 0 : _b.max);
                        hourlyRaw = Array.isArray((_c = res === null || res === void 0 ? void 0 : res.activity_hourly) === null || _c === void 0 ? void 0 : _c.all) ? res.activity_hourly.all : [];
                        hourlyMax_1 = Math.max((0, data_center_1.toInt)((_d = res === null || res === void 0 ? void 0 : res.activity_hourly) === null || _d === void 0 ? void 0 : _d.max), 1);
                        hourlyBars = hourlyRaw.map(function (h) { return ({
                            hour: (0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.hour),
                            total: (0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.total),
                            barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(h === null || h === void 0 ? void 0 : h.total) * 100) / hourlyMax_1)
                        }); });
                        daySums_1 = [0, 0, 0, 0, 0, 0, 0];
                        heatmapAll = Array.isArray((_e = res === null || res === void 0 ? void 0 : res.activity_heatmap) === null || _e === void 0 ? void 0 : _e.all) ? res.activity_heatmap.all : [];
                        heatmapAll.forEach(function (it) {
                            if (!it || it.length < 3)
                                return;
                            var day = (0, data_center_1.toInt)(it[0]);
                            var val = (0, data_center_1.toInt)(it[2]);
                            if (day < 0 || day > 6)
                                return;
                            daySums_1[day] += val;
                        });
                        dayMax_1 = Math.max.apply(Math, __spreadArray([1], daySums_1, false));
                        dayNames_1 = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
                        weekdayBars = daySums_1.map(function (val, idx) { return ({
                            name: dayNames_1[idx],
                            total: val,
                            barPct: (0, data_center_1.pct1)((val * 100) / dayMax_1)
                        }); });
                        typeRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.type_rows) ? res.type_rows : []).map(function (t) { return ({
                            q_type: String((t === null || t === void 0 ? void 0 : t.q_type) || ''),
                            answered: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.answered),
                            accuracy: (0, data_center_1.pct1)(t === null || t === void 0 ? void 0 : t.accuracy)
                        }); });
                        difficultyRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.difficulty_rows) ? res.difficulty_rows : []).map(function (d) { return ({
                            difficulty: (0, data_center_1.toInt)(d === null || d === void 0 ? void 0 : d.difficulty),
                            label: String((d === null || d === void 0 ? void 0 : d.label) || ''),
                            answered: (0, data_center_1.toInt)(d === null || d === void 0 ? void 0 : d.answered),
                            accuracy: (0, data_center_1.pct1)(d === null || d === void 0 ? void 0 : d.accuracy)
                        }); });
                        this.setData({
                            inited: true,
                            windowAnswered: windowAnswered,
                            windowAccuracy: windowAccuracy,
                            trendBars: trendBars,
                            hourlyBars: hourlyBars,
                            weekdayBars: weekdayBars,
                            heatmapRows: heatmapRows,
                            typeRows: typeRows,
                            difficultyRows: difficultyRows
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _f.sent();
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
