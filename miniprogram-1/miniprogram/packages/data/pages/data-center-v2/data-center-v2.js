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
var TAB_META = {
    global: { title: '全局', desc: '全局视角：覆盖、正确、连续与复盘资产，一屏把握你的学习系统。' },
    banks: { title: '题库', desc: '题库全景：规模、覆盖、质量，把投入方向选得更聪明。' },
    mistakes: { title: '错题', desc: '错题是最有杠杆的提升入口：高频先闭环，薄弱再专项。' },
    favorites: { title: '收藏', desc: '收藏是高价值题库：复习、背题、考前冲刺都能复用。' },
    tags: { title: '标签', desc: '标签让题目资产结构化：复盘与专项训练更容易“复用”。' }
};
var CHART_IDS_BY_TAB = {
    global: [
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
    ],
    banks: ['dcBankSplitChart', 'dcBankCategoryChart', 'dcBankBubbleChart', 'dcBankRankChart', 'dcSubjectProgressChart', 'dcSubjectRiskChart'],
    mistakes: ['dcMistakeTrendChart', 'dcMistakeTopChart', 'dcMistakeDifficultyChart', 'dcMistakeTypeChart'],
    favorites: ['dcFavoriteTrendChart', 'dcFavoriteTopChart', 'dcFavoriteDifficultyChart', 'dcFavoriteTypeChart'],
    tags: ['dcTagGraphChart', 'dcTagTreemapChart', 'dcTagTopChart', 'dcTagAccuracyChart']
};
function normalizeTab(raw) {
    var v = String(raw || '').trim().toLowerCase();
    if (v === 'banks' || v === 'mistakes' || v === 'favorites' || v === 'tags')
        return v;
    return 'global';
}
function safeSlice(list, n) {
    var arr = Array.isArray(list) ? list : [];
    if (n <= 0)
        return [];
    return arr.slice(0, n);
}
function safeArr(v) {
    return Array.isArray(v) ? v : [];
}
function lastActivity16(input) {
    var s = String(input || '').trim();
    if (!s)
        return '—';
    return s.slice(0, 16);
}
function pickAllSummaryLite(summary) {
    var s = summary && typeof summary === 'object' ? summary : {};
    return {
        answered: (0, data_center_1.toInt)(s.answered),
        accuracy: (0, data_center_1.pct1)(s.accuracy),
        completion: (0, data_center_1.pct1)(s.completion),
        mistakes: (0, data_center_1.toInt)(s.mistakes),
        mistakes_times: (0, data_center_1.toInt)(s.mistakes_times),
        favorites: (0, data_center_1.toInt)(s.favorites)
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
function buildBankViewModel(res, currentDays) {
    var payload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'banks');
    var allSummaryLite = pickAllSummaryLite((res === null || res === void 0 ? void 0 : res.all_summary) || {});
    var bankSummary = (res === null || res === void 0 ? void 0 : res.bank_summary) || {};
    var subjects = safeArr(res === null || res === void 0 ? void 0 : res.subject_rows).map(function (s, idx) { return ({
        key: String((s === null || s === void 0 ? void 0 : s.subject_id) || (s === null || s === void 0 ? void 0 : s.subject) || idx),
        subject_id: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.subject_id),
        subject: String((s === null || s === void 0 ? void 0 : s.subject) || ''),
        total: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.total),
        answered: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.answered),
        accuracy: (0, data_center_1.pct1)(s === null || s === void 0 ? void 0 : s.accuracy),
        completion: (0, data_center_1.pct1)(s === null || s === void 0 ? void 0 : s.completion),
        mistakes: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.mistakes),
        favorites: (0, data_center_1.toInt)(s === null || s === void 0 ? void 0 : s.favorites)
    }); });
    var banks = safeArr(res === null || res === void 0 ? void 0 : res.bank_rows).map(function (b, idx) { return ({
        key: String((b === null || b === void 0 ? void 0 : b.bank_id) || (b === null || b === void 0 ? void 0 : b.name) || idx),
        bank_id: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.bank_id),
        name: String((b === null || b === void 0 ? void 0 : b.name) || ''),
        category_name: String((b === null || b === void 0 ? void 0 : b.category_name) || '未分类'),
        total: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.total),
        answered: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.answered),
        accuracy: (0, data_center_1.pct1)(b === null || b === void 0 ? void 0 : b.accuracy),
        completion: (0, data_center_1.pct1)(b === null || b === void 0 ? void 0 : b.completion),
        mistakes: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.mistakes),
        favorites: (0, data_center_1.toInt)(b === null || b === void 0 ? void 0 : b.favorites)
    }); });
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    return {
        payload: payload,
        data: {
            inited: true,
            window_days: windowDays,
            errorMsg: '',
            all_summary: allSummaryLite,
            bank_summary: bankSummary,
            total_questions: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.total_questions),
            answered_count: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.answered_count),
            accuracy: (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.accuracy),
            window_answered: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.window_answered),
            window_accuracy: (0, data_center_1.pct1)(res === null || res === void 0 ? void 0 : res.window_accuracy),
            subject_rows: subjects,
            bank_rows: banks
        }
    };
}
function sumDailyAll(list) {
    var rows = Array.isArray(list) ? list : [];
    return rows.reduce(function (acc, r) { return acc + (0, data_center_1.toInt)(r === null || r === void 0 ? void 0 : r.all); }, 0);
}
function buildMistakesViewModel(res, currentDays) {
    var payload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'mistakes');
    var allSummaryLite = pickAllSummaryLite((res === null || res === void 0 ? void 0 : res.all_summary) || {});
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    var mistakesNew = sumDailyAll(res === null || res === void 0 ? void 0 : res.mistakes_daily);
    var topRaw = safeArr(res === null || res === void 0 ? void 0 : res.mistakes_top_items).slice(0, 12);
    var weights = topRaw.map(function (it) { return (0, data_center_1.toInt)((it === null || it === void 0 ? void 0 : it.times) || (it === null || it === void 0 ? void 0 : it.count)); });
    var denom = Math.max.apply(Math, __spreadArray([1], weights, false));
    var topItems = topRaw.map(function (it, idx) {
        var source = String((it === null || it === void 0 ? void 0 : it.source) || '');
        var bankId = (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.bank_id);
        var w = (0, data_center_1.toInt)((it === null || it === void 0 ? void 0 : it.times) || (it === null || it === void 0 ? void 0 : it.count));
        return {
            key: String((it === null || it === void 0 ? void 0 : it.bank_id) || (it === null || it === void 0 ? void 0 : it.name) || idx),
            source: source,
            scope_label: source === 'public' ? '公共' : '个人',
            name: String((it === null || it === void 0 ? void 0 : it.name) || ''),
            count: (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.count),
            times: (0, data_center_1.toInt)(it === null || it === void 0 ? void 0 : it.times),
            bank_id: bankId,
            can_quiz_bank: source === 'banks' && bankId > 0,
            bar_pct: (0, data_center_1.pct1)((w * 100) / denom)
        };
    });
    var recentPublic = safeArr(res === null || res === void 0 ? void 0 : res.recent_mistakes)
        .slice(0, 6)
        .map(function (m, idx) { return ({
        key: String((m === null || m === void 0 ? void 0 : m.question_id) || idx),
        subject: String((m === null || m === void 0 ? void 0 : m.subject) || ''),
        q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || ''),
        difficulty: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.difficulty),
        snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || '')
    }); });
    var recentBank = safeArr(res === null || res === void 0 ? void 0 : res.recent_mistakes_bank)
        .slice(0, 6)
        .map(function (m, idx) { return ({
        key: String((m === null || m === void 0 ? void 0 : m.question_id) || (m === null || m === void 0 ? void 0 : m.bank_id) || idx),
        bank_id: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.bank_id),
        bank_name: String((m === null || m === void 0 ? void 0 : m.bank_name) || ''),
        q_type: String((m === null || m === void 0 ? void 0 : m.q_type) || ''),
        difficulty: (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.difficulty),
        snippet: String((m === null || m === void 0 ? void 0 : m.snippet) || ''),
        wrong_count: (m === null || m === void 0 ? void 0 : m.wrong_count) == null ? null : (0, data_center_1.toInt)(m === null || m === void 0 ? void 0 : m.wrong_count)
    }); });
    return {
        payload: payload,
        data: {
            inited: true,
            window_days: windowDays,
            errorMsg: '',
            all_summary: allSummaryLite,
            health_score: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.health_score),
            mistakes_new: mistakesNew,
            mistakes_top_items: topItems,
            recent_mistakes: recentPublic,
            recent_mistakes_bank: recentBank
        }
    };
}
function buildFavoritesViewModel(res, currentDays) {
    var payload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'favorites');
    var allSummaryLite = pickAllSummaryLite((res === null || res === void 0 ? void 0 : res.all_summary) || {});
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    var favoritesNew = sumDailyAll(res === null || res === void 0 ? void 0 : res.favorites_daily);
    var answeredAll = (0, data_center_1.toInt)(allSummaryLite === null || allSummaryLite === void 0 ? void 0 : allSummaryLite.answered);
    var favAll = (0, data_center_1.toInt)(allSummaryLite === null || allSummaryLite === void 0 ? void 0 : allSummaryLite.favorites);
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
            all_summary: allSummaryLite,
            health_score: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.health_score),
            favorites_new: favoritesNew,
            favorites_density: favoritesDensity,
            favorites_top_items: topItems,
            recent_favorites_public: recentPublic,
            recent_favorites_bank: recentBank
        }
    };
}
function buildTagsViewModel(res, currentDays) {
    var payload = (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, 'tags');
    var windowDays = (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || currentDays);
    var kpiRaw = (res === null || res === void 0 ? void 0 : res.tags_kpis) || {};
    var tagsKpis = {
        all_tag_count: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.all_tag_count),
        public_tag_count: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.public_tag_count),
        banks_tag_count: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.banks_tag_count),
        all_tagged_questions: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.all_tagged_questions),
        public_tagged_questions: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.public_tagged_questions),
        banks_tagged_questions: (0, data_center_1.toInt)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.banks_tagged_questions),
        tagged_answered_coverage: (0, data_center_1.pct1)(kpiRaw === null || kpiRaw === void 0 ? void 0 : kpiRaw.tagged_answered_coverage)
    };
    var publicRaw = safeArr(res === null || res === void 0 ? void 0 : res.tags_public).slice(0, 12);
    var banksRaw = safeArr(res === null || res === void 0 ? void 0 : res.tags_banks).slice(0, 12);
    var publicDen = Math.max.apply(Math, __spreadArray([1], publicRaw.map(function (t) { return (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.count); }), false));
    var banksDen = Math.max.apply(Math, __spreadArray([1], banksRaw.map(function (t) { return (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.count); }), false));
    var tagsPublic = publicRaw.map(function (t, idx) {
        var count = (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.count);
        return {
            key: String((t === null || t === void 0 ? void 0 : t.tag) || idx),
            tag: String((t === null || t === void 0 ? void 0 : t.tag) || ''),
            count: count,
            answered: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.answered),
            accuracy: (0, data_center_1.pct1)(t === null || t === void 0 ? void 0 : t.accuracy),
            mistakes_times: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.mistakes_times),
            favorites: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.favorites),
            bar_count_pct: (0, data_center_1.pct1)((count * 100) / publicDen)
        };
    });
    var tagsBanks = banksRaw.map(function (t, idx) {
        var count = (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.count);
        return {
            key: String((t === null || t === void 0 ? void 0 : t.tag) || idx),
            tag: String((t === null || t === void 0 ? void 0 : t.tag) || ''),
            count: count,
            answered: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.answered),
            accuracy: (0, data_center_1.pct1)(t === null || t === void 0 ? void 0 : t.accuracy),
            mistakes_times: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.mistakes_times),
            favorites: (0, data_center_1.toInt)(t === null || t === void 0 ? void 0 : t.favorites),
            bar_count_pct: (0, data_center_1.pct1)((count * 100) / banksDen)
        };
    });
    return {
        payload: payload,
        data: {
            inited: true,
            window_days: windowDays,
            errorMsg: '',
            tags_kpis: tagsKpis,
            health_score: (0, data_center_1.toInt)(res === null || res === void 0 ? void 0 : res.health_score),
            tags_public: tagsPublic,
            tags_banks: tagsBanks
        }
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
        console.error('[data-center-v2] setData failed:', err);
        return false;
    }
}
function buildCompatPayloadSafe(res, tab) {
    try {
        return (0, data_center_echarts_1.buildDataCenterCompatPayload)(res, tab);
    }
    catch (err) {
        console.error('[data-center-v2] buildDataCenterCompatPayload failed:', tab, err);
        return { active_tab: tab, window_days: (0, data_center_1.normalizeDays)((res === null || res === void 0 ? void 0 : res.window_days) || 30) };
    }
}
function buildTabVm(tab, res, days) {
    if (tab === 'global') {
        var payload = buildCompatPayloadSafe(res, 'global');
        var vm = buildGlobalViewModel(res, days);
        return { payload: payload, data: vm.fullData, fallbackData: vm.fallbackData };
    }
    if (tab === 'banks')
        return buildBankViewModel(res, days);
    if (tab === 'mistakes')
        return buildMistakesViewModel(res, days);
    if (tab === 'favorites')
        return buildFavoritesViewModel(res, days);
    return buildTagsViewModel(res, days);
}
Page({
    data: __assign(__assign({}, (theme_1.themeManager.getPageData())), { loading: false, inited: false, errorMsg: '', tab: 'global', tabTitle: TAB_META.global.title, tabDesc: TAB_META.global.desc, scrollIntoView: '', lazyStage: 1, ecLazy: { lazyLoad: true }, days: 30, window_days: 30, last_activity_16: '—', all_summary: pickAllSummaryLite({}), health_score: 0, global_insights: [], next_actions: [], weakness_rows: [], recent_mistakes: [], recent_favorites_public: [], bank_summary: {}, total_questions: 0, answered_count: 0, accuracy: 0, window_answered: 0, window_accuracy: 0, subject_rows: [], bank_rows: [], mistakes_new: 0, mistakes_top_items: [], recent_mistakes_bank: [], favorites_new: 0, favorites_density: 0, favorites_top_items: [], recent_favorites_bank: [], tags_kpis: {
            all_tag_count: 0,
            public_tag_count: 0,
            banks_tag_count: 0,
            all_tagged_questions: 0,
            public_tagged_questions: 0,
            banks_tagged_questions: 0,
            tagged_answered_coverage: 0
        }, tags_public: [], tags_banks: [] }),
    onLoad: function (options) {
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        var tab = normalizeTab(options === null || options === void 0 ? void 0 : options.tab);
        var meta = TAB_META[tab] || TAB_META.global;
        this.setData({ tab: tab, tabTitle: meta.title, tabDesc: meta.desc, days: days, window_days: days, lazyStage: 1 });
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
                var stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {}));
                stageMap[_this.data.tab] = 2;
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
        var self = this;
        var tab = normalizeTab(this.data.tab);
        var days = this.data.days;
        var patch = {};
        var hydrated = false;
        try {
            Object.assign(patch, theme_1.themeManager.getPageData());
        }
        catch (e) { }
        var meta = TAB_META[tab] || TAB_META.global;
        patch.tabTitle = meta.title;
        patch.tabDesc = meta.desc;
        try {
            var stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {}));
            patch.lazyStage = Number(stageMap[tab] || 1) || 1;
        }
        catch (e) { }
        if (!this.data.inited || self.__dcResDays !== days) {
            try {
                var cached = (0, data_center_cache_1.getCachedDataCenter)(days);
                if (cached) {
                    self.__dcRes = cached;
                    self.__dcResDays = days;
                    self.__vmCache = {};
                    self.__dcPayloadByTab = {};
                    self.__lastLoadedAt = Date.now();
                    var built = buildTabVm(tab, cached, days);
                    (self.__vmCache || (self.__vmCache = {}))[tab] = built;
                    (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;
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
                                console.error('[data-center-v2] renderCharts failed:', err);
                            }
                        });
                    }
                    : undefined);
            }
        }
        catch (e) { }
        if (!hydrated && (!this.data.inited || self.__dcResDays !== days) && !this.data.loading) {
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
        var self = this;
        self.__dcRes = null;
        self.__dcResDays = 0;
        self.__vmCache = {};
        self.__dcPayloadByTab = {};
        self.__lastLoadedAt = 0;
        self.__lazyStageByTab = {};
        this.setData({ days: days, window_days: days, lazyStage: 1, scrollIntoView: 'dcTop' }, function () {
            _this.setData({ scrollIntoView: '' });
            _this.loadStats(true);
        });
    },
    onTabTap: function (e) {
        var _a, _b;
        var tab = normalizeTab((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab);
        this.switchTab(tab);
    },
    ensureTabVm: function (tab) {
        var self = this;
        var res = self.__dcRes;
        if (!res)
            return null;
        var days = this.data.days;
        var cache = (self.__vmCache || (self.__vmCache = {}));
        if (cache[tab])
            return cache[tab];
        var built = buildTabVm(tab, res, days);
        cache[tab] = built;
        (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;
        return built;
    },
    disposeChartsAndObserver: function () {
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
    switchTab: function (nextTab) {
        var _this = this;
        var self = this;
        var current = normalizeTab(this.data.tab);
        var tab = normalizeTab(nextTab);
        if (tab === current)
            return;
        var stageMap = (self.__lazyStageByTab || (self.__lazyStageByTab = {}));
        stageMap[current] = Number(this.data.lazyStage || 1) || 1;
        var nextStage = Number(stageMap[tab] || 1) || 1;
        this.disposeChartsAndObserver();
        var meta = TAB_META[tab] || TAB_META.global;
        var patch = { tab: tab, tabTitle: meta.title, tabDesc: meta.desc, lazyStage: nextStage, scrollIntoView: 'dcTop', errorMsg: '' };
        if (self.__dcRes && self.__dcResDays === this.data.days) {
            try {
                var built = this.ensureTabVm(tab);
                if (built && built.data)
                    Object.assign(patch, built.data);
            }
            catch (e) { }
        }
        this.setData(patch, function () {
            _this.setData({ scrollIntoView: '' });
            _this.initViewportLazy();
            wx.nextTick(function () {
                try {
                    _this.renderCharts(true);
                }
                catch (e) { }
            });
            if (!self.__dcRes || self.__dcResDays !== _this.data.days) {
                _this.loadStats(true);
            }
        });
    },
    renderCharts: function (forceInit, isDarkOverride) {
        var _this = this;
        if (forceInit === void 0) { forceInit = false; }
        var self = this;
        var tab = normalizeTab(this.data.tab);
        var payload = (self.__dcPayloadByTab || {})[tab];
        if (!payload)
            return;
        if (!self.__pageReady) {
            self.__pendingRender = true;
            return;
        }
        var ids = CHART_IDS_BY_TAB[tab] || [];
        var isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : theme_1.themeManager.isDarkMode();
        var style = theme_1.themeManager.getStyle();
        var tokens = (0, data_center_echarts_1.getDataCenterThemeTokens)(isDark, style);
        var charts = (self.__charts || (self.__charts = {}));
        ids.forEach(function (id) {
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
                    console.error('[data-center-v2] echarts.init failed:', id, err);
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
            var self, now, lastAt, tab, days, stage, res, built, afterSet, meta, ok, fallback, ok2, e_1, raw, msg, nowToast, lastToast;
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
                        tab = normalizeTab(this.data.tab);
                        days = this.data.days;
                        stage = 'init';
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        stage = 'getDataCenter';
                        return [4 /*yield*/, api_1.api.getDataCenter(days)];
                    case 2:
                        res = _a.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(days, res);
                        }
                        catch (e) { }
                        self.__dcRes = res;
                        self.__dcResDays = days;
                        self.__vmCache = {};
                        self.__dcPayloadByTab = {};
                        stage = 'buildViewModel';
                        built = buildTabVm(tab, res, days);
                        (self.__vmCache || (self.__vmCache = {}))[tab] = built;
                        (self.__dcPayloadByTab || (self.__dcPayloadByTab = {}))[tab] = built.payload;
                        afterSet = function () {
                            wx.nextTick(function () {
                                try {
                                    _this.renderCharts(true);
                                }
                                catch (err) {
                                    console.error('[data-center-v2] renderCharts failed:', err);
                                }
                            });
                        };
                        stage = 'setData';
                        meta = TAB_META[tab] || TAB_META.global;
                        ok = trySetData(this, __assign(__assign({}, built.data), { tabTitle: meta.title, tabDesc: meta.desc }), afterSet);
                        if (!ok) {
                            fallback = built.fallbackData || {};
                            ok2 = trySetData(this, __assign(__assign({}, fallback), { tabTitle: meta.title, tabDesc: meta.desc }), afterSet);
                            if (!ok2)
                                trySetData(this, { errorMsg: '数据渲染异常，请稍后再试。' });
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        console.error('[data-center-v2] loadStats failed:', stage, e_1);
                        raw = e_1 && e_1.message ? String(e_1.message) : '加载失败，请稍后再试。';
                        msg = raw.includes('Maximum call stack size exceeded') ? "\u6570\u636E\u6E32\u67D3\u5F02\u5E38\uFF08".concat(stage, "\uFF09\uFF1A").concat(raw) : raw;
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
    },
    onGoMyBanks: function () {
        (0, nav_1.safeNavigate)('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
    },
    onGoSubjectDetail: function (e) {
        var _a, _b, _c, _d;
        var sid = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subjectId) || 0);
        var subject = ((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.subject) ? String(e.currentTarget.dataset.subject) : '';
        if (!Number.isFinite(sid) || sid <= 0)
            return;
        var url = "/pages/subject-detail-v2/subject-detail-v2?id=".concat(encodeURIComponent(String(sid))) +
            (subject ? "&subject=".concat(encodeURIComponent(String(subject))) : '');
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoQuizSubject: function (e) {
        var _a, _b;
        var subject = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subject) || '').trim();
        if (!subject)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=all&subject=".concat(encodeURIComponent(subject));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoQuizBank: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=all&bank_id=".concat(encodeURIComponent(String(bankId)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoBankDetail: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?bank_id=".concat(encodeURIComponent(String(bankId))), 'navigateTo');
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
    onGoBankMistakes: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        (0, nav_1.safeNavigate)("/pages/mistakes-v2/mistakes-v2?bank_id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
    },
    onGoQuizBankMistakes: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=mistakes&bank_id=".concat(encodeURIComponent(String(bankId)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoBankFavorites: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        (0, nav_1.safeNavigate)("/pages/favorites-v2/favorites-v2?bank_id=".concat(encodeURIComponent(String(bankId))), 'redirectTo');
    },
    onGoQuizBankFavorites: function (e) {
        var _a, _b;
        var bankId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.bankId) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var url = "/pages/quiz/quiz?mode=quiz&source=favorites&bank_id=".concat(encodeURIComponent(String(bankId)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onGoTagsCenter: function () {
        (0, nav_1.safeNavigate)('/pages/tags-v2/tags-v2', 'redirectTo');
    },
    onGoTagCenterPublic: function (e) {
        var _a, _b;
        var tag = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) || '').trim();
        if (!tag)
            return;
        (0, nav_1.safeNavigate)("/pages/tags-v2/tags-v2?source=public&tag=".concat(encodeURIComponent(tag)), 'redirectTo');
    },
    onGoTagCenterBanks: function (e) {
        var _a, _b;
        var tag = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) || '').trim();
        if (!tag)
            return;
        (0, nav_1.safeNavigate)("/pages/tags-v2/tags-v2?source=banks&tag=".concat(encodeURIComponent(tag)), 'redirectTo');
    }
});
