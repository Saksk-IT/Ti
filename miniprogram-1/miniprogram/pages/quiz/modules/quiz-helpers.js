"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AI_EXPLAIN_CACHE_KEY_PREFIX = void 0;
exports.getAIExplainCacheKey = getAIExplainCacheKey;
exports.readAIExplainCache = readAIExplainCache;
exports.writeAIExplainCache = writeAIExplainCache;
exports.normalizeOptionItems = normalizeOptionItems;
exports.parseIdList = parseIdList;
exports.safeFromCodePoint = safeFromCodePoint;
exports.decodeHtmlEntities = decodeHtmlEntities;
exports.stripHtmlToText = stripHtmlToText;
exports.uniqUrls = uniqUrls;
exports.resolveInlineUrl = resolveInlineUrl;
exports.extractInlineImageUrls = extractInlineImageUrls;
var api_1 = require("../../../utils/api");
exports.AI_EXPLAIN_CACHE_KEY_PREFIX = 'saksk_ai_explain_v1_';
function getAIExplainCacheKey(qid) {
    return "".concat(exports.AI_EXPLAIN_CACHE_KEY_PREFIX).concat(qid);
}
function readAIExplainCache(qid) {
    if (!qid)
        return '';
    try {
        var cached = wx.getStorageSync(getAIExplainCacheKey(qid));
        if (!cached)
            return '';
        if (typeof cached === 'string')
            return cached;
        if (typeof cached === 'object' && typeof cached.explain === 'string')
            return cached.explain;
    }
    catch (e) {
        // ignore
    }
    return '';
}
function writeAIExplainCache(qid, explain) {
    if (!qid)
        return;
    var text = (explain || '').toString().trim();
    if (!text)
        return;
    try {
        wx.setStorageSync(getAIExplainCacheKey(qid), { v: 1, explain: text, updatedAt: Date.now() });
    }
    catch (e) {
        // ignore
    }
}
var OPTION_ALPHA_SEED = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
var OPTION_DIGIT_SEED = '123456789';
function parseExplicitOptionPrefix(text) {
    var match = text.match(/^([A-Za-z]|\d{1,2})\s*([、.．:：])\s*(.+)$/);
    if (!match)
        return null;
    var rawKey = match[1].trim();
    var delimiter = match[2];
    var value = match[3].trim();
    if (!rawKey || !value)
        return null;
    if (/^\d+$/.test(rawKey) && (delimiter === '.' || delimiter === '．') && /^\d/.test(value)) {
        return null;
    }
    return { key: rawKey.slice(0, 1).toUpperCase(), value: value };
}
function compactAlphaKey(text) {
    var first = text.slice(0, 1).toUpperCase();
    var second = text.slice(1, 2);
    if (!first || OPTION_ALPHA_SEED.indexOf(first) < 0 || !second)
        return '';
    if (/^[A-Za-z0-9]$/.test(second))
        return '';
    return first;
}
function compactDigitKey(text) {
    var first = text.slice(0, 1);
    var second = text.slice(1, 2);
    if (!/^\d$/.test(first) || !second)
        return '';
    if (!/[\u3400-\u9fff]/.test(second))
        return '';
    return first;
}
function isSequential(keys, seed) {
    if (!keys.length)
        return false;
    return keys.every(function (key, index) { return key === seed.slice(index, index + 1); });
}
function getCompactOptionKeys(texts) {
    var keyed = texts
        .map(function (text, index) { return ({ text: text, index: index }); })
        .filter(function (item) { return !!item.text; });
    if (!keyed.length)
        return {};
    var alphaKeys = keyed.map(function (item) { return compactAlphaKey(item.text); });
    if (alphaKeys.every(Boolean) && isSequential(alphaKeys, OPTION_ALPHA_SEED)) {
        return keyed.reduce(function (acc, item, index) {
            acc[item.index] = alphaKeys[index];
            return acc;
        }, {});
    }
    var digitKeys = keyed.map(function (item) { return compactDigitKey(item.text); });
    if (digitKeys.every(Boolean) && isSequential(digitKeys, OPTION_DIGIT_SEED)) {
        return keyed.reduce(function (acc, item, index) {
            acc[item.index] = digitKeys[index];
            return acc;
        }, {});
    }
    return {};
}
function normalizeOptionItems(rawOptions, valueFormatter) {
    if (valueFormatter === void 0) { valueFormatter = stripHtmlToText; }
    var optList = rawOptions;
    if (typeof optList === 'string') {
        var s = optList.trim();
        if (!s) {
            optList = [];
        }
        else {
            try {
                optList = JSON.parse(s);
            }
            catch (e) {
                optList = [s];
            }
        }
    }
    if (!Array.isArray(optList)) {
        optList = [];
    }
    var texts = optList.map(function (item) { return (item && typeof item === 'object' ? '' : valueFormatter(item)); });
    var compactKeys = getCompactOptionKeys(texts);
    var options = [];
    optList.forEach(function (item, index) {
        if (item && typeof item === 'object') {
            var rawKey = item.key;
            var rawValue = item.value;
            var key = String(rawKey == null ? '' : rawKey).trim();
            var value = valueFormatter(rawValue);
            if (key || value) {
                options.push({ key: key, value: value, answerValue: key || value });
            }
            return;
        }
        var s = texts[index] || '';
        if (!s)
            return;
        var explicit = parseExplicitOptionPrefix(s);
        if (explicit) {
            options.push({ key: explicit.key, value: explicit.value, answerValue: explicit.key });
            return;
        }
        var compactKey = compactKeys[index];
        if (compactKey) {
            var value = s.slice(1).replace(/^[\s:：,，.．、\)\]]+/, '').trim();
            options.push({ key: compactKey, value: value, answerValue: compactKey });
            return;
        }
        options.push({ key: '', value: s, answerValue: s });
    });
    if (options.length > 0 && options.every(function (x) { return !(x.key || '').trim(); })) {
        options.forEach(function (x, i) {
            x.key = OPTION_ALPHA_SEED.slice(i, i + 1) || String(i + 1);
            x.answerValue = x.key;
        });
    }
    return options;
}
function parseIdList(raw, maxLen) {
    if (maxLen === void 0) { maxLen = 200; }
    if (raw == null)
        return [];
    var s = String(raw || '').trim();
    try {
        if (/%[0-9A-Fa-f]{2}/.test(s)) {
            s = decodeURIComponent(s);
        }
    }
    catch (e) {
        // 忽略解码失败
    }
    s = s.replace(/，/g, ',').trim();
    if (!s)
        return [];
    var parts = s.split(',').map(function (x) { return String(x || '').trim(); }).filter(Boolean);
    var out = [];
    var seen = new Set();
    for (var _i = 0, parts_1 = parts; _i < parts_1.length; _i++) {
        var p = parts_1[_i];
        if (out.length >= maxLen)
            break;
        var n = Number(p);
        if (!Number.isFinite(n) || n <= 0)
            continue;
        var id = Math.floor(n);
        if (seen.has(id))
            continue;
        seen.add(id);
        out.push(id);
    }
    return out;
}
function safeFromCodePoint(n) {
    if (!Number.isFinite(n) || n <= 0 || n > 0x10ffff)
        return '';
    try {
        return String.fromCodePoint(n);
    }
    catch (e) {
        return '';
    }
}
function decodeHtmlEntities(input) {
    var s = String(input || '');
    if (!s)
        return '';
    if (!s.includes('&') && !s.includes('&#'))
        return s;
    return s
        .replace(/&nbsp;/g, ' ')
        .replace(/&emsp;/g, '  ')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&#x([0-9a-fA-F]+);/g, function (_, hex) { return safeFromCodePoint(parseInt(hex, 16)); })
        .replace(/&#([0-9]+);/g, function (_, num) { return safeFromCodePoint(parseInt(num, 10)); });
}
function stripHtmlToText(input) {
    var raw = String(input || '');
    if (!raw)
        return '';
    var s0 = raw.replace(/\r\n/g, '\n');
    var looksLikeHtml = /<\/?[a-z][\s>]/i.test(s0);
    var out = s0;
    if (looksLikeHtml) {
        out = out
            .replace(/<\s*(script|style)\b[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
            .replace(/<\s*br\s*\/?\s*>/gi, '\n')
            .replace(/<\/\s*(p|div|pre|code|blockquote|h[1-6])\s*>/gi, '\n')
            .replace(/<\/\s*li\s*>/gi, '\n')
            .replace(/<\s*li\b[^>]*>/gi, '\n- ')
            .replace(/<\s*img\b[^>]*>/gi, '')
            .replace(/<[^>]+>/g, '');
    }
    out = decodeHtmlEntities(out);
    out = out
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
    return out;
}
function uniqUrls(urls) {
    var set = new Set();
    var out = [];
    (urls || []).forEach(function (u) {
        var v = String(u || '').trim();
        if (!v || set.has(v))
            return;
        set.add(v);
        out.push(v);
    });
    return out;
}
function resolveInlineUrl(src) {
    var raw = String(src || '').trim();
    if (!raw)
        return '';
    if (raw.startsWith('data:') || raw.startsWith('blob:'))
        return '';
    if (/^https?:\/\//i.test(raw))
        return raw;
    if (raw.startsWith('//'))
        return "https:".concat(raw);
    return (0, api_1.resolveUploadUrl)(raw);
}
function extractInlineImageUrls(content) {
    var raw = String(content || '');
    if (!raw)
        return [];
    var out = [];
    // HTML <img src="...">
    var imgRe = /<\s*img\b[^>]*\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))/gi;
    var m = null;
    while ((m = imgRe.exec(raw))) {
        var src = decodeHtmlEntities((m[1] || m[2] || m[3] || '').trim());
        var url = resolveInlineUrl(src);
        if (url)
            out.push(url);
    }
    // Markdown ![alt](url)
    var mdRe = /!\[[^\]]*]\(([^)\s]+)(?:\s+[^)]*)?\)/g;
    while ((m = mdRe.exec(raw))) {
        var src = decodeHtmlEntities(String(m[1] || '').trim().replace(/^['"]|['"]$/g, ''));
        var url = resolveInlineUrl(src);
        if (url)
            out.push(url);
    }
    return uniqUrls(out);
}
