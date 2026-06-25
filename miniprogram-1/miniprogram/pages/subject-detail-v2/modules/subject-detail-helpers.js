"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DETAIL_TAB_LABELS = exports.VALID_DETAIL_TABS = exports.DEFAULT_DETAIL_TAB_ORDER = exports.KEY_SHUFFLE_O = exports.KEY_SHUFFLE_Q = exports.OPTION_TYPES = void 0;
exports.normalizeDetailTabOrder = normalizeDetailTabOrder;
exports.buildDetailTabViews = buildDetailTabViews;
exports.getSubjectDetailTabOrderKey = getSubjectDetailTabOrderKey;
exports.readSubjectDetailTabOrder = readSubjectDetailTabOrder;
exports.persistSubjectDetailTabOrder = persistSubjectDetailTabOrder;
exports.scopeFromEntry = scopeFromEntry;
exports.shouldCountForTab = shouldCountForTab;
exports.normalizeTab = normalizeTab;
exports.normalizeReinforceSubTab = normalizeReinforceSubTab;
exports.getStoredString = getStoredString;
exports.setStoredString = setStoredString;
exports.normalizeTextLines = normalizeTextLines;
exports.normalizeSubjectDetailOptions = normalizeSubjectDetailOptions;
exports.getStoredBool = getStoredBool;
exports.setStoredBool = setStoredBool;
exports.clampPct = clampPct;
exports.OPTION_TYPES = new Set(['选择题', '多选题']);
exports.KEY_SHUFFLE_Q = 'shuffle_questions';
exports.KEY_SHUFFLE_O = 'shuffle_options';
exports.DEFAULT_DETAIL_TAB_ORDER = ['practice', 'reinforce', 'exam', 'search', 'stats', 'export', 'share'];
exports.VALID_DETAIL_TABS = new Set(exports.DEFAULT_DETAIL_TAB_ORDER);
exports.DETAIL_TAB_LABELS = {
    practice: '练习',
    reinforce: '加强',
    exam: '考试',
    search: '搜索',
    stats: '数据',
    export: '导出',
    share: '分享'
};
function normalizeDetailTabOrder(input, fallback) {
    var base = Array.isArray(fallback) ? fallback : exports.DEFAULT_DETAIL_TAB_ORDER;
    var out = [];
    var seen = new Set();
    var push = function (k) {
        var key = String(k || '').trim().toLowerCase();
        if (!exports.VALID_DETAIL_TABS.has(key))
            return;
        if (seen.has(key))
            return;
        seen.add(key);
        out.push(key);
    };
    (Array.isArray(input) ? input : []).forEach(push);
    base.forEach(push);
    return out;
}
function buildDetailTabViews(order) {
    var list = Array.isArray(order) ? order : exports.DEFAULT_DETAIL_TAB_ORDER;
    return list.map(function (key) { return ({ key: key, label: exports.DETAIL_TAB_LABELS[key] || key }); });
}
function getSubjectDetailTabOrderKey(subjectId, subjectName) {
    var id = Number(subjectId || 0);
    if (Number.isFinite(id) && id > 0)
        return "subject_".concat(Math.floor(id), "_detail_tab_order_v1");
    var name = String(subjectName || '').trim();
    return name ? "subject_".concat(name, "_detail_tab_order_v1") : '';
}
function readSubjectDetailTabOrder(key, fallback) {
    if (!key)
        return normalizeDetailTabOrder(null, fallback);
    try {
        var raw = wx.getStorageSync(key);
        if (Array.isArray(raw))
            return normalizeDetailTabOrder(raw, fallback);
        if (typeof raw === 'string') {
            var s = raw.trim();
            if (!s)
                return normalizeDetailTabOrder(null, fallback);
            try {
                return normalizeDetailTabOrder(JSON.parse(s), fallback);
            }
            catch (e) {
                return normalizeDetailTabOrder(null, fallback);
            }
        }
        return normalizeDetailTabOrder(null, fallback);
    }
    catch (e) {
        return normalizeDetailTabOrder(null, fallback);
    }
}
function persistSubjectDetailTabOrder(key, order) {
    if (!key)
        return;
    try {
        wx.setStorageSync(key, Array.isArray(order) ? order : []);
    }
    catch (e) { }
}
function scopeFromEntry(entry) {
    if (entry === 'favorites')
        return 'favorites';
    if (entry === 'mistakes')
        return 'mistakes';
    return 'all';
}
function shouldCountForTab(tab) {
    return tab === 'practice' || tab === 'export';
}
function normalizeTab(input) {
    var s = String(input || '').trim().toLowerCase();
    if (s === 'data')
        return 'stats';
    if (s === 'exam')
        return 'exam';
    if (s === 'reinforce' || s === 'strengthen' || s === 'enhance')
        return 'reinforce';
    if (s === 'search')
        return 'search';
    if (s === 'stats')
        return 'stats';
    if (s === 'favorites' || s === 'mistakes')
        return 'practice';
    if (s === 'export')
        return 'export';
    if (s === 'share')
        return 'share';
    return 'practice';
}
function normalizeReinforceSubTab(input) {
    var s = String(input || '').trim().toLowerCase();
    return s === 'similar' ? 'similar' : 'wrong';
}
function getStoredString(key, fallback) {
    try {
        var raw = wx.getStorageSync(key);
        var s = String(raw || '').trim();
        return s ? s : fallback;
    }
    catch (e) {
        return fallback;
    }
}
function setStoredString(key, value) {
    try {
        wx.setStorageSync(key, String(value || ''));
    }
    catch (e) { }
}
function normalizeTextLines(input) {
    var text = String(input !== null && input !== void 0 ? input : '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    var lines = text.split('\n').map(function (s) { return String(s !== null && s !== void 0 ? s : '').replace(/[ \t]+$/g, ''); });
    while (lines.length && !lines[lines.length - 1])
        lines.pop();
    return lines;
}
function normalizeSubjectDetailOptions(rawOptions, qType) {
    var qt = String(qType || '').trim();
    var list = Array.isArray(rawOptions) ? rawOptions : [];
    if (!list.length && qt === '判断题') {
        return [
            { key: '正确', value: '正确' },
            { key: '错误', value: '错误' }
        ];
    }
    var out = [];
    list.forEach(function (opt, idx) {
        var _a, _b;
        if (opt && typeof opt === 'object') {
            var key = String((_a = opt.key) !== null && _a !== void 0 ? _a : '').trim();
            var value = String((_b = opt.value) !== null && _b !== void 0 ? _b : '').trim();
            if (key || value)
                out.push({ key: key || String(idx + 1), value: value });
        }
        else {
            var value = String(opt !== null && opt !== void 0 ? opt : '').trim();
            if (value)
                out.push({ key: String(idx + 1), value: value });
        }
    });
    return out;
}
function getStoredBool(key, fallback) {
    if (fallback === void 0) { fallback = false; }
    try {
        var raw = wx.getStorageSync(key);
        if (raw === true || raw === 1 || raw === '1')
            return true;
        if (raw === false || raw === 0 || raw === '0')
            return false;
        return fallback;
    }
    catch (e) {
        return fallback;
    }
}
function setStoredBool(key, value) {
    try {
        wx.setStorageSync(key, value ? '1' : '0');
    }
    catch (e) { }
}
function clampPct(v) {
    if (!Number.isFinite(v))
        return 0;
    return Math.max(0, Math.min(100, v));
}
