"use strict";
/**
 * font.ts - 字体样式管理工具
 *
 * 支持多套字体样式，独立于主题风格：
 * - 'system': 系统默认 - 使用系统字体栈
 * - 'elegant': 优雅 - 思源宋体标题 + 思源黑体正文
 * - 'modern': 现代 - 思源黑体 Medium
 * - 'rounded': 圆润 - 圆体风格
 * - 'classic': 经典 - 衬线标题 + 无衬线正文
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.fontManager = exports.LINE_HEIGHT = exports.FONT_WEIGHT = exports.FONT_SIZE = exports.FONT_STYLE_CONFIG = exports.FONT_STYLE_LIST = void 0;
var FONT_STYLE_STORAGE_KEY = 'app_font_style_v1';
var FONT_LOADED_CACHE_KEY = 'app_fonts_loaded_v1';
exports.FONT_STYLE_LIST = ['system', 'elegant', 'modern', 'rounded', 'classic'];
// 使用 jsDelivr CDN 加载思源字体（免费、稳定、国内可访问）
var WEB_FONTS = {
    elegant: [
        {
            family: 'Noto Serif SC',
            source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc@5.0.19/files/noto-serif-sc-chinese-simplified-400-normal.woff2") format("woff2")',
            weight: '400'
        }
    ],
    modern: [
        {
            family: 'Noto Sans SC',
            source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5.0.19/files/noto-sans-sc-chinese-simplified-500-normal.woff2") format("woff2")',
            weight: '500'
        }
    ],
    rounded: [
        {
            family: 'ZCOOL KuaiLe',
            source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/zcool-kuaile@5.0.19/files/zcool-kuaile-chinese-simplified-400-normal.woff2") format("woff2")',
            weight: '400'
        }
    ],
    classic: [
        {
            family: 'Noto Serif SC',
            source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc@5.0.19/files/noto-serif-sc-chinese-simplified-400-normal.woff2") format("woff2")',
            weight: '400'
        }
    ]
};
// 已加载的字体缓存
var loadedFonts = new Set();
/**
 * 加载网络字体
 */
function loadWebFont(config) {
    var fontKey = "".concat(config.family, "-").concat(config.weight || '400');
    // 已加载过则跳过
    if (loadedFonts.has(fontKey)) {
        return Promise.resolve(true);
    }
    return new Promise(function (resolve) {
        wx.loadFontFace({
            family: config.family,
            source: config.source,
            scopes: ['webview', 'native'],
            success: function () {
                console.log("\u5B57\u4F53\u52A0\u8F7D\u6210\u529F: ".concat(config.family));
                loadedFonts.add(fontKey);
                resolve(true);
            },
            fail: function (err) {
                console.warn("\u5B57\u4F53\u52A0\u8F7D\u5931\u8D25: ".concat(config.family), err);
                resolve(false);
            }
        });
    });
}
/**
 * 加载指定样式所需的字体
 */
function loadFontsForStyle(style) {
    return __awaiter(this, void 0, void 0, function () {
        var fonts, promises;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (style === 'system')
                        return [2 /*return*/];
                    fonts = WEB_FONTS[style];
                    if (!fonts || fonts.length === 0)
                        return [2 /*return*/];
                    promises = fonts.map(function (font) { return loadWebFont(font); });
                    return [4 /*yield*/, Promise.all(promises)];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    });
}
// 字体样式配置
exports.FONT_STYLE_CONFIG = {
    system: {
        id: 'system',
        name: '系统默认',
        description: '使用设备原生字体',
        titleFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
        bodyFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
        monoFont: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
    },
    elegant: {
        id: 'elegant',
        name: '优雅',
        description: '思源宋体，文艺气质',
        titleFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", serif',
        bodyFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", serif',
        monoFont: '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
    },
    modern: {
        id: 'modern',
        name: '现代',
        description: '思源黑体，简约专业',
        titleFont: '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
        bodyFont: '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
        monoFont: '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
    },
    rounded: {
        id: 'rounded',
        name: '圆润',
        description: '站酷快乐体，亲和可爱',
        titleFont: '"ZCOOL KuaiLe", "Yuanti SC", "Yuanti TC", "PingFang SC", -apple-system, BlinkMacSystemFont, sans-serif',
        bodyFont: '"ZCOOL KuaiLe", "Yuanti SC", "Yuanti TC", "PingFang SC", -apple-system, BlinkMacSystemFont, sans-serif',
        monoFont: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
    },
    classic: {
        id: 'classic',
        name: '经典',
        description: '思源宋体，传统稳重',
        titleFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", Georgia, "Times New Roman", serif',
        bodyFont: '"Noto Serif SC", "Source Han Serif SC", "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif',
        monoFont: '"Courier New", Courier, "Liberation Mono", monospace'
    }
};
// 字体大小规范
exports.FONT_SIZE = {
    // 标题
    h1: '44rpx',
    h2: '40rpx',
    h3: '36rpx',
    h4: '32rpx',
    // 正文
    body: '28rpx',
    bodyLarge: '30rpx',
    bodySmall: '26rpx',
    // 辅助
    caption: '24rpx',
    small: '22rpx',
    tiny: '20rpx',
    // 按钮
    button: '28rpx',
    buttonSmall: '24rpx',
    // 标签
    tag: '22rpx',
    tagSmall: '20rpx'
};
// 字重规范
exports.FONT_WEIGHT = {
    thin: 100,
    extraLight: 200,
    light: 300,
    regular: 400,
    medium: 500,
    semiBold: 600,
    bold: 700,
    extraBold: 800,
    black: 900
};
// 行高规范
exports.LINE_HEIGHT = {
    tight: 1.2,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2
};
// 当前字体样式
var currentFontStyle = 'modern';
var bootstrapped = false;
// 字体变更回调列表
var fontChangeCallbacks = [];
/**
 * 从本地存储获取保存的字体样式
 */
function getStoredFontStyle() {
    try {
        var stored = wx.getStorageSync(FONT_STYLE_STORAGE_KEY);
        if (stored && exports.FONT_STYLE_LIST.includes(stored)) {
            return stored;
        }
    }
    catch (e) {
        console.warn('读取字体样式失败:', e);
    }
    return 'modern';
}
/**
 * 保存字体样式到本地存储
 */
function saveFontStyle(style) {
    try {
        wx.setStorageSync(FONT_STYLE_STORAGE_KEY, style);
    }
    catch (e) {
        console.warn('保存字体样式失败:', e);
    }
}
/**
 * 获取字体样式对应的 CSS 类名
 */
function getFontStyleClass(style) {
    if (!style || style === 'system')
        return '';
    return "font-style-".concat(style);
}
/**
 * 通知所有页面字体变更
 */
function notifyFontChange() {
    var style = currentFontStyle;
    var fontStyleClass = getFontStyleClass(style);
    var config = exports.FONT_STYLE_CONFIG[style];
    // 调用所有注册的回调
    fontChangeCallbacks.forEach(function (callback) {
        try {
            callback(style);
        }
        catch (e) {
            console.error('字体变更回调执行失败:', e);
        }
    });
    // 获取所有页面并尝试更新
    var pages = getCurrentPages();
    pages.forEach(function (page) {
        if (page && typeof page.onFontChange === 'function') {
            try {
                page.onFontChange(style);
            }
            catch (e) {
                console.error('页面字体变更处理失败:', e);
            }
        }
        // 更新页面字体数据
        if (page && page.setData) {
            try {
                page.setData({
                    fontStyle: style,
                    fontStyleClass: fontStyleClass,
                    fontStyleName: config.name
                });
            }
            catch (e) {
                // 忽略 setData 失败
            }
        }
    });
}
/**
 * 字体管理器
 */
exports.fontManager = {
    /**
     * 启动期提前读取本地配置
     */
    bootstrap: function () {
        if (bootstrapped)
            return currentFontStyle;
        bootstrapped = true;
        currentFontStyle = getStoredFontStyle();
        // 启动时预加载当前样式的字体
        loadFontsForStyle(currentFontStyle);
        return currentFontStyle;
    },
    /**
     * 初始化字体系统（应在 app.ts onLaunch 中调用）
     */
    init: function () {
        this.bootstrap();
        return currentFontStyle;
    },
    /**
     * 获取当前字体样式
     */
    getStyle: function () {
        this.bootstrap();
        return currentFontStyle;
    },
    /**
     * 获取当前字体样式配置
     */
    getStyleConfig: function () {
        this.bootstrap();
        return exports.FONT_STYLE_CONFIG[currentFontStyle];
    },
    /**
     * 获取当前字体样式名称
     */
    getStyleName: function () {
        return exports.FONT_STYLE_CONFIG[currentFontStyle].name;
    },
    /**
     * 设置字体样式
     */
    setStyle: function (style) {
        return __awaiter(this, void 0, void 0, function () {
            var prev;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!style || !exports.FONT_STYLE_LIST.includes(style)) {
                            console.warn('无效的字体样式:', style);
                            return [2 /*return*/];
                        }
                        prev = currentFontStyle;
                        currentFontStyle = style;
                        saveFontStyle(style);
                        // 加载新样式所需的字体
                        return [4 /*yield*/, loadFontsForStyle(style)];
                    case 1:
                        // 加载新样式所需的字体
                        _a.sent();
                        if (prev !== style) {
                            notifyFontChange();
                        }
                        return [2 /*return*/];
                }
            });
        });
    },
    /**
     * 循环切换字体样式
     */
    cycleStyle: function () {
        var idx = exports.FONT_STYLE_LIST.indexOf(currentFontStyle);
        var next = exports.FONT_STYLE_LIST[(idx + 1) % exports.FONT_STYLE_LIST.length];
        this.setStyle(next);
        return next;
    },
    /**
     * 注册字体变更回调
     */
    onFontChange: function (callback) {
        fontChangeCallbacks.push(callback);
        return function () {
            var index = fontChangeCallbacks.indexOf(callback);
            if (index > -1) {
                fontChangeCallbacks.splice(index, 1);
            }
        };
    },
    /**
     * 获取用于页面的字体相关数据
     */
    getPageData: function () {
        this.bootstrap();
        return {
            fontStyle: currentFontStyle,
            fontStyleClass: getFontStyleClass(currentFontStyle),
            fontStyleName: exports.FONT_STYLE_CONFIG[currentFontStyle].name
        };
    },
    /**
     * 获取所有可用的字体样式列表
     */
    getStyleList: function () {
        return exports.FONT_STYLE_LIST.map(function (id) { return exports.FONT_STYLE_CONFIG[id]; });
    },
    /**
     * 获取字体大小规范
     */
    getFontSize: function () {
        return exports.FONT_SIZE;
    },
    /**
     * 获取字重规范
     */
    getFontWeight: function () {
        return exports.FONT_WEIGHT;
    },
    /**
     * 获取行高规范
     */
    getLineHeight: function () {
        return exports.LINE_HEIGHT;
    }
};
exports.default = exports.fontManager;
