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
function safeArr(v) {
    return Array.isArray(v) ? v : [];
}
function buildExportObject(tab, days, payload) {
    var p = tab === 'global' ? '/data/global' : "/data/".concat(tab);
    var search = "?days=".concat(encodeURIComponent(String(days || 30)));
    return {
        meta: { exported_at: new Date().toISOString(), path: p, search: search },
        data: payload
    };
}
function sumDailyAll(list) {
    var rows = Array.isArray(list) ? list : [];
    return rows.reduce(function (acc, r) { return acc + (0, data_center_1.toInt)(r === null || r === void 0 ? void 0 : r.all); }, 0);
}
function buildFavoritesViewModel(res, currentDays) {
    var payload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'favorites');
    var allSummary = (res === null || res === void 0 ? void 0 : res.all_summary) || {};
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    var favoritesNew = sumDailyAll(res === null || res === void 0 ? void 0 : res.favorites_daily);
    var answeredAll = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.answered);
    var favAll = (0, data_center_1.toInt)(allSummary === null || allSummary === void 0 ? void 0 : allSummary.favorites);
    var favoritesDensity = answeredAll > 0 ? (0, data_center_1.pct1)((favAll * 100) / answeredAll) : 0;
    var topRaw = safeArr(res === null || res === void 0 ? void 0 : res.favorites_top_items).slice(0, 12);
    var denom = Math.max.apply(Math, __spreadArray([1], topRaw.map(function (it) { return (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.count); }), false));
    var topItems = topRaw.map(function (it, idx) {
        var source = String((it === null || it === void 0 ? void 0 : it.source) || '');
        var bankId = (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.bank_id);
        var c = (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.count);
        return {
            key: String((it === null || it === void 0 ? void 0 : it.bank_id) || (it === null || it === void 0 ? void 0 : it.name) || idx),
            source: source,
            scope_label: source === 'public' ? '公共' : '个人',
            name: String((it === null || it === void 0 ? void 0 : it.name) || ''),
            count: c,
            bank_id: bankId,
            can_quiz_bank: source === 'banks' && bankId > 0,
            bar_pct: (0, data_center_1.pct1)((c * 100) / denom)
        };
    });
    var recentPublic = safeArr(res === null || res === void 0 ? void 0 : res.recent_favorites_public)
        .slice(0, 6)
        .map(function (f, idx) { return ({
        key: String((f === null || f === void 0 ? void 0 : f.question_id) || idx),
        subject: String((f === null || f === void 0 ? void 0 : f.subject) || ''),
        q_type: String((f === null || f === void 0 ? void 0 : f.q_type) || ''),
        difficulty: (0, data_center_1.toInt)(f === null || f === void 0 ? void 0 : f.difficulty),
        snippet: String((f === null || f === void 0 ? void 0 : f.snippet) || '')
    }); });
    var recentBank = safeArr(res === null || res === void 0 ? void 0 : res.recent_favorites_bank)
        .slice(0, 6)
        .map(function (f, idx) { return ({
        key: String((f === null || f === void 0 ? void 0 : f.question_id) || (f === null || f === void 0 ? void 0 : f.bank_id) || idx),
        bank_id: (0, data_center_1.toInt)(f === null || f === void 0 ? void 0 : f.bank_id),
        bank_name: String((f === null || f === void 0 ? void 0 : f.bank_name) || ''),
        q_type: String((f === null || f === void 0 ? void 0 : f.q_type) || ''),
        difficulty: (0, data_center_1.toInt)(f === null || f === void 0 ? void 0 : f.difficulty),
        snippet: String((f === null || f === void 0 ? void 0 : f.snippet) || '')
    }); });
    return {
        payload: payload,
        data: {
            inited: true,
            window_days: windowDays,
            errorMsg: '',
            all_summary: allSummary,
            health_score: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.health_score),
            favorites_new: favoritesNew,
            favorites_density: favoritesDensity,
            favorites_top_items: topItems,
            recent_favorites_public: recentPublic,
            recent_favorites_bank: recentBank
        }
    };
}
var CHART_IDS = ['dcFavoriteTrendChart', 'dcFavoriteTopChart', 'dcFavoriteDifficultyChart', 'dcFavoriteTypeChart'];
Page({
    data: __assign(__assign({}, (theme_1.themeManager.getPageData())), { loading: false, inited: false, lazyStage: 1, errorMsg: '', ecLazy: { lazyLoad: true }, days: 30, window_days: 30, all_summary: {}, health_score: 0, favorites_new: 0, favorites_density: 0, favorites_top_items: [], recent_favorites_public: [], recent_favorites_bank: [] }),
    onLoad: function (options) {
        var _this = this;
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        var url = "/packages/data/pages/data-center-v2/data-center-v2?tab=favorites&days=".concat(encodeURIComponent(String(days)));
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
                    var built = buildFavoritesViewModel(cached, this.data.days);
                    var self = this;
                    self.__dcPayload = built.payload;
                    self.__lastLoadedAt = Date.now();
                    Object.assign(patch, built.data);
                    hydrated = true;
                }
            }
            catch (e) { }
        }
        try {
            if (Object.keys(patch).length) {
                this.setData(patch, hydrated
                    ? function () {
                        wx.nextTick(function () {
                            try {
                                _this.renderCharts();
                            }
                            catch (err) {
                                console.error('[data-favorites-v2] renderCharts failed:', err);
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
        var tab = raw === 'global' || raw === 'banks' || raw === 'mistakes' || raw === 'tags' ? raw : 'favorites';
        var days = this.data.days;
        var base = resolveDataTabUrl(tab);
        (0, nav_1.safeNavigate)("".concat(base, "?days=").concat(encodeURIComponent(String(days))), 'redirectTo');
    },
    onGoFavoritesCenter: function () {
        (0, nav_1.safeNavigate)('/pages/favorites-v2/favorites-v2', 'redirectTo');
    },
    onGoBankFavorites: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=".concat(encodeURIComponent(String(bankId)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoQuizBankFavorites: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=".concat(encodeURIComponent(String(bankId)));
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
                var chart = echarts.init(canvas, null, { width: width, height: height, devicePixelRatio: dpr });
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
            var self, now, lastAt, res, built, e_1;
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
                        built = buildFavoritesViewModel(res, this.data.days);
                        self.__dcPayload = built.payload;
                        this.setData(built.data, function () {
                            wx.nextTick(function () {
                                try {
                                    _this.renderCharts();
                                }
                                catch (err) {
                                    console.error('[data-favorites-v2] renderCharts failed:', err);
                                }
                            });
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 && e_1.message) || '加载失败，请稍后再试。' });
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
