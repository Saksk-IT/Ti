"use strict";
function normalizeNavKey(raw) {
    var v = String(raw || '').trim().toLowerCase();
    if (v === 'theme' || v === 'about')
        return v;
    return 'account';
}
function normalizeAccTab(raw) {
    var v = String(raw || '').trim().toLowerCase();
    if (v === 'security' || v === 'bindings')
        return v;
    return 'profile';
}
function normalizeAboutTab(raw) {
    var v = String(raw || '').trim().toLowerCase();
    return v === 'legal' ? 'legal' : 'app';
}
function buildTargetUrl(options) {
    var navKey = normalizeNavKey((options === null || options === void 0 ? void 0 : options.navKey) || (options === null || options === void 0 ? void 0 : options.nav) || (options === null || options === void 0 ? void 0 : options.tab));
    var accTab = normalizeAccTab((options === null || options === void 0 ? void 0 : options.accTab) || (options === null || options === void 0 ? void 0 : options.acc) || (options === null || options === void 0 ? void 0 : options.sub));
    var aboutTab = normalizeAboutTab((options === null || options === void 0 ? void 0 : options.aboutTab) || (options === null || options === void 0 ? void 0 : options.about));
    if (navKey === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (navKey === 'about') {
        return aboutTab === 'legal'
            ? '/pages/settings-about-v2/settings-about-v2?aboutTab=legal'
            : '/pages/settings-about-v2/settings-about-v2';
    }
    if (accTab === 'security')
        return '/pages/settings-account-security-v2/settings-account-security-v2';
    if (accTab === 'bindings')
        return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
    var edit = String((options === null || options === void 0 ? void 0 : options.edit) || '');
    return edit === '1'
        ? '/pages/settings-account-profile-v2/settings-account-profile-v2?edit=1'
        : '/pages/settings-account-profile-v2/settings-account-profile-v2';
}
Page({
    onLoad: function (options) {
        wx.redirectTo({ url: buildTargetUrl(options || {}) });
    }
});
