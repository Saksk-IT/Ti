"use strict";
/**
 * theme.ts - 主题管理工具
 *
 * 主题风格：
 * - 'dark': 深色主题
 * - 'default': 默认浅色
 * - 'mist': 雾蓝
 * - 'dune': 暖砂
 * - 'pine': 岩松
 * - 'celadon': 影青
 */
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.themeManager = void 0;
var THEME_STYLE_STORAGE_KEY = 'app_theme_style_v1';
var THEME_PREV_STYLE_KEY = 'app_theme_prev_style_v1'; // 记录切换深色前的风格
var THEME_STYLE_LIST = ['dark', 'default', 'mist', 'dune', 'pine', 'celadon'];
var LIGHT_STYLE_LIST = ['default', 'mist', 'dune', 'pine', 'celadon'];
// 全局主题风格
var currentThemeStyle = 'dune';
var prevLightStyle = 'dune'; // 切换深色前的浅色风格
// 全局主题状态
var currentThemeInfo = {
    isDark: false
};
var bootstrapped = false;
// 主题变更回调列表
var themeChangeCallbacks = [];
function getStoredThemeStyle() {
    try {
        var stored = wx.getStorageSync(THEME_STYLE_STORAGE_KEY);
        if (stored && THEME_STYLE_LIST.includes(stored)) {
            return stored;
        }
    }
    catch (e) {
        console.warn('读取主题风格失败:', e);
    }
    return 'dune';
}
function getStoredPrevLightStyle() {
    try {
        var stored = wx.getStorageSync(THEME_PREV_STYLE_KEY);
        if (stored && LIGHT_STYLE_LIST.includes(stored)) {
            return stored;
        }
    }
    catch (e) {
        console.warn('读取上次浅色风格失败:', e);
    }
    return 'dune';
}
function saveThemeStyle(style) {
    try {
        wx.setStorageSync(THEME_STYLE_STORAGE_KEY, style);
    }
    catch (e) {
        console.warn('保存主题风格失败:', e);
    }
}
function savePrevLightStyle(style) {
    try {
        wx.setStorageSync(THEME_PREV_STYLE_KEY, style);
    }
    catch (e) {
        console.warn('保存上次浅色风格失败:', e);
    }
}
/**
 * 判断风格是否为深色
 */
function isDarkStyle(style) {
    return style === 'dark';
}
function getThemeClass(style) {
    return isDarkStyle(style) ? 'theme-dark' : 'theme-light';
}
function getThemeStyleClass(style) {
    if (!style || style === 'default' || style === 'dark')
        return '';
    return "theme-style-".concat(style);
}
function getCtaColorHex(style) {
    var isDark = isDarkStyle(style);
    if (style === 'mist')
        return '#F97316';
    if (style === 'dune')
        return isDark ? '#E7A46A' : '#EA580C';
    if (style === 'pine')
        return isDark ? '#63D29C' : '#2DBA7D';
    if (style === 'celadon')
        return '#EA580C';
    if (style === 'dark')
        return '#007AFF';
    return '#007AFF';
}
function getBackgroundColorHex(style) {
    var isDark = isDarkStyle(style);
    if (style === 'dark')
        return '#000000';
    if (style === 'mist')
        return isDark ? '#0C111A' : '#EEF2FF';
    if (style === 'dune')
        return isDark ? '#15110D' : '#FDFBF7';
    if (style === 'pine')
        return isDark ? '#0E1411' : '#F3F7F4';
    if (style === 'celadon')
        return isDark ? '#0D1314' : '#F0FDFA';
    return isDark ? '#000000' : '#F2F2F7';
}
function applyBackgroundStyle(style, done) {
    var bg = getBackgroundColorHex(style);
    var isDark = isDarkStyle(style);
    var doneCalled = false;
    var callDone = function () {
        if (!done || doneCalled)
            return;
        doneCalled = true;
        try {
            done();
        }
        catch (e) { }
    };
    if (done) {
        try {
            setTimeout(callDone, 80);
        }
        catch (e) { }
    }
    if (typeof wx.setBackgroundColor === 'function') {
        try {
            wx.setBackgroundColor({
                backgroundColor: bg,
                backgroundColorTop: bg,
                backgroundColorBottom: bg,
                success: function () { return callDone(); },
                fail: function () { return callDone(); }
            });
        }
        catch (e) {
            // 忽略 setBackgroundColor 异常
            callDone();
        }
    }
    else {
        callDone();
    }
    if (typeof wx.setBackgroundTextStyle === 'function') {
        try {
            wx.setBackgroundTextStyle({ textStyle: isDark ? 'light' : 'dark', fail: function () { } });
        }
        catch (e) {
            // 忽略 setBackgroundTextStyle 异常
        }
    }
}
function applyTabBarStyle(style) {
    var isDark = isDarkStyle(style);
    if (typeof wx.setTabBarStyle !== 'function')
        return;
    try {
        wx.setTabBarStyle({
            color: isDark ? '#8E8E93' : '#7A7E83',
            selectedColor: getCtaColorHex(style),
            backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
            borderStyle: isDark ? 'white' : 'black',
            fail: function () { }
        });
    }
    catch (e) {
        // 忽略 setTabBarStyle 异常
    }
}
/**
 * 通知所有页面主题变更
 */
function notifyThemeChange() {
    var style = currentThemeStyle;
    var isDark = isDarkStyle(style);
    var themeClass = getThemeClass(style);
    var themeStyleClass = getThemeStyleClass(style);
    var themeCtaColor = getCtaColorHex(style);
    currentThemeInfo.isDark = isDark;
    // 调用所有注册的回调
    themeChangeCallbacks.forEach(function (callback) {
        try {
            callback(isDark);
        }
        catch (e) {
            console.error('主题变更回调执行失败:', e);
        }
    });
    // 获取所有页面并尝试更新
    var pages = getCurrentPages();
    pages.forEach(function (page) {
        if (page && typeof page.onThemeChange === 'function') {
            try {
                page.onThemeChange(isDark);
            }
            catch (e) {
                console.error('页面主题变更处理失败:', e);
            }
        }
        // 更新页面主题数据
        if (page && page.setData) {
            try {
                page.setData({
                    isDarkMode: isDark,
                    themeClass: themeClass,
                    themeStyle: style,
                    themeStyleClass: themeStyleClass,
                    themeCtaColor: themeCtaColor
                });
            }
            catch (e) {
                // 忽略setData失败
            }
        }
    });
    applyTabBarStyle(style);
    applyBackgroundStyle(style);
}
/**
 * 主题管理器
 */
exports.themeManager = {
    /**
     * 启动期提前读取本地配置并同步系统 UI。
     * 目的：让 Page 注册阶段注入的默认主题数据就是正确的，避免手动深色下切页"先白后黑"闪烁。
     */
    bootstrap: function () {
        if (bootstrapped)
            return __assign({}, currentThemeInfo);
        bootstrapped = true;
        currentThemeStyle = getStoredThemeStyle();
        prevLightStyle = getStoredPrevLightStyle();
        var isDark = isDarkStyle(currentThemeStyle);
        currentThemeInfo = {
            isDark: isDark
        };
        applyTabBarStyle(currentThemeStyle);
        applyBackgroundStyle(currentThemeStyle);
        return __assign({}, currentThemeInfo);
    },
    /**
     * 初始化主题系统（应在 app.ts onLaunch 中调用）
     */
    init: function () {
        this.bootstrap();
        return __assign({}, currentThemeInfo);
    },
    /**
     * 获取当前主题信息
     */
    getThemeInfo: function () {
        this.bootstrap();
        return __assign({}, currentThemeInfo);
    },
    /**
     * 获取当前是否为深色模式
     */
    isDarkMode: function () {
        return currentThemeInfo.isDark;
    },
    getStyle: function () {
        return currentThemeStyle;
    },
    setStyle: function (style) {
        if (!style || !THEME_STYLE_LIST.includes(style)) {
            console.warn('无效的主题风格:', style);
            return;
        }
        var prev = currentThemeStyle;
        // 如果从浅色切换到深色，记录当前浅色风格
        if (!isDarkStyle(prev) && isDarkStyle(style)) {
            prevLightStyle = prev;
            savePrevLightStyle(prev);
        }
        currentThemeStyle = style;
        saveThemeStyle(style);
        if (prev !== style) {
            notifyThemeChange();
        }
    },
    /**
     * 在浅色风格之间循环（不包括深色）
     */
    cycleStyle: function () {
        var idx = LIGHT_STYLE_LIST.indexOf(currentThemeStyle);
        var next = LIGHT_STYLE_LIST[(idx + 1) % LIGHT_STYLE_LIST.length];
        this.setStyle(next);
        return next;
    },
    /**
     * 在所有风格之间循环（包括深色）
     */
    cycleAllStyles: function () {
        var idx = THEME_STYLE_LIST.indexOf(currentThemeStyle);
        var next = THEME_STYLE_LIST[(idx + 1) % THEME_STYLE_LIST.length];
        this.setStyle(next);
        return next;
    },
    getStyleName: function (style) {
        var s = style || currentThemeStyle;
        switch (s) {
            case 'dark':
                return '深色';
            case 'mist':
                return '雾蓝';
            case 'dune':
                return '暖砂';
            case 'pine':
                return '岩松';
            case 'celadon':
                return '影青';
            default:
                return '灰白';
        }
    },
    /**
     * 切换深色/暖砂
     * 顶部按钮固定在"暖砂"和"深色"之间切换
     * 太阳 = 暖砂，月亮 = 深色
     */
    toggleDark: function () {
        if (isDarkStyle(currentThemeStyle)) {
            // 从深色切换到暖砂
            this.setStyle('dune');
            return false;
        }
        else {
            // 从任何浅色切换到深色
            this.setStyle('dark');
            return true;
        }
    },
    /**
     * 注册主题变更回调
     */
    onThemeChange: function (callback) {
        themeChangeCallbacks.push(callback);
        // 返回取消注册的函数
        return function () {
            var index = themeChangeCallbacks.indexOf(callback);
            if (index > -1) {
                themeChangeCallbacks.splice(index, 1);
            }
        };
    },
    /**
     * 获取用于页面的主题相关数据
     * 可在页面 onLoad/onShow 中调用并 setData
     */
    getPageData: function () {
        this.bootstrap();
        return {
            isDarkMode: currentThemeInfo.isDark,
            themeClass: getThemeClass(currentThemeStyle),
            themeStyle: currentThemeStyle,
            themeStyleClass: getThemeStyleClass(currentThemeStyle),
            themeCtaColor: getCtaColorHex(currentThemeStyle)
        };
    },
    /**
     * 应用主题到系统 UI（如 tabBar）
     */
    applySystemUI: function () {
        this.bootstrap();
        applyTabBarStyle(currentThemeStyle);
        applyBackgroundStyle(currentThemeStyle);
    },
    applySystemUIAsync: function () {
        var _this = this;
        return new Promise(function (resolve) {
            _this.bootstrap();
            try {
                applyTabBarStyle(currentThemeStyle);
            }
            catch (e) { }
            try {
                applyBackgroundStyle(currentThemeStyle, function () { return resolve(); });
            }
            catch (e) {
                resolve();
            }
        });
    },
    /**
     * 获取主题相关的导航栏配置
     */
    getNavBarStyle: function () {
        return {
            background: currentThemeInfo.isDark ? '#1C1C1E' : '#FFFFFF',
            color: currentThemeInfo.isDark ? 'white' : 'black'
        };
    },
    /**
     * 获取主题图标（用于UI显示）
     */
    getThemeIcon: function () {
        return currentThemeInfo.isDark ? '🌙' : '☀';
    },
    // ========== 兼容旧代码的方法 ==========
    /**
     * 获取当前模式（兼容旧代码）
     * 新系统中不再区分 mode，深色作为风格之一
     */
    getMode: function () {
        return isDarkStyle(currentThemeStyle) ? 'dark' : 'light';
    },
    /**
     * 设置模式（兼容旧代码）
     * 新系统中：dark -> 切换到深色风格，light -> 切换回上次浅色风格，system -> 同 light
     */
    setMode: function (mode) {
        if (mode === 'dark') {
            this.setStyle('dark');
        }
        else {
            // light 或 system 都切换回浅色
            if (isDarkStyle(currentThemeStyle)) {
                this.setStyle(prevLightStyle);
            }
        }
    },
    /**
     * 循环切换模式（兼容旧代码）
     * 新系统中：直接切换深色/浅色
     */
    cycleMode: function () {
        this.toggleDark();
        return this.getMode();
    },
    /**
     * 获取模式名称（兼容旧代码）
     */
    getModeName: function () {
        return isDarkStyle(currentThemeStyle) ? '深色' : '浅色';
    }
};
exports.default = exports.themeManager;
