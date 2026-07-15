"use strict";
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
// data-web-v2.ts - Web 数据中心（web-view 1:1 复刻）
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var theme_1 = require("../../utils/theme");
function normalizeDays(v) {
    var n = Number(v);
    if (n === 7 || n === 30 || n === 90)
        return n;
    return 30;
}
function withDays(nextPath, days) {
    var raw = String(nextPath || '').trim() || '/data';
    var path = raw.startsWith('/') ? raw : "/".concat(raw);
    var parts = path.split('?');
    var base = parts[0] || '/data';
    var query = parts.slice(1).join('?');
    var params = new Map();
    if (query) {
        for (var _i = 0, _a = query.split('&'); _i < _a.length; _i++) {
            var seg = _a[_i];
            if (!seg)
                continue;
            var idx = seg.indexOf('=');
            if (idx >= 0)
                params.set(seg.slice(0, idx), seg.slice(idx + 1));
            else
                params.set(seg, '');
        }
    }
    params.set('days', encodeURIComponent(String(days)));
    var qs = Array.from(params.entries())
        .map(function (_a) {
        var k = _a[0], val = _a[1];
        return (val === '' ? k : "".concat(k, "=").concat(val));
    })
        .join('&');
    return qs ? "".concat(base, "?").concat(qs) : base;
}
Page({
    data: {
        src: '',
        next: '/data',
        days: 30,
        loading: false
    },
    onLoad: function (options) {
        var days = normalizeDays(options === null || options === void 0 ? void 0 : options.days);
        var tab = String((options === null || options === void 0 ? void 0 : options.tab) || '').trim();
        var nextRaw = (options && options.next ? String(options.next) : '').trim();
        var tabMap = {
            global: '/data/global',
            banks: '/data/banks',
            mistakes: '/data/mistakes',
            favorites: '/data/favorites',
            tags: '/data/tags'
        };
        var next = nextRaw || tabMap[tab] || '/data';
        this.setData({ next: next, days: days });
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        this.loadWebDataCenter();
    },
    onPullDownRefresh: function () {
        this.loadWebDataCenter(true).finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    loadWebDataCenter: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, next, res, origin, src, err_1;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 8000 && this.data.src)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, src: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        next = withDays(this.data.next || '/data', this.data.days);
                        return [4 /*yield*/, api_1.api.getMiniWebViewUrl(next)];
                    case 2:
                        res = _a.sent();
                        origin = (0, api_1.getApiOrigin)();
                        src = "".concat(origin).concat(res.path);
                        this.setData({ src: src, loading: false });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载 Web 数据中心失败:', err_1);
                        wx.showToast({ title: (err_1 && err_1.message) || '加载失败', icon: 'none' });
                        this.setData({ loading: false, src: '' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onRetryTap: function () {
        this.loadWebDataCenter(true);
    },
    onWebLoad: function () {
        this.setData({ loading: false });
    },
    onWebError: function (e) {
        console.error('web-view error:', e);
        this.setData({ loading: false, src: '' });
    }
});
