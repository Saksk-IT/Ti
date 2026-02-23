"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AI_EXPLAIN_CACHE_KEY_PREFIX = void 0;
exports.getAIExplainCacheKey = getAIExplainCacheKey;
exports.readAIExplainCache = readAIExplainCache;
exports.writeAIExplainCache = writeAIExplainCache;
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
