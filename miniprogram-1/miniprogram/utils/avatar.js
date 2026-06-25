"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getAvatarRev = getAvatarRev;
exports.bumpAvatarRev = bumpAvatarRev;
exports.decorateAvatarUrl = decorateAvatarUrl;
var AVATAR_REV_KEY = 'avatar_rev_v1';
function getAvatarRev() {
    try {
        var v = wx.getStorageSync(AVATAR_REV_KEY);
        return v == null ? '' : String(v);
    }
    catch (e) {
        return '';
    }
}
function bumpAvatarRev() {
    var rev = String(Date.now());
    try {
        wx.setStorageSync(AVATAR_REV_KEY, rev);
    }
    catch (e) { }
    return rev;
}
function decorateAvatarUrl(url) {
    var raw = String(url || '').trim();
    if (!raw)
        return '';
    var rev = getAvatarRev().trim();
    if (!rev)
        return raw;
    var sep = raw.includes('?') ? '&' : '?';
    return "".concat(raw).concat(sep, "v=").concat(encodeURIComponent(rev));
}
