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
var user_settings_1 = require("../../../../utils/user-settings");
var theme_1 = require("../../../../utils/theme");
var data_center_1 = require("../../../../utils/data-center");
var data_tags_cache_1 = require("../../../../utils/data-tags-cache");
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
function buildTagsViewData(res) {
    function mapRows(raw, barField) {
        if (barField === void 0) { barField = 'question_count'; }
        var rows = Array.isArray(raw) ? raw : [];
        var maxVal = Math.max.apply(Math, __spreadArray([1], rows.map(function (x) { return (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x[barField]); }), false));
        return rows.map(function (x, idx) { return ({
            key: String((x === null || x === void 0 ? void 0 : x.key) || "".concat(idx, "_").concat(String((x === null || x === void 0 ? void 0 : x.scope) || ''), "_").concat(String((x === null || x === void 0 ? void 0 : x.tag) || ''))),
            scope: (String((x === null || x === void 0 ? void 0 : x.scope) || 'public') === 'bank' ? 'bank' : 'public'),
            tag: String((x === null || x === void 0 ? void 0 : x.tag) || ''),
            bank_id: (x === null || x === void 0 ? void 0 : x.bank_id) == null ? undefined : (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.bank_id),
            bank_name: (x === null || x === void 0 ? void 0 : x.bank_name) ? String(x === null || x === void 0 ? void 0 : x.bank_name) : undefined,
            question_count: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.question_count),
            answered: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.answered),
            accuracy: (0, data_center_1.pct1)(x === null || x === void 0 ? void 0 : x.accuracy),
            favorites: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.favorites),
            mistakes_times: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.mistakes_times),
            barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x[barField]) * 100) / maxVal)
        }); });
    }
    var summary = (res === null || res === void 0 ? void 0 : res.summary) || {};
    var lastActivityText = String((((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.last_activity_text) || (summary === null || summary === void 0 ? void 0 : summary.last_activity_text) || '—')) || '—';
    var kpiAll = {
        tag_total: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.tag_total),
        tagged_questions: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.tagged_questions),
        answered: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.answered),
        accuracy: (0, data_center_1.pct1)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.accuracy),
        favorites: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.favorites),
        mistakes_times: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.all) === null || (summary === null || summary === void 0 ? void 0 : summary.all) === void 0 ? void 0 : summary.all.mistakes_times)
    };
    var kpiPublic = {
        tag_total: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.tag_total),
        tagged_questions: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.tagged_questions),
        answered: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.answered),
        accuracy: (0, data_center_1.pct1)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.accuracy),
        favorites: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.favorites),
        mistakes_times: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.public) === null || (summary === null || summary === void 0 ? void 0 : summary.public) === void 0 ? void 0 : summary.public.mistakes_times)
    };
    var kpiBanks = {
        tag_total: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.tag_total),
        tagged_questions: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.tagged_questions),
        answered: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.answered),
        accuracy: (0, data_center_1.pct1)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.accuracy),
        favorites: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.favorites),
        mistakes_times: (0, data_center_1.toInt)((summary === null || summary === void 0 ? void 0 : summary.banks) === null || (summary === null || summary === void 0 ? void 0 : summary.banks) === void 0 ? void 0 : summary.banks.mistakes_times)
    };
    var topUsage = mapRows(res === null || res === void 0 ? void 0 : res.top_usage, 'question_count');
    var lowAccuracy = mapRows(res === null || res === void 0 ? void 0 : res.low_accuracy, 'question_count');
    var topMistakes = mapRows(res === null || res === void 0 ? void 0 : res.top_mistakes, 'mistakes_times');
    return {
        inited: true,
        errorMsg: '',
        lastActivityText: lastActivityText,
        kpiAll: kpiAll,
        kpiPublic: kpiPublic,
        kpiBanks: kpiBanks,
        topUsage: topUsage,
        lowAccuracy: lowAccuracy,
        topMistakes: topMistakes
    };
}
Page({
    data: __assign(__assign({}, theme_1.themeManager.getPageData()), {
        drawerOpen: false,
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        lastActivityText: '—',
        kpiAll: {
            tag_total: 0,
            tagged_questions: 0,
            answered: 0,
            accuracy: 0,
            favorites: 0,
            mistakes_times: 0
        },
        kpiPublic: {
            tag_total: 0,
            tagged_questions: 0,
            answered: 0,
            accuracy: 0,
            favorites: 0,
            mistakes_times: 0
        },
        kpiBanks: {
            tag_total: 0,
            tagged_questions: 0,
            answered: 0,
            accuracy: 0,
            favorites: 0,
            mistakes_times: 0
        },
        topUsage: [],
        lowAccuracy: [],
        topMistakes: []
    }),
    onLoad: function (options) {
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        var url = "/packages/data/pages/data-center-v2/data-center-v2?tab=tags&days=".concat(encodeURIComponent(String(days)));
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
                var cached = (0, data_tags_cache_1.getCachedDataTags)(this.data.days);
                if (cached) {
                    this.__lastLoadedAt = Date.now();
                    __assign(patch, buildTagsViewData(cached));
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
    onHamburgerTap: function () {
        this.setData({ drawerOpen: true });
    },
    onDrawerClose: function () {
        this.setData({ drawerOpen: false });
    },
    onDrawerNavigate: function (e) {
        var _a, _b;
        var url = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.url;
        var navType = (_b = e === null || e === void 0 ? void 0 : e.detail) === null || _b === void 0 ? void 0 : _b.navType;
        this.setData({ drawerOpen: false });
        if (!url)
            return;
        (0, nav_1.safeNavigate)(url, navType);
    },
    onDrawerSelectStyle: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        style = (((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        this.setData({ drawerOpen: false });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
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
        var tab = raw === 'global' || raw === 'bank' || raw === 'mistakes' || raw === 'favorites' ? raw : 'tags';
        var days = this.data.days;
        var base = resolveDataTabUrl(tab);
        (0, nav_1.safeNavigate)("".concat(base, "?days=").concat(encodeURIComponent(String(days))), 'redirectTo');
    },
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            function mapRows(raw, barField) {
                if (barField === void 0) { barField = 'question_count'; }
                var rows = Array.isArray(raw) ? raw : [];
                var maxVal = Math.max.apply(Math, __spreadArray([1], rows.map(function (x) { return (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x[barField]); }), false));
                return rows.map(function (x, idx) { return ({
                    key: String((x === null || x === void 0 ? void 0 : x.key) || "".concat(idx, "_").concat(String((x === null || x === void 0 ? void 0 : x.scope) || ''), "_").concat(String((x === null || x === void 0 ? void 0 : x.tag) || ''))),
                    scope: (String((x === null || x === void 0 ? void 0 : x.scope) || 'public') === 'bank' ? 'bank' : 'public'),
                    tag: String((x === null || x === void 0 ? void 0 : x.tag) || ''),
                    bank_id: (x === null || x === void 0 ? void 0 : x.bank_id) == null ? undefined : (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.bank_id),
                    bank_name: (x === null || x === void 0 ? void 0 : x.bank_name) ? String(x === null || x === void 0 ? void 0 : x.bank_name) : undefined,
                    question_count: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.question_count),
                    answered: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.answered),
                    accuracy: (0, data_center_1.pct1)(x === null || x === void 0 ? void 0 : x.accuracy),
                    favorites: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.favorites),
                    mistakes_times: (0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x.mistakes_times),
                    barPct: (0, data_center_1.pct1)(((0, data_center_1.toInt)(x === null || x === void 0 ? void 0 : x[barField]) * 100) / maxVal)
                }); });
            }
            var self, now, lastAt, res, summary, lastActivityText, kpiAll, kpiPublic, kpiBanks, topUsage, lowAccuracy, topMistakes, e_1;
            var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q, _r, _s, _t, _u;
            if (force === void 0) { force = false; }
            return __generator(this, function (_v) {
                switch (_v.label) {
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
                        _v.label = 1;
                    case 1:
                        _v.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataTags(this.data.days)];
                    case 2:
                        res = _v.sent();
                        try {
                            (0, data_tags_cache_1.setCachedDataTags)(this.data.days, res);
                        }
                        catch (e) { }
                        summary = (res === null || res === void 0 ? void 0 : res.summary) || {};
                        lastActivityText = String(((_a = summary === null || summary === void 0 ? void 0 : summary.all) === null || _a === void 0 ? void 0 : _a.last_activity_text) || (summary === null || summary === void 0 ? void 0 : summary.last_activity_text) || '—') || '—';
                        kpiAll = {
                            tag_total: (0, data_center_1.toInt)((_b = summary === null || summary === void 0 ? void 0 : summary.all) === null || _b === void 0 ? void 0 : _b.tag_total),
                            tagged_questions: (0, data_center_1.toInt)((_c = summary === null || summary === void 0 ? void 0 : summary.all) === null || _c === void 0 ? void 0 : _c.tagged_questions),
                            answered: (0, data_center_1.toInt)((_d = summary === null || summary === void 0 ? void 0 : summary.all) === null || _d === void 0 ? void 0 : _d.answered),
                            accuracy: (0, data_center_1.pct1)((_e = summary === null || summary === void 0 ? void 0 : summary.all) === null || _e === void 0 ? void 0 : _e.accuracy),
                            favorites: (0, data_center_1.toInt)((_f = summary === null || summary === void 0 ? void 0 : summary.all) === null || _f === void 0 ? void 0 : _f.favorites),
                            mistakes_times: (0, data_center_1.toInt)((_g = summary === null || summary === void 0 ? void 0 : summary.all) === null || _g === void 0 ? void 0 : _g.mistakes_times)
                        };
                        kpiPublic = {
                            tag_total: (0, data_center_1.toInt)((_h = summary === null || summary === void 0 ? void 0 : summary.public) === null || _h === void 0 ? void 0 : _h.tag_total),
                            tagged_questions: (0, data_center_1.toInt)((_j = summary === null || summary === void 0 ? void 0 : summary.public) === null || _j === void 0 ? void 0 : _j.tagged_questions),
                            answered: (0, data_center_1.toInt)((_k = summary === null || summary === void 0 ? void 0 : summary.public) === null || _k === void 0 ? void 0 : _k.answered),
                            accuracy: (0, data_center_1.pct1)((_l = summary === null || summary === void 0 ? void 0 : summary.public) === null || _l === void 0 ? void 0 : _l.accuracy),
                            favorites: (0, data_center_1.toInt)((_m = summary === null || summary === void 0 ? void 0 : summary.public) === null || _m === void 0 ? void 0 : _m.favorites),
                            mistakes_times: (0, data_center_1.toInt)((_o = summary === null || summary === void 0 ? void 0 : summary.public) === null || _o === void 0 ? void 0 : _o.mistakes_times)
                        };
                        kpiBanks = {
                            tag_total: (0, data_center_1.toInt)((_p = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _p === void 0 ? void 0 : _p.tag_total),
                            tagged_questions: (0, data_center_1.toInt)((_q = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _q === void 0 ? void 0 : _q.tagged_questions),
                            answered: (0, data_center_1.toInt)((_r = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _r === void 0 ? void 0 : _r.answered),
                            accuracy: (0, data_center_1.pct1)((_s = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _s === void 0 ? void 0 : _s.accuracy),
                            favorites: (0, data_center_1.toInt)((_t = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _t === void 0 ? void 0 : _t.favorites),
                            mistakes_times: (0, data_center_1.toInt)((_u = summary === null || summary === void 0 ? void 0 : summary.banks) === null || _u === void 0 ? void 0 : _u.mistakes_times)
                        };
                        topUsage = mapRows(res === null || res === void 0 ? void 0 : res.top_usage, 'question_count');
                        lowAccuracy = mapRows(res === null || res === void 0 ? void 0 : res.low_accuracy, 'question_count');
                        topMistakes = mapRows(res === null || res === void 0 ? void 0 : res.top_mistakes, 'mistakes_times');
                        this.setData({
                            inited: true,
                            lastActivityText: lastActivityText,
                            kpiAll: kpiAll,
                            kpiPublic: kpiPublic,
                            kpiBanks: kpiBanks,
                            topUsage: topUsage,
                            lowAccuracy: lowAccuracy,
                            topMistakes: topMistakes
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _v.sent();
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
