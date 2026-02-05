"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var config_1 = require("../../utils/config");
var DEV_API_BASE_URL_KEY = 'dev_api_base_url';
var DEV_API_HOST_KEY = 'dev_api_host';
var DEV_API_PORT_KEY = 'dev_api_port';
var PROD_API_BASE_URL_KEY = 'prod_api_base_url';
var PROD_API_PRESETS_KEY = 'prod_api_presets_v1';
function normalizeMode(input) {
    var m = String(input || '').trim().toLowerCase();
    return m === 'custom' ? 'custom' : 'prod';
}
function getMode() {
    try {
        var m = config_1.config.getApiMode ? config_1.config.getApiMode() : wx.getStorageSync('api_mode_v1');
        return normalizeMode(m);
    }
    catch (e) {
        return 'prod';
    }
}
function setMode(mode) {
    try {
        if (config_1.config.setApiMode) {
            config_1.config.setApiMode(mode);
            return;
        }
    }
    catch (e) { }
    try {
        wx.setStorageSync('api_mode_v1', mode);
    }
    catch (e) { }
}
function getProdApiUrl() {
    try {
        return (config_1.config.getProdApiUrl && config_1.config.getProdApiUrl()) || '';
    }
    catch (e) {
        return '';
    }
}
function readCustomInputs() {
    try {
        var baseUrlRaw = wx.getStorageSync(DEV_API_BASE_URL_KEY);
        var baseUrl = String(baseUrlRaw || '').trim();
        if (baseUrl) {
            return { host: baseUrl, port: '', preview: baseUrl };
        }
        var host = String(wx.getStorageSync(DEV_API_HOST_KEY) || '').trim();
        var portRaw = wx.getStorageSync(DEV_API_PORT_KEY);
        var portNum = Number(portRaw);
        var port = String(Number.isFinite(portNum) && portNum > 0 ? Math.floor(portNum) : 5000);
        var preview = host ? "http://".concat(host, ":").concat(port, "/api") : '';
        return { host: host, port: port, preview: preview };
    }
    catch (e) {
        return { host: '', port: '5000', preview: '' };
    }
}
function normalizeBaseUrl(input) {
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
function readProdPresets(defaultUrl) {
    var baseDefault = normalizeBaseUrl(defaultUrl) || defaultUrl;
    var fallback = [{ name: '线上', url: baseDefault }];
    try {
        var raw = wx.getStorageSync(PROD_API_PRESETS_KEY);
        if (!Array.isArray(raw))
            return fallback;
        var list_1 = [];
        raw.forEach(function (item) {
            var name = String(item && item.name ? item.name : '').trim();
            var url = normalizeBaseUrl(item && item.url ? item.url : '');
            if (!name || !url)
                return;
            if (list_1.some(function (x) { return x.name === name || x.url === url; }))
                return;
            list_1.push({ name: name, url: url });
        });
        if (!list_1.some(function (x) { return x.url === baseDefault; }))
            list_1.unshift({ name: '线上', url: baseDefault });
        return list_1.length ? list_1 : fallback;
    }
    catch (e) {
        return fallback;
    }
}
function saveProdPresets(list) {
    try {
        wx.setStorageSync(PROD_API_PRESETS_KEY, list);
    }
    catch (e) { }
}
function isDevEnv() {
    try {
        return wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
    }
    catch (e) {
        return false;
    }
}
function getEnvVersion() {
    try {
        return wx.getAccountInfoSync().miniProgram.envVersion || '';
    }
    catch (e) {
        return '';
    }
}
function getPlatform() {
    try {
        var info = wx.getDeviceInfo ? wx.getDeviceInfo() : null;
        var p = info && info.platform;
        if (p)
            return String(p);
    }
    catch (e) {
        // ignore
    }
    try {
        return wx.getSystemInfoSync().platform || '';
    }
    catch (e) {
        return '';
    }
}
Page({
    data: {
        mode: 'prod',
        prodApiUrl: '',
        prodUrlInput: '',
        prodPresetName: '',
        prodPresets: [],
        customPreview: '',
        host: '',
        port: '',
        apiUrl: '',
        envVersion: '',
        platform: '',
        saving: false,
        testing: false,
        testResult: ''
    },
    onLoad: function () {
        var _this = this;
        if (!isDevEnv()) {
            wx.showModal({
                title: '仅开发版可用',
                content: '「开发设置」仅在开发版（develop）开放，避免线上误操作。',
                showCancel: false,
                success: function () {
                    var pages = getCurrentPages();
                    if (pages.length <= 1)
                        wx.redirectTo({ url: '/pages/login/login' });
                    else
                        wx.navigateBack();
                }
            });
            return;
        }
        this.refresh();
    },
    onShow: function () {
        this.refresh();
    },
    refresh: function () {
        var mode = getMode();
        var prodApiUrl = getProdApiUrl() || 'https://saksk.top/api';
        var prodUrlInput = prodApiUrl;
        var prodPresets = readProdPresets(prodApiUrl);
        var _a = readCustomInputs(), host = _a.host, port = _a.port, preview = _a.preview;
        var apiUrl = config_1.config.getApiUrl();
        this.setData({
            mode: mode,
            prodApiUrl: prodApiUrl,
            prodUrlInput: prodUrlInput,
            prodPresets: prodPresets,
            customPreview: preview,
            host: host,
            port: port,
            apiUrl: apiUrl,
            envVersion: getEnvVersion(),
            platform: getPlatform()
        });
    },
    onModeTap: function (e) {
        var mode = normalizeMode(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.mode);
        setMode(mode);
        this.refresh();
    },
    onUseProdTap: function () {
        setMode('prod');
        this.refresh();
        wx.showToast({ title: '已切换到生产', icon: 'success' });
    },
    onUseCustomTap: function () {
        setMode('custom');
        this.refresh();
        wx.showToast({ title: '已切换到自定义', icon: 'success' });
    },
    onProdUrlInput: function (e) {
        this.setData({ prodUrlInput: (e && e.detail && e.detail.value) || '' });
    },
    onProdPresetNameInput: function (e) {
        this.setData({ prodPresetName: (e && e.detail && e.detail.value) || '' });
    },
    onSaveProdTap: function () {
        var input = String(this.data.prodUrlInput || '').trim();
        var url = normalizeBaseUrl(input);
        if (!url) {
            wx.showToast({ title: '生产地址无效', icon: 'none' });
            return;
        }
        try {
            if (config_1.config.setProdApiUrl)
                config_1.config.setProdApiUrl(url);
            else
                wx.setStorageSync(PROD_API_BASE_URL_KEY, url);
            setMode('prod');
            this.refresh();
            wx.showToast({ title: '生产地址已保存', icon: 'success' });
        }
        catch (e) {
            wx.showToast({ title: '保存失败', icon: 'none' });
        }
    },
    onClearProdTap: function () {
        try {
            if (config_1.config.clearProdApiUrl)
                config_1.config.clearProdApiUrl();
            else
                wx.removeStorageSync(PROD_API_BASE_URL_KEY);
            setMode('prod');
            this.refresh();
            wx.showToast({ title: '已恢复默认生产', icon: 'success' });
        }
        catch (e) {
            wx.showToast({ title: '操作失败', icon: 'none' });
        }
    },
    onApplyProdPresetTap: function (e) {
        var idx = Number(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.idx);
        var presets = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
        var item = Number.isFinite(idx) && idx >= 0 && idx < presets.length ? presets[idx] : null;
        if (!item || !item.url)
            return;
        try {
            if (config_1.config.setProdApiUrl)
                config_1.config.setProdApiUrl(item.url);
            else
                wx.setStorageSync(PROD_API_BASE_URL_KEY, item.url);
            setMode('prod');
            this.refresh();
            wx.showToast({ title: "\u5DF2\u5207\u6362\uFF1A".concat(item.name || '预设'), icon: 'success' });
        }
        catch (e2) {
            wx.showToast({ title: '切换失败', icon: 'none' });
        }
    },
    onDeleteProdPresetTap: function (e) {
        var idx = Number(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.idx);
        var presets = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
        if (!Number.isFinite(idx) || idx < 0 || idx >= presets.length)
            return;
        var next = presets.filter(function (_, i) { return i !== idx; });
        saveProdPresets(next);
        this.refresh();
        wx.showToast({ title: '已删除预设', icon: 'success' });
    },
    onSaveProdPresetTap: function () {
        var name = String(this.data.prodPresetName || '').trim();
        if (!name) {
            wx.showToast({ title: '请填写预设名称', icon: 'none' });
            return;
        }
        var url = normalizeBaseUrl(this.data.prodUrlInput);
        if (!url) {
            wx.showToast({ title: '预设地址无效', icon: 'none' });
            return;
        }
        var list = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
        if (list.some(function (x) { return x && (x.name === name || x.url === url); })) {
            wx.showToast({ title: '预设已存在', icon: 'none' });
            return;
        }
        var next = list.concat([{ name: name, url: url }]);
        saveProdPresets(next);
        this.setData({ prodPresetName: '' });
        this.refresh();
        wx.showToast({ title: '预设已保存', icon: 'success' });
    },
    onHostInput: function (e) {
        this.setData({ host: (e && e.detail && e.detail.value) || '' });
    },
    onPortInput: function (e) {
        this.setData({ port: (e && e.detail && e.detail.value) || '' });
    },
    onSaveTap: function () {
        if (this.data.saving)
            return;
        var hostInput = String(this.data.host || '').trim();
        var portInput = String(this.data.port || '').trim();
        if (!hostInput) {
            wx.showToast({ title: '请填写 Host 或完整 URL', icon: 'none' });
            return;
        }
        var isFullUrl = /^https?:\/\//i.test(hostInput);
        this.setData({ saving: true });
        try {
            config_1.config.setDevHost(hostInput);
            // Host 输入为完整 URL（含 https）时，以 URL 为准并忽略 Port
            if (!isFullUrl && portInput) {
                var n = Number(portInput);
                if (!Number.isFinite(n) || n <= 0 || n > 65535) {
                    wx.showToast({ title: '端口无效', icon: 'none' });
                    this.setData({ saving: false });
                    return;
                }
                if (config_1.config.setDevPort)
                    config_1.config.setDevPort(n);
            }
            var apiUrl = config_1.config.getApiUrl();
            setMode('custom');
            this.setData({ apiUrl: apiUrl, saving: false, testResult: '' });
            this.refresh();
            wx.showToast({ title: '已保存并启用', icon: 'success' });
        }
        catch (e) {
            this.setData({ saving: false });
            wx.showToast({ title: '保存失败', icon: 'none' });
        }
    },
    onResetTap: function () {
        var _this = this;
        wx.showModal({
            title: '清除自定义',
            content: '将清除自定义 Host/Port/URL，并切回生产模式。',
            confirmText: '清除',
            cancelText: '取消',
            success: function (res) {
                if (!res.confirm)
                    return;
                try {
                    if (config_1.config.clearDevServer)
                        config_1.config.clearDevServer();
                    setMode('prod');
                    _this.refresh();
                    wx.showToast({ title: '已清除', icon: 'success' });
                }
                catch (e) {
                    wx.showToast({ title: '操作失败', icon: 'none' });
                }
            }
        });
    },
    onTestTap: function () {
        var _this = this;
        if (this.data.testing)
            return;
        var apiUrl = config_1.config.getApiUrl();
        this.setData({ testing: true, testResult: '' });
        wx.request({
            url: "".concat(apiUrl, "/ping"),
            method: 'GET',
            timeout: 8000,
            success: function (res) {
                var ok = res &&
                    res.statusCode === 200 &&
                    res.data &&
                    ((res.data.status === 'success' && res.data.data) || (res.data.code === 0 && res.data.data));
                var msg = ok
                    ? "\u8FDE\u63A5\u6210\u529F\uFF1A".concat(apiUrl)
                    : "\u8FDE\u63A5\u5931\u8D25\uFF1AHTTP ".concat(res && res.statusCode ? res.statusCode : '未知', "\n").concat(JSON.stringify(res && res.data ? res.data : {}, null, 2));
                _this.setData({ testing: false, testResult: msg });
                wx.showToast({ title: ok ? '连接成功' : '连接失败', icon: ok ? 'success' : 'none' });
            },
            fail: function (err) {
                var errorMsg = (err && (err.errMsg || err.message)) || '请求失败';
                _this.setData({ testing: false, testResult: "\u8BF7\u6C42\u5931\u8D25\uFF1A".concat(errorMsg, "\nAPI: ").concat(apiUrl) });
                wx.showToast({ title: '请求失败', icon: 'none' });
            }
        });
    }
});
