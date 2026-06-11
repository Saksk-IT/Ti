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
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var user_settings_1 = require("../../utils/user-settings");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
function formatDate(dateStr) {
    var raw = String(dateStr || '').trim();
    if (!raw)
        return '-';
    var d = new Date(raw);
    if (Number.isNaN(d.getTime()))
        return '-';
    try {
        return d.toLocaleDateString('zh-CN');
    }
    catch (e) {
        return '-';
    }
}
function hideNativeTabBar() {
    try {
        wx.hideTabBar({ animation: false });
    }
    catch (e) { }
}
function showNativeTabBar() {
    try {
        wx.showTabBar({ animation: false });
    }
    catch (e) { }
}
Page({
    data: {
        drawerOpen: false,
        loading: false,
        inited: false,
        keyword: '',
        filter: 'all',
        banks: [],
        filteredBanks: [],
        createOpen: false,
        createName: '',
        createDesc: '',
        createError: '',
        creating: false
    },
    onShow: function () {
        hideNativeTabBar();
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        this.loadBanks();
    },
    onHide: function () {
        showNativeTabBar();
    },
    onUnload: function () {
        showNativeTabBar();
    },
    loadBanks: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, myRes, sharedRes, createdList, sharedList, createdBanks, sharedBanks, byId_1, banks, e_1;
            var _this = this;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getMyBanks().catch(function () { return ({ banks: [] }); }),
                                api_1.api.getSharedBanks().catch(function () { return ({ banks: [] }); })
                            ])];
                    case 2:
                        _a = _b.sent(), myRes = _a[0], sharedRes = _a[1];
                        createdList = Array.isArray(myRes === null || myRes === void 0 ? void 0 : myRes.banks) ? myRes.banks : [];
                        sharedList = Array.isArray(sharedRes === null || sharedRes === void 0 ? void 0 : sharedRes.banks) ? sharedRes.banks : [];
                        createdBanks = createdList.map(function (b) { return ({
                            id: Number((b === null || b === void 0 ? void 0 : b.id) || 0),
                            name: String((b === null || b === void 0 ? void 0 : b.name) || '未命名题库'),
                            description: (b === null || b === void 0 ? void 0 : b.description) ? String(b.description) : '',
                            question_count: Number((b === null || b === void 0 ? void 0 : b.question_count) || 0) || 0,
                            is_public: b === null || b === void 0 ? void 0 : b.is_public,
                            updated_at: b === null || b === void 0 ? void 0 : b.updated_at,
                            updated_at_fmt: formatDate(b === null || b === void 0 ? void 0 : b.updated_at),
                            source: 'created'
                        }); }).filter(function (b) { return Number.isFinite(b.id) && b.id > 0; });
                        sharedBanks = sharedList.map(function (b) { return ({
                            id: Number((b === null || b === void 0 ? void 0 : b.bank_id) || (b === null || b === void 0 ? void 0 : b.id) || 0),
                            name: String((b === null || b === void 0 ? void 0 : b.bank_name) || (b === null || b === void 0 ? void 0 : b.name) || '未命名题库'),
                            description: (b === null || b === void 0 ? void 0 : b.description) ? String(b.description) : '',
                            question_count: Number((b === null || b === void 0 ? void 0 : b.question_count) || 0) || 0,
                            is_public: false,
                            updated_at: (b === null || b === void 0 ? void 0 : b.last_access_at) || (b === null || b === void 0 ? void 0 : b.created_at),
                            updated_at_fmt: formatDate((b === null || b === void 0 ? void 0 : b.last_access_at) || (b === null || b === void 0 ? void 0 : b.created_at)),
                            source: 'shared',
                            owner_name: (b === null || b === void 0 ? void 0 : b.owner_nickname) ? String(b.owner_nickname) : ''
                        }); }).filter(function (b) { return Number.isFinite(b.id) && b.id > 0; });
                        byId_1 = new Map();
                        __spreadArray(__spreadArray([], sharedBanks, true), createdBanks, true).forEach(function (b) {
                            byId_1.set(b.id, b);
                        });
                        banks = Array.from(byId_1.values());
                        banks.sort(function (a, b) { return String(b.updated_at || '').localeCompare(String(a.updated_at || '')) || (b.id - a.id); });
                        this.setData({ banks: banks, inited: true }, function () { return _this.applyFilter(); });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _b.sent();
                        wx.showToast({ title: (e_1 && e_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onKeywordInput: function (e) {
        var _this = this;
        var keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
        this.setData({ keyword: keyword }, function () { return _this.applyFilter(); });
    },
    onClearKeyword: function () {
        var _this = this;
        this.setData({ keyword: '' }, function () { return _this.applyFilter(); });
    },
    onFilterTap: function (e) {
        var _this = this;
        var _a, _b;
        var filter = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.filter;
        if (!filter || filter === this.data.filter)
            return;
        if (filter !== 'all' && filter !== 'created' && filter !== 'shared')
            return;
        this.setData({ filter: filter }, function () { return _this.applyFilter(); });
    },
    applyFilter: function () {
        var kw = (this.data.keyword || '').trim().toLowerCase();
        var filter = this.data.filter;
        var out = (this.data.banks || []).slice();
        if (kw) {
            out = out.filter(function (b) {
                var name = String(b.name || '').toLowerCase();
                var desc = String(b.description || '').toLowerCase();
                var owner = String(b.owner_name || '').toLowerCase();
                return name.includes(kw) || desc.includes(kw) || owner.includes(kw);
            });
        }
        if (filter === 'created')
            out = out.filter(function (b) { return b.source === 'created'; });
        if (filter === 'shared')
            out = out.filter(function (b) { return b.source === 'shared'; });
        this.setData({ filteredBanks: out });
    },
    onBankTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(id), 'navigateTo');
    },
    onBankManageTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        (0, nav_1.safeNavigate)("/pages/bank-detail/bank-detail?id=".concat(id), 'navigateTo');
    },
    onGoPublicBank: function () {
        (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
    },
    onGoCreateBank: function () {
        if (this.data.createOpen)
            return;
        this.setData({
            createOpen: true,
            createName: '',
            createDesc: '',
            createError: '',
            creating: false
        });
    },
    onCreateClose: function () {
        if (this.data.creating)
            return;
        this.setData({ createOpen: false });
    },
    onCreateSheetTap: function () { },
    onCreateNameInput: function (e) {
        var _a;
        var value = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ createName: value, createError: '' });
    },
    onCreateDescInput: function (e) {
        var _a;
        var value = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ createDesc: value, createError: '' });
    },
    onCreateSubmit: function () {
        return __awaiter(this, void 0, void 0, function () {
            var name, description, msg, msg, msg, e_2, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.creating)
                            return [2 /*return*/];
                        name = String(this.data.createName || '').trim();
                        description = String(this.data.createDesc || '').trim();
                        if (!name) {
                            msg = '题库名称不能为空';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (name.length < 2 || name.length > 50) {
                            msg = '题库名称需要 2-50 个字符';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (description.length > 200) {
                            msg = '描述不能超过 200 个字符';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ creating: true, createError: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createBank({ name: name, description: description })];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '创建成功', icon: 'success' });
                        this.setData({
                            createOpen: false,
                            createName: '',
                            createDesc: '',
                            createError: '',
                            creating: false
                        });
                        this.loadBanks();
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        msg = (e_2 && e_2.message) ? String(e_2.message) : '创建失败';
                        this.setData({ creating: false, createError: msg });
                        wx.showToast({ title: msg, icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
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
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    }
});
