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
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var KEY_TAB = 'review_hub_v3_tab';
var KEY_KW = 'review_hub_v3_kw';
var KEY_LAST_SESSION = 'review_last_session_v1';
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
function normalizeLastSession(raw) {
    if (!raw)
        return null;
    var obj = raw;
    if (typeof raw === 'string') {
        try {
            obj = JSON.parse(raw);
        }
        catch (e) {
            return null;
        }
    }
    var kind = String((obj === null || obj === void 0 ? void 0 : obj.kind) || '').trim();
    if (kind !== 'mistakes' && kind !== 'favorites' && kind !== 'tags')
        return null;
    var sourceType = String((obj === null || obj === void 0 ? void 0 : obj.sourceType) || '').trim();
    if (sourceType !== 'public' && sourceType !== 'bank')
        return null;
    var subject = String((obj === null || obj === void 0 ? void 0 : obj.subject) || '').trim();
    var bankId = Number((obj === null || obj === void 0 ? void 0 : obj.bankId) || (obj === null || obj === void 0 ? void 0 : obj.bank_id) || 0) || 0;
    if (sourceType === 'public' && !subject)
        return null;
    if (sourceType === 'bank' && bankId <= 0)
        return null;
    var tabRaw = String((obj === null || obj === void 0 ? void 0 : obj.tab) || 'practice').trim().toLowerCase();
    var tab = tabRaw === 'search' ? 'search' : tabRaw === 'data' ? 'data' : 'practice';
    var qType = String((obj === null || obj === void 0 ? void 0 : obj.qType) || (obj === null || obj === void 0 ? void 0 : obj.type) || (obj === null || obj === void 0 ? void 0 : obj.q_type) || 'all') || 'all';
    var tag = String((obj === null || obj === void 0 ? void 0 : obj.tag) || 'all') || 'all';
    var scopeLabel = String((obj === null || obj === void 0 ? void 0 : obj.scopeLabel) || '').trim();
    var scopeName = String((obj === null || obj === void 0 ? void 0 : obj.scopeName) || '').trim();
    var modeRaw = String((obj === null || obj === void 0 ? void 0 : obj.mode) || '').trim().toLowerCase();
    var mode = modeRaw === 'memo' ? 'memo' : modeRaw === 'quiz' ? 'quiz' : undefined;
    var start_id = Number((obj === null || obj === void 0 ? void 0 : obj.start_id) || (obj === null || obj === void 0 ? void 0 : obj.startId) || 0) || 0;
    var ts = Number((obj === null || obj === void 0 ? void 0 : obj.ts) || (obj === null || obj === void 0 ? void 0 : obj.timestamp) || 0) || 0;
    return {
        ts: ts,
        kind: kind,
        tab: tab,
        sourceType: sourceType,
        subject: subject,
        bankId: bankId,
        qType: qType,
        tag: tag,
        shuffleQuestions: !!(obj === null || obj === void 0 ? void 0 : obj.shuffleQuestions),
        shuffleOptions: !!(obj === null || obj === void 0 ? void 0 : obj.shuffleOptions),
        scopeLabel: scopeLabel,
        scopeName: scopeName,
        mode: mode,
        start_id: start_id > 0 ? start_id : undefined
    };
}
function readLastSession() {
    try {
        return normalizeLastSession(wx.getStorageSync(KEY_LAST_SESSION));
    }
    catch (e) {
        return null;
    }
}
function kindLabel(kind) {
    if (kind === 'favorites')
        return '收藏';
    if (kind === 'tags')
        return '标签';
    return '错题';
}
function sourceTypeLabel(sourceType) {
    return sourceType === 'bank' ? '个人' : '公共';
}
function buildLastSessionSummary(s) {
    var scope = String(s.scopeName || '').trim() ||
        (s.sourceType === 'public' ? String(s.subject || '').trim() : "\u9898\u5E93".concat(Number(s.bankId || 0) || 0));
    var parts = [sourceTypeLabel(s.sourceType), scope, kindLabel(s.kind)].filter(Boolean);
    var filters = [];
    var qType = String(s.qType || 'all');
    var tag = String(s.tag || 'all');
    if (qType && qType !== 'all')
        filters.push(qType);
    if (tag && tag !== 'all')
        filters.push(tag);
    return filters.length ? "".concat(parts.join(' · '), " \u00B7 ").concat(filters.join(' · ')) : parts.join(' · ');
}
function buildReviewCenterUrl(session, override) {
    var _a, _b, _c, _d;
    var kind = ((override === null || override === void 0 ? void 0 : override.kind) || session.kind || 'mistakes');
    var tab = ((override === null || override === void 0 ? void 0 : override.tab) || session.tab || 'practice');
    var qType = String((_b = (_a = override === null || override === void 0 ? void 0 : override.qType) !== null && _a !== void 0 ? _a : session.qType) !== null && _b !== void 0 ? _b : 'all') || 'all';
    var tag = String((_d = (_c = override === null || override === void 0 ? void 0 : override.tag) !== null && _c !== void 0 ? _c : session.tag) !== null && _d !== void 0 ? _d : 'all') || 'all';
    var params = ["kind=".concat(encodeURIComponent(kind)), "tab=".concat(encodeURIComponent(tab))];
    if (session.sourceType === 'bank') {
        params.push("bank_id=".concat(encodeURIComponent(String(Number(session.bankId || 0) || 0))));
    }
    else {
        params.push("subject=".concat(encodeURIComponent(String(session.subject || '').trim())));
    }
    if (qType && qType !== 'all')
        params.push("type=".concat(encodeURIComponent(qType)));
    if (tag && tag !== 'all')
        params.push("tag=".concat(encodeURIComponent(tag)));
    if (session.shuffleQuestions)
        params.push('shuffle_questions=1');
    if (session.shuffleOptions)
        params.push('shuffle_options=1');
    return "/pages/review-center-v2/review-center-v2?".concat(params.join('&'));
}
function buildQuizUrlFromSession(session, mode) {
    var params = ["mode=".concat(encodeURIComponent(mode))];
    if (session.sourceType === 'bank') {
        params.push("bank_id=".concat(encodeURIComponent(String(Number(session.bankId || 0) || 0))));
    }
    else {
        params.push("subject=".concat(encodeURIComponent(String(session.subject || '').trim())));
    }
    var qType = String(session.qType || 'all');
    if (qType && qType !== 'all')
        params.push("type=".concat(encodeURIComponent(qType)));
    var source = session.kind === 'mistakes' ? 'mistakes' : session.kind === 'favorites' ? 'favorites' : 'all';
    if (source !== 'all')
        params.push("source=".concat(encodeURIComponent(source)));
    var tag = String(session.tag || 'all');
    if (tag && tag !== 'all')
        params.push("tag=".concat(encodeURIComponent(tag)));
    if (session.shuffleQuestions)
        params.push('shuffle_questions=1');
    if (session.shuffleOptions)
        params.push('shuffle_options=1');
    var startId = Number(session.start_id || 0) || 0;
    if (startId > 0)
        params.push("start_id=".concat(encodeURIComponent(String(startId))));
    return "/pages/quiz/quiz?".concat(params.join('&'));
}
Page({
    data: {
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
        shownTotal: 0,
        hasLastSession: false,
        lastSession: null,
        lastSessionSummary: ''
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
        this.refreshLastSession();
        if (!this.data.inited && !this.data.loading) {
            this.bootstrap();
            return;
        }
        this.applyFilter();
    },
    refreshLastSession: function () {
        var session = readLastSession();
        this.setData({
            hasLastSession: !!session,
            lastSession: session,
            lastSessionSummary: session ? buildLastSessionSummary(session) : ''
        });
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, meta, myBanksRes, sharedBanksRes, metaObj, subjectsRaw, subjects, map, myBanksObj, sharedBanksObj, myBanksRaw, sharedBanksRaw, _i, myBanksRaw_1, b, item, _b, sharedBanksRaw_1, b, item, banks, e_1;
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
                        metaObj = (meta && typeof meta === 'object' ? meta : {});
                        subjectsRaw = Array.isArray(metaObj.subjects) ? metaObj.subjects : [];
                        subjects = subjectsRaw.map(normalizeSubject).filter(Boolean);
                        subjects.sort(function (a, b) { return a.id - b.id; });
                        map = new Map();
                        myBanksObj = (myBanksRes && typeof myBanksRes === 'object' ? myBanksRes : {});
                        sharedBanksObj = (sharedBanksRes && typeof sharedBanksRes === 'object' ? sharedBanksRes : {});
                        myBanksRaw = Array.isArray(myBanksObj.banks) ? myBanksObj.banks : [];
                        sharedBanksRaw = Array.isArray(sharedBanksObj.banks) ? sharedBanksObj.banks : [];
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
                        banks = Array.from(map.values()).sort(function (a, b) { return String(b.sort_key || '').localeCompare(String(a.sort_key || '')) || b.id - a.id; });
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
        var url = "/pages/review-center-v2/review-center-v2?kind=mistakes&subject=".concat(encodeURIComponent(name));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onBankTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var url = "/pages/review-center-v2/review-center-v2?kind=mistakes&bank_id=".concat(encodeURIComponent(String(id)));
        (0, nav_1.safeNavigate)(url, 'navigateTo');
    },
    onContinueLast: function () {
        var session = this.data.lastSession;
        if (!session) {
            wx.showToast({ title: '暂无上次复盘记录', icon: 'none' });
            return;
        }
        (0, nav_1.safeNavigate)(buildReviewCenterUrl(session), 'navigateTo');
    },
    onContinueLastQuick: function (e) {
        var _a, _b;
        var session = this.data.lastSession;
        if (!session)
            return;
        var modeRaw = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.mode) || '').trim().toLowerCase();
        var mode = modeRaw === 'memo' ? 'memo' : 'quiz';
        (0, nav_1.safeNavigate)(buildQuizUrlFromSession(session, mode), 'navigateTo');
    },
    onTodayFocus: function () {
        var session = this.data.lastSession;
        if (!session) {
            wx.showToast({ title: '请先选择范围开始复盘', icon: 'none' });
            return;
        }
        (0, nav_1.safeNavigate)(buildReviewCenterUrl(session, { kind: 'mistakes', tab: 'practice', qType: 'all', tag: 'all' }), 'navigateTo');
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    }
});
