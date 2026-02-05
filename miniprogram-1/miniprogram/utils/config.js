"use strict";
// 配置文件：小程序 API 地址/模式统一入口（开发 / 生产）
//
// 只需要改【快速配置区】即可完成：
// - 默认模式（DEFAULT_API_MODE：'prod' | 'custom'）
// - 生产地址（PROD_API_BASE_URL）
// - 开发默认 Host/Port（DEV_DEFAULT_HOST / DEV_PORT）
//
// 运行时优先级（高 → 低）：
// 1) setDevHost/setDevPort/setProdApiUrl 写入的本地存储
// 2) 本文件的快速配置区默认值
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = exports.API_BASE_URL = void 0;
/** ======================== 快速配置区（建议只改这里） ======================== */
var DEFAULT_API_MODE = 'prod';
// 生产环境默认地址（可通过 config.setProdApiUrl 覆盖）
var PROD_API_BASE_URL = 'https://saksk.top/api';
// 开发环境默认 Host（仅在开发者工具 devtools 且未手动配置时生效）
// 真机预览无法访问 127.0.0.1/localhost，请在「开发设置」页设置为电脑局域网 IP
var DEV_DEFAULT_HOST = '127.0.0.1';
/** ======================== 本地存储 key（一般不需要改） ======================== */
var PROD_API_BASE_URL_KEY = 'prod_api_base_url';
// 开发环境：后端服务端口（默认值，可在真机里动态覆盖）
var DEV_PORT = 5000;
// 开发环境：允许直接配置完整的 API BaseURL（例如 https://saksk.top/api）
var DEV_API_BASE_URL_KEY = 'dev_api_base_url';
var DEV_API_HOST_KEY = 'dev_api_host';
var DEV_API_PORT_KEY = 'dev_api_port';
var API_MODE_KEY = 'api_mode_v1';
function normalizeDevApiBaseUrl(input) {
    var raw = String(input || '').trim();
    if (!raw)
        return '';
    var m = raw.match(/^(https?):\/\/([^/]+)(\/.*)?$/i);
    if (!m)
        return '';
    var scheme = String(m[1] || '').toLowerCase();
    var hostPort = String(m[2] || '').trim();
    if (!hostPort)
        return '';
    return "".concat(scheme, "://").concat(hostPort, "/api");
}

function normalizeProdApiBaseUrl(input) {
    return normalizeDevApiBaseUrl(input);
}
function parseSchemeHostPort(url) {
    var m = String(url || '').trim().match(/^(https?):\/\/([^/]+)(\/|$)/i);
    if (!m)
        return null;
    var scheme = String(m[1] || '').toLowerCase();
    var hostPort = String(m[2] || '').trim();
    if (!hostPort)
        return null;
    // 注意：这里不处理 IPv6（当前项目场景基本用不到）
    var hp = hostPort.split(':');
    var host = String(hp[0] || '').trim();
    if (!host)
        return null;
    var portRaw = hp.length > 1 ? hp[1] : '';
    var portNum = portRaw ? Number(portRaw) : NaN;
    var port = Number.isFinite(portNum) && portNum > 0 && portNum <= 65535 ? Math.floor(portNum) : undefined;
    return { scheme: scheme, host: host, port: port };
}
function getDevApiBaseUrlOverride() {
    try {
        var v = wx.getStorageSync(DEV_API_BASE_URL_KEY);
        var url = normalizeDevApiBaseUrl(String(v || ''));
        return url;
    }
    catch (e) {
        return '';
    }
}

function getProdApiBaseUrlOverride() {
    try {
        var v = wx.getStorageSync(PROD_API_BASE_URL_KEY);
        var url = normalizeProdApiBaseUrl(String(v || ''));
        return url;
    }
    catch (e) {
        return '';
    }
}

function getProdApiBaseUrl() {
    return getProdApiBaseUrlOverride() || PROD_API_BASE_URL;
}

function hasAnyCustomConfig() {
    try {
        if (getDevApiBaseUrlOverride())
            return true;
        var host = wx.getStorageSync(DEV_API_HOST_KEY);
        var port = wx.getStorageSync(DEV_API_PORT_KEY);
        return !!(host || port);
    }
    catch (e) {
        return false;
    }
}

function getApiMode() {
    try {
        var v = wx.getStorageSync(API_MODE_KEY);
        if (v === 'prod' || v === 'custom')
            return v;
    }
    catch (e) { }
    return hasAnyCustomConfig() ? 'custom' : DEFAULT_API_MODE;
}

function setApiMode(mode) {
    try {
        wx.setStorageSync(API_MODE_KEY, mode);
    }
    catch (e) { }
}
function getDevPort() {
    var override = getDevApiBaseUrlOverride();
    if (override) {
        var info = parseSchemeHostPort(override);
        if (info && typeof info.port === 'number')
            return info.port;
        if (info && info.scheme === 'https')
            return 443;
        if (info && info.scheme === 'http')
            return 80;
    }
    var raw = wx.getStorageSync(DEV_API_PORT_KEY);
    var n = Number(raw);
    if (!Number.isFinite(n))
        return DEV_PORT;
    if (n <= 0 || n > 65535)
        return DEV_PORT;
    return Math.floor(n);
}
function getWxPlatform() {
    try {
        var info = wx.getDeviceInfo ? wx.getDeviceInfo() : null;
        var p = info && info.platform;
        if (p)
            return String(p);
    }
    catch (e) { }
    try {
        var p = wx.getSystemInfoSync().platform;
        if (p)
            return String(p);
    }
    catch (e) { }
    return '';
}
function getDevHost() {
    var override = getDevApiBaseUrlOverride();
    if (override)
        return override;
    var savedHost = wx.getStorageSync(DEV_API_HOST_KEY);
    if (savedHost)
        return String(savedHost).trim();
    // 默认 Host：开发者工具可用；真机需要手动设置为电脑局域网 IP
    try {
        var platform = getWxPlatform();
        if (platform === 'devtools')
            return DEV_DEFAULT_HOST;
        if (platform && platform !== 'devtools') {
            console.warn('当前为真机环境但未设置 dev_api_host。请在「开发设置」页中设置为电脑局域网 IP（真机无法访问 127.0.0.1/localhost）。');
        }
    }
    catch (e) {
        // 忽略
    }
    return '';
}
/**
 * 自动获取开发环境 API 地址
 * 在微信开发者工具中，通过获取本机 IP 来构建 API 地址
 */
function getDevApiBaseUrl() {
    var override = getDevApiBaseUrlOverride();
    if (override)
        return override;
    var host = getDevHost();
    if (!host)
        return '';
    var port = getDevPort();
    return "http://".concat(host, ":").concat(port, "/api");
}

function getApiBaseUrl() {
    var mode = getApiMode();
    if (mode === 'prod')
        return getProdApiBaseUrl();
    return getDevApiBaseUrl() || getProdApiBaseUrl();
}
/**
 * 检测当前是否为开发环境
 */
function isDev() {
    try {
        var accountInfo = wx.getAccountInfoSync();
        // miniProgram.envVersion: 'develop' | 'trial' | 'release'
        return accountInfo.miniProgram.envVersion === 'develop';
    }
    catch (e) {
        // 获取失败时默认为开发环境
        return true;
    }
}
// 根据环境选择 API 地址
exports.API_BASE_URL = getApiBaseUrl();
// 导出配置
exports.config = {
    apiBaseUrl: exports.API_BASE_URL,
    devPort: DEV_PORT,
    isDev: isDev(),
    getApiMode: getApiMode,
    setApiMode: setApiMode,
    getProdApiUrl: function () {
        return getProdApiBaseUrl();
    },
    setProdApiUrl: function (input) {
        var raw = String(input || '').trim();
        if (!raw) {
            wx.removeStorageSync(PROD_API_BASE_URL_KEY);
            return;
        }
        var baseUrl = normalizeProdApiBaseUrl(raw);
        if (!baseUrl)
            return;
        wx.setStorageSync(PROD_API_BASE_URL_KEY, baseUrl);
    },
    clearProdApiUrl: function () {
        wx.removeStorageSync(PROD_API_BASE_URL_KEY);
    },
    /**
     * 动态设置开发环境的 API Host（保存到本地存储）
     * 使用方法：在小程序控制台执行 config.setDevHost('192.168.1.100')
     */
    setDevHost: function (host) {
        var raw = String(host || '').trim();
        if (!raw)
            return;
        setApiMode('custom');
        // 支持直接粘贴完整 URL（含 https），例如：https://saksk.top/api 或 https://saksk.top
        if (/^https?:\/\//i.test(raw)) {
            var baseUrl = normalizeDevApiBaseUrl(raw);
            if (!baseUrl)
                return;
            wx.setStorageSync(DEV_API_BASE_URL_KEY, baseUrl);
            var info = parseSchemeHostPort(baseUrl);
            if (info && info.host)
                wx.setStorageSync(DEV_API_HOST_KEY, info.host);
            if (info && typeof info.port === 'number')
                wx.setStorageSync(DEV_API_PORT_KEY, info.port);
            else
                wx.removeStorageSync(DEV_API_PORT_KEY);
            console.log("\u5DF2\u8BBE\u7F6E\u5F00\u53D1\u73AF\u5883 API \u5730\u5740\u4E3A: ".concat(baseUrl));
            console.log('返回上一页后即可生效（如仍不生效，可重启小程序）');
            return;
        }
        // Host/Port 模式：清理 BaseURL 覆盖
        wx.removeStorageSync(DEV_API_BASE_URL_KEY);
        var hp = raw.split(':');
        var h = (hp[0] || '').trim();
        var p = hp.length > 1 ? Number(hp[1]) : undefined;
        if (h)
            wx.setStorageSync(DEV_API_HOST_KEY, h);
        if (p && Number.isFinite(p))
            wx.setStorageSync(DEV_API_PORT_KEY, Math.floor(p));
        var apiUrl = getDevApiBaseUrl();
        console.log("\u5DF2\u8BBE\u7F6E\u5F00\u53D1\u73AF\u5883 API \u5730\u5740\u4E3A: ".concat(apiUrl));
        console.log('返回上一页后即可生效（如仍不生效，可重启小程序）');
    },
    /**
     * 动态设置开发环境的 API 端口（保存到本地存储）
     */
    setDevPort: function (port) {
        var n = Number(port);
        if (!Number.isFinite(n) || n <= 0 || n > 65535)
            return;
        setApiMode('custom');
        wx.setStorageSync(DEV_API_PORT_KEY, Math.floor(n));
    },
    /**
     * 清除开发环境 API 覆盖配置（回到默认 127.0.0.1:5000）
     */
    clearDevServer: function () {
        wx.removeStorageSync(DEV_API_HOST_KEY);
        wx.removeStorageSync(DEV_API_PORT_KEY);
        wx.removeStorageSync(DEV_API_BASE_URL_KEY);
        wx.removeStorageSync(API_MODE_KEY);
    },
    /**
     * 获取当前配置的 API 地址
     */
    getApiUrl: function () {
        return getApiBaseUrl();
    },
    getDevHost: getDevHost,
    getDevPort: getDevPort
};
