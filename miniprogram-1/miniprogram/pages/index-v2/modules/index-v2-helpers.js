"use strict";
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
exports.qTypesCache = exports.examPresetApplied = exports.DEFAULT_PICKED_TYPES = exports.FALLBACK_PUBLIC_Q_TYPES = exports.SYSTEM_TEMPLATES = exports.QUICK_PRESETS = void 0;
exports.clampInt = clampInt;
exports.clampFloat = clampFloat;
exports.formatNum = formatNum;
exports.todayStamp = todayStamp;
exports.setDataAsync = setDataAsync;
exports.uniqueBanks = uniqueBanks;
exports.buildSubjectOptions = buildSubjectOptions;
exports.buildBankOptions = buildBankOptions;
exports.findOptionLabel = findOptionLabel;
exports.normalizeTemplateConfig = normalizeTemplateConfig;
exports.buildTemplateScopeLabel = buildTemplateScopeLabel;
exports.distributeCounts = distributeCounts;
exports.QUICK_PRESETS = [
    { duration: 15, total: 20, label: '15 分钟 · 20 题' },
    { duration: 30, total: 30, label: '30 分钟 · 30 题' },
    { duration: 60, total: 50, label: '60 分钟 · 50 题' }
];
exports.SYSTEM_TEMPLATES = [
    {
        id: 'quick-15',
        title: '速测 15 分钟',
        total: 20,
        duration: 15,
        preferred: ['单选题', '判断题'],
        tags: ['碎片时间', '基础回顾'],
        note: '适合课后小测与快速复盘。'
    },
    {
        id: 'standard-45',
        title: '标准 45 分钟',
        total: 40,
        duration: 45,
        preferred: ['单选题', '多选题', '判断题'],
        tags: ['综合覆盖', '模拟节奏'],
        note: '覆盖主流题型，节奏接近模拟考试。'
    },
    {
        id: 'focus-60',
        title: '专项 60 分钟',
        total: 60,
        duration: 60,
        preferred: ['多选题', '综合题', '简答题'],
        tags: ['强化', '高权重'],
        note: '偏重综合与高分题型，适合冲刺阶段。'
    }
];
exports.FALLBACK_PUBLIC_Q_TYPES = ['单选题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
exports.DEFAULT_PICKED_TYPES = ['单选题', '多选题', '判断题'];
exports.examPresetApplied = false;
exports.qTypesCache = new Map();
function clampInt(v, fallback, minV, maxV) {
    var n = Math.floor(Number(v));
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(minV, Math.min(maxV, n));
}
function clampFloat(v, fallback, minV, maxV) {
    var n = Number(v);
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(minV, Math.min(maxV, n));
}
function formatNum(n) {
    var v = Number(n);
    if (!Number.isFinite(v))
        return '0';
    if (Math.abs(v - Math.round(v)) < 1e-6)
        return String(Math.round(v));
    return String(v.toFixed(2)).replace(/\.?0+$/, '');
}
function todayStamp() {
    var now = new Date();
    var y = String(now.getFullYear());
    var m = String(now.getMonth() + 1).padStart(2, '0');
    var d = String(now.getDate()).padStart(2, '0');
    return "".concat(y, "-").concat(m, "-").concat(d);
}
function setDataAsync(ctx, patch) {
    return new Promise(function (resolve) { return ctx.setData(patch, resolve); });
}
function uniqueBanks(list) {
    var map = new Map();
    (list || []).forEach(function (b) {
        var id = Number(b && b.id);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var name = String(b.name || '').trim();
        if (!name)
            return;
        var question_count = Number(b.question_count || 0) || 0;
        map.set(id, { id: id, name: name, question_count: question_count });
    });
    return Array.from(map.values());
}
function buildSubjectOptions(subjects) {
    var rest = (subjects || [])
        .filter(function (s) { return typeof s === 'string' && s.trim(); })
        .map(function (s) { return String(s).trim(); });
    return __spreadArray([{ value: 'all', label: '全部科目' }], rest.map(function (s) { return ({ value: s, label: s }); }), true);
}
function buildBankOptions(banks) {
    return (banks || []).map(function (b) { return ({
        value: b.id,
        label: b.question_count ? "".concat(b.name, "\uFF08").concat(b.question_count, "\u9898\uFF09") : b.name
    }); });
}
function findOptionLabel(options, value, fallback) {
    var hit = (options || []).find(function (o) { return o && o.value === value; });
    return hit ? hit.label : fallback;
}
function normalizeTemplateConfig(raw) {
    var _a, _b;
    if (!raw || typeof raw !== 'object')
        return null;
    var source = String(raw.source || 'public').toLowerCase() === 'user_bank' ? 'user_bank' : 'public';
    var subject = String(raw.subject || 'all').trim() || 'all';
    var bank_id = raw.bank_id != null && raw.bank_id !== '' ? Number(raw.bank_id) : null;
    var duration = clampInt(raw.duration, 60, 1, 1440);
    var typesRaw = raw.types && typeof raw.types === 'object' ? raw.types : {};
    var scoresRaw = raw.scores && typeof raw.scores === 'object' ? raw.scores : {};
    var types = {};
    var scores = {};
    Object.keys(typesRaw || {}).forEach(function (k) {
        var name = String(k || '').trim();
        if (!name)
            return;
        var c = clampInt(typesRaw[k], 0, 0, 500);
        if (c <= 0)
            return;
        types[name] = c;
        scores[name] = clampFloat(scoresRaw[k], 1, 0, 1000);
    });
    var targetTotal = (_b = (_a = raw.targetTotal) !== null && _a !== void 0 ? _a : raw.total) !== null && _b !== void 0 ? _b : raw.target_total;
    targetTotal = clampInt(targetTotal, 0, 0, 300);
    if (!targetTotal) {
        targetTotal = Object.values(types).reduce(function (sum, v) { return sum + (Number(v) || 0); }, 0);
        targetTotal = clampInt(targetTotal, 0, 0, 300);
    }
    return {
        source: source,
        subject: subject,
        bank_id: source === 'user_bank' ? (Number.isFinite(bank_id) ? bank_id : null) : null,
        duration: duration,
        targetTotal: targetTotal,
        types: types,
        scores: scores
    };
}
function buildTemplateScopeLabel(cfg, bankLabel) {
    if (cfg.source === 'user_bank')
        return bankLabel ? "\u4E2A\u4EBA\u9898\u5E93 \u00B7 ".concat(bankLabel) : '个人题库';
    return "\u516C\u5171\u9898\u5E93 \u00B7 ".concat(cfg.subject === 'all' ? '全部科目' : cfg.subject);
}
function distributeCounts(targetTotal, enabledTypes) {
    var cfg = {};
    var n = enabledTypes.length;
    if (n <= 0)
        return cfg;
    var target = clampInt(targetTotal, 30, 1, 300);
    var base = Math.floor(target / n);
    var rem = target % n;
    enabledTypes.forEach(function (t) {
        var want = base + (rem > 0 ? 1 : 0);
        if (rem > 0)
            rem -= 1;
        cfg[t.name] = Math.min(want, Math.max(0, t.available));
    });
    var assignedTotal = Object.values(cfg).reduce(function (s, v) { return s + (Number(v) || 0); }, 0);
    var remaining = target - assignedTotal;
    var safety = 5000;
    while (remaining > 0 && safety-- > 0) {
        var progressed = false;
        for (var _i = 0, enabledTypes_1 = enabledTypes; _i < enabledTypes_1.length; _i++) {
            var t = enabledTypes_1[_i];
            if (remaining <= 0)
                break;
            var cap = Math.max(0, t.available) - (cfg[t.name] || 0);
            if (cap > 0) {
                cfg[t.name] = (cfg[t.name] || 0) + 1;
                remaining -= 1;
                progressed = true;
            }
        }
        if (!progressed)
            break;
    }
    assignedTotal = Object.values(cfg).reduce(function (s, v) { return s + (Number(v) || 0); }, 0);
    if (assignedTotal <= 0) {
        enabledTypes.forEach(function (t) {
            cfg[t.name] = Math.min(1, Math.max(0, t.available));
        });
    }
    return cfg;
}
