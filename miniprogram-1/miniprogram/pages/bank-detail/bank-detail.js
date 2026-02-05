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
var config_1 = require("../../utils/config");
var user_settings_1 = require("../../utils/user-settings");
var quiz_source_1 = require("../../utils/quiz-source");
var theme_1 = require("../../utils/theme");
var web_1 = require("../../utils/web");
var OPTION_TYPES = new Set(['选择题', '多选题']);
var KEY_SHUFFLE_Q = 'shuffle_questions';
var KEY_SHUFFLE_O = 'shuffle_options';
var DEFAULT_DETAIL_TAB_ORDER = ['practice', 'reinforce', 'exam', 'search', 'stats', 'share', 'manage'];
var VALID_DETAIL_TABS = new Set(DEFAULT_DETAIL_TAB_ORDER);
var DETAIL_TAB_LABELS = {
    practice: '练习',
    reinforce: '加强',
    exam: '考试',
    search: '搜索',
    stats: '数据',
    share: '分享',
    manage: '管理'
};
function normalizeDetailTabOrder(input, fallback) {
    var base = Array.isArray(fallback) ? fallback : DEFAULT_DETAIL_TAB_ORDER;
    var out = [];
    var seen = new Set();
    var push = function (k) {
        var key = String(k || '').trim().toLowerCase();
        if (!VALID_DETAIL_TABS.has(key))
            return;
        if (seen.has(key))
            return;
        seen.add(key);
        out.push(key);
    };
    (Array.isArray(input) ? input : []).forEach(push);
    base.forEach(push);
    return out;
}
function buildDetailTabViews(order, canManage) {
    if (canManage === void 0) { canManage = false; }
    var list = Array.isArray(order) ? order : DEFAULT_DETAIL_TAB_ORDER;
    var filtered = canManage ? list : list.filter(function (k) { return k !== 'manage'; });
    return filtered.map(function (key) { return ({ key: key, label: DETAIL_TAB_LABELS[key] || key }); });
}
function getBankDetailTabOrderKey(bankId) {
    var id = Number(bankId || 0);
    if (!Number.isFinite(id) || id <= 0)
        return '';
    return "bank_".concat(Math.floor(id), "_detail_tab_order_v1");
}
function readBankDetailTabOrder(key, fallback) {
    if (!key)
        return normalizeDetailTabOrder(null, fallback);
    try {
        var raw = wx.getStorageSync(key);
        if (Array.isArray(raw))
            return normalizeDetailTabOrder(raw, fallback);
        if (typeof raw === 'string') {
            var s = raw.trim();
            if (!s)
                return normalizeDetailTabOrder(null, fallback);
            try {
                return normalizeDetailTabOrder(JSON.parse(s), fallback);
            }
            catch (e) {
                return normalizeDetailTabOrder(null, fallback);
            }
        }
        return normalizeDetailTabOrder(null, fallback);
    }
    catch (e) {
        return normalizeDetailTabOrder(null, fallback);
    }
}
function persistBankDetailTabOrder(key, order) {
    if (!key)
        return;
    try {
        wx.setStorageSync(key, Array.isArray(order) ? order : []);
    }
    catch (e) { }
}
function normalizeScope(input) {
    var s = String(input || '').trim().toLowerCase();
    if (s === 'favorites')
        return 'favorites';
    if (s === 'mistakes')
        return 'mistakes';
    return 'all';
}
function shouldCountForTab(tab) {
    return tab === 'practice';
}
function normalizeTab(input) {
    var s = String(input || '').trim().toLowerCase();
    if (s === 'data')
        return 'stats';
    if (s === 'exam')
        return 'exam';
    if (s === 'search')
        return 'search';
    if (s === 'stats')
        return 'stats';
    if (s === 'reinforce' || s === 'strengthen' || s === 'enhance')
        return 'reinforce';
    if (s === 'favorites' || s === 'mistakes')
        return 'practice';
    if (s === 'share')
        return 'share';
    if (s === 'manage')
        return 'manage';
    return 'practice';
}
function normalizeReinforceSubTab(input) {
    var s = String(input || '').trim().toLowerCase();
    return s === 'similar' ? 'similar' : 'wrong';
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
function normalizeTextLines(input) {
    var text = String(input !== null && input !== void 0 ? input : '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    var lines = text.split('\n').map(function (s) { return String(s !== null && s !== void 0 ? s : '').trimEnd(); });
    while (lines.length && !lines[lines.length - 1])
        lines.pop();
    return lines;
}
function normalizeBankDetailOptions(rawOptions, qType) {
    var qt = String(qType || '').trim();
    if (rawOptions == null || rawOptions === '') {
        if (qt === '判断题') {
            return [
                { key: '正确', value: '正确' },
                { key: '错误', value: '错误' }
            ];
        }
        return [];
    }
    var parsed = rawOptions;
    if (typeof rawOptions === 'string') {
        var s = rawOptions.trim();
        if (s) {
            try {
                parsed = JSON.parse(s);
            }
            catch (e) {
                parsed = rawOptions;
            }
        }
    }
    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    var out = [];
    if (Array.isArray(parsed)) {
        parsed.forEach(function (opt, idx) {
            var _a, _b, _c;
            if (opt && typeof opt === 'object') {
                var key = String((_b = (_a = opt.key) !== null && _a !== void 0 ? _a : letters[idx]) !== null && _b !== void 0 ? _b : '').trim();
                var value = String((_c = opt.value) !== null && _c !== void 0 ? _c : '').trim();
                if (key || value)
                    out.push({ key: key || String(idx + 1), value: value });
            }
            else {
                var value = String(opt !== null && opt !== void 0 ? opt : '').trim();
                if (value)
                    out.push({ key: letters[idx] || String(idx + 1), value: value });
            }
        });
        return out;
    }
    if (parsed && typeof parsed === 'object') {
        Object.keys(parsed).forEach(function (k) {
            var _a;
            var key = String(k !== null && k !== void 0 ? k : '').trim();
            var value = String((_a = parsed[k]) !== null && _a !== void 0 ? _a : '').trim();
            if (key || value)
                out.push({ key: key, value: value });
        });
        return out;
    }
    return [];
}
function getStoredBool(key, fallback) {
    if (fallback === void 0) { fallback = false; }
    try {
        var raw = wx.getStorageSync(key);
        if (raw === true || raw === 1 || raw === '1')
            return true;
        if (raw === false || raw === 0 || raw === '0')
            return false;
        return fallback;
    }
    catch (e) {
        return fallback;
    }
}
function setStoredBool(key, value) {
    try {
        wx.setStorageSync(key, value ? '1' : '0');
    }
    catch (e) { }
}
function clampPct(v) {
    if (!Number.isFinite(v))
        return 0;
    return Math.max(0, Math.min(100, v));
}
function parseBoolFlag(v, fallback) {
    if (v === true || v === 1 || v === '1')
        return true;
    if (v === false || v === 0 || v === '0')
        return false;
    return fallback;
}
function appendFromMiniapp(url) {
    var raw = String(url || '').trim();
    if (!raw)
        return '';
    if (/([?&])from=/.test(raw))
        return raw;
    return "".concat(raw).concat(raw.includes('?') ? '&' : '?', "from=miniapp");
}
function buildExternalWebUrl(next) {
    var origin = String((0, api_1.getApiOrigin)() || '').trim().replace(/\/$/, '');
    var path = (0, web_1.normalizeWebNextPath)(next, '/hub');
    if (!origin)
        return path;
    return appendFromMiniapp("".concat(origin).concat(path));
}
Page({
    data: {
        drawerOpen: false,
        loading: false,
        inited: false,
        tab: 'practice',
        entry: '',
        tabOrderOpen: false,
        detailTabs: buildDetailTabViews(DEFAULT_DETAIL_TAB_ORDER, false),
        bankId: 0,
        bankName: '',
        bankDescription: '',
        canManageShare: false,
        bankIsPublic: false,
        bankAllowCopy: true,
        bankPublicDescription: '',
        bankPublicSaving: false,
        bankPublicError: '',
        totalCount: 0,
        favCount: 0,
        mistakeCount: 0,
        examBuilderOpen: false,
        myStats: {
            total_answered: 0,
            correct_count: 0,
            wrong_count: 0,
            accuracy: 0
        },
        searchKeyword: '',
        searchType: 'all',
        searchResults: [],
        searchTotal: 0,
        searchPage: 1,
        searchPerPage: 20,
        searchLoading: false,
        searchSearched: false,
        searchError: '',
        qDetailOpen: false,
        qDetailLoading: false,
        qDetailError: '',
        qDetailId: 0,
        qDetailMeta: '',
        qDetailContentLines: [],
        qDetailAnswerLines: [],
        qDetailExplanationLines: [],
        qDetailOptions: [],
        webLeadOpen: false,
        webLeadTitle: '',
        webLeadContent: '',
        webLeadUrl: '',
        practiceScope: 'all',
        types: [],
        qType: 'all',
        tags: [],
        tag: 'all',
        practiceAdvancedOpen: false,
        shuffleQuestions: false,
        shuffleOptions: false,
        shuffleOptionsDisabled: false,
        startCount: 0,
        startCountText: '—',
        startDisabled: true,
        startError: '',
        // 统计详情（对齐 Web 题库详情-统计子页面）
        statsSubTab: 'global',
        statsDays: 14,
        statsLoading: false,
        statsLoadedDays: 0,
        statsLoadedSubTab: 'global',
        statsError: '',
        statsOverview: {
            total: 0,
            answered: 0,
            correct: 0,
            wrong: 0,
            favorites: 0,
            mistakes: 0,
            mistakeTimes: 0,
            accuracy: 0,
            completion: 0,
            accuracyText: '0.0%',
            completionText: '0.0%',
            streakDays: 0,
            lastText: '—'
        },
        statsTrend: [],
        statsByType: [],
        statsByDifficulty: [],
        // 加强模块（对齐 Web：错题/相似题）
        reinforceSubTab: 'wrong',
        reinforceWrong: {
            loading: false,
            loaded: false,
            error: '',
            desc: '—',
            listMeta: '—',
            wrongTotal: 0,
            recommendIds: [],
            top: []
        },
        reinforceSimilar: {
            loading: false,
            loaded: false,
            error: '',
            desc: '—',
            listMeta: '—',
            wrongTotal: 0,
            similarMode: '',
            pairsCount: 0,
            seedIds: [],
            startIds: [],
            pairs: []
        },
        statsAdvice: [],
        statsHasDifficulty: false,
        statsQuestions: [],
        favoritesTrend: {},
        ringAccuracy: 0,
        ringCompletion: 0,
        ringActive: 0,
        activeDaysRate: 0,
        ringRepeat: 0,
        repeatRateText: '0%',
        mistakeRateText: '0%',
        favMistakeRateText: '0%',
        heatCells: [],
        displayTypes: [],
        // 分享管理（仅创建者可用；无权限时给出提示）
        shares: [],
        shareLoading: false,
        shareError: '',
        usageStats: { shared_users: 0, public_users: 0, total_users: 0 },
        usageStatsLoaded: false,
        usageStatsLoading: false,
        wechatShareToken: '',
        wechatShareReady: false,
        wechatSharePreparing: false,
        newShare: {
            permission: 'read',
            expiresIn: 0,
            maxUses: 0
        }
    },
    startCountTimer: null,
    startCountReq: 0,
    statsReq: 0,
    qDetailReq: 0,
    tabExplicit: false,
    scopeForced: '',
    onLoad: function (options) {
        var bankId = Number((options === null || options === void 0 ? void 0 : options.id) || (options === null || options === void 0 ? void 0 : options.bank_id) || (options === null || options === void 0 ? void 0 : options.bankId) || 0);
        var rawTab = options === null || options === void 0 ? void 0 : options.tab;
        var tab = normalizeTab(rawTab);
        var entry = String((options === null || options === void 0 ? void 0 : options.entry) || '').trim().toLowerCase();
        var tabKey = String(rawTab || '').trim().toLowerCase();
        var scopeFromParams = (tabKey === 'favorites' || tabKey === 'mistakes')
            ? normalizeScope(tabKey)
            : (entry === 'favorites' || entry === 'mistakes') ? normalizeScope(entry) : 'all';
        this.scopeForced = scopeFromParams !== 'all' ? scopeFromParams : '';
        this.tabExplicit = rawTab !== undefined && rawTab !== null && String(rawTab).trim() !== '';
        this.setData({
            bankId: Number.isFinite(bankId) ? bankId : 0,
            tab: tab,
            entry: entry,
            practiceScope: scopeFromParams
        });
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
        try {
            wx.showShareMenu({ withShareTicket: true });
        }
        catch (e) { }
        this.consumeReturnTab();
        if (!this.data.inited && !this.data.loading) {
            this.bootstrap();
            return;
        }
        this.syncShuffleOptionsDisabled();
        if (shouldCountForTab(this.data.tab)) {
            this.scheduleStartCount();
        }
        if (this.data.tab === 'share' && this.data.canManageShare) {
            this.loadUsageStats();
            this.ensureWechatShareToken(false);
        }
        if (this.data.tab === 'stats') {
            this.ensureStatsDetail();
        }
        if (this.data.tab === 'reinforce') {
            this.ensureReinforce(false);
        }
    },
    consumeReturnTab: function () {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        var key = "bank_".concat(bankId, "_return_tab");
        var desired = getStoredString(key, '');
        if (!desired)
            return;
        setStoredString(key, '');
        var tab = normalizeTab(desired);
        if (tab === this.data.tab)
            return;
        this.setData({ tab: tab });
    },
    openDataPage: function (subtab) {
        var _this = this;
        var raw = String(subtab || 'global');
        var next = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
        var bankId = Number(this.data.bankId || 0);
        if (bankId)
            setStoredString("bank_".concat(bankId, "_stats_subtab"), next);
        this.setData({ tab: 'stats', statsSubTab: next, statsLoadedDays: 0, statsLoadedSubTab: next }, function () {
            _this.ensureStatsDetail(true);
        });
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, keyType, keyTag, keyScope, keySearchType, keyStatsSubTab, keyReinforceSubTab, storedType, storedTag, storedScope, storedSearchType, storedStatsSubTab, storedReinforceSubTab, shuffleQuestions, shuffleOptions, entry, tab, practiceScope, forcedScope, statsSubTab, reinforceSubTab, _a, detailRes, countsRes, myStatsRes, tagsRes, bankData, countsData, myStatsData, tagsData, bankName, bankDescription, accessType, permission, canManageShare, bankIsPublic, bankAllowCopy, bankPublicDescription, tabOrderKey, tabOrder, detailTabs, typesRaw, types, qType, tagsRaw, tags, tag, searchType, totalCount, favCount, mistakeCount, e_1;
            var _b, _c, _d, _e;
            return __generator(this, function (_f) {
                switch (_f.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0) {
                            wx.showToast({ title: '题库参数缺失', icon: 'none' });
                            setTimeout(function () { return wx.navigateBack(); }, 1200);
                            return [2 /*return*/];
                        }
                        this.initDetailTabOrder();
                        keyType = "bank_".concat(bankId, "_type");
                        keyTag = "bank_".concat(bankId, "_tag");
                        keyScope = "bank_".concat(bankId, "_scope");
                        keySearchType = "bank_".concat(bankId, "_search_type");
                        keyStatsSubTab = "bank_".concat(bankId, "_stats_subtab");
                        keyReinforceSubTab = "bank_".concat(bankId, "_reinforce_subtab");
                        storedType = getStoredString(keyType, 'all');
                        storedTag = getStoredString(keyTag, 'all');
                        storedScope = getStoredString(keyScope, 'all');
                        storedSearchType = getStoredString(keySearchType, 'all');
                        storedStatsSubTab = getStoredString(keyStatsSubTab, 'global');
                        storedReinforceSubTab = getStoredString(keyReinforceSubTab, 'wrong');
                        shuffleQuestions = getStoredBool(KEY_SHUFFLE_Q, false);
                        shuffleOptions = getStoredBool(KEY_SHUFFLE_O, false);
                        entry = String(this.data.entry || '').trim().toLowerCase();
                        tab = this.data.tab;
                        practiceScope = this.data.practiceScope || 'all';
                        if (!this.tabExplicit) {
                            if (entry === 'favorites') {
                                tab = 'practice';
                                practiceScope = 'favorites';
                                this.scopeForced = 'favorites';
                            }
                            else if (entry === 'mistakes') {
                                tab = 'practice';
                                practiceScope = 'mistakes';
                                this.scopeForced = 'mistakes';
                            }
                            else if (entry === 'exam') {
                                tab = 'exam';
                            }
                        }
                        forcedScope = this.scopeForced;
                        if (forcedScope === 'favorites' || forcedScope === 'mistakes') {
                            practiceScope = forcedScope;
                        }
                        else {
                            practiceScope = normalizeScope(storedScope);
                        }
                        statsSubTab = (storedStatsSubTab === 'mistakes' || storedStatsSubTab === 'favorites') ? storedStatsSubTab : 'global';
                        reinforceSubTab = normalizeReinforceSubTab(storedReinforceSubTab);
                        this.setData({ loading: true, startError: '' });
                        _f.label = 1;
                    case 1:
                        _f.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getBankDetail(bankId),
                                api_1.api.getBankUserCounts(bankId, { source: 'all' }).catch(function () { return ({ data: { total: 0, favorites: 0, mistakes: 0 } }); }),
                                api_1.api.getBankMyStats(bankId).catch(function () { return ({ data: { total_answered: 0, correct_count: 0, wrong_count: 0, accuracy: 0 } }); }),
                                api_1.api.getBankTags(bankId).catch(function () { return ({ data: { tags: [] } }); })
                            ])];
                    case 2:
                        _a = _f.sent(), detailRes = _a[0], countsRes = _a[1], myStatsRes = _a[2], tagsRes = _a[3];
                        bankData = (detailRes === null || detailRes === void 0 ? void 0 : detailRes.data) || detailRes || {};
                        countsData = (countsRes === null || countsRes === void 0 ? void 0 : countsRes.data) || countsRes || {};
                        myStatsData = (myStatsRes === null || myStatsRes === void 0 ? void 0 : myStatsRes.data) || myStatsRes || {};
                        tagsData = (tagsRes === null || tagsRes === void 0 ? void 0 : tagsRes.data) || ((_b = tagsRes === null || tagsRes === void 0 ? void 0 : tagsRes.data) === null || _b === void 0 ? void 0 : _b.data) || (tagsRes === null || tagsRes === void 0 ? void 0 : tagsRes.data) || tagsRes || {};
                        bankName = String((bankData === null || bankData === void 0 ? void 0 : bankData.name) || '').trim();
                        bankDescription = String((bankData === null || bankData === void 0 ? void 0 : bankData.description) || '').trim();
                        accessType = String((bankData === null || bankData === void 0 ? void 0 : bankData.access_type) || '').trim().toLowerCase();
                        permission = String((bankData === null || bankData === void 0 ? void 0 : bankData.permission) || '').trim().toLowerCase();
                        canManageShare = accessType === 'owner' || permission === 'owner';
                        if (tab === 'manage' && !canManageShare)
                            tab = 'practice';
                        bankIsPublic = parseBoolFlag(bankData === null || bankData === void 0 ? void 0 : bankData.is_public, false);
                        bankAllowCopy = parseBoolFlag(bankData === null || bankData === void 0 ? void 0 : bankData.allow_copy, true);
                        bankPublicDescription = String((bankData === null || bankData === void 0 ? void 0 : bankData.public_description) || '').trim();
                        tabOrderKey = getBankDetailTabOrderKey(bankId);
                        tabOrder = readBankDetailTabOrder(tabOrderKey, DEFAULT_DETAIL_TAB_ORDER);
                        detailTabs = buildDetailTabViews(tabOrder, canManageShare);
                        typesRaw = Array.isArray(bankData === null || bankData === void 0 ? void 0 : bankData.available_types) ? bankData.available_types : [];
                        types = (typesRaw || [])
                            .filter(function (t) { return typeof t === 'string' && t.trim(); })
                            .map(function (t) { return String(t).trim(); });
                        qType = storedType === 'all' || types.includes(storedType) ? storedType : 'all';
                        tagsRaw = Array.isArray(tagsData === null || tagsData === void 0 ? void 0 : tagsData.tags)
                            ? tagsData.tags
                            : Array.isArray((_c = tagsData === null || tagsData === void 0 ? void 0 : tagsData.data) === null || _c === void 0 ? void 0 : _c.tags)
                                ? tagsData.data.tags
                                : [];
                        tags = (tagsRaw || [])
                            .map(function (t) { return ({ name: String((t === null || t === void 0 ? void 0 : t.name) || '').trim(), count: t === null || t === void 0 ? void 0 : t.count }); })
                            .filter(function (t) { return t.name; });
                        tag = storedTag === 'all' || tags.some(function (t) { return t.name === storedTag; }) ? storedTag : 'all';
                        searchType = storedSearchType === 'all' || types.includes(storedSearchType) ? storedSearchType : 'all';
                        totalCount = Number((_e = (_d = countsData === null || countsData === void 0 ? void 0 : countsData.total) !== null && _d !== void 0 ? _d : bankData === null || bankData === void 0 ? void 0 : bankData.question_count) !== null && _e !== void 0 ? _e : 0) || 0;
                        favCount = Number((countsData === null || countsData === void 0 ? void 0 : countsData.favorites) || 0) || 0;
                        mistakeCount = Number((countsData === null || countsData === void 0 ? void 0 : countsData.mistakes) || 0) || 0;
                        this.setData({
                            inited: true,
                            bankName: bankName || "\u9898\u5E93".concat(bankId),
                            bankDescription: bankDescription,
                            canManageShare: canManageShare,
                            detailTabs: detailTabs,
                            bankIsPublic: bankIsPublic,
                            bankAllowCopy: bankAllowCopy,
                            bankPublicDescription: bankPublicDescription,
                            bankPublicSaving: false,
                            bankPublicError: '',
                            totalCount: totalCount,
                            favCount: favCount,
                            mistakeCount: mistakeCount,
                            myStats: {
                                total_answered: Number((myStatsData === null || myStatsData === void 0 ? void 0 : myStatsData.total_answered) || 0) || 0,
                                correct_count: Number((myStatsData === null || myStatsData === void 0 ? void 0 : myStatsData.correct_count) || 0) || 0,
                                wrong_count: Number((myStatsData === null || myStatsData === void 0 ? void 0 : myStatsData.wrong_count) || 0) || 0,
                                accuracy: Number((myStatsData === null || myStatsData === void 0 ? void 0 : myStatsData.accuracy) || 0) || 0
                            },
                            tab: tab,
                            practiceScope: practiceScope,
                            types: types,
                            qType: qType,
                            tags: tags,
                            tag: tag,
                            searchType: searchType,
                            statsSubTab: statsSubTab,
                            statsLoadedSubTab: statsSubTab,
                            reinforceSubTab: reinforceSubTab,
                            reinforceWrong: {
                                loading: false,
                                loaded: false,
                                error: '',
                                desc: '—',
                                listMeta: '—',
                                wrongTotal: 0,
                                recommendIds: [],
                                top: []
                            },
                            reinforceSimilar: {
                                loading: false,
                                loaded: false,
                                error: '',
                                desc: '—',
                                listMeta: '—',
                                wrongTotal: 0,
                                similarMode: '',
                                pairsCount: 0,
                                seedIds: [],
                                startIds: [],
                                pairs: []
                            },
                            shuffleQuestions: shuffleQuestions,
                            shuffleOptions: shuffleOptions
                        });
                        setStoredString(keyType, qType);
                        setStoredString(keyTag, tag);
                        setStoredString(keyScope, practiceScope);
                        setStoredString(keySearchType, searchType);
                        setStoredString(keyStatsSubTab, statsSubTab);
                        setStoredString(keyReinforceSubTab, reinforceSubTab);
                        this.syncShuffleOptionsDisabled();
                        if (shouldCountForTab(tab)) {
                            this.scheduleStartCount();
                        }
                        if (tab === 'share' && canManageShare) {
                            this.loadShares();
                        }
                        if (tab === 'stats') {
                            this.ensureStatsDetail();
                        }
                        if (tab === 'reinforce') {
                            this.ensureReinforce(true);
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _f.sent();
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
    },
    initDetailTabOrder: function () {
        var bankId = Number(this.data.bankId || 0);
        var key = getBankDetailTabOrderKey(bankId);
        var order = readBankDetailTabOrder(key, DEFAULT_DETAIL_TAB_ORDER);
        this.setData({ detailTabs: buildDetailTabViews(order, Boolean(this.data.canManageShare)) });
    },
    applyDetailTabOrder: function (nextOrder) {
        var normalized = normalizeDetailTabOrder(nextOrder, DEFAULT_DETAIL_TAB_ORDER);
        var bankId = Number(this.data.bankId || 0);
        var key = getBankDetailTabOrderKey(bankId);
        persistBankDetailTabOrder(key, normalized);
        this.setData({ detailTabs: buildDetailTabViews(normalized, Boolean(this.data.canManageShare)) });
    },
    onOpenTabOrder: function () {
        this.setData({ tabOrderOpen: true });
    },
    onCloseTabOrder: function () {
        this.setData({ tabOrderOpen: false });
    },
    onTabOrderSheetTap: function () { },
    onMoveTabOrder: function (e) {
        var _a, _b, _c, _d;
        var act = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.act) || '').trim();
        var keyRaw = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.key) || '').trim().toLowerCase();
        if (!VALID_DETAIL_TABS.has(keyRaw))
            return;
        var order = (this.data.detailTabs || [])
            .map(function (it) { return String((it === null || it === void 0 ? void 0 : it.key) || '').trim().toLowerCase(); })
            .filter(function (k) { return VALID_DETAIL_TABS.has(k); });
        var idx = order.indexOf(keyRaw);
        if (idx < 0)
            return;
        var delta = act === 'up' ? -1 : act === 'down' ? 1 : 0;
        if (!delta)
            return;
        var next = idx + delta;
        if (next < 0 || next >= order.length)
            return;
        var copy = order.slice();
        var it = copy.splice(idx, 1)[0];
        copy.splice(next, 0, it);
        this.applyDetailTabOrder(copy);
    },
    onResetTabOrder: function () {
        this.applyDetailTabOrder(DEFAULT_DETAIL_TAB_ORDER.slice());
    },
    onTabTap: function (e) {
        var _this = this;
        var _a, _b;
        var tab = normalizeTab(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || 'practice');
        if (tab === this.data.tab)
            return;
        this.setData({ tab: tab, startError: '' }, function () {
            _this.syncShuffleOptionsDisabled();
            if (shouldCountForTab(tab)) {
                _this.scheduleStartCount();
            }
            if (tab === 'share' && _this.data.canManageShare) {
                _this.loadUsageStats();
                _this.ensureWechatShareToken(false);
            }
            if (tab === 'stats') {
                _this.ensureStatsDetail();
            }
            if (tab === 'reinforce') {
                _this.ensureReinforce(false);
            }
        });
    },
    onGoManageQuestions: function () {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        this.openWebLead({
            title: '题目管理',
            content: '小程序端暂不支持题目管理，请在浏览器打开 Web 端进行新增/编辑/删除（建议电脑端）。',
            next: "/user/banks/".concat(bankId)
        });
    },
    onGoManageSettings: function () {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        this.openWebLead({
            title: '题库设置',
            content: '题库设置（公开/私密、描述、复制权限等）请在浏览器打开 Web 端完成。',
            next: "/user/banks/".concat(bankId, "/edit")
        });
    },
    openWebLead: function (options) {
        var title = String((options === null || options === void 0 ? void 0 : options.title) || '请前往网页端').trim() || '请前往网页端';
        var content = String((options === null || options === void 0 ? void 0 : options.content) || '').trim();
        var url = buildExternalWebUrl(options === null || options === void 0 ? void 0 : options.next);
        this.setData({
            webLeadOpen: true,
            webLeadTitle: title,
            webLeadContent: content,
            webLeadUrl: url
        });
    },
    onWebLeadClose: function () {
        this.setData({ webLeadOpen: false });
    },
    onWebLeadSheetTap: function () { },
    onWebLeadCopy: function () {
        var _this = this;
        var url = String(this.data.webLeadUrl || '').trim();
        if (!url)
            return;
        wx.setClipboardData({
            data: url,
            success: function () {
                wx.showToast({ title: '链接已复制', icon: 'success' });
                _this.setData({ webLeadOpen: false });
            },
            fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
        });
    },
    onGoShareTab: function () {
        var _this = this;
        this.setData({ tab: 'share', startError: '' }, function () {
            if (_this.data.canManageShare) {
                _this.loadUsageStats();
                _this.ensureWechatShareToken(false);
            }
        });
    },
    onBankOwnershipTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, raw, nextPublic, confirmed, payload, res, msg, err_1, msg;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!this.data.canManageShare) {
                            wx.showToast({ title: '无权操作', icon: 'none' });
                            return [2 /*return*/];
                        }
                        raw = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.public;
                        nextPublic = raw === true || raw === 1 || raw === '1';
                        if (nextPublic === Boolean(this.data.bankIsPublic))
                            return [2 /*return*/];
                        if (this.data.bankPublicSaving)
                            return [2 /*return*/];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: nextPublic ? '设为公共题库' : '设为个人题库',
                                    content: nextPublic
                                        ? '设为公共后将出现在题库广场，其他用户可进入使用。是否继续？'
                                        : '设为个人后将从题库广场移除（不影响你自己刷题）。是否继续？',
                                    confirmText: '确定',
                                    cancelText: '取消',
                                    success: function (res) { return resolve(!!res.confirm); },
                                    fail: function () { return resolve(false); }
                                });
                            })];
                    case 1:
                        confirmed = _c.sent();
                        if (!confirmed)
                            return [2 /*return*/];
                        payload = {
                            is_public: nextPublic,
                            public_description: String(this.data.bankPublicDescription || ''),
                            allow_copy: Boolean(this.data.bankAllowCopy)
                        };
                        this.setData({ bankPublicSaving: true, bankPublicError: '' });
                        _c.label = 2;
                    case 2:
                        _c.trys.push([2, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.setBankPublic(bankId, payload)];
                    case 3:
                        res = _c.sent();
                        msg = String((res === null || res === void 0 ? void 0 : res.message) || (nextPublic ? '题库已公开' : '题库已设为私密'));
                        this.setData({ bankIsPublic: nextPublic });
                        wx.showToast({ title: msg, icon: 'success' });
                        return [3 /*break*/, 6];
                    case 4:
                        err_1 = _c.sent();
                        msg = (err_1 && err_1.message) ? String(err_1.message) : '保存失败';
                        this.setData({ bankPublicError: msg });
                        wx.showToast({ title: msg, icon: 'none' });
                        return [3 /*break*/, 6];
                    case 5:
                        this.setData({ bankPublicSaving: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onReinforceSubTabTap: function (e) {
        var _this = this;
        var _a, _b;
        var next = normalizeReinforceSubTab(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.subtab) || 'wrong');
        if (next === this.data.reinforceSubTab)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (bankId)
            setStoredString("bank_".concat(bankId, "_reinforce_subtab"), next);
        this.setData({ reinforceSubTab: next }, function () {
            _this.ensureReinforce(false);
        });
    },
    ensureReinforce: function (force) {
        var kind = this.data.reinforceSubTab;
        if (kind === 'similar') {
            if (force || !this.data.reinforceSimilar.loaded)
                this.loadReinforceSimilar();
            return;
        }
        if (force || !this.data.reinforceWrong.loaded)
            this.loadReinforceWrong();
    },
    parseIdList: function (raw, maxLen) {
        if (maxLen === void 0) { maxLen = 200; }
        var s = String(raw || '').replace(/，/g, ',').trim();
        if (!s)
            return [];
        var parts = s.split(',').map(function (x) { return String(x || '').trim(); }).filter(Boolean);
        var out = [];
        var seen = new Set();
        for (var _i = 0, parts_1 = parts; _i < parts_1.length; _i++) {
            var p = parts_1[_i];
            if (out.length >= maxLen)
                break;
            var n = Number(p);
            if (!Number.isFinite(n) || n <= 0)
                continue;
            var id = Math.floor(n);
            if (seen.has(id))
                continue;
            seen.add(id);
            out.push(id);
        }
        return out;
    },
    buildReinforceQuizUrl: function (ids, rk) {
        var bankId = Number(this.data.bankId || 0);
        var list = Array.isArray(ids)
            ? ids.map(function (x) { return Number(x); }).filter(function (n) { return Number.isFinite(n) && n > 0; }).map(function (n) { return Math.floor(n); })
            : [];
        if (!Number.isFinite(bankId) || bankId <= 0 || !list.length)
            return '';
        var qs = "bank_id=".concat(encodeURIComponent(String(bankId))) +
            "&mode=reinforce" +
            "&rk=".concat(encodeURIComponent(rk)) +
            "&ids=".concat(list.join(','));
        return "/pages/quiz/quiz?".concat(qs);
    },
    onStartReinforceWrong: function () {
        var ids = (this.data.reinforceWrong && Array.isArray(this.data.reinforceWrong.recommendIds))
            ? this.data.reinforceWrong.recommendIds
            : [];
        var url = this.buildReinforceQuizUrl(ids, 'wrong');
        if (!url)
            return;
        wx.navigateTo({ url: url });
    },
    onStartReinforceWrongAll: function () {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        wx.navigateTo({ url: "/pages/quiz/quiz?bank_id=".concat(encodeURIComponent(String(bankId)), "&mode=quiz&source=mistakes") });
    },
    onStartReinforceWrongOne: function (e) {
        var _a, _b;
        var qid = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(qid) || qid <= 0)
            return;
        var url = this.buildReinforceQuizUrl([qid], 'wrong');
        if (!url)
            return;
        wx.navigateTo({ url: url });
    },
    onStartReinforceSimilar: function () {
        var ids = (this.data.reinforceSimilar && Array.isArray(this.data.reinforceSimilar.startIds))
            ? this.data.reinforceSimilar.startIds
            : [];
        var url = this.buildReinforceQuizUrl(ids, 'similar');
        if (!url)
            return;
        wx.navigateTo({ url: url });
    },
    onStartReinforceSimilarPair: function (e) {
        var _a, _b, _c, _d;
        var a = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.a) || 0);
        var b = Number(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.b) || 0);
        if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0)
            return;
        var url = this.buildReinforceQuizUrl([a, b], 'similar');
        if (!url)
            return;
        wx.navigateTo({ url: url });
    },
    loadReinforceWrong: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, data, wrongTotal, recommendIds, topRaw, top, recommendN, desc, listMeta, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (this.data.reinforceWrong.loading)
                            return [2 /*return*/];
                        this.setData({
                            reinforceWrong: Object.assign({}, this.data.reinforceWrong, { loading: true, error: '' })
                        });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getQuizReinforce({
                                source: 'user_bank',
                                bank_id: bankId,
                                include: 'wrong',
                                wrong_list_n: 30
                            })];
                    case 2:
                        data = _a.sent();
                        wrongTotal = Number((data === null || data === void 0 ? void 0 : data.wrong_total) || 0) || 0;
                        recommendIds = Array.isArray(data === null || data === void 0 ? void 0 : data.wrong_recommend_ids)
                            ? this.parseIdList(data.wrong_recommend_ids.join(','), 200)
                            : this.parseIdList(data === null || data === void 0 ? void 0 : data.wrong_recommend_ids, 200);
                        topRaw = Array.isArray(data === null || data === void 0 ? void 0 : data.wrong_top) ? data.wrong_top : [];
                        top = topRaw
                            .map(function (it) { return ({
                            question_id: Number((it === null || it === void 0 ? void 0 : it.question_id) || 0) || 0,
                            wrong_count: Number((it === null || it === void 0 ? void 0 : it.wrong_count) || 1) || 1,
                            q_type: String((it === null || it === void 0 ? void 0 : it.q_type) || '').trim(),
                            content_preview: String((it === null || it === void 0 ? void 0 : it.content_preview) || '').trim()
                        }); })
                            .filter(function (it) { return it.question_id > 0; });
                        recommendN = recommendIds.length ? recommendIds.length : Math.min(wrongTotal, 20);
                        desc = wrongTotal > 0
                            ? "\u4F60\u5728\u672C\u9898\u5E93\u7D2F\u8BA1\u9519\u9898 ".concat(wrongTotal, " \u9053\uFF0C\u63A8\u8350\u4F18\u5148\u5DE9\u56FA\u5176\u4E2D ").concat(recommendN, " \u9053\u9AD8\u9891\u9519\u9898\u3002")
                            : '当前没有错题记录，继续保持！';
                        listMeta = wrongTotal > 0
                            ? "\u5C55\u793A ".concat(top.length, " \u9898 \u00B7 \u5171\u9519\u9898 ").concat(wrongTotal, " \u9898")
                            : '暂无错题记录';
                        this.setData({
                            reinforceWrong: {
                                loading: false,
                                loaded: true,
                                error: '',
                                desc: desc,
                                listMeta: listMeta,
                                wrongTotal: wrongTotal,
                                recommendIds: recommendIds,
                                top: top
                            }
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        this.setData({
                            reinforceWrong: Object.assign({}, this.data.reinforceWrong, {
                                loading: false,
                                loaded: true,
                                error: (e_2 && e_2.message) ? String(e_2.message) : '加载失败',
                                desc: '加载失败，请下拉刷新重试',
                                listMeta: '加载失败'
                            })
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    loadReinforceSimilar: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, data, wrongTotal, seedIds, seedSet_1, similarIds, similarOnlyIds, similarMode, pairsCount, pairsRaw, pairs, startIds, desc, pairsText, listMeta, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (this.data.reinforceSimilar.loading)
                            return [2 /*return*/];
                        this.setData({
                            reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, { loading: true, error: '' })
                        });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getQuizReinforce({
                                source: 'user_bank',
                                bank_id: bankId,
                                include: 'similar',
                                pairs_n: 30
                            })];
                    case 2:
                        data = _a.sent();
                        wrongTotal = Number((data === null || data === void 0 ? void 0 : data.wrong_total) || 0) || 0;
                        seedIds = Array.isArray(data === null || data === void 0 ? void 0 : data.similar_seed_ids)
                            ? (data.similar_seed_ids || []).map(function (x) { return Number(x); }).filter(function (n) { return Number.isFinite(n) && n > 0; }).map(function (n) { return Math.floor(n); })
                            : [];
                        seedSet_1 = new Set(seedIds);
                        similarIds = Array.isArray(data === null || data === void 0 ? void 0 : data.similar_training_ids)
                            ? (data.similar_training_ids || []).map(function (x) { return Number(x); }).filter(function (n) { return Number.isFinite(n) && n > 0; }).map(function (n) { return Math.floor(n); })
                            : [];
                        similarOnlyIds = similarIds.filter(function (id) { return !seedSet_1.has(id); });
                        similarMode = String((data === null || data === void 0 ? void 0 : data.similar_mode) || '').trim().toLowerCase();
                        pairsCount = Number((data === null || data === void 0 ? void 0 : data.similar_pairs_count) || 0) || 0;
                        pairsRaw = Array.isArray(data === null || data === void 0 ? void 0 : data.similar_pairs) ? data.similar_pairs : [];
                        pairs = pairsRaw
                            .map(function (p) {
                            var stem = Number((p === null || p === void 0 ? void 0 : p.stem_sim) || 0) || 0;
                            var opt = Number((p === null || p === void 0 ? void 0 : p.opt_sim) || 0) || 0;
                            var pct = Math.max(stem, opt) > 0 ? Math.round(Math.max(stem, opt) * 100) : 0;
                            var aId = Number((p === null || p === void 0 ? void 0 : p.a_id) || 0) || 0;
                            var bId = Number((p === null || p === void 0 ? void 0 : p.b_id) || 0) || 0;
                            return {
                                key: (aId > 0 && bId > 0) ? "".concat(aId, "_").concat(bId) : '',
                                a_id: aId,
                                b_id: bId,
                                a_type: String((p === null || p === void 0 ? void 0 : p.a_type) || '').trim(),
                                b_type: String((p === null || p === void 0 ? void 0 : p.b_type) || '').trim(),
                                a_preview: String((p === null || p === void 0 ? void 0 : p.a_preview) || '').trim(),
                                b_preview: String((p === null || p === void 0 ? void 0 : p.b_preview) || '').trim(),
                                stem_sim: stem,
                                opt_sim: opt,
                                sim_pct: pct,
                                sim_pct_text: pct > 0 ? "\u76F8\u4F3C ".concat(pct, "%") : '相似'
                            };
                        })
                            .filter(function (p) { return p.a_id > 0 && p.b_id > 0; });
                        startIds = [];
                        desc = '先完成一些练习后，这里会给出相似题加强。';
                        if (similarMode === 'bank_dedupe' || similarMode === 'subject_dedupe') {
                            if (similarOnlyIds.length) {
                                startIds = similarOnlyIds.slice();
                                pairsText = pairsCount > 0 ? "".concat(pairsCount, " \u7EC4") : '';
                                desc = "\u5DF2\u5728\u672C\u9898\u5E93\u68C0\u6D4B\u5230".concat(pairsText ? (' ' + pairsText) : '', "\u76F8\u4F3C\u9898\uFF08\u9898\u5E72\u76F8\u4F3C\u4F18\u5148\uFF0C\u9009\u9879\u76F8\u4F3C\u515C\u5E95\uFF09\uFF0C\u8BAD\u7EC3\u5171 ").concat(similarOnlyIds.length, " \u9053\u3002");
                            }
                            else {
                                desc = wrongTotal > 0 ? '暂未检测到明显相似题（题干/选项相似），可先做错题加强。' : '暂未检测到明显相似题（题干/选项相似）。';
                            }
                        }
                        else {
                            if (similarOnlyIds.length) {
                                startIds = similarOnlyIds.slice();
                                desc = "\u57FA\u4E8E\u4F60\u6700\u8FD1\u7684\u9519\u9898\uFF0C\u4E3A\u4F60\u5339\u914D\u4E86 ".concat(similarOnlyIds.length, " \u9053\u76F8\u4F3C\u9898\uFF0C\u53EF\u7528\u4E8E\u6613\u6DF7\u5F3A\u5316\u3002");
                            }
                            else if (wrongTotal > 0 && seedIds.length) {
                                startIds = seedIds.slice();
                                desc = "\u6682\u672A\u5339\u914D\u5230\u8DB3\u591F\u7A33\u5B9A\u7684\u76F8\u4F3C\u9898\uFF0C\u5148\u7528\u6700\u8FD1\u9519\u9898 ".concat(seedIds.length, " \u9053\u4F5C\u4E3A\u201C\u76F8\u4F3C\u9898\u79CD\u5B50\u8BAD\u7EC3\u201D\u3002");
                            }
                            else {
                                desc = wrongTotal > 0 ? '暂未匹配到足够稳定的相似题，建议先做错题加强。' : '先完成一些练习后，这里会给出相似题加强。';
                            }
                        }
                        listMeta = pairs.length
                            ? "\u5C55\u793A ".concat(pairs.length, " / ").concat(pairsCount || pairs.length, " \u7EC4")
                            : (pairsCount > 0 ? "\u5DF2\u68C0\u6D4B\u5230 ".concat(pairsCount, " \u7EC4\uFF08\u6682\u65E0\u53EF\u5C55\u793A\u8BE6\u60C5\uFF09") : '暂无相似题目');
                        this.setData({
                            reinforceSimilar: {
                                loading: false,
                                loaded: true,
                                error: '',
                                desc: desc,
                                listMeta: listMeta,
                                wrongTotal: wrongTotal,
                                similarMode: similarMode,
                                pairsCount: pairsCount,
                                seedIds: seedIds,
                                startIds: startIds,
                                pairs: pairs
                            }
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_3 = _a.sent();
                        this.setData({
                            reinforceSimilar: Object.assign({}, this.data.reinforceSimilar, {
                                loading: false,
                                loaded: true,
                                error: (e_3 && e_3.message) ? String(e_3.message) : '加载失败',
                                desc: '加载失败，请下拉刷新重试',
                                listMeta: '加载失败'
                            })
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onScopeTap: function (e) {
        var _this = this;
        var _a, _b;
        var next = normalizeScope(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.scope) || 'all');
        if (next === this.data.practiceScope)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (bankId)
            setStoredString("bank_".concat(bankId, "_scope"), next);
        this.scopeForced = '';
        this.setData({ practiceScope: next, startError: '' }, function () {
            if (_this.data.tab === 'practice') {
                _this.scheduleStartCount();
            }
        });
    },
    onTogglePracticeAdvanced: function () {
        this.setData({ practiceAdvancedOpen: !this.data.practiceAdvancedOpen });
    },
    onClearProgressTap: function () {
        var _this = this;
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        if (this.data.loading) {
            wx.showToast({ title: '加载中，请稍候', icon: 'none' });
            return;
        }
        wx.showActionSheet({
            itemList: ['清除刷题进度', '清除背题进度'],
            success: function (res) {
                var mode = res.tapIndex === 1 ? 'memo' : 'quiz';
                _this.confirmAndClearProgress(mode);
            }
        });
    },
    buildProgressKey: function (mode) {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return '';
        var qs = (0, quiz_source_1.createQuizSource)({ bankId: bankId });
        return qs.buildProgressKey(mode, {
            type: this.data.qType,
            source: this.data.practiceScope,
            tag: this.data.tag,
            shuffleQuestions: this.data.shuffleQuestions,
            shuffleOptions: this.data.shuffleOptions
        });
    },
    confirmAndClearProgress: function (mode) {
        var _this = this;
        var key = this.buildProgressKey(mode);
        if (!key)
            return;
        var scopeLabel = this.data.practiceScope === 'favorites' ? '收藏' : this.data.practiceScope === 'mistakes' ? '错题' : '全部';
        var typeLabel = this.data.qType === 'all' ? '全部题型' : String(this.data.qType || '').trim() || '全部题型';
        var tagLabel = this.data.tag && this.data.tag !== 'all' ? String(this.data.tag || '').trim() : '全部标签';
        var modeLabel = mode === 'memo' ? '背题' : '刷题';
        var shuffleQ = this.data.shuffleQuestions ? '开' : '关';
        var shuffleO = this.data.shuffleOptions ? '开' : '关';
        var bankName = String(this.data.bankName || '').trim() || "\u9898\u5E93".concat(Number(this.data.bankId || 0) || '');
        wx.showModal({
            title: '确认清除',
            content: "\u5C06\u6E05\u9664\u4EE5\u4E0B\u7EC4\u5408\u7684\u8FDB\u5EA6\uFF1A\n\u9898\u5E93\uFF1A".concat(bankName, "\n\u8303\u56F4\uFF1A").concat(scopeLabel, "\n\u9898\u578B\uFF1A").concat(typeLabel, "\n\u6807\u7B7E\uFF1A").concat(tagLabel, "\n\u6A21\u5F0F\uFF1A").concat(modeLabel, "\n\u6253\u4E71\u9898\u76EE\uFF1A").concat(shuffleQ, "  \u6253\u4E71\u9009\u9879\uFF1A").concat(shuffleO),
            confirmText: '清除',
            confirmColor: '#FF3B30',
            success: function (r) { return __awaiter(_this, void 0, void 0, function () {
                var e_4;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (!r.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '清除中...' });
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.deleteProgress(key)];
                        case 2:
                            _a.sent();
                            return [3 /*break*/, 4];
                        case 3:
                            e_4 = _a.sent();
                            console.error('清除云端进度失败:', e_4);
                            return [3 /*break*/, 4];
                        case 4:
                            try {
                                wx.removeStorageSync(key);
                            }
                            catch (e) { }
                            wx.hideLoading();
                            wx.showToast({ title: '已清除', icon: 'success' });
                            return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    onSearchInput: function (e) {
        var _a;
        this.setData({ searchKeyword: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onBankSearch: function () {
        this.doBankSearch(true);
    },
    onSearchTypeTap: function (e) {
        var _this = this;
        var _a, _b;
        var next = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) || 'all').trim() || 'all';
        var types = Array.isArray(this.data.types) ? this.data.types : [];
        var v = next === 'all' || types.includes(next) ? next : 'all';
        if (v === this.data.searchType)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (bankId)
            setStoredString("bank_".concat(bankId, "_search_type"), v);
        this.setData({ searchType: v }, function () {
            if (_this.data.searchSearched && String(_this.data.searchKeyword || '').trim()) {
                _this.doBankSearch(true);
            }
        });
    },
    doBankSearch: function (reset) {
        return __awaiter(this, void 0, void 0, function () {
            var kw, bankId, page, perPage, res, list, total, nextList, err_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        kw = String(this.data.searchKeyword || '').trim();
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!kw) {
                            this.setData({
                                searchSearched: true,
                                searchResults: [],
                                searchTotal: 0,
                                searchPage: 1,
                                searchError: ''
                            });
                            wx.showToast({ title: '请输入关键词', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (this.data.searchLoading)
                            return [2 /*return*/];
                        page = reset ? 1 : Number(this.data.searchPage || 1) || 1;
                        perPage = Number(this.data.searchPerPage || 20) || 20;
                        this.setData(__assign({ searchLoading: true, searchSearched: true, searchError: '' }, (reset ? { searchResults: [], searchTotal: 0, searchPage: 1 } : {})));
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankQuestions(bankId, {
                                keyword: kw,
                                q_type: this.data.searchType && this.data.searchType !== 'all' ? this.data.searchType : undefined,
                                page: page,
                                per_page: perPage
                            })];
                    case 2:
                        res = _a.sent();
                        list = Array.isArray(res === null || res === void 0 ? void 0 : res.questions) ? res.questions : [];
                        total = Number((res === null || res === void 0 ? void 0 : res.total) || 0) || 0;
                        nextList = reset ? list : (this.data.searchResults || []).concat(list);
                        this.setData({
                            searchResults: nextList,
                            searchTotal: total,
                            searchPage: page + 1,
                            searchLoading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _a.sent();
                        this.setData({ searchLoading: false, searchError: (err_2 && err_2.message) ? String(err_2.message) : '搜索失败' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onSearchLoadMore: function () {
        if (this.data.searchLoading)
            return;
        if ((this.data.searchResults || []).length >= (this.data.searchTotal || 0))
            return;
        this.doBankSearch(false);
    },
    onSearchClear: function () {
        this.setData({
            searchKeyword: '',
            searchSearched: false,
            searchResults: [],
            searchTotal: 0,
            searchPage: 1,
            searchError: ''
        });
    },
    onSearchResultTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        this.openQuestionDetail(id);
    },
    openQuestionDetail: function (questionId) {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, qid, reqId, q, qType, options, metaParts, err_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        qid = Number(questionId || 0);
                        if (!Number.isFinite(qid) || qid <= 0)
                            return [2 /*return*/];
                        reqId = ++this.qDetailReq;
                        this.setData({
                            qDetailOpen: true,
                            qDetailLoading: true,
                            qDetailError: '',
                            qDetailId: qid,
                            qDetailMeta: "ID\uFF1A".concat(qid),
                            qDetailContentLines: [],
                            qDetailAnswerLines: [],
                            qDetailExplanationLines: [],
                            qDetailOptions: []
                        });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankQuestionDetail(bankId, qid)];
                    case 2:
                        q = _a.sent();
                        if (reqId !== this.qDetailReq)
                            return [2 /*return*/];
                        qType = String((q === null || q === void 0 ? void 0 : q.q_type) || '').trim();
                        options = normalizeBankDetailOptions(q === null || q === void 0 ? void 0 : q.options, qType);
                        metaParts = ["ID\uFF1A".concat(qid)];
                        if (qType)
                            metaParts.push(qType);
                        if ((q === null || q === void 0 ? void 0 : q.difficulty) != null && Number.isFinite(Number(q.difficulty)))
                            metaParts.push("\u96BE\u5EA6 ".concat(Number(q.difficulty)));
                        this.setData({
                            qDetailLoading: false,
                            qDetailError: '',
                            qDetailMeta: metaParts.join(' · '),
                            qDetailContentLines: normalizeTextLines(q === null || q === void 0 ? void 0 : q.content),
                            qDetailAnswerLines: normalizeTextLines(q === null || q === void 0 ? void 0 : q.answer),
                            qDetailExplanationLines: normalizeTextLines(q === null || q === void 0 ? void 0 : q.explanation),
                            qDetailOptions: options
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_3 = _a.sent();
                        if (reqId !== this.qDetailReq)
                            return [2 /*return*/];
                        this.setData({
                            qDetailLoading: false,
                            qDetailError: (err_3 && err_3.message) ? String(err_3.message) : '加载失败'
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onQDetailClose: function () {
        this.setData({ qDetailOpen: false });
    },
    onQDetailSheetTap: function () {
        // 阻止冒泡：点击面板内部不关闭
    },
    onQDetailGoQuiz: function () {
        var id = Number(this.data.qDetailId || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        this.onQDetailClose();
        wx.navigateTo({ url: "/pages/quiz/quiz?bank_id=".concat(encodeURIComponent(String(bankId)), "&mode=quiz&source=all&start_id=").concat(id) });
    },
    onTypeTap: function (e) {
        var _a, _b;
        var type = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) || 'all').trim();
        var types = this.data.types || [];
        var next = type === 'all' || types.includes(type) ? type : 'all';
        if (next === this.data.qType)
            return;
        var keyType = "bank_".concat(Number(this.data.bankId || 0), "_type");
        this.setData({ qType: next });
        setStoredString(keyType, next);
        this.syncShuffleOptionsDisabled();
        if (shouldCountForTab(this.data.tab)) {
            this.scheduleStartCount();
        }
    },
    onTagTap: function (e) {
        var _a, _b;
        var next = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) || 'all').trim();
        var tags = this.data.tags || [];
        var ok = next === 'all' || tags.some(function (t) { return t.name === next; });
        var val = ok ? next : 'all';
        if (val === this.data.tag)
            return;
        var keyTag = "bank_".concat(Number(this.data.bankId || 0), "_tag");
        this.setData({ tag: val });
        setStoredString(keyTag, val);
        if (shouldCountForTab(this.data.tab)) {
            this.scheduleStartCount();
        }
    },
    onTagDeleteTap: function (e) {
        var _this = this;
        var _a, _b;
        var name = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) || '').trim();
        if (!name || name.toLowerCase() === 'all')
            return;
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        wx.showModal({
            title: '删除标签',
            content: "\u5220\u9664\u6807\u7B7E\u300C".concat(name, "\u300D\uFF1F\n\n\u4EC5\u5220\u9664\uFF1A\u5F53\u524D\u7528\u6237 \u00B7 \u5F53\u524D\u9898\u5E93\u4E0B\u7684\u6807\u7B7E\uFF0C\u5E76\u79FB\u9664\u8BE5\u6807\u7B7E\u5728\u672C\u9898\u5E93\u4E0B\u6240\u6709\u9898\u76EE\u4E0A\u7684\u7ED1\u5B9A\u3002"),
            confirmText: '删除',
            confirmColor: '#FF3B30',
            success: function (r) { return __awaiter(_this, void 0, void 0, function () {
                var res, tagsRaw, tags, prevTag, nextTag, keyTag, err_4;
                var _this = this;
                var _a;
                return __generator(this, function (_b) {
                    switch (_b.label) {
                        case 0:
                            if (!r.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '删除中...' });
                            _b.label = 1;
                        case 1:
                            _b.trys.push([1, 3, 4, 5]);
                            return [4 /*yield*/, api_1.api.deleteBankTag(bankId, name)];
                        case 2:
                            res = _b.sent();
                            tagsRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.tags)
                                ? res.tags
                                : Array.isArray((_a = res === null || res === void 0 ? void 0 : res.data) === null || _a === void 0 ? void 0 : _a.tags)
                                    ? res.data.tags
                                    : [];
                            tags = (tagsRaw || [])
                                .map(function (t) { return ({ name: String((t === null || t === void 0 ? void 0 : t.name) || '').trim(), count: t === null || t === void 0 ? void 0 : t.count }); })
                                .filter(function (t) { return t.name; });
                            prevTag = String(this.data.tag || 'all').trim() || 'all';
                            nextTag = prevTag === name ? 'all' : prevTag;
                            keyTag = "bank_".concat(bankId, "_tag");
                            if (nextTag !== prevTag)
                                setStoredString(keyTag, nextTag);
                            this.setData({ tags: tags, tag: nextTag }, function () {
                                if (shouldCountForTab(_this.data.tab)) {
                                    _this.scheduleStartCount();
                                }
                            });
                            wx.showToast({ title: '已删除', icon: 'success' });
                            return [3 /*break*/, 5];
                        case 3:
                            err_4 = _b.sent();
                            wx.showToast({ title: (err_4 && err_4.message) ? String(err_4.message) : '删除失败', icon: 'none' });
                            return [3 /*break*/, 5];
                        case 4:
                            try {
                                wx.hideLoading();
                            }
                            catch (e) { }
                            return [7 /*endfinally*/];
                        case 5: return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    syncShuffleOptionsDisabled: function () {
        var disabled = this.data.qType !== 'all' && !OPTION_TYPES.has(String(this.data.qType || ''));
        if (disabled !== this.data.shuffleOptionsDisabled) {
            this.setData({ shuffleOptionsDisabled: disabled });
        }
        if (disabled && this.data.shuffleOptions) {
            this.setData({ shuffleOptions: false });
            setStoredBool(KEY_SHUFFLE_O, false);
        }
    },
    onToggleShuffleQuestions: function () {
        var next = !this.data.shuffleQuestions;
        this.setData({ shuffleQuestions: next });
        setStoredBool(KEY_SHUFFLE_Q, next);
        if (shouldCountForTab(this.data.tab)) {
            this.scheduleStartCount();
        }
    },
    onToggleShuffleOptions: function () {
        if (this.data.shuffleOptionsDisabled)
            return;
        var next = !this.data.shuffleOptions;
        this.setData({ shuffleOptions: next });
        setStoredBool(KEY_SHUFFLE_O, next);
        if (shouldCountForTab(this.data.tab)) {
            this.scheduleStartCount();
        }
    },
    scheduleStartCount: function () {
        var _this = this;
        if (!shouldCountForTab(this.data.tab))
            return;
        if (this.startCountTimer) {
            clearTimeout(this.startCountTimer);
            this.startCountTimer = null;
        }
        this.setData({ startCountText: '…', startDisabled: true, startError: '' });
        this.startCountTimer = setTimeout(function () { return _this.loadStartCount(); }, 260);
    },
    loadStartCount: function () {
        return __awaiter(this, void 0, void 0, function () {
            var reqId, bankId, params, res, data, count, e_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        reqId = ++this.startCountReq;
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        params = { source: this.data.practiceScope || 'all' };
                        if (this.data.qType && this.data.qType !== 'all')
                            params.q_type = this.data.qType;
                        if (this.data.tag && this.data.tag !== 'all')
                            params.tag = this.data.tag;
                        return [4 /*yield*/, api_1.api.getBankUserCounts(bankId, params)];
                    case 2:
                        res = _a.sent();
                        if (reqId !== this.startCountReq)
                            return [2 /*return*/];
                        data = (res === null || res === void 0 ? void 0 : res.data) || res || {};
                        count = Number((data === null || data === void 0 ? void 0 : data.total) || 0) || 0;
                        this.setData({
                            startCount: count,
                            startCountText: String(count),
                            startDisabled: count <= 0,
                            startError: ''
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_5 = _a.sent();
                        if (reqId !== this.startCountReq)
                            return [2 /*return*/];
                        this.setData({
                            startCount: 0,
                            startCountText: '0',
                            startDisabled: true,
                            startError: (e_5 && e_5.message) ? String(e_5.message) : '获取题量失败'
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    buildQuizUrl: function (mode) {
        var bankId = Number(this.data.bankId || 0);
        var params = [];
        params.push("bank_id=".concat(bankId));
        params.push("mode=".concat(mode));
        params.push("source=".concat(encodeURIComponent(String(this.data.practiceScope || 'all'))));
        if (this.data.qType && this.data.qType !== 'all')
            params.push("type=".concat(encodeURIComponent(String(this.data.qType))));
        if (this.data.tag && this.data.tag !== 'all')
            params.push("tag=".concat(encodeURIComponent(String(this.data.tag))));
        if (this.data.shuffleQuestions)
            params.push('shuffle_questions=1');
        if (this.data.shuffleOptions && !this.data.shuffleOptionsDisabled)
            params.push('shuffle_options=1');
        return "/pages/quiz/quiz?".concat(params.join('&'));
    },
    onStartQuiz: function () {
        if (this.data.startDisabled)
            return;
        wx.navigateTo({ url: this.buildQuizUrl('quiz') });
    },
    onStartMemo: function () {
        if (this.data.startDisabled)
            return;
        wx.navigateTo({ url: this.buildQuizUrl('memo') });
    },
    onQuickExam: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, typesList, duration, total, typesCfg, n, base_1, rem_1, name, detail, ok, res, examId, err_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        typesList = Array.isArray(this.data.types) ? this.data.types.filter(function (t) { return !!t; }) : [];
                        if (!typesList.length) {
                            wx.showToast({ title: '暂无可用题型', icon: 'none' });
                            return [2 /*return*/];
                        }
                        duration = 60;
                        total = 30;
                        typesCfg = {};
                        if (this.data.qType && this.data.qType !== 'all') {
                            typesCfg[String(this.data.qType)] = total;
                        }
                        else {
                            n = Math.max(1, typesList.length);
                            base_1 = Math.floor(total / n);
                            rem_1 = total % n;
                            typesList.forEach(function (t) {
                                var v = base_1 + (rem_1 > 0 ? 1 : 0);
                                if (rem_1 > 0)
                                    rem_1 -= 1;
                                if (v > 0)
                                    typesCfg[String(t)] = v;
                            });
                        }
                        name = String(this.data.bankName || '').trim() || "\u9898\u5E93#".concat(bankId);
                        detail = Object.keys(typesCfg).map(function (k) { return "".concat(k, ":").concat(typesCfg[k]); }).join('，');
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '创建并开始考试',
                                    content: "\u9898\u5E93\uFF1A".concat(name, "\n\u65F6\u957F\uFF1A").concat(duration, "\u5206\u949F\n\u9898\u91CF\uFF1A").concat(total, "\uFF08").concat(detail, "\uFF09"),
                                    confirmText: '开始',
                                    cancelText: '取消',
                                    success: function (res) { return resolve(!!res.confirm); },
                                    fail: function () { return resolve(false); }
                                });
                            })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        wx.showLoading({ title: '创建中…', mask: true });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.createExam({
                                source: 'user_bank',
                                subject: name,
                                bank_id: bankId,
                                duration: duration,
                                types: typesCfg,
                                scores: {}
                            })];
                    case 3:
                        res = _a.sent();
                        examId = Number((res === null || res === void 0 ? void 0 : res.exam_id) || (res === null || res === void 0 ? void 0 : res.id) || 0);
                        if (!Number.isFinite(examId) || examId <= 0) {
                            wx.showToast({ title: '创建考试失败', icon: 'none' });
                            return [2 /*return*/];
                        }
                        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                        return [3 /*break*/, 6];
                    case 4:
                        err_5 = _a.sent();
                        wx.showToast({ title: (err_5 && err_5.message) ? String(err_5.message) : '创建失败', icon: 'none' });
                        return [3 /*break*/, 6];
                    case 5:
                        wx.hideLoading();
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onToggleExamBuilder: function () {
        this.setData({ examBuilderOpen: !this.data.examBuilderOpen });
    },
    onOpenExamSetup: function () {
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        wx.navigateTo({ url: "/pages/bank-exam-setup/bank-exam-setup?bank_id=".concat(bankId) });
    },
    // ===== 统计详情 =====
    statsSourceForSubTab: function (subtab) {
        var s = String(subtab || '').trim().toLowerCase();
        if (s === 'mistakes')
            return 'mistakes';
        if (s === 'favorites')
            return 'favorites';
        return 'all';
    },
    onStatsSubTabTap: function (e) {
        var _this = this;
        var _a, _b, _c;
        var raw = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.subtab) || ((_c = (_b = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _b === void 0 ? void 0 : _b.dataset) === null || _c === void 0 ? void 0 : _c.subtab) || '').trim().toLowerCase();
        var next = (raw === 'mistakes' || raw === 'favorites') ? raw : 'global';
        if (next === this.data.statsSubTab)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (bankId)
            setStoredString("bank_".concat(bankId, "_stats_subtab"), next);
        this.setData({ statsSubTab: next, statsLoadedDays: 0, statsLoadedSubTab: next }, function () {
            if (_this.data.tab === 'stats') {
                _this.ensureStatsDetail(true);
            }
        });
    },
    onStatsDaysTap: function (e) {
        var _this = this;
        var _a, _b, _c;
        var days = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.days) || ((_c = (_b = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _b === void 0 ? void 0 : _b.dataset) === null || _c === void 0 ? void 0 : _c.days) || 14);
        if (![7, 14, 30, 90].includes(days))
            return;
        if (days === this.data.statsDays)
            return;
        this.setData({ statsDays: days, statsLoadedDays: 0 }, function () {
            if (_this.data.tab === 'stats') {
                _this.ensureStatsDetail(true);
            }
        });
    },
    onStatsQuickStart: function (e) {
        var _a, _b, _c;
        var raw = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.subtab) || ((_c = (_b = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _b === void 0 ? void 0 : _b.dataset) === null || _c === void 0 ? void 0 : _c.subtab) || '').trim().toLowerCase();
        var subtab = raw === 'mistakes' || raw === 'favorites' ? raw : '';
        if (!subtab)
            return;
        var bankId = Number(this.data.bankId || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        wx.navigateTo({ url: "/pages/quiz/quiz?bank_id=".concat(encodeURIComponent(String(bankId)), "&mode=quiz&source=").concat(encodeURIComponent(subtab)) });
    },
    ensureStatsDetail: function (force) {
        if (force === void 0) { force = false; }
        if (this.data.statsLoading)
            return;
        var days = Number(this.data.statsDays || 14) || 14;
        var subtab = this.data.statsSubTab || 'global';
        if (!force && this.data.statsLoadedDays === days && this.data.statsLoadedSubTab === subtab)
            return;
        this.loadStatsDetail(days, subtab);
    },
    formatDateTime: function (raw) {
        var s = String(raw || '').trim();
        if (!s)
            return '—';
        try {
            var iso = s.includes('T') ? s : s.replace(' ', 'T');
            var d = new Date(iso);
            if (isNaN(d.getTime()))
                return s;
            var y = d.getFullYear();
            var m = String(d.getMonth() + 1).padStart(2, '0');
            var day = String(d.getDate()).padStart(2, '0');
            var hh = String(d.getHours()).padStart(2, '0');
            var mm = String(d.getMinutes()).padStart(2, '0');
            return "".concat(y, "-").concat(m, "-").concat(day, " ").concat(hh, ":").concat(mm);
        }
        catch (_a) {
            return s;
        }
    },
    buildStatsView: function (data) {
        var total = Number((data === null || data === void 0 ? void 0 : data.total_count) || 0) || 0;
        var answered = Number((data === null || data === void 0 ? void 0 : data.answered) || 0) || 0;
        var correct = Number((data === null || data === void 0 ? void 0 : data.correct) || 0) || 0;
        var wrong = Number((data === null || data === void 0 ? void 0 : data.wrong) || 0) || 0;
        var favorites = Number((data === null || data === void 0 ? void 0 : data.favorites) || 0) || 0;
        var mistakes = Number((data === null || data === void 0 ? void 0 : data.mistakes) || 0) || 0;
        var mistakeTimes = Number((data === null || data === void 0 ? void 0 : data.mistakes_times) || 0) || 0;
        var accuracy = Number((data === null || data === void 0 ? void 0 : data.accuracy) || 0) || 0;
        var completion = Number((data === null || data === void 0 ? void 0 : data.completion) || 0) || 0;
        var streakDays = Number((data === null || data === void 0 ? void 0 : data.streak_days) || 0) || 0;
        var lastText = this.formatDateTime(data === null || data === void 0 ? void 0 : data.last_activity);
        var overview = {
            total: total,
            answered: answered,
            correct: correct,
            wrong: wrong,
            favorites: favorites,
            mistakes: mistakes,
            mistakeTimes: mistakeTimes,
            accuracy: accuracy,
            completion: completion,
            accuracyText: "".concat(accuracy.toFixed(1), "%"),
            completionText: "".concat(completion.toFixed(1), "%"),
            streakDays: streakDays,
            lastText: lastText
        };
        var rawTrend = Array.isArray(data === null || data === void 0 ? void 0 : data.trend) ? data.trend : [];
        var maxAnswered = rawTrend.reduce(function (m, it) { return Math.max(m, Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0); }, 0) || 0;
        var trend = rawTrend.map(function (it) {
            var day = String((it === null || it === void 0 ? void 0 : it.day) || '');
            var label = day ? day.slice(5) : '';
            var a = Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0;
            var c = Number((it === null || it === void 0 ? void 0 : it.correct) || 0) || 0;
            var w = Number((it === null || it === void 0 ? void 0 : it.wrong) || 0) || Math.max(0, a - c);
            var answeredPct = maxAnswered > 0 ? clampPct((a / maxAnswered) * 100) : 0;
            var correctPctInAnswered = a > 0 ? clampPct((Math.min(a, c) / a) * 100) : 0;
            return { day: day, label: label, answered: a, correct: Math.min(a, c), wrong: w, answeredPct: answeredPct, correctPctInAnswered: correctPctInAnswered };
        });
        var rawByType = Array.isArray(data === null || data === void 0 ? void 0 : data.by_type) ? data.by_type : [];
        var byType = rawByType.map(function (it) {
            var q_type = String((it === null || it === void 0 ? void 0 : it.q_type) || '未知');
            var t = Number((it === null || it === void 0 ? void 0 : it.total) || 0) || 0;
            var a = Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0;
            var c = Number((it === null || it === void 0 ? void 0 : it.correct) || 0) || 0;
            var w = Number((it === null || it === void 0 ? void 0 : it.wrong) || 0) || Math.max(0, a - c);
            var fav = Number((it === null || it === void 0 ? void 0 : it.favorites) || 0) || 0;
            var mis = Number((it === null || it === void 0 ? void 0 : it.mistakes) || 0) || 0;
            var acc = Number((it === null || it === void 0 ? void 0 : it.accuracy) || 0) || 0;
            var comp = Number((it === null || it === void 0 ? void 0 : it.completion) || 0) || 0;
            var completionWidth = Math.max(0, Math.min(100, comp));
            return {
                q_type: q_type,
                total: t,
                answered: a,
                correct: c,
                wrong: w,
                favorites: fav,
                mistakes: mis,
                accuracyText: "".concat(acc.toFixed(1), "%"),
                completionText: "".concat(comp.toFixed(1), "%"),
                completionWidth: completionWidth,
                metaText: "\u5DF2\u505A ".concat(a, "/").concat(t, " \u00B7 \u6B63\u786E\u7387 ").concat(acc.toFixed(1), "% \u00B7 \u8986\u76D6\u7387 ").concat(comp.toFixed(1), "% \u00B7 \u6536\u85CF ").concat(fav, " \u00B7 \u9519\u9898 ").concat(mis)
            };
        });
        var rawByDiff = Array.isArray(data === null || data === void 0 ? void 0 : data.by_difficulty) ? data.by_difficulty : [];
        var byDifficulty = rawByDiff.map(function (it) {
            var label = String((it === null || it === void 0 ? void 0 : it.label) || (it === null || it === void 0 ? void 0 : it.difficulty) || '');
            var t = Number((it === null || it === void 0 ? void 0 : it.total) || 0) || 0;
            var a = Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0;
            var c = Number((it === null || it === void 0 ? void 0 : it.correct) || 0) || 0;
            var w = Number((it === null || it === void 0 ? void 0 : it.wrong) || 0) || Math.max(0, a - c);
            var acc = Number((it === null || it === void 0 ? void 0 : it.accuracy) || 0) || 0;
            var comp = Number((it === null || it === void 0 ? void 0 : it.completion) || 0) || 0;
            var completionWidth = Math.max(0, Math.min(100, comp));
            return {
                label: label,
                total: t,
                answered: a,
                correct: c,
                wrong: w,
                accuracyText: "".concat(acc.toFixed(1), "%"),
                completionText: "".concat(comp.toFixed(1), "%"),
                completionWidth: completionWidth
            };
        });
        var advice = Array.isArray(data === null || data === void 0 ? void 0 : data.advice) ? data.advice : [];
        return { overview: overview, trend: trend, byType: byType, byDifficulty: byDifficulty, advice: advice };
    },
    buildHeatCells: function (trend) {
        var slice = trend.slice(-28);
        var maxAnswered = slice.reduce(function (m, it) { return Math.max(m, Number((it === null || it === void 0 ? void 0 : it.answered) || 0) || 0); }, 0) || 0;
        var cells = slice.map(function (it) {
            if (!maxAnswered)
                return { level: 0 };
            var pct = (it.answered || 0) / maxAnswered;
            var level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
            return { level: level };
        });
        var pad = 28 - cells.length;
        if (pad > 0) {
            return Array.from({ length: pad }, function () { return ({ level: 0 }); }).concat(cells);
        }
        return cells;
    },
    loadStatsDetail: function (days, subtab) {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, reqId, source, statsPromise, questionsPromise, favTrendPromise, settle, _a, statsRes, qRes, favRes, data, qPayload, statsQuestions, favoritesTrend, view, ringAccuracy, ringCompletion, heatCells, displayTypes, ringActive, activeDaysRate, ringRepeat, repeatRateText, mistakeRateText, favMistakeRateText, repeatRate, mistakeRate, activeDays, favMistakeRate, activeDays, err_6;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        reqId = ++this.statsReq;
                        this.setData({ statsLoading: true, statsError: '', statsQuestions: [], favoritesTrend: {} });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        source = this.statsSourceForSubTab(subtab || 'global');
                        statsPromise = source === 'all'
                            ? api_1.api.getBankStatsDetail(bankId, days)
                            : api_1.api.getBankStatsDetail(bankId, { days: days, source: source });
                        questionsPromise = Promise.resolve(null);
                        favTrendPromise = Promise.resolve(null);
                        if (subtab === 'mistakes') {
                            questionsPromise = api_1.api.getBankQuestions(bankId, { source: 'mistakes', page: 1, per_page: 300 });
                        }
                        else if (subtab === 'favorites') {
                            questionsPromise = api_1.api.getBankQuestions(bankId, { source: 'favorites', page: 1, per_page: 200 });
                            favTrendPromise = api_1.api.getBankFavoritesTrend(bankId, days);
                        }
                        settle = function (p) {
                            return p.then(function (value) { return ({ ok: true, value: value }); }, function (reason) { return ({ ok: false, reason: reason }); });
                        };
                        return [4 /*yield*/, Promise.all([
                                settle(statsPromise),
                                settle(questionsPromise),
                                settle(favTrendPromise)
                            ])];
                    case 2:
                        _a = _b.sent(), statsRes = _a[0], qRes = _a[1], favRes = _a[2];
                        if (reqId !== this.statsReq)
                            return [2 /*return*/];
                        if (!statsRes.ok)
                            throw statsRes.reason;
                        data = statsRes.value;
                        qPayload = qRes.ok ? qRes.value : null;
                        statsQuestions = Array.isArray(qPayload === null || qPayload === void 0 ? void 0 : qPayload.questions) ? qPayload.questions : [];
                        favoritesTrend = favRes.ok ? (favRes.value || {}) : {};
                        view = this.buildStatsView(data || {});
                        ringAccuracy = clampPct(view.overview.accuracy);
                        ringCompletion = clampPct(view.overview.completion);
                        heatCells = this.buildHeatCells(view.trend);
                        displayTypes = view.byType || [];
                        ringActive = 0;
                        activeDaysRate = 0;
                        ringRepeat = 0;
                        repeatRateText = '0%';
                        mistakeRateText = '0%';
                        favMistakeRateText = '0%';
                        if (subtab === 'mistakes') {
                            repeatRate = view.overview.total > 0 ? clampPct((view.overview.mistakeTimes / view.overview.total) * 100) : 0;
                            mistakeRate = view.overview.answered > 0 ? clampPct((view.overview.wrong / view.overview.answered) * 100) : 0;
                            ringRepeat = repeatRate;
                            repeatRateText = "".concat(repeatRate.toFixed(0), "%");
                            mistakeRateText = "".concat(mistakeRate.toFixed(0), "%");
                            displayTypes = (view.byType || [])
                                .map(function (t) {
                                return Object.assign({}, t, {
                                    metaText: "\u9519\u9898 ".concat(t.mistakes, " \u00B7 \u5DF2\u505A ").concat(t.answered, "/").concat(t.total, " \u00B7 \u6B63\u786E\u7387 ").concat(t.accuracyText, " \u00B7 \u8986\u76D6\u7387 ").concat(t.completionText)
                                });
                            })
                                .sort(function (a, b) { return b.wrong - a.wrong; });
                        }
                        else if (subtab === 'favorites') {
                            activeDays = view.trend.filter(function (it) { return it.answered > 0; }).length;
                            activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
                            ringActive = clampPct(activeDaysRate);
                            favMistakeRate = view.overview.total > 0 ? clampPct((view.overview.mistakes / view.overview.total) * 100) : 0;
                            favMistakeRateText = "".concat(favMistakeRate.toFixed(0), "%");
                            displayTypes = (view.byType || [])
                                .map(function (t) {
                                return Object.assign({}, t, {
                                    metaText: "\u6536\u85CF ".concat(t.favorites, " \u00B7 \u5DF2\u505A ").concat(t.answered, "/").concat(t.total, " \u00B7 \u6B63\u786E\u7387 ").concat(t.accuracyText, " \u00B7 \u8986\u76D6\u7387 ").concat(t.completionText)
                                });
                            })
                                .sort(function (a, b) { return b.favorites - a.favorites; });
                        }
                        else {
                            activeDays = view.trend.filter(function (it) { return it.answered > 0; }).length;
                            activeDaysRate = view.trend.length ? Math.round((activeDays / view.trend.length) * 100) : 0;
                            ringActive = clampPct(activeDaysRate);
                            displayTypes = view.byType || [];
                        }
                        this.setData({
                            statsLoadedDays: days,
                            statsLoadedSubTab: subtab,
                            statsLoading: false,
                            statsOverview: view.overview,
                            statsTrend: view.trend,
                            statsByType: view.byType,
                            statsByDifficulty: view.byDifficulty,
                            statsAdvice: view.advice,
                            statsHasDifficulty: view.byDifficulty.length > 0,
                            statsQuestions: statsQuestions,
                            favoritesTrend: favoritesTrend,
                            ringAccuracy: ringAccuracy,
                            ringCompletion: ringCompletion,
                            ringActive: ringActive,
                            activeDaysRate: activeDaysRate,
                            ringRepeat: ringRepeat,
                            repeatRateText: repeatRateText,
                            mistakeRateText: mistakeRateText,
                            favMistakeRateText: favMistakeRateText,
                            heatCells: heatCells,
                            displayTypes: displayTypes
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_6 = _b.sent();
                        if (reqId !== this.statsReq)
                            return [2 /*return*/];
                        this.setData({
                            statsLoading: false,
                            statsError: (err_6 && err_6.message) ? String(err_6.message) : '统计加载失败',
                            statsQuestions: [],
                            favoritesTrend: {}
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onStatsQuestionTap: function (e) {
        var _a, _b, _c;
        var id = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.id) || ((_c = (_b = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _b === void 0 ? void 0 : _b.dataset) === null || _c === void 0 ? void 0 : _c.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        this.openQuestionDetail(id);
    },
    onCopyBankName: function () {
        var name = String(this.data.bankName || '').trim();
        if (!name)
            return;
        wx.setClipboardData({ data: name });
    },
    // ==================== 分享管理（仅创建者） ====================
    formatDate: function (dateStr) {
        try {
            var date = new Date(dateStr);
            var month = String(date.getMonth() + 1).padStart(2, '0');
            var day = String(date.getDate()).padStart(2, '0');
            return "".concat(month, "-").concat(day);
        }
        catch (_a) {
            return '';
        }
    },
    getShareBaseUrl: function () {
        try {
            var apiUrl = String(config_1.config.getApiUrl ? config_1.config.getApiUrl() : config_1.config.apiBaseUrl || '').trim();
            return apiUrl.replace(/\/api\/?$/i, '');
        }
        catch (_a) {
            return '';
        }
    },
    buildShareLink: function (token) {
        var base = this.getShareBaseUrl();
        if (!base)
            return token;
        return "".concat(base, "/bank/join?token=").concat(encodeURIComponent(String(token || '')));
    },
    isExpiredIso: function (expiresAt) {
        var s = String(expiresAt || '').trim();
        if (!s)
            return false;
        try {
            var d = new Date(s);
            var ts = d.getTime();
            if (!Number.isFinite(ts))
                return true;
            return ts < Date.now();
        }
        catch (e) {
            return true;
        }
    },
    pickShareTokenFromShares: function (shares) {
        var list = Array.isArray(shares) ? shares : [];
        for (var i = 0; i < list.length; i++) {
            var s = list[i];
            if (!s)
                continue;
            if (!s.is_active)
                continue;
            var token = s.share_token ? String(s.share_token).trim() : '';
            if (!token)
                continue;
            if (s.expires_at && this.isExpiredIso(s.expires_at))
                continue;
            return token;
        }
        return '';
    },
    ensureWechatShareToken: function (force) {
        if (force === void 0) { force = false; }
        return __awaiter(this, void 0, void 0, function () {
            var bankId, token, payload, created, err_7;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!this.data.canManageShare)
                            return [2 /*return*/];
                        if (!force && this.data.wechatShareReady && String(this.data.wechatShareToken || '').trim())
                            return [2 /*return*/];
                        if (this.data.wechatSharePreparing)
                            return [2 /*return*/];
                        this.setData({ wechatSharePreparing: true, wechatShareReady: false });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        return [4 /*yield*/, this.loadShares()];
                    case 2:
                        _a.sent();
                        token = String(this.data.wechatShareToken || '').trim();
                        if (!!token) return [3 /*break*/, 5];
                        payload = {
                            type: 'link',
                            permission: this.data.newShare.permission,
                            expires_in: this.data.newShare.expiresIn ? this.data.newShare.expiresIn : null
                        };
                        if (this.data.newShare.maxUses)
                            payload.max_uses = this.data.newShare.maxUses;
                        return [4 /*yield*/, api_1.api.createBankShare(bankId, payload)];
                    case 3:
                        created = _a.sent();
                        token = String((created === null || created === void 0 ? void 0 : created.share_token) || '').trim() || this.extractTokenFromShareLink(created === null || created === void 0 ? void 0 : created.share_link);
                        if (!token) return [3 /*break*/, 5];
                        this.setData({ wechatShareToken: token, wechatShareReady: true });
                        return [4 /*yield*/, this.loadShares()];
                    case 4:
                        _a.sent();
                        this.loadUsageStats();
                        _a.label = 5;
                    case 5: return [3 /*break*/, 8];
                    case 6:
                        err_7 = _a.sent();
                        return [3 /*break*/, 8];
                    case 7:
                        this.setData({ wechatSharePreparing: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    loadShares: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, res, data, raw, base_2, shares, err_7, msg;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!this.data.canManageShare)
                            return [2 /*return*/];
                        if (this.data.shareLoading)
                            return [2 /*return*/];
                        this.setData({ shareLoading: true, shareError: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankShares(bankId)];
                    case 2:
                        res = _a.sent();
                        data = (res === null || res === void 0 ? void 0 : res.data) || res || {};
                        raw = Array.isArray(data === null || data === void 0 ? void 0 : data.shares) ? data.shares : [];
                        base_2 = this.getShareBaseUrl();
                        shares = raw.map(function (s) {
                            var token = (s === null || s === void 0 ? void 0 : s.share_token) ? String(s.share_token) : '';
                            var share_link = token ? (base_2 ? "".concat(base_2, "/bank/join?token=").concat(encodeURIComponent(token)) : token) : '';
                            return Object.assign({}, s, {
                                expires_at_display: (s === null || s === void 0 ? void 0 : s.expires_at) ? _this.formatDate(String(s.expires_at)) : '',
                                share_link: share_link
                            });
                        });
                        var picked = this.pickShareTokenFromShares(shares);
                        this.setData({
                            shares: shares,
                            shareLoading: false,
                            wechatShareToken: picked,
                            wechatShareReady: !!picked
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_7 = _a.sent();
                        msg = (err_7 && err_7.message) ? String(err_7.message) : '无权查看分享（仅创建者可管理）';
                        this.setData({
                            shares: [],
                            shareLoading: false,
                            shareError: msg,
                            wechatShareToken: '',
                            wechatShareReady: false
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    loadUsageStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, res, data, stats, err_8;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!this.data.canManageShare)
                            return [2 /*return*/];
                        if (this.data.usageStatsLoading)
                            return [2 /*return*/];
                        this.setData({ usageStatsLoading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankUsageStats(bankId)];
                    case 2:
                        res = _a.sent();
                        data = (res === null || res === void 0 ? void 0 : res.data) || res || {};
                        stats = {
                            bank_id: bankId,
                            is_public: !!data.is_public,
                            owner_id: Number(data.owner_id || 0),
                            owner_count: Number(data.owner_count || 1),
                            shared_users: Number(data.shared_users || 0),
                            public_users: Number(data.public_users || 0),
                            total_users: Number(data.total_users || 0),
                            total_users_excluding_owner: Number(data.total_users_excluding_owner || 0)
                        };
                        this.setData({ usageStats: stats, usageStatsLoaded: true, usageStatsLoading: false });
                        return [3 /*break*/, 4];
                    case 3:
                        err_8 = _a.sent();
                        this.setData({ usageStatsLoaded: false, usageStatsLoading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    extractTokenFromShareLink: function (input) {
        var s = String(input || '').trim();
        if (!s)
            return '';
        if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?'))
            return s;
        var m = s.match(/[?&]token=([^&#]+)/i);
        if (m && m[1]) {
            try {
                return decodeURIComponent(m[1]);
            }
            catch (e) {
                return m[1];
            }
        }
        return '';
    },
    onWechatShareCard: function () {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, shareAppMessage, token, shares, _i, shares_1, s, payload, created, updated, _a, updated_1, it, name, title, path, link, err_9;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        if (!this.data.canManageShare) {
                            wx.showToast({ title: '无权操作', icon: 'none' });
                            return [2 /*return*/];
                        }
                        shareAppMessage = wx.shareAppMessage;
                        wx.showLoading({ title: '准备分享...' });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 8, 9, 10]);
                        return [4 /*yield*/, this.loadShares()];
                    case 2:
                        _b.sent();
                        token = '';
                        shares = Array.isArray(this.data.shares) ? this.data.shares : [];
                        for (_i = 0, shares_1 = shares; _i < shares_1.length; _i++) {
                            s = shares_1[_i];
                            if (!s)
                                continue;
                            if (!s.is_active)
                                continue;
                            if (!s.share_token)
                                continue;
                            token = String(s.share_token).trim();
                            break;
                        }
                        if (!!token) return [3 /*break*/, 6];
                        payload = {
                            type: 'link',
                            permission: this.data.newShare.permission,
                            expires_in: this.data.newShare.expiresIn ? this.data.newShare.expiresIn : null
                        };
                        if (this.data.newShare.maxUses)
                            payload.max_uses = this.data.newShare.maxUses;
                        return [4 /*yield*/, api_1.api.createBankShare(bankId, payload)];
                    case 3:
                        created = _b.sent();
                        token = String((created && created.share_token) || '').trim() || this.extractTokenFromShareLink(created && created.share_link);
                        if (!!token) return [3 /*break*/, 6];
                        return [4 /*yield*/, this.loadShares()];
                    case 4:
                        _b.sent();
                        updated = Array.isArray(this.data.shares) ? this.data.shares : [];
                        for (_a = 0, updated_1 = updated; _a < updated_1.length; _a++) {
                            it = updated_1[_a];
                            if (!it)
                                continue;
                            if (!it.is_active)
                                continue;
                            if (!it.share_token)
                                continue;
                            token = String(it.share_token).trim();
                            break;
                        }
                        _b.label = 5;
                    case 5: return [3 /*break*/, 6];
                    case 6:
                        if (!token)
                            throw new Error('生成分享链接失败');
                        name = String(this.data.bankName || '').trim();
                        title = name ? "邀请你加入题库：".concat(name) : '邀请你加入题库';
                        path = "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(token));
                        if (typeof shareAppMessage === 'function') {
                            shareAppMessage({ title: title, path: path });
                        }
                        else {
                            link = this.buildShareLink(token);
                            if (link)
                                wx.setClipboardData({ data: link });
                            wx.showModal({
                                title: '已复制分享链接',
                                content: '当前微信版本暂不支持直接唤起名片分享，可把链接发送给好友。',
                                showCancel: false
                            });
                        }
                        return [3 /*break*/, 10];
                    case 8:
                        err_9 = _b.sent();
                        wx.showToast({ title: (err_9 && err_9.message) ? String(err_9.message) : '分享失败', icon: 'none' });
                        return [3 /*break*/, 10];
                    case 9:
                        wx.hideLoading();
                        return [7 /*endfinally*/];
                    case 10: return [2 /*return*/];
                }
            });
        });
    },
    onSharePermissionTap: function (e) {
        var _a, _b;
        var permission = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.permission;
        if (permission !== 'read' && permission !== 'copy')
            return;
        this.setData({ 'newShare.permission': permission });
    },
    onShareExpiresTap: function (e) {
        var _a, _b;
        var expiresIn = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.expires) || 0);
        var val = Number.isFinite(expiresIn) ? Math.max(0, Math.min(365, expiresIn)) : 0;
        this.setData({ 'newShare.expiresIn': val });
    },
    onShareMaxTap: function (e) {
        var _a, _b;
        var maxUses = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.max) || 0);
        var val = Number.isFinite(maxUses) ? Math.max(0, Math.min(100000, Math.floor(maxUses))) : 0;
        this.setData({ 'newShare.maxUses': val });
    },
    onCreateShare: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var bankId, type, shareType, payload, res, data, code, link, copied, err_8;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        bankId = Number(this.data.bankId || 0);
                        if (!Number.isFinite(bankId) || bankId <= 0)
                            return [2 /*return*/];
                        type = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) || 'code');
                        shareType = type === 'link' ? 'link' : 'code';
                        wx.showLoading({ title: '创建中...' });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 4, 5, 6]);
                        payload = {
                            type: shareType,
                            permission: this.data.newShare.permission,
                            expires_in: this.data.newShare.expiresIn ? this.data.newShare.expiresIn : null
                        };
                        if (this.data.newShare.maxUses)
                            payload.max_uses = this.data.newShare.maxUses;
                        return [4 /*yield*/, api_1.api.createBankShare(bankId, payload)];
                    case 2:
                        res = _c.sent();
                        data = (res === null || res === void 0 ? void 0 : res.data) || res || {};
                        code = data.share_code ? String(data.share_code) : '';
                        link = data.share_link ? String(data.share_link) : (data.share_token ? this.buildShareLink(String(data.share_token)) : '');
                        copied = code || link;
                        if (copied) {
                            wx.setClipboardData({ data: copied });
                            wx.showToast({ title: '已复制', icon: 'success' });
                        }
                        else {
                            wx.showToast({ title: '创建成功', icon: 'success' });
                        }
                        return [4 /*yield*/, this.loadShares()];
                    case 3:
                        _c.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        err_8 = _c.sent();
                        wx.showToast({ title: (err_8 && err_8.message) ? String(err_8.message) : '创建失败', icon: 'none' });
                        return [3 /*break*/, 6];
                    case 5:
                        wx.hideLoading();
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onRefreshShares: function () {
        this.loadUsageStats();
        this.ensureWechatShareToken(true);
    },
    onCopyShareCode: function (e) {
        var _a, _b;
        var code = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.code) || '').trim();
        if (!code)
            return;
        wx.setClipboardData({ data: code });
    },
    onCopyShareLink: function (e) {
        var _a, _b;
        var link = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.link) || '').trim();
        if (!link)
            return;
        wx.setClipboardData({ data: link });
    },
    onDeleteShare: function (e) {
        var _this = this;
        var _a, _b;
        var bankId = Number(this.data.bankId || 0);
        var shareId = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(bankId) || bankId <= 0)
            return;
        if (!Number.isFinite(shareId) || shareId <= 0)
            return;
        wx.showModal({
            title: '确认撤销',
            content: '撤销后，使用此分享加入的用户将无法继续访问。',
            confirmColor: '#FF3B30',
            success: function (res) { return __awaiter(_this, void 0, void 0, function () {
                var err_9;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (!res.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '撤销中...' });
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 4, 5, 6]);
                            return [4 /*yield*/, api_1.api.deleteBankShare(bankId, shareId)];
                        case 2:
                            _a.sent();
                            wx.showToast({ title: '已撤销', icon: 'success' });
                            return [4 /*yield*/, this.loadShares()];
                        case 3:
                            _a.sent();
                            this.loadUsageStats();
                            this.ensureWechatShareToken(false);
                            return [3 /*break*/, 6];
                        case 4:
                            err_9 = _a.sent();
                            wx.showToast({ title: (err_9 && err_9.message) ? String(err_9.message) : '撤销失败', icon: 'none' });
                            return [3 /*break*/, 6];
                        case 5:
                            wx.hideLoading();
                            return [7 /*endfinally*/];
                        case 6: return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    onShareAppMessage: function () {
        var bankId = Number(this.data.bankId || 0);
        var name = String(this.data.bankName || '').trim();
        if (this.data.canManageShare) {
            var token = String(this.data.wechatShareToken || '').trim();
            if (token) {
                return {
                    title: name ? "\u9080\u8BF7\u4F60\u52A0\u5165\u9898\u5E93\uFF1A".concat(name) : '邀请你加入题库',
                    path: "/pages/bank-join/bank-join?token=".concat(encodeURIComponent(token))
                };
            }
        }
        var path = bankId ? "/pages/bank-detail/bank-detail?id=".concat(bankId) : '/pages/my-banks-v2/my-banks-v2';
        return {
            title: name ? "\u9898\u5E93\uFF1A".concat(name) : '题库分享',
            path: path
        };
    }
});
