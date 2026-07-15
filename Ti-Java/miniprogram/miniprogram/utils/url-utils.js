"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getApiBaseUrl = getApiBaseUrl;
exports.getApiOrigin = getApiOrigin;
exports.maybeUpgradeToHttps = maybeUpgradeToHttps;
exports.resolveUploadUrl = resolveUploadUrl;
exports.normalizeImageUrls = normalizeImageUrls;
// URL 工具函数（从 api-endpoints.ts 提取）
var config_1 = require("./config");
function getApiBaseUrl() {
    return config_1.config.getApiUrl();
}
function getApiOriginFromBaseUrl(apiBaseUrl) {
    return apiBaseUrl.replace(/\/api\/?$/, '');
}
function getApiOrigin() {
    return getApiOriginFromBaseUrl(getApiBaseUrl());
}
function isPrivateHostname(hostname) {
    var h = String(hostname || '').trim().toLowerCase();
    if (!h)
        return true;
    if (h === 'localhost')
        return true;
    if (h.endsWith('.local'))
        return true;
    var m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (!m)
        return false;
    var a = Number(m[1]);
    var b = Number(m[2]);
    var c = Number(m[3]);
    var d = Number(m[4]);
    if (![a, b, c, d].every(function (n) { return Number.isFinite(n) && n >= 0 && n <= 255; }))
        return false;
    if (a === 127)
        return true;
    if (a === 10)
        return true;
    if (a === 192 && b === 168)
        return true;
    if (a === 172 && b >= 16 && b <= 31)
        return true;
    if (a === 169 && b === 254)
        return true;
    return false;
}
function maybeUpgradeToHttps(url) {
    var raw = String(url || '').trim();
    if (!/^http:\/\//i.test(raw))
        return raw;
    try {
        if ((0, config_1.getWxPlatform)() === 'devtools')
            return raw;
    }
    catch (e) { }
    var noScheme = raw.replace(/^http:\/\//i, '');
    var slashIdx = noScheme.indexOf('/');
    var hostPort = slashIdx === -1 ? noScheme : noScheme.slice(0, slashIdx);
    var rest = slashIdx === -1 ? '' : noScheme.slice(slashIdx);
    if (!hostPort)
        return raw;
    var parts = hostPort.split(':');
    var host = String(parts[0] || '').trim();
    var portRaw = parts.length > 1 ? String(parts[1] || '').trim() : '';
    var portNum = portRaw ? Number(portRaw) : NaN;
    var port = Number.isFinite(portNum) && portNum > 0 && portNum <= 65535 ? Math.floor(portNum) : undefined;
    if (!host)
        return raw;
    if (isPrivateHostname(host))
        return raw;
    if (typeof port === 'number' && port !== 80)
        return raw;
    var finalHostPort = typeof port === 'number' && port === 80 ? host : hostPort;
    return "https://".concat(finalHostPort).concat(rest);
}
// 将后端存储的相对路径转换为可访问的完整 URL
function resolveUploadUrl(input) {
    var API_ORIGIN = maybeUpgradeToHttps(getApiOrigin());
    if (input == null)
        return '';
    var raw = String(input).trim();
    if (!raw || raw === '[]')
        return '';
    if (/^https?:\/\//i.test(raw))
        return maybeUpgradeToHttps(raw);
    if (raw.startsWith('/uploads/'))
        return "".concat(API_ORIGIN).concat(raw);
    if (raw.startsWith('uploads/'))
        return "".concat(API_ORIGIN, "/").concat(raw);
    if (raw.startsWith('/'))
        return "".concat(API_ORIGIN).concat(raw);
    return "".concat(API_ORIGIN, "/uploads/").concat(raw);
}
function normalizeImagePathList(input) {
    if (Array.isArray(input)) {
        return input
            .map(function (p) { return resolveUploadUrl(p); })
            .filter(function (p) { return typeof p === 'string' && p.length > 0; });
    }
    if (input && typeof input === 'object') {
        var content = input.content || input.question || input.stem || input.images;
        return normalizeImagePathList(content);
    }
    if (typeof input === 'string') {
        var url = resolveUploadUrl(input);
        return url ? [url] : [];
    }
    return [];
}
// 兼容 image_path 可能为：单路径字符串、JSON 数组字符串、JSON 对象字符串、数组
function normalizeImageUrls(imagePath) {
    if (imagePath == null)
        return [];
    if (Array.isArray(imagePath)) {
        return normalizeImagePathList(imagePath);
    }
    var raw = String(imagePath).trim();
    if (!raw || raw === '[]')
        return [];
    if (raw.startsWith('[') || raw.startsWith('{')) {
        try {
            var parsed = JSON.parse(raw);
            return normalizeImagePathList(parsed);
        }
        catch (e) {
            // 忽略 JSON 解析失败，走单路径兜底
        }
    }
    var url = resolveUploadUrl(raw);
    return url ? [url] : [];
}
