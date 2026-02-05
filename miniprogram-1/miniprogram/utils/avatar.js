"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decorateAvatarUrl = exports.bumpAvatarRev = exports.getAvatarRev = void 0;
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
exports.getAvatarRev = getAvatarRev;
function bumpAvatarRev() {
    var rev = String(Date.now());
    try {
        wx.setStorageSync(AVATAR_REV_KEY, rev);
    }
    catch (e) { }
    return rev;
}
exports.bumpAvatarRev = bumpAvatarRev;
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
exports.decorateAvatarUrl = decorateAvatarUrl;
