"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// app.ts
var theme_1 = require("./utils/theme");
var user_settings_1 = require("./utils/user-settings");
// 启动期尽早读取用户手动主题（避免 Page 首帧使用默认浅色导致白屏闪烁）
try {
    theme_1.themeManager.bootstrap();
}
catch (e) { }
var lastSettingsSyncAt = 0;
function maybeSyncUserSettings() {
    var token = wx.getStorageSync('token');
    if (!token)
        return;
    var now = Date.now();
    if (now - lastSettingsSyncAt < 30000)
        return;
    lastSettingsSyncAt = now;
    (0, user_settings_1.syncUserSettingsFromServer)();
}
var subpackagePreloaded = false;
function preloadCriticalSubpackages() {
    if (subpackagePreloaded)
        return;
    subpackagePreloaded = true;
    try {
        var loadSubpackage = wx.loadSubpackage;
        if (typeof loadSubpackage !== 'function')
            return;
        setTimeout(function () {
            try {
                loadSubpackage({ name: 'packages/data', fail: function () { } });
            }
            catch (e) { }
        }, 200);
    }
    catch (e) { }
}
function patchPageThemeOnce() {
    var g = globalThis;
    if (g.__appThemePagePatched)
        return;
    g.__appThemePagePatched = true;
    var originalPage = g.Page;
    if (typeof originalPage !== 'function')
        return;
    g.Page = function (options) {
        // 注入主题数据，避免组件在首帧拿到 null/undefined（如 v2-drawer 的 themeStyle）
        try {
            var themeData = theme_1.themeManager.getPageData();
            var base = options && options.data && typeof options.data === 'object' ? options.data : {};
            var merged = {};
            for (var k in base) {
                if (!Object.prototype.hasOwnProperty.call(base, k))
                    continue;
                merged[k] = base[k];
            }
            for (var k in themeData) {
                if (!Object.prototype.hasOwnProperty.call(themeData, k))
                    continue;
                merged[k] = themeData[k];
            }
            options.data = merged;
        }
        catch (e) {
            // 忽略异常
        }
        var originalOnLoad = options.onLoad;
        var originalOnShow = options.onShow;
        options.onLoad = function () {
            var args = [];
            for (var _i = 0; _i < arguments.length; _i++) {
                args[_i] = arguments[_i];
            }
            try {
                theme_1.themeManager.applySystemUI();
            }
            catch (e) {
                // 忽略 applySystemUI 失败
            }
            try {
                this.setData(theme_1.themeManager.getPageData());
            }
            catch (e) {
                // 忽略 setData 失败
            }
            return typeof originalOnLoad === 'function' ? originalOnLoad.apply(this, args) : undefined;
        };
        options.onShow = function () {
            var args = [];
            for (var _i = 0; _i < arguments.length; _i++) {
                args[_i] = arguments[_i];
            }
            try {
                theme_1.themeManager.applySystemUI();
            }
            catch (e) {
                // 忽略 applySystemUI 失败
            }
            try {
                this.setData(theme_1.themeManager.getPageData());
            }
            catch (e) {
                // 忽略 setData 失败
            }
            return typeof originalOnShow === 'function' ? originalOnShow.apply(this, args) : undefined;
        };
        return originalPage(options);
    };
}
patchPageThemeOnce();
App({
    globalData: {
        isDarkMode: false,
        themeMode: 'system',
        themeStyle: 'default'
    },
    onLaunch: function () {
        var _this = this;
        // 初始化主题系统
        var themeInfo = theme_1.themeManager.init();
        this.globalData.isDarkMode = themeInfo.isDark;
        this.globalData.themeMode = themeInfo.mode;
        this.globalData.themeStyle = theme_1.themeManager.getStyle();
        maybeSyncUserSettings();
        preloadCriticalSubpackages();
        // 监听主题变化，更新全局数据
        theme_1.themeManager.onThemeChange(function (isDark) {
            _this.globalData.isDarkMode = isDark;
            _this.globalData.themeMode = theme_1.themeManager.getMode();
            _this.globalData.themeStyle = theme_1.themeManager.getStyle();
        });
        // 路由变化时同步系统 UI（兜底覆盖非 safeNavigate 的跳转时机）
        try {
            var g = globalThis;
            if (!g.__appThemeRouteHooked && typeof wx.onAppRoute === 'function') {
                g.__appThemeRouteHooked = true;
                wx.onAppRoute(function () {
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
                        }
                    }
                    catch (e) { }
                });
            }
        }
        catch (e) { }
        // 展示本地存储能力
        var logs = wx.getStorageSync('logs') || [];
        logs.unshift(Date.now());
        wx.setStorageSync('logs', logs);
        // 登录
        wx.login({
            success: function (res) {
                console.log(res.code);
                // 发送 res.code 到后台换取 openId, sessionKey, unionId
            },
        });
    },
    onShow: function () {
        theme_1.themeManager.applySystemUI();
        maybeSyncUserSettings();
    },
});
