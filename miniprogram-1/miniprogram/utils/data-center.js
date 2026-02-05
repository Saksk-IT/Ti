"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildTopMix = exports.buildHeatmapGrid = exports.buildTrendBars = exports.pct1 = exports.toInt = exports.normalizeDays = void 0;
function normalizeDays(input) {
    var n = Number(input || 30);
    if (n === 7 || n === 30 || n === 90)
        return n;
    return 30;
}
exports.normalizeDays = normalizeDays;
function toInt(v) {
    var n = Number(v);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
}
exports.toInt = toInt;
function pct1(v) {
    var n = Number(v);
    if (!Number.isFinite(n))
        return 0;
    return Math.round(n * 10) / 10;
}
exports.pct1 = pct1;
function buildTrendBars(dailyRaw, dailyMax) {
    var max = Math.max(toInt(dailyMax), 1);
    var rows = Array.isArray(dailyRaw) ? dailyRaw : [];
    return rows.map(function (d) {
        var total = toInt(d === null || d === void 0 ? void 0 : d.total);
        var correct = toInt(d === null || d === void 0 ? void 0 : d.correct);
        var acc = pct1(d === null || d === void 0 ? void 0 : d.accuracy);
        var barPct = max > 0 ? pct1((total * 100) / max) : 0;
        var fillPct = total > 0 ? pct1((correct * 100) / total) : 0;
        return {
            day: String((d === null || d === void 0 ? void 0 : d.day) || ''),
            total: total,
            correct: correct,
            accuracy: acc,
            barPct: barPct,
            fillPct: fillPct
        };
    });
}
exports.buildTrendBars = buildTrendBars;
function buildHeatmapGrid(all, maxValue) {
    var max = Math.max(toInt(maxValue), 1);
    var grid = Array.from({ length: 7 }, function () { return Array.from({ length: 24 }, function () { return 0; }); });
    var rows = Array.isArray(all) ? all : [];
    rows.forEach(function (item) {
        if (!item || item.length < 3)
            return;
        var day = toInt(item[0]);
        var hour = toInt(item[1]);
        var val = toInt(item[2]);
        if (day < 0 || day > 6)
            return;
        if (hour < 0 || hour > 23)
            return;
        grid[day][hour] = val;
    });
    return grid.map(function (row, dayIndex) { return ({
        dayIndex: dayIndex,
        cells: row.map(function (val) {
            var level = val <= 0 ? 0 : Math.min(4, Math.ceil((val / max) * 4));
            return { level: level, value: val };
        })
    }); });
}
exports.buildHeatmapGrid = buildHeatmapGrid;
function buildTopMix(subjects, banks, limit) {
    if (limit === void 0) { limit = 8; }
    var items = [];
    (Array.isArray(subjects) ? subjects : []).forEach(function (s) {
        var name = (s === null || s === void 0 ? void 0 : s.subject) ? String(s.subject) : '公共题库';
        items.push({ name: "\u516C\u00B7".concat(name), answered: toInt(s === null || s === void 0 ? void 0 : s.answered), accuracy: pct1(s === null || s === void 0 ? void 0 : s.accuracy) });
    });
    (Array.isArray(banks) ? banks : []).forEach(function (b) {
        var name = (b === null || b === void 0 ? void 0 : b.name) ? String(b.name) : '个人题库';
        items.push({ name: "\u4E2A\u00B7".concat(name), answered: toInt(b === null || b === void 0 ? void 0 : b.answered), accuracy: pct1(b === null || b === void 0 ? void 0 : b.accuracy) });
    });
    return items.sort(function (a, b) { return b.answered - a.answered; }).slice(0, limit);
}
exports.buildTopMix = buildTopMix;
