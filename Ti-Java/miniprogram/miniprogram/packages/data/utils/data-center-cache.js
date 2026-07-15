"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getCachedDataCenter = getCachedDataCenter;
exports.setCachedDataCenter = setCachedDataCenter;
exports.clearCachedDataCenter = clearCachedDataCenter;
var TTL_MS = 60 * 1000;
var cache = Object.create(null);
function toKey(days) {
    var n = Number(days || 0);
    if (!Number.isFinite(n) || n <= 0)
        return '';
    return String(Math.trunc(n));
}
function getCachedDataCenter(days) {
    var key = toKey(days);
    if (!key)
        return null;
    var entry = cache[key];
    if (!entry)
        return null;
    if (Date.now() - entry.at > TTL_MS)
        return null;
    return entry.res;
}
function setCachedDataCenter(days, res) {
    var key = toKey(days);
    if (!key)
        return;
    cache[key] = { at: Date.now(), res: res };
}
function clearCachedDataCenter(days) {
    if (days == null) {
        Object.keys(cache).forEach(function (k) { return delete cache[k]; });
        return;
    }
    var key = toKey(days);
    if (!key)
        return;
    delete cache[key];
}
