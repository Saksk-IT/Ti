"use strict";
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
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var data_center_1 = require("../../packages/data/utils/data-center");
var data_center_cache_1 = require("../../packages/data/utils/data-center-cache");
function buildAiPatch(res) {
    var abilityList = (Array.isArray(res === null || res === void 0 ? void 0 : res.ability_radar) ? res.ability_radar : []).map(function (a) { return ({
        name: String((a === null || a === void 0 ? void 0 : a.name) || ''),
        value: (0, data_center_1.pct1)(a === null || a === void 0 ? void 0 : a.value)
    }); });
    var focusRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [])
        .map(function (w) {
        var acc = (0, data_center_1.pct1)(w === null || w === void 0 ? void 0 : w.accuracy);
        return {
            name: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), " \u00B7 ").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
            gap: (0, data_center_1.pct1)(100 - acc),
            accuracy: acc,
            answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered)
        };
    })
        .sort(function (a, b) { return b.gap - a.gap; })
        .slice(0, 8);
    return { inited: true, abilityList: abilityList, focusRows: focusRows };
}
Page({
    data: {
        loading: false,
        inited: false,
        errorMsg: '',
        days: 30,
        abilityList: [],
        focusRows: [],
        aiReply: '点击“生成建议”，获取基于你数据的训练方案。',
        aiPrompt: '',
        aiLoading: false
    },
    onLoad: function (options) {
        var days = (0, data_center_1.normalizeDays)(options === null || options === void 0 ? void 0 : options.days);
        this.setData({ days: days });
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var patch = {};
        var hydrated = false;
        try {
            __assign(patch, theme_1.themeManager.getPageData());
        }
        catch (e) { }
        if (!this.data.inited) {
            try {
                var cached = (0, data_center_cache_1.getCachedDataCenter)(this.data.days);
                if (cached) {
                    __assign(patch, buildAiPatch(cached), { errorMsg: '' });
                    this.__lastLoadedAt = Date.now();
                    hydrated = true;
                }
            }
            catch (e) { }
        }
        try {
            if (Object.keys(patch).length)
                this.setData(patch);
        }
        catch (e) { }
        if (!hydrated && !this.data.inited && !this.data.loading) {
            this.loadStats(true);
        }
    },
    onPullDownRefresh: function () {
        this.loadStats(true).finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    onTabTap: function (e) {
        var _a, _b;
        var tab = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '');
        var days = this.data.days;
        var map = {
            overview: '/pages/history-v2/history-v2',
            banks: '/pages/data-banks-v2/data-banks-v2',
            trend: '/pages/data-trend-v2/data-trend-v2',
            ai: '/pages/data-ai-v2/data-ai-v2'
        };
        if (!map[tab])
            return;
        (0, nav_1.safeNavigate)("".concat(map[tab], "?days=").concat(days), 'reLaunch');
    },
    onPromptInput: function (e) {
        var _a;
        this.setData({ aiPrompt: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onQuickPrompt: function (e) {
        var _a, _b;
        var prompt = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.prompt) || '');
        if (!prompt)
            return;
        this.askAi(prompt);
    },
    onGenerateAdvice: function () {
        var prompt = '请基于我的学习数据，给出今天最重要的5条建议，并按优先级排序。';
        this.askAi(prompt);
    },
    onAskPrompt: function () {
        var prompt = String(this.data.aiPrompt || '').trim();
        if (!prompt) {
            wx.showToast({ title: '请先输入问题', icon: 'none' });
            return;
        }
        this.askAi(prompt);
    },
    askAi: function (prompt) {
        return __awaiter(this, void 0, void 0, function () {
            var res, reply, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.aiLoading)
                            return [2 /*return*/];
                        this.setData({ aiLoading: true, aiReply: '正在生成建议...' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataAiAdvice(prompt, this.data.days)];
                    case 2:
                        res = _a.sent();
                        reply = (res === null || res === void 0 ? void 0 : res.reply) ? String(res.reply) : 'AI暂时没有返回有效建议。';
                        this.setData({ aiReply: reply });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ aiReply: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '生成失败，请稍后再试。' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ aiLoading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    loadStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, res, abilityList, focusRows, e_2;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 10000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getDataCenter(this.data.days)];
                    case 2:
                        res = _a.sent();
                        try {
                            (0, data_center_cache_1.setCachedDataCenter)(this.data.days, res);
                        }
                        catch (e) { }
                        abilityList = (Array.isArray(res === null || res === void 0 ? void 0 : res.ability_radar) ? res.ability_radar : []).map(function (a) { return ({
                            name: String((a === null || a === void 0 ? void 0 : a.name) || ''),
                            value: (0, data_center_1.pct1)(a === null || a === void 0 ? void 0 : a.value)
                        }); });
                        focusRows = (Array.isArray(res === null || res === void 0 ? void 0 : res.weakness_rows) ? res.weakness_rows : [])
                            .map(function (w) {
                            var acc = (0, data_center_1.pct1)(w === null || w === void 0 ? void 0 : w.accuracy);
                            return {
                                name: "".concat(String((w === null || w === void 0 ? void 0 : w.subject) || ''), " \u00B7 ").concat(String((w === null || w === void 0 ? void 0 : w.q_type) || '')),
                                gap: (0, data_center_1.pct1)(100 - acc),
                                accuracy: acc,
                                answered: (0, data_center_1.toInt)(w === null || w === void 0 ? void 0 : w.answered)
                            };
                        })
                            .sort(function (a, b) { return b.gap - a.gap; })
                            .slice(0, 8);
                        this.setData({
                            inited: true,
                            abilityList: abilityList,
                            focusRows: focusRows
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_2 = _a.sent();
                        this.setData({ errorMsg: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '加载失败，请稍后再试。' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
