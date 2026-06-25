"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.safeNavigate = safeNavigate;
exports.consumePendingMiniRedirect = consumePendingMiniRedirect;
var theme_1 = require("./theme");
var NAV_LOCK_MS = 350;
var STACK_SOFT_LIMIT = 8;
var lastNavAt = 0;
var lastNavTarget = '';
function toRoutePath(url) {
    var raw = String(url || '').trim();
    var path = raw.split('?')[0] || '';
    return path.startsWith('/') ? path.slice(1) : path;
}
function getCurrentRoutePath() {
    try {
        var pages = getCurrentPages();
        var cur = pages && pages.length ? pages[pages.length - 1] : null;
        return String((cur === null || cur === void 0 ? void 0 : cur.route) || (cur === null || cur === void 0 ? void 0 : cur.__route__) || '');
    }
    catch (e) {
        return '';
    }
}
function normalizeType(input) {
    var t = String(input || '').trim();
    if (t === 'switchTab' || t === 'navigateTo' || t === 'redirectTo' || t === 'reLaunch')
        return t;
    return 'redirectTo';
}
function getPageStackLength() {
    try {
        var pages = getCurrentPages();
        return Array.isArray(pages) ? pages.length : 0;
    }
    catch (e) {
        return 0;
    }
}
function attempt(type, url, onFail, onSuccess) {
    var ok = function () {
        try {
            if (typeof onSuccess === 'function')
                onSuccess();
        }
        catch (e) { }
    };
    if (type === 'switchTab') {
        wx.switchTab({ url: url, success: function () { return ok(); }, fail: function () { return onFail(); } });
        return;
    }
    if (type === 'redirectTo') {
        wx.redirectTo({ url: url, success: function () { return ok(); }, fail: function () { return onFail(); } });
        return;
    }
    if (type === 'reLaunch') {
        wx.reLaunch({ url: url, success: function () { return ok(); }, fail: function () { return onFail(); } });
        return;
    }
    wx.navigateTo({ url: url, success: function () { return ok(); }, fail: function () { return onFail(); } });
}
/**
 * 安全跳转：优先按 navType 执行，失败时自动降级（解决页面栈过深/跳 tabBar 等导致的静默失败）
 */
function safeNavigate(url, navType) {
    var targetUrl = String(url || '').trim();
    if (!targetUrl)
        return;
    // 防止重复触发（例如侧边栏关闭 setData 尚未渲染时连续触发导航）
    var now = Date.now();
    if (now - lastNavAt < NAV_LOCK_MS && targetUrl === lastNavTarget)
        return;
    lastNavAt = now;
    lastNavTarget = targetUrl;
    var current = getCurrentRoutePath();
    var targetRoute = toRoutePath(targetUrl);
    if (current && targetRoute && current === targetRoute && !targetUrl.includes('?'))
        return;
    var isDataCenterSubRoute = targetRoute === 'pages/history-v2/history-v2' ||
        targetRoute === 'pages/data-banks-v2/data-banks-v2' ||
        targetRoute === 'pages/data-trend-v2/data-trend-v2' ||
        targetRoute === 'pages/data-ai-v2/data-ai-v2' ||
        targetRoute === 'packages/data/pages/data-center-v2/data-center-v2' ||
        targetRoute === 'packages/data/pages/data-global-v2/data-global-v2' ||
        targetRoute === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
        targetRoute === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
        targetRoute === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
        targetRoute === 'packages/data/pages/data-tags-v2/data-tags-v2';
    // 数据中心五大子页（全局/题库/错题/收藏/标签）之间切换：更像「同页 tab 切换」
    // - 避免 navigateTo 堆栈不断增长
    // - 避免 reLaunch 的“先白屏再出现”观感
    var isDataCenterTabRoute = targetRoute === 'packages/data/pages/data-center-v2/data-center-v2' ||
        targetRoute === 'packages/data/pages/data-global-v2/data-global-v2' ||
        targetRoute === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
        targetRoute === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
        targetRoute === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
        targetRoute === 'packages/data/pages/data-tags-v2/data-tags-v2';
    var isCurrentDataCenterTabRoute = current === 'packages/data/pages/data-center-v2/data-center-v2' ||
        current === 'packages/data/pages/data-global-v2/data-global-v2' ||
        current === 'packages/data/pages/data-bank-v2/data-bank-v2' ||
        current === 'packages/data/pages/data-mistakes-v2/data-mistakes-v2' ||
        current === 'packages/data/pages/data-favorites-v2/data-favorites-v2' ||
        current === 'packages/data/pages/data-tags-v2/data-tags-v2';
    var isDataCenterTabSwitch = isDataCenterTabRoute && isCurrentDataCenterTabRoute;
    var primary = normalizeType(navType);
    var stackLen = getPageStackLength();
    var stackFull = stackLen >= 10;
    var stackTight = stackLen >= STACK_SOFT_LIMIT;
    // 统一切页策略：以深色模式的“顺滑切页”为基准
    // 1) 导航前先同步原生背景色/TabBar（避免浅色/主题风格下出现“全白屏”）
    // 2) 栈不紧张时优先使用 navigateTo 触发系统自带滑动过渡；栈过深再降级 redirectTo/reLaunch
    var preferNavigateTo = !stackTight && primary !== 'switchTab' && !isDataCenterTabSwitch && !(primary === 'reLaunch' && isDataCenterSubRoute);
    var chain = primary === 'switchTab'
        ? ['switchTab', 'reLaunch', 'redirectTo', 'navigateTo']
        : primary === 'navigateTo'
            ? (stackFull ? ['redirectTo', 'reLaunch', 'navigateTo', 'switchTab'] : ['navigateTo', 'redirectTo', 'reLaunch', 'switchTab'])
            : preferNavigateTo && primary === 'reLaunch'
                ? ['navigateTo', 'reLaunch', 'redirectTo', 'switchTab']
                : preferNavigateTo
                    ? ['navigateTo', 'redirectTo', 'reLaunch', 'switchTab']
                    : primary === 'reLaunch'
                        ? ['reLaunch', 'redirectTo', 'navigateTo', 'switchTab']
                        : ['redirectTo', 'reLaunch', 'navigateTo', 'switchTab'];
    var afterSuccess = function () {
        try {
            theme_1.themeManager.applySystemUI();
        }
        catch (e) { }
        try {
            var nextTick = wx.nextTick;
            if (typeof nextTick === 'function') {
                nextTick(function () {
                    try {
                        theme_1.themeManager.applySystemUI();
                    }
                    catch (e) { }
                });
                return;
            }
        }
        catch (e) { }
        setTimeout(function () {
            try {
                theme_1.themeManager.applySystemUI();
            }
            catch (e) { }
        }, 0);
    };
    var run = function (idx) {
        if (idx >= chain.length) {
            wx.showToast({ title: '跳转失败', icon: 'none' });
            return;
        }
        attempt(chain[idx], targetUrl, function () { return run(idx + 1); }, afterSuccess);
    };
    var start = function () { return run(0); };
    var scheduleStart = function () {
        // 延迟到下一帧，给 setData（如关闭抽屉）一次渲染机会，减少“跳动/闪烁”
        try {
            var nextTick = wx.nextTick;
            if (typeof nextTick === 'function') {
                nextTick(start);
                return;
            }
        }
        catch (e) { }
        setTimeout(start, 0);
    };
    // 导航前先同步一次系统 UI（背景色/TabBar），并等待原生背景色应用（兜底），减少主题切页白屏
    var applyAsync = theme_1.themeManager.applySystemUIAsync;
    if (typeof applyAsync === 'function') {
        try {
            Promise.resolve(applyAsync.call(theme_1.themeManager))
                .catch(function () { })
                .finally(function () { return scheduleStart(); });
            return;
        }
        catch (e) { }
    }
    try {
        theme_1.themeManager.applySystemUI();
    }
    catch (e) { }
    scheduleStart();
}
var PENDING_MINI_REDIRECT_KEY = 'pendingMiniRedirect';
/** 消费并返回待跳转的小程序页面路径（一次性读取后清除） */
function consumePendingMiniRedirect() {
    try {
        var raw = wx.getStorageSync(PENDING_MINI_REDIRECT_KEY);
        var url = String(raw || '').trim();
        if (!url)
            return '';
        wx.removeStorageSync(PENDING_MINI_REDIRECT_KEY);
        if (!url.startsWith('/'))
            return '';
        return url;
    }
    catch (e) {
        return '';
    }
}
