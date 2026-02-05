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
var user_settings_1 = require("../../utils/user-settings");
var theme_1 = require("../../utils/theme");
var KEY_TAB = 'exams_bank_tab';
var KEY_KW = 'exams_bank_kw';
function normalizeTab(input) {
    var s = String(input || '').trim().toLowerCase();
    return s === 'bank' ? 'bank' : 'public';
}
function getStoredString(key, fallback) {
    try {
        var raw = wx.getStorageSync(key);
        var s = String(raw || '').trim();
        return s ? s : fallback;
    }
    catch (e) {
        return fallback;
    }
}
function setStoredString(key, value) {
    try {
        wx.setStorageSync(key, String(value || ''));
    }
    catch (e) { }
}
function normalizeSubject(raw) {
    var id = Number((raw === null || raw === void 0 ? void 0 : raw.id) || 0);
    var name = String((raw === null || raw === void 0 ? void 0 : raw.name) || '').trim();
    if (!Number.isFinite(id) || id <= 0 || !name)
        return null;
    return { id: id, name: name, question_count: Number((raw === null || raw === void 0 ? void 0 : raw.question_count) || 0) || 0 };
}
function normalizeBank(raw) {
    var isShared = raw && raw.bank_id != null;
    var id = Number(isShared ? raw.bank_id : (raw === null || raw === void 0 ? void 0 : raw.id) || 0);
    var name = String(isShared ? raw.bank_name : (raw === null || raw === void 0 ? void 0 : raw.name) || '').trim();
    if (!Number.isFinite(id) || id <= 0 || !name)
        return null;
    var question_count = Number((raw === null || raw === void 0 ? void 0 : raw.question_count) || 0) || 0;
    var sort_key = String(isShared ? raw === null || raw === void 0 ? void 0 : raw.last_access_at : (raw === null || raw === void 0 ? void 0 : raw.updated_at) || '').trim();
    return { id: id, name: name, question_count: question_count, sort_key: sort_key };
}
Page({
    data: {
        drawerOpen: false,
        loading: false,
        inited: false,
        tab: 'public',
        keyword: '',
        subjects: [],
        filteredSubjects: [],
        banks: [],
        filteredBanks: [],
        publicTotal: 0,
        bankTotal: 0,
        currentTotal: 0,
        shownTotal: 0
    },
    onLoad: function (options) {
        var storedTab = normalizeTab(getStoredString(KEY_TAB, 'public'));
        var storedKw = getStoredString(KEY_KW, '');
        var tab = normalizeTab((options === null || options === void 0 ? void 0 : options.tab) || storedTab);
        var keyword = (options === null || options === void 0 ? void 0 : options.keyword) ? String(options.keyword) : storedKw;
        this.setData({ tab: tab, keyword: keyword || '' });
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
        if (!this.data.inited && !this.data.loading) {
            this.bootstrap();
            return;
        }
        this.applyFilter();
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, meta, myBanksRes, sharedBanksRes, subjectsRaw, subjects, map, myBanksRaw, sharedBanksRaw, _i, myBanksRaw_1, b, item, _b, sharedBanksRaw_1, b, item, banks, e_1;
            var _this = this;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getSubjectsMeta().catch(function () { return ({ subjects: [], quiz_count: 0 }); }),
                                api_1.api.getMyBanks().catch(function () { return ({ banks: [] }); }),
                                api_1.api.getSharedBanks().catch(function () { return ({ banks: [] }); })
                            ])];
                    case 2:
                        _a = _c.sent(), meta = _a[0], myBanksRes = _a[1], sharedBanksRes = _a[2];
                        subjectsRaw = Array.isArray(meta === null || meta === void 0 ? void 0 : meta.subjects) ? meta.subjects : [];
                        subjects = subjectsRaw.map(normalizeSubject).filter(Boolean);
                        subjects.sort(function (a, b) { return a.id - b.id; });
                        map = new Map();
                        myBanksRaw = Array.isArray(myBanksRes === null || myBanksRes === void 0 ? void 0 : myBanksRes.banks) ? myBanksRes.banks : [];
                        sharedBanksRaw = Array.isArray(sharedBanksRes === null || sharedBanksRes === void 0 ? void 0 : sharedBanksRes.banks) ? sharedBanksRes.banks : [];
                        for (_i = 0, myBanksRaw_1 = myBanksRaw; _i < myBanksRaw_1.length; _i++) {
                            b = myBanksRaw_1[_i];
                            item = normalizeBank(b);
                            if (!item)
                                continue;
                            map.set(item.id, item);
                        }
                        for (_b = 0, sharedBanksRaw_1 = sharedBanksRaw; _b < sharedBanksRaw_1.length; _b++) {
                            b = sharedBanksRaw_1[_b];
                            item = normalizeBank(b);
                            if (!item)
                                continue;
                            if (!map.has(item.id))
                                map.set(item.id, item);
                        }
                        banks = Array.from(map.values()).sort(function (a, b) { return String(b.sort_key || '').localeCompare(String(a.sort_key || '')) || (b.id - a.id); });
                        this.setData({
                            inited: true,
                            subjects: subjects,
                            banks: banks,
                            publicTotal: subjects.length,
                            bankTotal: banks.length
                        }, function () { return _this.applyFilter(); });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _c.sent();
                        wx.showToast({ title: (e_1 && e_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        try {
                            wx.stopPullDownRefresh();
                        }
                        catch (e) { }
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onPullDownRefresh: function () {
        this.bootstrap();
    },
    onTabTap: function (e) {
        var _this = this;
        var _a, _b;
        var tab = normalizeTab(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || 'public');
        if (tab === this.data.tab)
            return;
        this.setData({ tab: tab }, function () { return _this.applyFilter(); });
        setStoredString(KEY_TAB, tab);
    },
    onKeywordInput: function (e) {
        var _this = this;
        var _a;
        var keyword = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ keyword: keyword }, function () { return _this.applyFilter(); });
        setStoredString(KEY_KW, keyword);
    },
    onClearKeyword: function () {
        var _this = this;
        this.setData({ keyword: '' }, function () { return _this.applyFilter(); });
        setStoredString(KEY_KW, '');
    },
    applyFilter: function () {
        var kw = String(this.data.keyword || '').trim().toLowerCase();
        var subjects = Array.isArray(this.data.subjects) ? this.data.subjects : [];
        var banks = Array.isArray(this.data.banks) ? this.data.banks : [];
        var filteredSubjects = subjects.slice();
        var filteredBanks = banks.slice();
        if (kw) {
            filteredSubjects = filteredSubjects.filter(function (s) { return String(s.name || '').toLowerCase().includes(kw); });
            filteredBanks = filteredBanks.filter(function (b) { return String(b.name || '').toLowerCase().includes(kw); });
        }
        var currentTotal = this.data.tab === 'bank' ? banks.length : subjects.length;
        var shownTotal = this.data.tab === 'bank' ? filteredBanks.length : filteredSubjects.length;
        this.setData({ filteredSubjects: filteredSubjects, filteredBanks: filteredBanks, currentTotal: currentTotal, shownTotal: shownTotal });
    },
    onPublicBankTap: function (e) {
        var _a, _b;
        var name = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.name) || '').trim();
        if (!name)
            return;
        var url = "/pages/index-v2/index-v2?tab=new&source=public&subject=".concat(encodeURIComponent(name));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onBankTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var url = "/pages/index-v2/index-v2?tab=new&source=user_bank&bank_id=".concat(encodeURIComponent(String(id)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onHamburgerTap: function () {
        this.setData({ drawerOpen: true });
    },
    onDrawerClose: function () {
        this.setData({ drawerOpen: false });
    },
    onDrawerNavigate: function (e) {
        var _a, _b;
        var url = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.url;
        var navType = (_b = e === null || e === void 0 ? void 0 : e.detail) === null || _b === void 0 ? void 0 : _b.navType;
        this.setData({ drawerOpen: false });
        if (!url)
            return;
        (0, nav_1.safeNavigate)(url, navType);
    },
    onDrawerSelectStyle: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        style = (((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        this.setData({ drawerOpen: false });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    }
});
