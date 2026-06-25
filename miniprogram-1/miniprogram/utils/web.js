"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeWebNextPath = normalizeWebNextPath;
exports.buildWebFrontendUrl = buildWebFrontendUrl;
exports.openWebFrontend = openWebFrontend;
exports.showOpenWebModal = showOpenWebModal;
var nav_1 = require("./nav");
function normalizeWebNextPath(next, fallback) {
    if (fallback === void 0) { fallback = '/hub'; }
    var raw = String(next || '').trim();
    var base = raw || String(fallback || '/hub').trim() || '/hub';
    return base.startsWith('/') ? base : "/".concat(base);
}
function buildWebFrontendUrl(next) {
    var path = normalizeWebNextPath(next, '/hub');
    return "/pages/web-frontend/web-frontend?next=".concat(encodeURIComponent(path));
}
function openWebFrontend(next, navType) {
    if (navType === void 0) { navType = 'navigateTo'; }
    (0, nav_1.safeNavigate)(buildWebFrontendUrl(next), navType);
}
function showOpenWebModal(options) {
    var title = String((options === null || options === void 0 ? void 0 : options.title) || '请前往网页端').trim() || '请前往网页端';
    var content = String((options === null || options === void 0 ? void 0 : options.content) || '').trim();
    var next = normalizeWebNextPath(options === null || options === void 0 ? void 0 : options.next, '/hub');
    var confirmText = String((options === null || options === void 0 ? void 0 : options.confirmText) || '打开网页端').trim() || '打开网页端';
    var cancelText = String((options === null || options === void 0 ? void 0 : options.cancelText) || '取消').trim() || '取消';
    var navType = ((options === null || options === void 0 ? void 0 : options.navType) || 'navigateTo');
    return new Promise(function (resolve) {
        wx.showModal({
            title: title,
            content: content,
            confirmText: confirmText,
            cancelText: cancelText,
            success: function (res) {
                if (res.confirm) {
                    openWebFrontend(next, navType);
                    resolve(true);
                    return;
                }
                resolve(false);
            },
            fail: function () { return resolve(false); }
        });
    });
}
