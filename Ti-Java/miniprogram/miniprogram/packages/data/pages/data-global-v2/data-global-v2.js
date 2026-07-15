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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
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
var api_1 = require("../../../../utils/api");
var auth_1 = require("../../../../utils/auth");
var nav_1 = require("../../../../utils/nav");
var theme_1 = require("../../../../utils/theme");
var data_center_1 = require("../../utils/data-center");
var data_center_cache_1 = require("../../utils/data-center-cache");
var data_center_echarts_1 = require("../../utils/data-center-echarts");
var echarts = __importStar(require("../../components/ec-canvas/echarts"));
function resolveDataTabUrl(tab) {
    var map = {
        global: '/packages/data/pages/data-global-v2/data-global-v2',
        banks: '/packages/data/pages/data-bank-v2/data-bank-v2',
        mistakes: '/packages/data/pages/data-mistakes-v2/data-mistakes-v2',
        favorites: '/packages/data/pages/data-favorites-v2/data-favorites-v2',
        tags: '/packages/data/pages/data-tags-v2/data-tags-v2'
    };
    return map[tab];
}
function safeSlice(list, n) {
    var arr = Array.isArray(list) ? list : [];
    if (n <= 0)
        return [];
    return arr.slice(0, n);
}
function lastActivity16(input) {
    var s = String(input || '').trim();
    if (!s)
        return '—';
    return s.slice(0, 16);
}
function buildExportObject(tab, days, payload) {
    var p = tab === 'global' ? '/data/global' : "/data/".concat(tab);
    var search = "?days=".concat(encodeURIComponent(String(days || 30)));
    return {
        meta: { exported_at: new Date().toISOString(), path: p, search: search },
        data: payload
    };
}
function pickAllSummaryLite(summary) {
    var s = summary && typeof summary === 'object' ? summary : {};
    return {
        answered: (0, data_center_1.toInt)(s.answered),
        accuracy: (0, data_center_1.pct1)(s.accuracy),
        completion: (0, data_center_1.pct1)(s.completion)
    };
}
function buildGlobalViewModel(res, currentDays) {
    var allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
    var allSummaryLite = pickAllSummaryLite(allSummary);
    var globalInsights = safeSlice(res === null || res === void 0 ? void 0 : res.global_insights, 999).map(function (it, idx) { return ({
        key: String((it === null || it === void 0 ? void 0 : it.title) || idx),
        title: String((it === null || it === void 0 ? void 0 : it.title) || ''),
        value: String((it === null || it === void 0 ? void 0 : it.value) || ''),
        hint: String((it === null || it === void 0 ? void 0 : it.hint) || '')
    }); });
    var nextActions = safeSlice(res === null || res === void 0 ? void 0 : res.next_actions, 8).map(function (a, idx) { return ({
        key: String((a === null || a === void 0 ? void 0 : a.title) || idx),
        title: String((a === null || a === void 0 ? void 0 : a.title) || ''),
        reason: String((a === null || a === void 0 ? void 0 : a.reason) || ''),
        metrics: String((a === null || a === void 0 ? void 0 : a.metrics) || ''),
        subject: String((a === null || a === void 0 ? void 0 : a.subject) || ''),
        q_type: String((a === null || a === void 0 ? void 0 : a.q_type) || '')
    }); });
    var weaknessRows = safeSlice(res === null || res === void 0 ? void 0 : res.weakness_rows, 8).map(function (w, idx) { return ({
        key: String((w === null || w === void 0 ? void 0 : w.key) || "".concat((w === null || w === void 0 ? void 0 : w.subject) || '', "__").concat((w === null || w === void 0 ? void 0 : w.q_type) || '', "__").concat(idx)),
        subject: String((w === null || w === void 0 ? void 0 : w.subject) || ''),
        q_type: String((w === null || w === void 0 ? void 0 : w.q_type) || ''),
        answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered),
        accuracy: (0, data_center_1.pct1)(w === null || w === void 0 ? void 0 : w.accuracy),
        mistakes: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.mistakes)
    }); });
    var recentMistakes = safeSlice(res === null || res === void 0 ? void 0 : res.recent_mistakes, 6).map(function (m, idx) { return ({
        key: String((m === null || m === void 0 ? void 0 : m.question_id) || idx),
        subject: String((m === null || m === void 0 ? void 0 : m.subject) || ''),
        q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || ''),
        question_id: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.question_id),
        snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || ''),
        difficulty: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.difficulty)
    }); });
    var recentFavoritesPublic = safeSlice(res === null || res === void 0 ? void 0 : res.recent_favorites_public, 6).map(function (m, idx) { return ({
        key: String((m === null || m === void 0 ? void 0 : m.question_id) || idx),
        subject: String((m === null || m === void 0 ? void 0 : m.subject) || ''),
        q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || ''),
        question_id: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.question_id),
        snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || ''),
        difficulty: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.difficulty)
    }); });
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    var baseData = {
        inited: true,
        window_days: windowDays,
        last_activity_16: lastActivity16(allSummary === null || allSummary === void 0 ? void 0 : allSummary.last_activity),
        // 避免把后端 ctx 的大对象直接塞进 data（可能触发 setData 栈溢出）
        all_summary: allSummaryLite,
        health_score: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.health_score),
        errorMsg: ''
    };
    return {
        windowDays: windowDays,
        fullData: __assign(__assign({}, baseData), { global_insights: globalInsights, next_actions: nextActions, weakness_rows: weaknessRows, recent_mistakes: recentMistakes, recent_favorites_public: recentFavoritesPublic }),
        fallbackData: __assign(__assign({}, baseData), { global_insights: [], next_actions: [], weakness_rows: [], recent_mistakes: [], recent_favorites_public: [] })
    };
}
function trySetData(page, data, cb) {
    try {
        if (typeof cb === 'function')
            page.setData(data, cb);
        else
            page.setData(data);
        return true;
    }
    catch (err) {
        console.error('[data-global-v2] setData failed:', err);
        return false;
    }
}
var CHART_IDS = [
    'dcTrendDetailChart',
    'dcGlobalLoopChart',
    'dcHealthGaugeChart',
    'dcCalendarChart',
    'dcHeatmapChart',
    'dcHourlyChart',
    'dcWeekdayChart',
    'dcAssetTrendChart',
    'dcRadarChart',
    'dcTopMixChart',
    'dcTypeDistChart',
    'dcDifficultyDistChart'
];
Page({
    data: __assign(__assign({}, (theme_1.themeManager.getPageData())), { loading: false, inited: false, lazyStage: 1, errorMsg: '', ecLazy: { lazyLoad: true }, days: 30, window_days: 30, last_activity_16: '—', all_summary: {}, health_score: 0, global_insights: [], next_actions: [], weakness_rows: [], recent_mistakes: [], recent_favorites_public: [] }),
    onLoad: function (options) {
        var _this = this;
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        var url = "/packages/data/pages/data-center-v2/data-center-v2?tab=global&days=".concat(encodeURIComponent(String(days)));
        wx.redirectTo({
            url: url,
            fail: function () {
                _this.setData({ days: days, window_days: days });
            }
        });
    },
    onReady: function () {
        var self = this;
        self.__pageReady = true;
        this.initViewportLazy();
        if (self.__pendingRender) {
            self.__pendingRender = false;
            this.renderCharts();
        }
    },
    initViewportLazy: function () {
        var _this = this;
        var self = this;
        if (this.data.lazyStage >= 2)
            return;
        if (self.__lazyObserver)
            return;
        var ob;
        try {
            ob = this.createIntersectionObserver({ observeAll: false });
        }
        catch (e) {
            return;
        }
        self.__lazyObserver = ob;
        try {
            ob.relativeToViewport({ bottom: 600 }).observe('#dcLazyStage2Trigger', function (res) {
                if (!res || res.intersectionRatio <= 0)
                    return;
                if (_this.data.lazyStage >= 2)
                    return;
                _this.setData({ lazyStage: 2 }, function () {
                    wx.nextTick(function () {
                        try {
                            _this.renderCharts();
                        }
                        catch (err) { }
                    });
                });
                try {
                    ob.disconnect();
                }
                catch (e) { }
                self.__lazyObserver = null;
            });
        }
        catch (e) { }
    },
    onShow: function () {
        var _this = this;
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
                    var self = this;
                    self.__lastLoadedAt = Date.now();
                    try {
                        self.__dcPayload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(cached, 'global');
                    }
                    catch (err) {
                        console.error('[data-global-v2] buildDataCenterCompatPayload failed (hydrate):', err);
                        self.__dcPayload = {
                            active_tab: 'global',
                            window_days: (0, data_center_1.normalizeDays)((cached === null || cached === void 0 ? void 0 : cached.window_days) || this.data.days)
                        };
                    }
                    Object.assign(patch, buildGlobalViewModel(cached, this.data.days).fullData);
                    hydrated = true;
                }
            }
            catch (e) { }
        }
        try {
            if (Object.keys(patch).length) {
                trySetData(this, patch, hydrated
                    ? function () {
                        wx.nextTick(function () {
                            try {
                                _this.renderCharts();
                            }
                            catch (err) {
                                console.error('[data-global-v2] renderCharts failed:', err);
                            }
                        });
                    }
                    : undefined);
            }
        }
        catch (e) { }
        if (!hydrated && !this.data.inited && !this.data.loading) {
            this.loadStats(true);
            return;
        }
        if (!hydrated)
            this.renderCharts();
    },
    onUnload: function () {
        var self = this;
        try {
            self.__lazyObserver && typeof self.__lazyObserver.disconnect === 'function' && self.__lazyObserver.disconnect();
        }
        catch (e) { }
        self.__lazyObserver = null;
        var charts = (self.__charts || {});
        Object.keys(charts).forEach(function (k) {
            try {
                charts[k] && typeof charts[k].dispose === 'function' && charts[k].dispose();
            }
            catch (e) { }
        });
        self.__charts = {};
    },
    onThemeChange: function (isDark) {
        this.renderCharts(false, isDark);
    },
    onPullDownRefresh: function () {
        this.loadStats(true).finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onDaysTap: function (e) {
        var _this = this;
        var _a, _b;
        var days = (0, data_center_1.normalizeDays)((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.days);
        if (days === this.data.days)
            return;
        this.setData({ days: days, window_days: days }, function () {
            _this.loadStats(true);
        });
    },
    onTabTap: function (e) {
        var _a, _b;
        var raw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '').trim().toLowerCase();
        var tab = raw === 'banks' || raw === 'mistakes' || raw === 'favorites' || raw === 'tags' ? raw : 'global';
        var days = this.data.days;
        var base = resolveDataTabUrl(tab);
        (0, nav_1.safeNavigate)("".concat(base, "?days=").concat(encodeURIComponent(String(days))), 'redirectTo');
    },
    onGoMistakesCenter: function () {
        (0, nav_1.safeNavigate)('/pages/mistakes-v2/mistakes-v2', 'redirectTo');
    },
    onGoFavoritesCenter: function () {
        (0, nav_1.safeNavigate)('/pages/favorites-v2/favorites-v2', 'redirectTo');
    },
    onGoQuizPublicMistakes: function (e) {
        var _a, _b, _c, _d;
        var subject = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subject) || '').trim();
        var qType = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.qType) || '').trim();
        if (!subject)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=mistakes&subject=".concat(encodeURIComponent(subject)) +
            (qType ? "&type=".concat(encodeURIComponent(qType)) : '');
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoQuizPublicAll: function (e) {
        var _a, _b, _c, _d;
        var subject = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subject) || '').trim();
        var qType = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.qType) || '').trim();
        if (!subject)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=all&subject=".concat(encodeURIComponent(subject)) + (qType ? "&type=".concat(encodeURIComponent(qType)) : '');
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    renderCharts: function (forceInit, isDarkOverride) {
        var _this = this;
        if (forceInit === void 0) { forceInit = false; }
        var self = this;
        var payload = self.__dcPayload;
        if (!payload)
            return;
        if (!self.__pageReady) {
            self.__pendingRender = true;
            return;
        }
        var isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : theme_1.themeManager.isDarkMode();
        var style = theme_1.themeManager.getStyle();
        var tokens = (0, data_center_echarts_1.getDataCenterThemeTokens)(isDark, style);
        var charts = (self.__charts || (self.__charts = {}));
        CHART_IDS.forEach(function (id) {
            var comp = _this.selectComponent("#".concat(id));
            if (!comp || typeof comp.init !== 'function')
                return;
            var existing = charts[id];
            if (existing && !forceInit) {
                try {
                    var opt = (0, data_center_echarts_1.buildDataCenterChartOption)(id, payload, tokens, existing);
                    if (opt)
                        existing.setOption(opt, { notMerge: true, lazyUpdate: false });
                }
                catch (e) { }
                return;
            }
            if (existing) {
                try {
                    existing.dispose && existing.dispose();
                }
                catch (e) { }
                delete charts[id];
            }
            comp.init(function (canvas, width, height, dpr) {
                var chart;
                try {
                    chart = echarts.init(canvas, null, { width: width, height: height, devicePixelRatio: dpr });
                }
                catch (err) {
                    console.error('[data-global-v2] echarts.init failed:', id, err);
                    return undefined;
                }
                canvas.setChart(chart);
                charts[id] = chart;
                try {
                    var opt = (0, data_center_echarts_1.buildDataCenterChartOption)(id, payload, tokens, chart);
                    if (opt)
                        chart.setOption(opt, { notMerge: true, lazyUpdate: false });
                }
                catch (e) { }
                return chart;
            });
        });
    },
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, stage, res, vm, afterSet, ok, e_1, raw, isStack, msg, nowToast, lastToast;
            var _this = this;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 8000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        trySetData(this, { loading: true, errorMsg: '' });
                        stage = 'init';
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        stage = 'getDataCenter';
                        return [4 /*yield*/, api_1.api.getDataCenter(this.data.days)];
                    case 2:
                        res = _a.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(this.data.days, res);
                        }
                        catch (e) { }
                        stage = 'buildCompatPayload';
                        try {
                            self.__dcPayload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'global');
                        }
                        catch (err) {
                            console.error('[data-global-v2] buildDataCenterCompatPayload failed:', err);
                            self.__dcPayload = {
                                active_tab: 'global',
                                window_days: (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || this.data.days)
                            };
                        }
                        stage = 'buildViewModel';
                        vm = buildGlobalViewModel(res, this.data.days);
                        stage = 'setData';
                        afterSet = function () {
                            wx.nextTick(function () {
                                try {
                                    _this.renderCharts();
                                }
                                catch (err) {
                                    console.error('[data-global-v2] renderCharts failed:', err);
                                }
                            });
                        };
                        if (!trySetData(this, vm.fullData, afterSet)) {
                            ok = trySetData(this, vm.fallbackData, afterSet);
                            if (!ok) {
                                trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
                            }
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        console.error('[data-global-v2] loadStats failed:', stage, e_1);
                        raw = (e_1 && e_1.message) ? String(e_1.message) : '加载失败，请稍后再试。';
                        isStack = raw.includes('Maximum call stack size exceeded');
                        msg = isStack ? "\u6570\u636E\u6E32\u67D3\u5F02\u5E38\uFF08".concat(stage, "\uFF09\uFF1A").concat(raw) : raw;
                        trySetData(this, { errorMsg: msg });
                        try {
                            nowToast = Date.now();
                            lastToast = Number(self.__lastErrorToastAt || 0) || 0;
                            if (nowToast - lastToast > 3500) {
                                self.__lastErrorToastAt = nowToast;
                                wx.showToast({ title: msg.length > 18 ? '数据加载失败' : msg, icon: 'none' });
                            }
                        }
                        catch (e) { }
                        return [3 /*break*/, 5];
                    case 4:
                        trySetData(this, { loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
