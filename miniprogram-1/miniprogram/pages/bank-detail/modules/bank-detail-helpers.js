"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DETAIL_TAB_LABELS = exports.VALID_DETAIL_TABS = exports.DEFAULT_DETAIL_TAB_ORDER = exports.KEY_SHUFFLE_O = exports.KEY_SHUFFLE_Q = exports.OPTION_TYPES = void 0;
exports.normalizeDetailTabOrder = normalizeDetailTabOrder;
exports.buildDetailTabViews = buildDetailTabViews;
exports.getBankDetailTabOrderKey = getBankDetailTabOrderKey;
exports.readBankDetailTabOrder = readBankDetailTabOrder;
exports.persistBankDetailTabOrder = persistBankDetailTabOrder;
exports.normalizeScope = normalizeScope;
exports.shouldCountForTab = shouldCountForTab;
exports.normalizeTab = normalizeTab;
exports.normalizeReinforceSubTab = normalizeReinforceSubTab;
exports.getStoredString = getStoredString;
exports.setStoredString = setStoredString;
exports.normalizeTextLines = normalizeTextLines;
exports.normalizeBankDetailOptions = normalizeBankDetailOptions;
exports.getStoredBool = getStoredBool;
exports.setStoredBool = setStoredBool;
exports.clampPct = clampPct;
exports.parseBoolFlag = parseBoolFlag;
exports.appendFromMiniapp = appendFromMiniapp;
exports.buildExternalWebUrl = buildExternalWebUrl;
var api_1 = require("../../../utils/api");
var web_1 = require("../../../utils/web");
exports.OPTION_TYPES = new Set(['选择题', '多选题']);
exports.KEY_SHUFFLE_Q = 'shuffle_questions';
exports.KEY_SHUFFLE_O = 'shuffle_options';
exports.DEFAULT_DETAIL_TAB_ORDER = ['practice', 'reinforce', 'exam', 'search', 'stats', 'share', 'manage'];
exports.VALID_DETAIL_TABS = new Set(exports.DEFAULT_DETAIL_TAB_ORDER);
exports.DETAIL_TAB_LABELS = {
    practice: '练习',
    reinforce: '加强',
    exam: '考试',
    search: '搜索',
    stats: '数据',
    share: '分享',
    manage: '管理'
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
function buildDetailTabViews(order, canManage) {
    if (canManage === void 0) { canManage = false; }
    var list = Array.isArray(order) ? order : exports.DEFAULT_DETAIL_TAB_ORDER;
    var filtered = canManage ? list : list.filter(function (k) { return k !== 'manage'; });
    return filtered.map(function (key) { return ({ key: key, label: exports.DETAIL_TAB_LABELS[key] || key }); });
}
function getBankDetailTabOrderKey(bankId) {
    var id = Number(bankId || 0);
    if (!Number.isFinite(id) || id <= 0)
        return '';
    return "bank_".concat(Math.floor(id), "_detail_tab_order_v1");
}
function readBankDetailTabOrder(key, fallback) {
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
function persistBankDetailTabOrder(key, order) {
    if (!key)
        return;
    try {
        wx.setStorageSync(key, Array.isArray(order) ? order : []);
    }
    catch (e) { }
}
function normalizeScope(input) {
    var s = String(input || '').trim().toLowerCase();
    if (s === 'favorites')
        return 'favorites';
    if (s === 'mistakes')
        return 'mistakes';
    return 'all';
}
function shouldCountForTab(tab) {
    return tab === 'practice';
}
function normalizeTab(input) {
    var s = String(input || '').trim().toLowerCase();
    if (s === 'data')
        return 'stats';
    if (s === 'exam')
        return 'exam';
    if (s === 'search')
        return 'search';
    if (s === 'stats')
        return 'stats';
    if (s === 'reinforce' || s === 'strengthen' || s === 'enhance')
        return 'reinforce';
    if (s === 'favorites' || s === 'mistakes')
        return 'practice';
    if (s === 'share')
        return 'share';
    if (s === 'manage')
        return 'manage';
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
function normalizeBankDetailOptions(rawOptions, qType) {
    var qt = String(qType || '').trim();
    if (rawOptions == null || rawOptions === '') {
        if (qt === '判断题') {
            return [
                { key: '正确', value: '正确' },
                { key: '错误', value: '错误' }
            ];
        }
        return [];
    }
    var parsed = rawOptions;
    if (typeof rawOptions === 'string') {
        var s = rawOptions.trim();
        if (s) {
            try {
                parsed = JSON.parse(s);
            }
            catch (e) {
                parsed = rawOptions;
            }
        }
    }
    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    var out = [];
    if (Array.isArray(parsed)) {
        parsed.forEach(function (opt, idx) {
            var _a, _b, _c;
            if (opt && typeof opt === 'object') {
                var key = String((_b = (_a = opt.key) !== null && _a !== void 0 ? _a : letters[idx]) !== null && _b !== void 0 ? _b : '').trim();
                var value = String((_c = opt.value) !== null && _c !== void 0 ? _c : '').trim();
                if (key || value)
                    out.push({ key: key || String(idx + 1), value: value });
            }
            else {
                var value = String(opt !== null && opt !== void 0 ? opt : '').trim();
                if (value)
                    out.push({ key: letters[idx] || String(idx + 1), value: value });
            }
        });
        return out;
    }
    if (parsed && typeof parsed === 'object') {
        Object.keys(parsed).forEach(function (k) {
            var _a;
            var key = String(k !== null && k !== void 0 ? k : '').trim();
            var value = String((_a = parsed[k]) !== null && _a !== void 0 ? _a : '').trim();
            if (key || value)
                out.push({ key: key, value: value });
        });
        return out;
    }
    return [];
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
function parseBoolFlag(v, fallback) {
    if (v === true || v === 1 || v === '1')
        return true;
    if (v === false || v === 0 || v === '0')
        return false;
    return fallback;
}
function appendFromMiniapp(url) {
    var raw = String(url || '').trim();
    if (!raw)
        return '';
    if (/([?&])from=/.test(raw))
        return raw;
    return "".concat(raw).concat(raw.includes('?') ? '&' : '?', "from=miniapp");
}
function buildExternalWebUrl(next) {
    var origin = String((0, api_1.getApiOrigin)() || '').trim().replace(/\/$/, '');
    var path = (0, web_1.normalizeWebNextPath)(next, '/hub');
    if (!origin)
        return path;
    return appendFromMiniapp("".concat(origin).concat(path));
}
