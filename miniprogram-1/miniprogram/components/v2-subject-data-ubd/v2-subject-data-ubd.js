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
Object.defineProperty(exports, "__esModule", { value: true });
var theme_1 = require("../../utils/theme");
// 主包 components/ec-canvas/echarts 是占位 stub（会抛错），
// 这里显式复用 subject-detail-v2 页面内的完整 ECharts 实现，避免数据页空白。
var echarts = __importStar(require("../../pages/subject-detail-v2/components/ec-canvas/echarts"));
var ubdv2Echarts = __importStar(require("../../utils/ubdv2-echarts"));
function clamp(value, min, max) {
    if (!Number.isFinite(value))
        return min;
    return Math.max(min, Math.min(max, value));
}
function toNum(input) {
    var n = Number(input || 0);
    return Number.isFinite(n) ? n : 0;
}
function fmtCount(n) {
    var v = Math.max(0, Math.floor(toNum(n)));
    try {
        return v.toLocaleString('zh-CN');
    }
    catch (_a) {
        return String(v);
    }
}
function fmtPercent(n) {
    var v = clamp(toNum(n), 0, 100);
    return "".concat(v.toFixed(1), "%");
}
function parseDateTime(raw) {
    var s = String(raw || '').trim();
    if (!s)
        return null;
    try {
        var iso = s.includes('T') ? s : s.replace(' ', 'T');
        var d = new Date(iso);
        if (Number.isNaN(d.getTime()))
            return null;
        return d;
    }
    catch (_a) {
        return null;
    }
}
function daysSince(raw) {
    var d = parseDateTime(raw);
    if (!d)
        return null;
    var diff = Date.now() - d.getTime();
    if (!Number.isFinite(diff))
        return null;
    return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}
function fmtMDHM(raw) {
    var d = parseDateTime(raw);
    if (!d)
        return '—';
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var hh = String(d.getHours()).padStart(2, '0');
    var mm = String(d.getMinutes()).padStart(2, '0');
    return "".concat(m, "-").concat(day, " ").concat(hh, ":").concat(mm);
}
function fmtMD(raw) {
    var d = parseDateTime(raw);
    if (!d)
        return '—';
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return "".concat(m, "-").concat(day);
}
function weekdayFromIsoDate(isoDate) {
    var s = String(isoDate || '').trim();
    if (!/^\d{4}-\d{2}-\d{2}/.test(s))
        return 0;
    try {
        var d = new Date("".concat(s.slice(0, 10), "T00:00:00"));
        if (Number.isNaN(d.getTime()))
            return 0;
        return d.getDay(); // 0 Sunday .. 6 Saturday
    }
    catch (_a) {
        return 0;
    }
}
function buildCalendarCells(trend, statsDays) {
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length)
        return [];
    var maxAnswered = list.reduce(function (m, it) { return Math.max(m, toNum(it.answered)); }, 0) || 0;
    var padStart = weekdayFromIsoDate(list[0].day);
    var cells = [];
    for (var i = 0; i < padStart; i++) {
        cells.push({ key: "pad_s_".concat(i), level: 0, dayText: '' });
    }
    for (var _i = 0, list_1 = list; _i < list_1.length; _i++) {
        var it = list_1[_i];
        var day = String(it.day || '');
        var answered = toNum(it.answered);
        var pct = maxAnswered > 0 ? answered / maxAnswered : 0;
        var level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
        var dayText = /^\d{4}-\d{2}-\d{2}/.test(day) ? day.slice(8, 10) : '';
        cells.push({ key: day || "d_".concat(cells.length), level: level, dayText: dayText });
    }
    var remainder = cells.length % 7;
    if (remainder) {
        var padEnd = 7 - remainder;
        for (var i = 0; i < padEnd; i++) {
            cells.push({ key: "pad_e_".concat(i), level: 0, dayText: '' });
        }
    }
    var cap = clamp(toNum(statsDays) + 16, 14, 110);
    if (cells.length > cap)
        return cells.slice(cells.length - cap);
    return cells;
}
function calcActiveDays(trend) {
    return (trend || []).filter(function (d) { return toNum(d.answered) > 0; }).length;
}
function calcRecentAnswered(trend, days) {
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length)
        return 0;
    var slice = list.slice(Math.max(0, list.length - Math.max(1, Math.floor(days))));
    return slice.reduce(function (sum, it) { return sum + toNum(it.answered); }, 0);
}
function buildHeadline(subtab, overview, trend, statsDays) {
    var activeDays = calcActiveDays(trend);
    var accuracy = toNum(overview.accuracy);
    var completion = toNum(overview.completion);
    var total = toNum(overview.total);
    var answered = toNum(overview.answered);
    var mistakesTimes = toNum(overview.mistakeTimes);
    if (subtab === 'mistakes') {
        return "\u9519\u9898\u6C60 ".concat(fmtCount(total), " \u9898 \u00B7 \u9519\u9898\u6B21\u6570 ").concat(fmtCount(mistakesTimes), " \u00B7 \u8FD1").concat(statsDays, "\u5929\u6D3B\u8DC3").concat(fmtCount(activeDays), "\u5929");
    }
    if (subtab === 'favorites') {
        var todo = Math.max(0, total - answered);
        return "\u6536\u85CF\u6C60 ".concat(fmtCount(total), " \u9898 \u00B7 \u672A\u505A ").concat(fmtCount(todo), " \u9898 \u00B7 \u8FD1").concat(statsDays, "\u5929\u6D3B\u8DC3").concat(fmtCount(activeDays), "\u5929");
    }
    return "\u5168\u5C40\uFF1A\u8986\u76D6\u7387 ".concat(fmtPercent(completion), " \u00B7 \u6B63\u786E\u7387 ").concat(fmtPercent(accuracy), " \u00B7 \u8FD1").concat(statsDays, "\u5929\u6D3B\u8DC3").concat(fmtCount(activeDays), "\u5929");
}
function computeKpis(subtab, overview, trend, statsDays, extras) {
    var _a;
    var total = toNum(overview.total);
    var answered = toNum(overview.answered);
    var correct = toNum(overview.correct);
    var wrong = toNum(overview.wrong);
    var favorites = toNum(overview.favorites);
    var mistakes = toNum(overview.mistakes);
    var mistakeTimes = toNum(overview.mistakeTimes);
    var accuracy = toNum(overview.accuracy);
    var completion = toNum(overview.completion);
    var streakDays = toNum(overview.streakDays);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, Math.max(1, Math.floor(statsDays || 7))));
    var mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;
    if (subtab === 'mistakes') {
        var bankTotal = toNum(extras === null || extras === void 0 ? void 0 : extras.bankTotal);
        var ratio = bankTotal > 0 ? (total * 100) / bankTotal : 0;
        var avgTimes = total > 0 ? mistakeTimes / total : 0;
        var highRisk_1 = 0;
        var aging_1 = 0;
        ((extras === null || extras === void 0 ? void 0 : extras.questions) || []).forEach(function (q) {
            var wc = toNum(q.mistake_wrong_count) || 1;
            if (wc >= 3)
                highRisk_1 += 1;
            var ds = daysSince(q.mistake_updated_at || q.mistake_created_at);
            if (ds != null && ds >= 14)
                aging_1 += 1;
        });
        return [
            { key: 'mis_total', label: '错题池', value: fmtCount(total), meta: bankTotal > 0 ? "\u5360\u9898\u5E93 ".concat(fmtPercent(ratio)) : '—' },
            { key: 'mis_times', label: '累计次数', value: fmtCount(mistakeTimes), meta: "\u5E73\u5747 ".concat(avgTimes.toFixed(1), " \u6B21/\u9898") },
            { key: 'mis_high', label: '高危错题', value: fmtCount(highRisk_1), meta: 'wrong_count ≥ 3' },
            { key: 'mis_aging', label: '冷却错题', value: fmtCount(aging_1), meta: '14天未再错' },
            { key: 'mis_accuracy', label: '复习正确率', value: fmtPercent(accuracy), meta: "\u8FD17\u5929\u590D\u4E60 ".concat(fmtCount(recentAnswered), " \u9898") },
            { key: 'mis_completion', label: '复习覆盖率', value: fmtPercent(completion), meta: '（错题集内）' },
            { key: 'mis_recent', label: '近7天复习', value: fmtCount(recentAnswered), meta: '基于“最后一次作答”' },
        ];
    }
    if (subtab === 'favorites') {
        var todo = Math.max(0, total - answered);
        var added = toNum((_a = ((extras === null || extras === void 0 ? void 0 : extras.favoritesTrend) || {})) === null || _a === void 0 ? void 0 : _a.total_added);
        return [
            { key: 'fav_total', label: '收藏池', value: fmtCount(total), meta: '当前收藏题数' },
            { key: 'fav_answered', label: '已做', value: fmtCount(answered), meta: "\u672A\u505A ".concat(fmtCount(todo), " \u9898") },
            { key: 'fav_accuracy', label: '正确率', value: fmtPercent(accuracy), meta: "\u6B63\u786E ".concat(fmtCount(correct), " / \u5DF2\u505A ").concat(fmtCount(answered)) },
            { key: 'fav_completion', label: '覆盖率', value: fmtPercent(completion), meta: "\u672A\u8986\u76D6 ".concat(fmtPercent(100 - completion)) },
            { key: 'fav_todo', label: '未做收藏', value: fmtCount(todo), meta: '建议优先补齐覆盖' },
            { key: 'fav_recent', label: '近7天复习', value: fmtCount(recentAnswered), meta: '基于“最后一次作答”' },
            { key: 'fav_added', label: '最近新增', value: fmtCount(added), meta: '按收藏时间统计' },
        ];
    }
    return [
        { key: 'total', label: '题库总题', value: fmtCount(total), meta: '题库规模基座' },
        { key: 'answered', label: '已做', value: fmtCount(answered), meta: "\u8FD17\u5929\u4F5C\u7B54 ".concat(fmtCount(recentAnswered), " \u9898") },
        { key: 'accuracy', label: '正确率', value: fmtPercent(accuracy), meta: "\u6B63\u786E ".concat(fmtCount(correct), " / \u5DF2\u505A ").concat(fmtCount(answered)) },
        { key: 'completion', label: '覆盖率', value: fmtPercent(completion), meta: "\u672A\u8986\u76D6 ".concat(fmtPercent(100 - completion)) },
        { key: 'mistakeTimes', label: '错题次数', value: fmtCount(mistakeTimes), meta: "\u9519\u9898\u7387 ".concat(fmtPercent(mistakeRate), " \u00B7 \u9519\u9898\u6C60 ").concat(fmtCount(mistakes), " \u9898") },
        { key: 'favorites', label: '收藏', value: fmtCount(favorites), meta: '收藏池题数' },
        { key: 'mistakes', label: '错题池', value: fmtCount(mistakes), meta: '当前错题池' },
        { key: 'streak', label: '连刷', value: fmtCount(streakDays), meta: '近似连续活跃' },
    ];
}
function computeGauge(subtab, overview, trend, statsDays) {
    var accuracy = toNum(overview.accuracy);
    var completion = toNum(overview.completion);
    var answered = toNum(overview.answered);
    var wrong = toNum(overview.wrong);
    var activeDays = calcActiveDays(trend);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, Math.max(1, Math.floor(statsDays || 7))));
    var mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;
    var score = accuracy * 0.6 + completion * 0.4;
    if (subtab === 'mistakes')
        score = 100 - mistakeRate;
    var label = subtab === 'mistakes' ? '纠错指数' : subtab === 'favorites' ? '收藏掌握度' : '掌握指数';
    var avgPerActiveDay = activeDays > 0 ? recentAnswered / activeDays : 0;
    var pacePercent = clamp((avgPerActiveDay / 20) * 100, 0, 100);
    return {
        gaugeValue: String(Math.round(clamp(score, 0, 100))),
        gaugePercent: clamp(score, 0, 100),
        gaugeLabel: label,
        metricStability: clamp(accuracy, 0, 100),
        metricStabilityText: fmtPercent(accuracy),
        metricPace: clamp(pacePercent, 0, 100),
        metricPaceText: "".concat(avgPerActiveDay.toFixed(1), "/\u5929")
    };
}
function computeTypeChartRows(byType) {
    var list = Array.isArray(byType) ? byType.slice() : [];
    if (!list.length)
        return [];
    var top = list
        .slice()
        .sort(function (a, b) { return toNum(b.answered) - toNum(a.answered); })
        .slice(0, 8);
    var maxAnswered = top.reduce(function (m, it) { return Math.max(m, toNum(it.answered)); }, 0) || 0;
    return top.map(function (it) {
        var correct = toNum(it.correct);
        var wrong = toNum(it.wrong);
        var correctWidth = maxAnswered > 0 ? clamp((correct / maxAnswered) * 100, 0, 100) : 0;
        var wrongWidth = maxAnswered > 0 ? clamp((wrong / maxAnswered) * 100, 0, 100) : 0;
        return {
            q_type: String(it.q_type || '未知'),
            correctWidth: correctWidth,
            wrongWidth: wrongWidth,
            completionText: String(it.completionText || '0.0%')
        };
    });
}
function normalizeDifficultyText(raw) {
    var n = toNum(raw);
    if (!Number.isFinite(n) || n <= 0)
        return '—';
    return String(Math.max(1, Math.floor(n)));
}
function normalizeResult(raw) {
    if (raw === true || raw === 1)
        return { text: '正确', cls: 'ok' };
    if (raw === false || raw === 0)
        return { text: '错误', cls: 'bad' };
    return { text: '—', cls: 'muted' };
}
function buildMistakeMatrixDots(items) {
    var list = Array.isArray(items) ? items : [];
    if (!list.length)
        return [];
    var sample = list.slice(0, 80);
    var maxWrong = sample.reduce(function (m, it) { return Math.max(m, Math.max(1, toNum(it.mistake_wrong_count) || 1)); }, 1);
    var capWrong = clamp(maxWrong, 3, 8);
    var capDays = 30;
    var out = [];
    sample.forEach(function (it) {
        var id = Math.floor(toNum(it.id));
        if (!id)
            return;
        var wc = Math.max(1, toNum(it.mistake_wrong_count) || 1);
        var ds = daysSince(it.mistake_updated_at || it.mistake_created_at);
        if (ds == null)
            return;
        var x = capWrong > 1 ? clamp(((Math.min(wc, capWrong) - 1) / (capWrong - 1)) * 100, 0, 100) : 0;
        var yVal = clamp((Math.min(ds, capDays) / capDays) * 100, 0, 100);
        var y = 100 - yVal;
        var level = wc >= 3 ? 3 : wc === 2 ? 2 : 1;
        out.push({ id: id, x: x, y: y, level: level });
    });
    return out;
}
function buildTopMistakes(items) {
    var list = Array.isArray(items) ? items.slice() : [];
    if (!list.length)
        return [];
    var sorted = list
        .slice()
        .sort(function (a, b) { return (toNum(b.mistake_wrong_count) || 1) - (toNum(a.mistake_wrong_count) || 1); })
        .slice(0, 8);
    var max = sorted.reduce(function (m, it) { return Math.max(m, toNum(it.mistake_wrong_count) || 1); }, 1) || 1;
    return sorted.map(function (it) {
        var id = Math.floor(toNum(it.id));
        var wc = Math.max(1, toNum(it.mistake_wrong_count) || 1);
        var title = String(it.content_preview || '').trim() || "\u9898\u76EE #".concat(id);
        var qt = String(it.q_type || '').trim() || '—';
        var lw = fmtMD(it.mistake_updated_at || it.mistake_created_at);
        var meta = "".concat(qt, " \u00B7 \u6700\u8FD1\u9519\u9898 ").concat(lw);
        var bar = clamp((wc / max) * 100, 0, 100);
        return { id: id, title: title, meta: meta, count: wc, bar: bar };
    });
}
function buildAddedBars(favTrend) {
    var raw = Array.isArray(favTrend === null || favTrend === void 0 ? void 0 : favTrend.trend) ? favTrend.trend : [];
    var list = raw
        .map(function (it) { return ({
        day: String((it === null || it === void 0 ? void 0 : it.day) || ''),
        added: toNum(it === null || it === void 0 ? void 0 : it.added),
    }); })
        .filter(function (it) { return !!it.day; });
    if (!list.length)
        return [];
    var maxAdded = list.reduce(function (m, it) { return Math.max(m, toNum(it.added)); }, 0) || 0;
    var n = list.length;
    return list.map(function (it, idx) {
        var label = it.day ? it.day.slice(5) : '';
        var h = maxAdded > 0 ? clamp((toNum(it.added) / maxAdded) * 100, 0, 100) : 0;
        var showLabel = idx === 0 || idx === n - 1 || (n >= 9 && idx === Math.floor(n / 2));
        return { day: it.day, label: label, added: toNum(it.added), h: h, showLabel: showLabel };
    });
}
function buildMistakeRows(items, limit) {
    if (limit === void 0) { limit = 50; }
    var list = Array.isArray(items) ? items.slice(0, Math.max(0, limit)) : [];
    return list.map(function (q) {
        var id = Math.floor(toNum(q.id));
        var content = String(q.content_preview || '').trim() || "\u9898\u76EE #".concat(id);
        var q_type = String(q.q_type || '').trim() || '—';
        var difficultyText = normalizeDifficultyText(q.difficulty);
        var wc = Math.max(1, toNum(q.mistake_wrong_count) || 1);
        var lastWrong = fmtMDHM(q.mistake_updated_at || q.mistake_created_at);
        var lastAnswer = fmtMDHM(q.last_answered_at);
        var res = normalizeResult(q.last_is_correct);
        return {
            id: id,
            content: content,
            q_type: q_type,
            difficultyText: difficultyText,
            col1: fmtCount(wc),
            col2: lastWrong,
            col3: lastAnswer,
            resultText: res.text,
            resultClass: res.cls
        };
    });
}
function buildFavoriteRows(items, limit) {
    if (limit === void 0) { limit = 50; }
    var list = Array.isArray(items) ? items.slice(0, Math.max(0, limit)) : [];
    return list.map(function (q) {
        var id = Math.floor(toNum(q.id));
        var content = String(q.content_preview || '').trim() || "\u9898\u76EE #".concat(id);
        var q_type = String(q.q_type || '').trim() || '—';
        var difficultyText = normalizeDifficultyText(q.difficulty);
        var favAt = fmtMDHM(q.favorite_created_at);
        var lastAnswer = fmtMDHM(q.last_answered_at);
        var res = normalizeResult(q.last_is_correct);
        return {
            id: id,
            content: content,
            q_type: q_type,
            difficultyText: difficultyText,
            col1: favAt,
            col2: lastAnswer,
            col3: '',
            resultText: res.text,
            resultClass: res.cls
        };
    });
}
function buildTypeDistRows(byType) {
    var list = Array.isArray(byType) ? byType.slice() : [];
    if (!list.length)
        return [];
    var sum = list.reduce(function (m, it) { return m + Math.max(0, toNum(it.total)); }, 0) || 0;
    var rows = list
        .slice()
        .sort(function (a, b) { return toNum(b.total) - toNum(a.total); })
        .slice(0, 12);
    return rows.map(function (it) {
        var total = Math.max(0, toNum(it.total));
        var answered = Math.max(0, toNum(it.answered));
        var accText = String(it.accuracyText || '');
        var bar = sum > 0 ? clamp((total / sum) * 100, 0, 100) : 0;
        var q_type = String(it.q_type || '未知');
        var meta = "\u5171 ".concat(fmtCount(total), " \u9898 \u00B7 \u5DF2\u505A ").concat(fmtCount(answered), " \u00B7 \u6B63\u786E\u7387 ").concat(accText || '—');
        return { q_type: q_type, total: total, bar: bar, meta: meta };
    });
}
function buildCompatByTypeStats(byType) {
    var list = Array.isArray(byType) ? byType.slice() : [];
    return list.map(function (it) {
        var total = Math.max(0, toNum(it.total));
        var answered = Math.max(0, toNum(it.answered));
        var correctRaw = Math.max(0, toNum(it.correct));
        var correct = Math.min(answered, correctRaw);
        var wrongRaw = toNum(it.wrong);
        var wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
        var accuracy = answered > 0 ? clamp((correct * 100) / answered, 0, 100) : 0;
        var completion = total > 0 ? clamp((answered * 100) / total, 0, 100) : 0;
        return {
            q_type: String(it.q_type || '未知'),
            total: total,
            answered: answered,
            correct: correct,
            wrong: wrong,
            favorites: Math.max(0, toNum(it.favorites)),
            mistakes: Math.max(0, toNum(it.mistakes)),
            accuracy: accuracy,
            completion: completion
        };
    });
}
function buildCompatByDifficultyStats(byDifficulty) {
    var list = Array.isArray(byDifficulty) ? byDifficulty.slice() : [];
    return list.map(function (it) {
        var label = String(it.label || it.difficulty || '—');
        var total = Math.max(0, toNum(it.total));
        var answered = Math.max(0, toNum(it.answered));
        var correctRaw = Math.max(0, toNum(it.correct));
        var correct = Math.min(answered, correctRaw);
        var wrongRaw = toNum(it.wrong);
        var wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
        var accuracy = answered > 0 ? clamp((correct * 100) / answered, 0, 100) : 0;
        var completion = total > 0 ? clamp((answered * 100) / total, 0, 100) : 0;
        return { label: label, total: total, answered: answered, correct: correct, wrong: wrong, accuracy: accuracy, completion: completion };
    });
}
function buildCompatStatsPayload(overview, trend, byType, byDifficulty) {
    var total = Math.max(0, toNum(overview.total));
    var answered = Math.max(0, toNum(overview.answered));
    var correctRaw = Math.max(0, toNum(overview.correct));
    var correct = Math.min(answered, correctRaw);
    var wrongRaw = toNum(overview.wrong);
    var wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
    return {
        total_count: total,
        answered: answered,
        correct: correct,
        wrong: wrong,
        favorites: Math.max(0, toNum(overview.favorites)),
        mistakes: Math.max(0, toNum(overview.mistakes)),
        mistakes_times: Math.max(0, toNum(overview.mistakeTimes)),
        accuracy: clamp(toNum(overview.accuracy), 0, 100),
        completion: clamp(toNum(overview.completion), 0, 100),
        streak_days: Math.max(0, toNum(overview.streakDays)),
        last_activity: String(overview.lastText || ''),
        trend: Array.isArray(trend) ? trend : [],
        by_type: buildCompatByTypeStats(byType),
        by_difficulty: buildCompatByDifficultyStats(byDifficulty),
    };
}
function resolveActiveChartIds(subtab, hasDifficulty) {
    if (subtab === 'mistakes') {
        return ['ubdMistakeMatrixChart', 'ubdMistakeTopChart', 'ubdMisTrendChart', 'ubdMisTypePieChart', 'ubdMisDiffChart'];
    }
    if (subtab === 'favorites') {
        return ['ubdFavAddedChart', 'ubdFavTypePieChart', 'ubdFavDiffChart', 'ubdFavReviewTrendChart'];
    }
    var ids = ['ubdCalendarChart', 'ubdGaugeChart', 'ubdTrendChart', 'ubdTypeChart', 'ubdFunnelChart', 'ubdRiskRadarChart'];
    if (hasDifficulty)
        ids.push('ubdDiffChart');
    return ids;
}
Component({
    options: {
        styleIsolation: 'apply-shared',
        addGlobalClass: true
    },
    properties: {
        subjectName: { type: String, value: '' },
        totalCount: { type: Number, value: 0 },
        favCount: { type: Number, value: 0 },
        mistakeCount: { type: Number, value: 0 },
        dataSubTab: { type: String, value: 'global' },
        statsDays: { type: Number, value: 14 },
        stickyTop: { type: String, value: '0rpx' },
        statsLoading: { type: Boolean, value: false },
        statsError: { type: String, value: '' },
        statsOverview: { type: Object, value: {} },
        statsTrend: { type: Array, value: [] },
        statsByType: { type: Array, value: [] },
        statsByDifficulty: { type: Array, value: [] },
        statsHasDifficulty: { type: Boolean, value: false },
        statsAdvice: { type: Array, value: [] },
        // 错题/收藏列表与收藏新增趋势（与 Web 统计页对齐）
        statsQuestions: { type: Array, value: [] },
        favoritesTrend: { type: Object, value: {} },
    },
    data: {
        heroTotalText: '0',
        heroFavText: '0',
        heroMistakeText: '0',
        ecLazy: { lazyLoad: true },
        headlineText: '加载中…',
        updatedAtText: '—',
        kpiItems: [],
        quickStartLabel: '',
        calendarCells: [],
        gaugeValue: '0',
        gaugePercent: 0,
        gaugeLabel: '掌握指数',
        metricStability: 0,
        metricStabilityText: '0.0%',
        metricPace: 0,
        metricPaceText: '0.0%',
        typeChartRows: [],
        typeTableRows: [],
        typeDistRows: [],
        mistakeMatrixDots: [],
        mistakeTopItems: [],
        mistakeRows: [],
        favoriteAddedBars: [],
        favoriteRows: [],
    },
    observers: {
        'totalCount,favCount,mistakeCount': function () {
            this.setData({
                heroTotalText: fmtCount(this.data.totalCount),
                heroFavText: fmtCount(this.data.favCount),
                heroMistakeText: fmtCount(this.data.mistakeCount)
            });
        },
        'dataSubTab,statsDays,statsLoading,statsError,statsOverview,statsTrend,statsByType,totalCount,statsQuestions,favoritesTrend': function () {
            var _this = this;
            var rawSub = String(this.data.dataSubTab || 'global');
            var subtab = rawSub === 'mistakes' || rawSub === 'favorites' ? rawSub : 'global';
            var days = Math.max(1, Math.floor(toNum(this.data.statsDays || 14)));
            var overview = (this.data.statsOverview || {});
            var trend = (this.data.statsTrend || []);
            var byType = (this.data.statsByType || []);
            var questions = (this.data.statsQuestions || []);
            var favTrend = (this.data.favoritesTrend || {});
            var bankTotal = toNum(this.data.totalCount);
            var loading = !!this.data.statsLoading;
            var err = String(this.data.statsError || '').trim();
            var headlineText = '加载中…';
            var updatedAtText = '—';
            var kpiItems = [];
            var calendarCells = [];
            var gauge = {
                gaugeValue: '0',
                gaugePercent: 0,
                gaugeLabel: '掌握指数',
                metricStability: 0,
                metricStabilityText: '0.0%',
                metricPace: 0,
                metricPaceText: '0.0%'
            };
            var typeChartRows = [];
            var typeTableRows = [];
            var typeDistRows = [];
            var mistakeMatrixDots = [];
            var mistakeTopItems = [];
            var mistakeRows = [];
            var favoriteAddedBars = [];
            var favoriteRows = [];
            if (loading) {
                headlineText = '加载中…';
                updatedAtText = '—';
                kpiItems = computeKpis(subtab, {}, [], days, { bankTotal: bankTotal, questions: questions, favoritesTrend: favTrend }).map(function (it) {
                    return Object.assign({}, it, { value: '—', meta: '—' });
                });
            }
            else if (err) {
                headlineText = '数据加载失败，请稍后重试。';
                updatedAtText = '—';
                kpiItems = computeKpis(subtab, {}, [], days, { bankTotal: bankTotal, questions: questions, favoritesTrend: favTrend }).map(function (it) {
                    return Object.assign({}, it, { value: '—', meta: '—' });
                });
            }
            else {
                headlineText = buildHeadline(subtab, overview, trend, days);
                updatedAtText = "\u6700\u8FD1\u6D3B\u8DC3\uFF1A".concat(String(overview.lastText || '—'));
                kpiItems = computeKpis(subtab, overview, trend, days, { bankTotal: bankTotal, questions: questions, favoritesTrend: favTrend });
                if (subtab === 'global') {
                    calendarCells = buildCalendarCells(trend, days);
                    gauge = computeGauge(subtab, overview, trend, days);
                    typeChartRows = computeTypeChartRows(byType);
                    typeTableRows = Array.isArray(byType) ? byType : [];
                }
                else {
                    typeDistRows = buildTypeDistRows(byType);
                }
                if (subtab === 'mistakes') {
                    mistakeMatrixDots = buildMistakeMatrixDots(questions);
                    mistakeTopItems = buildTopMistakes(questions);
                    mistakeRows = buildMistakeRows(questions, 50);
                }
                else if (subtab === 'favorites') {
                    favoriteAddedBars = buildAddedBars(favTrend);
                    favoriteRows = buildFavoriteRows(questions, 50);
                }
            }
            this.setData(__assign({ headlineText: headlineText, updatedAtText: updatedAtText, kpiItems: kpiItems, calendarCells: calendarCells, typeChartRows: typeChartRows, typeTableRows: typeTableRows, typeDistRows: typeDistRows, mistakeMatrixDots: mistakeMatrixDots, mistakeTopItems: mistakeTopItems, mistakeRows: mistakeRows, favoriteAddedBars: favoriteAddedBars, favoriteRows: favoriteRows }, gauge), function () {
                try {
                    _this.scheduleRenderCharts(false);
                }
                catch (e) { }
            });
        }
    },
    lifetimes: {
        ready: function () {
            var _this = this;
            var self = this;
            self.__charts = {};
            self.__renderTimer = null;
            self.__pendingForceInit = false;
            self.__pendingIsDark = undefined;
            self.__themeUnsub = theme_1.themeManager.onThemeChange(function (isDark) {
                try {
                    _this.scheduleRenderCharts(false, isDark);
                }
                catch (e) { }
            });
            this.scheduleRenderCharts(true);
        },
        detached: function () {
            var self = this;
            try {
                this.disposeCharts();
            }
            catch (e) { }
            if (typeof self.__themeUnsub === 'function') {
                try {
                    self.__themeUnsub();
                }
                catch (e) { }
            }
            self.__themeUnsub = null;
            if (self.__renderTimer) {
                try {
                    clearTimeout(self.__renderTimer);
                }
                catch (e) { }
                self.__renderTimer = null;
            }
        }
    },
    methods: {
        onQuickStartTap: function () {
            var raw = String(this.data.dataSubTab || 'global');
            var subtab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
            if (subtab !== 'mistakes' && subtab !== 'favorites')
                return;
            this.triggerEvent('quickstart', { subtab: subtab });
        },
        disposeCharts: function () {
            var self = this;
            var charts = (self.__charts || {});
            Object.keys(charts).forEach(function (k) {
                try {
                    charts[k] && typeof charts[k].dispose === 'function' && charts[k].dispose();
                }
                catch (e) { }
            });
            self.__charts = {};
        },
        scheduleRenderCharts: function (forceInit, isDarkOverride) {
            var _this = this;
            if (forceInit === void 0) { forceInit = false; }
            var self = this;
            if (forceInit)
                self.__pendingForceInit = true;
            if (typeof isDarkOverride === 'boolean')
                self.__pendingIsDark = isDarkOverride;
            if (self.__renderTimer)
                return;
            self.__renderTimer = setTimeout(function () {
                var pendingForce = !!self.__pendingForceInit;
                var pendingIsDark = typeof self.__pendingIsDark === 'boolean' ? self.__pendingIsDark : undefined;
                self.__pendingForceInit = false;
                self.__pendingIsDark = undefined;
                self.__renderTimer = null;
                wx.nextTick(function () {
                    try {
                        _this.renderCharts(pendingForce, pendingIsDark);
                    }
                    catch (e) { }
                });
            }, 0);
        },
        renderCharts: function (forceInit, isDarkOverride) {
            var _this = this;
            if (forceInit === void 0) { forceInit = false; }
            var raw = String(this.data.dataSubTab || 'global');
            var subtab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
            var hasDifficulty = !!this.data.statsHasDifficulty;
            var isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : theme_1.themeManager.isDarkMode();
            var style = theme_1.themeManager.getStyle();
            var tokens = ubdv2Echarts.getUbdv2ThemeTokens(isDark, style);
            var overview = (this.data.statsOverview || {});
            var trend = (this.data.statsTrend || []);
            var byType = (this.data.statsByType || []);
            var byDifficulty = (this.data.statsByDifficulty || []);
            var payload = {
                loading: !!this.data.statsLoading,
                error: String(this.data.statsError || '').trim(),
                stats: buildCompatStatsPayload(overview, trend, byType, byDifficulty),
                questions: (this.data.statsQuestions || []),
                favoritesTrend: (this.data.favoritesTrend || {})
            };
            var activeIds = resolveActiveChartIds(subtab, hasDifficulty);
            var self = this;
            var charts = (self.__charts || (self.__charts = {}));
            Object.keys(charts).forEach(function (id) {
                if (activeIds.indexOf(id) === -1) {
                    try {
                        charts[id] && typeof charts[id].dispose === 'function' && charts[id].dispose();
                    }
                    catch (e) { }
                    delete charts[id];
                }
            });
            activeIds.forEach(function (id) {
                var comp = _this.selectComponent("#".concat(id));
                var existing = charts[id];
                if (!comp || typeof comp.init !== 'function') {
                    if (existing) {
                        try {
                            existing.dispose && existing.dispose();
                        }
                        catch (e) { }
                        delete charts[id];
                    }
                    return;
                }
                if (existing && !forceInit) {
                    try {
                        var opt = ubdv2Echarts.buildUbdv2ChartOption(id, payload, tokens);
                        if (opt)
                            existing.setOption(opt, { notMerge: true, lazyUpdate: false });
                        if (typeof existing.resize === 'function')
                            existing.resize();
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
                        var opt = ubdv2Echarts.buildUbdv2ChartOption(id, payload, tokens);
                        if (opt)
                            chart.setOption(opt, { notMerge: true, lazyUpdate: false });
                    }
                    catch (e) { }
                    return chart;
                });
            });
        },
        onSubTabTap: function (e) {
            var _a, _b;
            var raw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subtab) || 'global');
            var subtab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
            this.triggerEvent('subtabchange', { subtab: subtab });
        },
        onDaysTap: function (e) {
            var _a, _b;
            var days = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.days) || 14);
            if (![7, 14, 30, 90].includes(days))
                return;
            this.triggerEvent('dayschange', { days: days });
        },
        onQuestionTap: function (e) {
            var _a, _b;
            var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
            if (!Number.isFinite(id) || id <= 0)
                return;
            this.triggerEvent('questiontap', { id: id });
        }
    }
});
