"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.restartTabPageTransition = restartTabPageTransition;
var theme_1 = require("./theme");
var TAB_TRANSITION_CLASS = 'tab-switch-enter';
var TAB_ROUTES = [
    'pages/hub-v2/hub-v2',
    'pages/public-bank-v2/public-bank-v2',
    'pages/my-banks-v2/my-banks-v2',
    'pages/campus/campus',
    'pages/mine/mine',
];
function restartTabPageTransition(page) {
    if (!page || typeof page.setData !== 'function')
        return;
    syncCustomTabBar(page);
    page.setData({ tabPageTransitionClass: '' }, function () {
        setTimeout(function () {
            page.setData({ tabPageTransitionClass: TAB_TRANSITION_CLASS });
        }, 16);
    });
}
function currentTabIndex() {
    var _a;
    try {
        var pages = getCurrentPages();
        var current = pages && pages.length ? pages[pages.length - 1] : null;
        var route = String((current === null || current === void 0 ? void 0 : current.route) || ((_a = current) === null || _a === void 0 ? void 0 : _a.__route__) || '').trim();
        var index = TAB_ROUTES.indexOf(route);
        return index >= 0 ? index : 0;
    }
    catch (e) {
        return 0;
    }
}
function updateTabBar(tabBar, selected) {
    if (!tabBar || typeof tabBar.setData !== 'function')
        return;
    try {
        var themeData = theme_1.themeManager.getPageData();
        tabBar.setData({
            selected: selected,
            switching: false,
            switchingIndex: -1,
            isDarkMode: themeData.isDarkMode,
            themeClass: themeData.themeClass,
            themeStyleClass: themeData.themeStyleClass,
        });
    }
    catch (e) {
        tabBar.setData({ selected: selected, switching: false, switchingIndex: -1 });
    }
}
function syncCustomTabBar(page) {
    var instance = page;
    if (typeof instance.getTabBar !== 'function')
        return;
    var selected = currentTabIndex();
    try {
        var maybe = instance.getTabBar(function (tabBar) { return updateTabBar(tabBar, selected); });
        if (maybe)
            updateTabBar(maybe, selected);
    }
    catch (e) {
        try {
            var tabBar = instance.getTabBar();
            updateTabBar(tabBar, selected);
        }
        catch (err) { }
    }
}
