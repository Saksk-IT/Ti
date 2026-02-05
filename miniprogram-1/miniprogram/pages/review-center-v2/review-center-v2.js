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
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var user_settings_1 = require("../../utils/user-settings");
var theme_1 = require("../../utils/theme");
function safeDecode(v) {
    if (v == null)
        return '';
    var raw = String(v);
    try {
        return decodeURIComponent(raw);
    }
    catch (e) {
        return raw;
    }
}
function normalizeKind(input) {
    var v = String(input || '').trim().toLowerCase();
    if (v === 'favorites')
        return 'favorites';
    if (v === 'tags')
        return 'tags';
    return 'mistakes';
}
function normalizeTab(input) {
    var v = String(input || '').trim().toLowerCase();
    if (v === 'search')
        return 'search';
    if (v === 'data')
        return 'data';
    return 'practice';
}
function buildOptions(list) {
    var uniq = [];
    (list || []).forEach(function (x) {
        var s = String(x || '').trim();
        if (!s)
            return;
        if (!uniq.includes(s))
            uniq.push(s);
    });
    return __spreadArray([{ value: 'all', label: '全部题型' }], uniq.map(function (s) { return ({ value: s, label: s }); }), true);
}
function normalizeTags(raw) {
    var tags = Array.isArray(raw) ? raw : [];
    var out = [];
    tags.forEach(function (t) {
        var name = String((t === null || t === void 0 ? void 0 : t.name) || '').trim();
        if (!name)
            return;
        var count = Number((t === null || t === void 0 ? void 0 : t.count) || 0) || 0;
        out.push({ name: name, count: count });
    });
    return out;
}
function isOptionShuffleSupported(qType) {
    var t = String(qType || '').trim();
    if (!t || t === 'all')
        return false;
    if (t === '选择题' || t === '多选题')
        return true;
    if (t.includes('单选') || t.includes('多选'))
        return true;
    return false;
}
function formatCountText(n) {
    var v = Number(n);
    if (!Number.isFinite(v))
        return '0';
    if (v > 9999)
        return '9999+';
    return String(Math.max(0, Math.floor(v)));
}
function pctOf(n, maxN) {
    if (maxN <= 0)
        return 0;
    var v = Math.max(0, Math.min(100, (n * 100) / maxN));
    return Math.round(v);
}
function defaultTitles(kind) {
    if (kind === 'favorites') {
        return { navTitle: '收藏中心', pageTitle: '收藏中心', drawerKey: 'review', quizLabel: '刷题', memoLabel: '背题' };
    }
    if (kind === 'tags') {
        return { navTitle: '标签中心', pageTitle: '标签中心', drawerKey: 'review', quizLabel: '刷标签', memoLabel: '背标签' };
    }
    return { navTitle: '错题中心', pageTitle: '错题中心', drawerKey: 'review', quizLabel: '刷错题', memoLabel: '背错题' };
}
function getPracticeMeta(kind) {
    if (kind === 'favorites') {
        return {
            title: '收藏',
            subtitle: '范围固定为收藏。支持题型/标签/模式筛选，便于针对性复习。',
            recommend: '先刷后背',
            tip: '筛选仅作用于收藏范围',
            countLabel: '可用收藏'
        };
    }
    if (kind === 'tags') {
        return {
            title: '标签',
            subtitle: '按你的标签体系聚合题目：练习、搜索与数据复盘均可按标签过滤。',
            recommend: '分组复习',
            tip: '先选标签，再开始练习',
            countLabel: '可用题目'
        };
    }
    return {
        title: '错题',
        subtitle: '范围固定为错题。支持题型/标签/模式筛选，便于集中复盘。',
        recommend: '错因复盘',
        tip: '筛选仅作用于错题范围',
        countLabel: '可用错题'
    };
}
Page({
    data: {
        drawerOpen: false,
        loading: false,
        inited: false,
        kind: 'mistakes',
        sourceType: 'public',
        subject: '',
        bankId: 0,
        navTitle: '复盘中心',
        pageTitle: '复盘中心',
        pageSubtitle: '在当前题库范围内完成练习、搜索与数据复盘（与 Web 端保持同语义）。',
        drawerActiveKey: 'review',
        scopeLabel: '公共',
        scopeName: '',
        tab: 'practice',
        practiceMeta: getPracticeMeta('mistakes'),
        types: [],
        typeOptions: [],
        typeIndex: 0,
        qType: 'all',
        tagOptions: [],
        tagIndex: 0,
        tag: 'all',
        tagChips: [],
        isTagsMode: false,
        shuffleQuestions: false,
        shuffleOptions: false,
        shuffleOptionsDisabled: true,
        startCount: 0,
        startCountText: '0',
        startDisabled: true,
        startError: '',
        startQuizLabel: '刷题',
        startMemoLabel: '背题',
        filterHint: '',
        // 搜索
        searchKeyword: '',
        searched: false,
        searchLoading: false,
        page: 1,
        perPage: 20,
        total: 0,
        hasMore: false,
        questions: [],
        // 数据
        dataLoading: false,
        dataHint: '',
        dataDays: 14,
        dataTotalLabel: '可用题目',
        dataTotal: 0,
        dataAnswered: 0,
        dataCorrect: 0,
        dataWrong: 0,
        dataAccuracy: 0,
        dataCompletion: 0,
        dataFavorites: 0,
        dataMistakes: 0,
        dataMistakesTimes: 0,
        dataStreakDays: 0,
        dataLastActivityText: '—',
        dataTrendDays: 14,
        trendBars: [],
        dataTypeCount: 0,
        dataTagCount: 0,
        typeStats: [],
        diffStats: [],
        tagStats: [],
        tagStatsAll: [],
        tagStatsExpanded: false,
        advice: []
    },
    onLoad: function (options) {
        var _a, _b;
        var kind = normalizeKind((options === null || options === void 0 ? void 0 : options.kind) || (options === null || options === void 0 ? void 0 : options.entry) || (options === null || options === void 0 ? void 0 : options.mode));
        var tab = normalizeTab(options === null || options === void 0 ? void 0 : options.tab);
        var subject = safeDecode((options === null || options === void 0 ? void 0 : options.subject) || '');
        var bankIdRaw = (_b = (_a = options === null || options === void 0 ? void 0 : options.bank_id) !== null && _a !== void 0 ? _a : options === null || options === void 0 ? void 0 : options.bankId) !== null && _b !== void 0 ? _b : options === null || options === void 0 ? void 0 : options.id;
        var bankId = Number(bankIdRaw || 0) || 0;
        var qType = safeDecode((options === null || options === void 0 ? void 0 : options.type) || (options === null || options === void 0 ? void 0 : options.q_type) || 'all') || 'all';
        var tag = safeDecode((options === null || options === void 0 ? void 0 : options.tag) || 'all') || 'all';
        var titles = defaultTitles(kind);
        var practiceMeta = getPracticeMeta(kind);
        var sourceType = bankId > 0 ? 'bank' : 'public';
        var scopeLabel = sourceType === 'bank' ? '个人' : '公共';
        this.setData({
            kind: kind,
            tab: tab,
            subject: sourceType === 'public' ? subject : '',
            bankId: sourceType === 'bank' ? bankId : 0,
            navTitle: titles.navTitle,
            pageTitle: titles.pageTitle,
            drawerActiveKey: titles.drawerKey,
            startQuizLabel: titles.quizLabel,
            startMemoLabel: titles.memoLabel,
            isTagsMode: kind === 'tags',
            scopeLabel: scopeLabel,
            practiceMeta: practiceMeta,
            qType: qType || 'all',
            tag: tag || 'all'
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
        if (!this.data.inited && !this.data.loading) {
            this.bootstrap();
        }
        else {
            this.refreshComputed();
        }
    },
    onPullDownRefresh: function () {
        this.bootstrap(true);
    },
    onReachBottom: function () {
        if (this.data.tab !== 'search')
            return;
        if (!this.data.hasMore || this.data.searchLoading)
            return;
        this.loadMore();
    },
    bootstrap: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var kind, sourceType, subject, bankId, _a, info, tagsRes, infoData, scopeName, availableTypes, types, typeOptions, tagsData, tagsList, tagOptions, qType_1, typeIndex, tag_1, tagIndex, firstHit_1, idx2, e_1;
            var _this = this;
            var _b, _c;
            if (force === void 0) { force = false; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        if (this.data.loading && !force)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 3, 4, 5]);
                        kind = this.data.kind;
                        sourceType = this.data.bankId > 0 ? 'bank' : 'public';
                        subject = String(this.data.subject || '').trim();
                        bankId = Number(this.data.bankId || 0) || 0;
                        if (sourceType === 'public' && !subject) {
                            wx.showToast({ title: '缺少科目参数', icon: 'none' });
                            setTimeout(function () { return wx.navigateBack(); }, 500);
                            return [2 /*return*/];
                        }
                        if (sourceType === 'bank' && bankId <= 0) {
                            wx.showToast({ title: '缺少题库参数', icon: 'none' });
                            setTimeout(function () { return wx.navigateBack(); }, 500);
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, Promise.all([
                                sourceType === 'public'
                                    ? api_1.api.getSubjectInfo(subject).catch(function () { return ({}); })
                                    : api_1.api.getBankDetail(bankId).catch(function () { return ({}); }),
                                sourceType === 'public'
                                    ? api_1.api.getTags({ subject: subject }).catch(function () { return ({ tags: [] }); })
                                    : api_1.api.getBankTags(bankId).catch(function () { return ({ tags: [] }); })
                            ])];
                    case 2:
                        _a = _d.sent(), info = _a[0], tagsRes = _a[1];
                        infoData = (info === null || info === void 0 ? void 0 : info.data) || info || {};
                        scopeName = sourceType === 'public'
                            ? String((infoData === null || infoData === void 0 ? void 0 : infoData.name) || subject)
                            : String((infoData === null || infoData === void 0 ? void 0 : infoData.name) || "\u9898\u5E93".concat(bankId));
                        availableTypes = Array.isArray(infoData === null || infoData === void 0 ? void 0 : infoData.available_types) ? infoData.available_types : [];
                        types = (availableTypes || [])
                            .filter(function (t) { return typeof t === 'string' && String(t).trim(); })
                            .map(function (t) { return String(t).trim(); });
                        typeOptions = buildOptions(types);
                        tagsData = (tagsRes === null || tagsRes === void 0 ? void 0 : tagsRes.data) || tagsRes || {};
                        tagsList = normalizeTags((tagsData === null || tagsData === void 0 ? void 0 : tagsData.tags) || []);
                        tagOptions = __spreadArray([
                            { value: 'all', label: '全部标签' }
                        ], tagsList.map(function (t) { return ({ value: t.name, label: t.name }); }), true);
                        qType_1 = String(this.data.qType || 'all');
                        typeIndex = typeOptions.findIndex(function (o) { return o.value === qType_1; });
                        if (typeIndex < 0)
                            typeIndex = 0;
                        tag_1 = String(this.data.tag || 'all');
                        tagIndex = tagOptions.findIndex(function (o) { return o.value === tag_1; });
                        if (tagIndex < 0)
                            tagIndex = 0;
                        tag_1 = ((_b = tagOptions[tagIndex]) === null || _b === void 0 ? void 0 : _b.value) || 'all';
                        // 标签中心：默认选中第一个真实标签（避免“全部标签=全量题目”造成误解）
                        if (kind === 'tags' && tag_1 === 'all' && tagsList.length) {
                            firstHit_1 = tagsList.find(function (t) { return (Number((t === null || t === void 0 ? void 0 : t.count) || 0) || 0) > 0; }) || tagsList[0];
                            if (firstHit_1 && firstHit_1.name) {
                                idx2 = tagOptions.findIndex(function (o) { return o.value === firstHit_1.name; });
                                tagIndex = idx2 >= 0 ? idx2 : 0;
                                tag_1 = ((_c = tagOptions[tagIndex]) === null || _c === void 0 ? void 0 : _c.value) || firstHit_1.name;
                            }
                        }
                        this.setData({
                            inited: true,
                            sourceType: sourceType,
                            scopeName: scopeName,
                            types: types,
                            typeOptions: typeOptions,
                            typeIndex: typeIndex,
                            qType: qType_1 || 'all',
                            tagOptions: tagOptions,
                            tagIndex: tagIndex,
                            tag: tag_1,
                            tagChips: tagsList,
                            dataTagCount: tagsList.length
                        }, function () { return _this.refreshComputed(); });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _d.sent();
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
    refreshComputed: function () {
        var qType = String(this.data.qType || 'all');
        var tag = String(this.data.tag || 'all');
        var hintParts = [];
        if (qType && qType !== 'all')
            hintParts.push(qType);
        if (tag && tag !== 'all')
            hintParts.push(tag);
        var filterHint = hintParts.length ? hintParts.join(' · ') : '全部';
        var shuffleOptionsDisabled = !isOptionShuffleSupported(qType);
        var shuffleOptions = shuffleOptionsDisabled ? false : !!this.data.shuffleOptions;
        this.setData({ filterHint: filterHint, shuffleOptionsDisabled: shuffleOptionsDisabled, shuffleOptions: shuffleOptions });
        this.refreshStartCount();
        if (this.data.tab === 'data') {
            this.refreshDataStats();
        }
    },
    onTabTap: function (e) {
        var _this = this;
        var _a, _b;
        var tab = normalizeTab(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || 'practice');
        if (tab === this.data.tab)
            return;
        this.setData({ tab: tab }, function () {
            if (tab === 'data')
                _this.refreshDataStats();
        });
    },
    onTypeTap: function (e) {
        var _this = this;
        var _a, _b;
        var t = ((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) ? String(e.currentTarget.dataset.type) : 'all';
        var types = Array.isArray(this.data.types) ? this.data.types : [];
        var qType = t === 'all' || types.includes(t) ? t : 'all';
        var typeOptions = this.data.typeOptions || [];
        var typeIndex = typeOptions.findIndex(function (o) { return o.value === qType; });
        if (typeIndex < 0)
            typeIndex = 0;
        if (qType === this.data.qType && typeIndex === this.data.typeIndex)
            return;
        this.setData({ typeIndex: typeIndex, qType: qType }, function () { return _this.refreshComputed(); });
    },
    onTypePickerChange: function (e) {
        var _this = this;
        var _a;
        var idx = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || 0) || 0;
        var hit = (this.data.typeOptions || [])[idx];
        var qType = hit ? hit.value : 'all';
        this.setData({ typeIndex: idx, qType: qType }, function () { return _this.refreshComputed(); });
    },
    onTagTap: function (e) {
        var _this = this;
        var _a, _b, _c;
        var tag = ((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) ? String(e.currentTarget.dataset.tag) : 'all';
        var tagOptions = this.data.tagOptions || [];
        var tagIndex = tagOptions.findIndex(function (o) { return o.value === tag; });
        if (tagIndex < 0)
            tagIndex = 0;
        var next = ((_c = tagOptions[tagIndex]) === null || _c === void 0 ? void 0 : _c.value) || 'all';
        if (next === this.data.tag && tagIndex === this.data.tagIndex)
            return;
        this.setData({ tagIndex: tagIndex, tag: next }, function () { return _this.refreshComputed(); });
    },
    onTagPickerChange: function (e) {
        var _this = this;
        var _a;
        var idx = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || 0) || 0;
        var hit = (this.data.tagOptions || [])[idx];
        var tag = hit ? hit.value : 'all';
        this.setData({ tagIndex: idx, tag: tag }, function () { return _this.refreshComputed(); });
    },
    onTagChipTap: function (e) {
        var _this = this;
        var _a, _b;
        var tag = ((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tag) ? String(e.currentTarget.dataset.tag) : 'all';
        var tagOptions = this.data.tagOptions || [];
        var tagIndex = tagOptions.findIndex(function (o) { return o.value === tag; });
        if (tagIndex < 0)
            tagIndex = 0;
        this.setData({ tagIndex: tagIndex, tag: tag }, function () { return _this.refreshComputed(); });
    },
    onSearchKeywordInput: function (e) {
        var _a;
        var v = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ searchKeyword: v });
    },
    onClearSearchKeyword: function () {
        this.setData({ searchKeyword: '' });
    },
    refreshStartCount: function () {
        return __awaiter(this, void 0, void 0, function () {
            var kind, sourceType, subject, bankId, qType, tag, isTagsMode, tagRequired, count, params, source, res, params, source, res, startDisabled, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        kind = this.data.kind;
                        sourceType = this.data.sourceType;
                        subject = String(this.data.subject || '').trim();
                        bankId = Number(this.data.bankId || 0) || 0;
                        qType = String(this.data.qType || 'all');
                        tag = String(this.data.tag || 'all');
                        isTagsMode = kind === 'tags';
                        tagRequired = isTagsMode;
                        if (tagRequired && (!tag || tag === 'all')) {
                            this.setData({
                                startCount: 0,
                                startCountText: '—',
                                startDisabled: true,
                                startError: '请选择一个标签再开始练习。'
                            });
                            return [2 /*return*/];
                        }
                        this.setData({ startError: '', startCountText: '…' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, , 7]);
                        count = 0;
                        if (!(sourceType === 'public')) return [3 /*break*/, 3];
                        params = { subject: subject };
                        if (qType && qType !== 'all')
                            params.type = qType;
                        if (tag && tag !== 'all')
                            params.tag = tag;
                        source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
                        if (source !== 'all')
                            params.source = source;
                        return [4 /*yield*/, api_1.api.getQuestionsCount(params)];
                    case 2:
                        res = _a.sent();
                        count = Number((res === null || res === void 0 ? void 0 : res.count) || 0) || 0;
                        return [3 /*break*/, 5];
                    case 3:
                        params = {};
                        if (qType && qType !== 'all')
                            params.q_type = qType;
                        source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
                        params.source = source;
                        if (tag && tag !== 'all')
                            params.tag = tag;
                        return [4 /*yield*/, api_1.api.getBankUserCounts(bankId, params)];
                    case 4:
                        res = _a.sent();
                        count = Number((res === null || res === void 0 ? void 0 : res.total) || 0) || 0;
                        _a.label = 5;
                    case 5:
                        startDisabled = count <= 0;
                        this.setData({ startCount: count, startCountText: formatCountText(count), startDisabled: startDisabled });
                        return [3 /*break*/, 7];
                    case 6:
                        e_2 = _a.sent();
                        this.setData({
                            startCount: 0,
                            startCountText: '0',
                            startDisabled: true,
                            startError: (e_2 && e_2.message) || '统计失败'
                        });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    buildQuizUrl: function (mode, extra) {
        var kind = this.data.kind;
        var sourceType = this.data.sourceType;
        var subject = String(this.data.subject || '').trim();
        var bankId = Number(this.data.bankId || 0) || 0;
        var qType = String(this.data.qType || 'all');
        var tag = String(this.data.tag || 'all');
        var params = ["mode=".concat(encodeURIComponent(mode))];
        if (sourceType === 'public')
            params.push("subject=".concat(encodeURIComponent(subject)));
        else
            params.push("bank_id=".concat(encodeURIComponent(String(bankId))));
        if (qType && qType !== 'all')
            params.push("type=".concat(encodeURIComponent(qType)));
        var source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
        if (source !== 'all')
            params.push("source=".concat(encodeURIComponent(source)));
        if (tag && tag !== 'all')
            params.push("tag=".concat(encodeURIComponent(tag)));
        if (this.data.shuffleQuestions)
            params.push('shuffle_questions=1');
        if (this.data.shuffleOptions && !this.data.shuffleOptionsDisabled)
            params.push('shuffle_options=1');
        if (extra === null || extra === void 0 ? void 0 : extra.start_id)
            params.push("start_id=".concat(encodeURIComponent(String(extra.start_id))));
        return "/pages/quiz/quiz?".concat(params.join('&'));
    },
    onStartQuiz: function () {
        if (this.data.startDisabled)
            return;
        (0, nav_1.safeNavigate)(this.buildQuizUrl('quiz'), 'navigateTo');
    },
    onStartMemo: function () {
        if (this.data.startDisabled)
            return;
        (0, nav_1.safeNavigate)(this.buildQuizUrl('memo'), 'navigateTo');
    },
    onResultTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        (0, nav_1.safeNavigate)(this.buildQuizUrl('quiz', { start_id: id }), 'navigateTo');
    },
    onJumpPracticeType: function (e) {
        var _this = this;
        var _a, _b, _c;
        var t = ((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) ? String(e.currentTarget.dataset.type) : 'all';
        var idx = (this.data.typeOptions || []).findIndex(function (o) { return o.value === t; });
        var typeIndex = idx >= 0 ? idx : 0;
        var qType = ((_c = (this.data.typeOptions || [])[typeIndex]) === null || _c === void 0 ? void 0 : _c.value) || 'all';
        this.setData({ tab: 'practice', typeIndex: typeIndex, qType: qType }, function () { return _this.refreshComputed(); });
    },
    buildTagStats: function () {
        var chips = Array.isArray(this.data.tagChips) ? this.data.tagChips : [];
        var rows = chips
            .map(function (t) { return ({ name: String((t === null || t === void 0 ? void 0 : t.name) || '').trim(), count: Number((t === null || t === void 0 ? void 0 : t.count) || 0) || 0 }); })
            .filter(function (t) { return t.name && t.count > 0; })
            .sort(function (a, b) { return b.count - a.count; });
        var maxN = rows.length ? rows[0].count : 0;
        return rows.map(function (r) { return ({ name: r.name, count: r.count, pct: pctOf(r.count, maxN) }); });
    },
    onDataDaysTap: function (e) {
        var _this = this;
        var _a, _b;
        var days = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.days) || 14);
        if (![7, 14, 30, 90].includes(days))
            return;
        if (days === this.data.dataDays)
            return;
        this.setData({ dataDays: days }, function () {
            if (_this.data.tab === 'data')
                _this.refreshDataStats();
        });
    },
    onToggleTagStatsExpanded: function () {
        var next = !this.data.tagStatsExpanded;
        var all = Array.isArray(this.data.tagStatsAll) ? this.data.tagStatsAll : [];
        var tagStats = next ? all : all.slice(0, 12);
        this.setData({ tagStatsExpanded: next, tagStats: tagStats });
    },
    refreshDataStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var kind, sourceType, subject, bankId, tag, qType, source, dataTotalLabel, days, params, stats, _a, dataTotal, dataAnswered, dataCorrect, dataWrong, dataFavorites, dataMistakes, dataMistakesTimes, dataAccuracy, dataCompletion, dataStreakDays, lastActivityRaw, dataLastActivityText, dataTrendDays, trend, trendBars, byType, typeRows, maxType_1, typeStats, dataTypeCount, byDiff, diffRows, maxDiff_1, diffStats, advice, tagStatsAll, tagStats, e_3, tagStatsAll, tagStats;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.dataLoading)
                            return [2 /*return*/];
                        this.setData({ dataLoading: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, 7, 8]);
                        kind = this.data.kind;
                        sourceType = this.data.sourceType;
                        subject = String(this.data.subject || '').trim();
                        bankId = Number(this.data.bankId || 0) || 0;
                        tag = String(this.data.tag || 'all');
                        qType = String(this.data.qType || 'all');
                        source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
                        dataTotalLabel = kind === 'mistakes' ? '可用错题' : kind === 'favorites' ? '收藏题目' : tag && tag !== 'all' ? '标签题目' : '题库题目';
                        days = [7, 14, 30, 90].includes(Number(this.data.dataDays)) ? Number(this.data.dataDays) : 14;
                        params = { days: days };
                        if (source !== 'all')
                            params.source = source;
                        if (qType && qType !== 'all')
                            params.q_type = qType;
                        if (tag && tag !== 'all')
                            params.tag = tag;
                        if (!(sourceType === 'public')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.getSubjectStatsDetail(subject, params)];
                    case 2:
                        _a = _b.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.getBankStatsDetail(bankId, params)];
                    case 4:
                        _a = _b.sent();
                        _b.label = 5;
                    case 5:
                        stats = _a;
                        dataTotal = Number((stats === null || stats === void 0 ? void 0 : stats.total_count) || 0) || 0;
                        dataAnswered = Number((stats === null || stats === void 0 ? void 0 : stats.answered) || 0) || 0;
                        dataCorrect = Number((stats === null || stats === void 0 ? void 0 : stats.correct) || 0) || 0;
                        dataWrong = Number((stats === null || stats === void 0 ? void 0 : stats.wrong) || 0) || 0;
                        dataFavorites = Number((stats === null || stats === void 0 ? void 0 : stats.favorites) || 0) || 0;
                        dataMistakes = Number((stats === null || stats === void 0 ? void 0 : stats.mistakes) || 0) || 0;
                        dataMistakesTimes = Number((stats === null || stats === void 0 ? void 0 : stats.mistakes_times) || 0) || 0;
                        dataAccuracy = Math.max(0, Math.min(100, Number((stats === null || stats === void 0 ? void 0 : stats.accuracy) || 0) || 0));
                        dataCompletion = Math.max(0, Math.min(100, Number((stats === null || stats === void 0 ? void 0 : stats.completion) || 0) || 0));
                        dataStreakDays = Number((stats === null || stats === void 0 ? void 0 : stats.streak_days) || 0) || 0;
                        lastActivityRaw = (stats === null || stats === void 0 ? void 0 : stats.last_activity) ? String(stats.last_activity) : '';
                        dataLastActivityText = lastActivityRaw ? lastActivityRaw.slice(0, 16) : '—';
                        dataTrendDays = Number((stats === null || stats === void 0 ? void 0 : stats.trend_days) || params.days || 14) || 14;
                        trend = Array.isArray(stats === null || stats === void 0 ? void 0 : stats.trend) ? stats.trend : [];
                        trendBars = trend.map(function (r) {
                            var answered = Number((r === null || r === void 0 ? void 0 : r.answered) || 0) || 0;
                            var correct = Number((r === null || r === void 0 ? void 0 : r.correct) || 0) || 0;
                            var accuracy = answered > 0 ? Math.round((correct * 1000) / answered) / 10 : 0;
                            return { day: String((r === null || r === void 0 ? void 0 : r.day) || ''), accuracy: Math.max(0, Math.min(100, accuracy)), answered: answered };
                        });
                        byType = Array.isArray(stats === null || stats === void 0 ? void 0 : stats.by_type) ? stats.by_type : [];
                        typeRows = byType
                            .map(function (r) { return ({
                            q_type: String((r === null || r === void 0 ? void 0 : r.q_type) || '').trim() || '未知',
                            count: Number((r === null || r === void 0 ? void 0 : r.total) || 0) || 0,
                            answered: Number((r === null || r === void 0 ? void 0 : r.answered) || 0) || 0,
                            accuracy: Math.max(0, Math.min(100, Number((r === null || r === void 0 ? void 0 : r.accuracy) || 0) || 0))
                        }); })
                            .filter(function (r) { return r.count > 0; });
                        typeRows.sort(function (a, b) { return b.count - a.count; });
                        maxType_1 = typeRows.length ? typeRows[0].count : 0;
                        typeStats = typeRows.map(function (r) { return (__assign(__assign({}, r), { pct: pctOf(r.count, maxType_1) })); });
                        dataTypeCount = typeRows.length;
                        byDiff = Array.isArray(stats === null || stats === void 0 ? void 0 : stats.by_difficulty) ? stats.by_difficulty : [];
                        diffRows = byDiff
                            .map(function (r) { return ({
                            label: String((r === null || r === void 0 ? void 0 : r.label) || '').trim() || "\u96BE\u5EA6".concat(Number((r === null || r === void 0 ? void 0 : r.difficulty) || 1) || 1),
                            count: Number((r === null || r === void 0 ? void 0 : r.total) || 0) || 0,
                            answered: Number((r === null || r === void 0 ? void 0 : r.answered) || 0) || 0,
                            accuracy: Math.max(0, Math.min(100, Number((r === null || r === void 0 ? void 0 : r.accuracy) || 0) || 0))
                        }); })
                            .filter(function (r) { return r.count > 0; });
                        maxDiff_1 = diffRows.reduce(function (acc, cur) { return Math.max(acc, Number(cur.count || 0) || 0); }, 0);
                        diffStats = diffRows.map(function (r) { return (__assign(__assign({}, r), { pct: pctOf(r.count, maxDiff_1) })); });
                        advice = Array.isArray(stats === null || stats === void 0 ? void 0 : stats.advice)
                            ? stats.advice
                                .map(function (a) { return ({ title: String((a === null || a === void 0 ? void 0 : a.title) || '').trim(), content: String((a === null || a === void 0 ? void 0 : a.content) || '').trim() }); })
                                .filter(function (a) { return a.title && a.content; })
                            : [];
                        tagStatsAll = this.buildTagStats();
                        tagStats = this.data.tagStatsExpanded ? tagStatsAll : tagStatsAll.slice(0, 12);
                        this.setData({
                            dataHint: '',
                            dataDays: days,
                            dataTotalLabel: dataTotalLabel,
                            dataTotal: dataTotal,
                            dataAnswered: dataAnswered,
                            dataCorrect: dataCorrect,
                            dataWrong: dataWrong,
                            dataAccuracy: dataAccuracy,
                            dataCompletion: dataCompletion,
                            dataFavorites: dataFavorites,
                            dataMistakes: dataMistakes,
                            dataMistakesTimes: dataMistakesTimes,
                            dataStreakDays: dataStreakDays,
                            dataLastActivityText: dataLastActivityText,
                            dataTrendDays: dataTrendDays,
                            trendBars: trendBars,
                            dataTypeCount: dataTypeCount,
                            typeStats: typeStats,
                            diffStats: diffStats,
                            tagStats: tagStats,
                            tagStatsAll: tagStatsAll,
                            advice: advice
                        });
                        return [3 /*break*/, 8];
                    case 6:
                        e_3 = _b.sent();
                        tagStatsAll = this.buildTagStats();
                        tagStats = this.data.tagStatsExpanded ? tagStatsAll : tagStatsAll.slice(0, 12);
                        this.setData({
                            dataHint: '',
                            dataTotal: 0,
                            dataAnswered: 0,
                            dataCorrect: 0,
                            dataWrong: 0,
                            dataAccuracy: 0,
                            dataCompletion: 0,
                            dataFavorites: 0,
                            dataMistakes: 0,
                            dataMistakesTimes: 0,
                            dataStreakDays: 0,
                            dataLastActivityText: '—',
                            trendBars: [],
                            typeStats: [],
                            dataTypeCount: 0,
                            diffStats: [],
                            tagStats: tagStats,
                            tagStatsAll: tagStatsAll,
                            advice: []
                        });
                        return [3 /*break*/, 8];
                    case 7:
                        this.setData({ dataLoading: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    onSearch: function () {
        return __awaiter(this, void 0, void 0, function () {
            var kw;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        kw = String(this.data.searchKeyword || '').trim();
                        if (!kw) {
                            wx.showToast({ title: '请输入关键词', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (this.data.searchLoading)
                            return [2 /*return*/];
                        this.setData({ searched: true, searchLoading: true, page: 1, total: 0, hasMore: false, questions: [] });
                        return [4 /*yield*/, this.fetchSearchPage(1)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    loadMore: function () {
        return __awaiter(this, void 0, void 0, function () {
            var nextPage;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.searchLoading)
                            return [2 /*return*/];
                        nextPage = (Number(this.data.page || 1) || 1) + 1;
                        this.setData({ searchLoading: true });
                        return [4 /*yield*/, this.fetchSearchPage(nextPage, true)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    fetchSearchPage: function (page_1) {
        return __awaiter(this, arguments, void 0, function (page, append) {
            var kind, sourceType, subject, bankId, qType, tag, keyword, tagRequired, source, per_page, data, params, params, questions, total, nextList, hasMore, e_4;
            var _a, _b, _c;
            if (append === void 0) { append = false; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        _d.trys.push([0, 5, 6, 7]);
                        kind = this.data.kind;
                        sourceType = this.data.sourceType;
                        subject = String(this.data.subject || '').trim();
                        bankId = Number(this.data.bankId || 0) || 0;
                        qType = String(this.data.qType || 'all');
                        tag = String(this.data.tag || 'all');
                        keyword = String(this.data.searchKeyword || '').trim();
                        tagRequired = kind === 'tags';
                        if (tagRequired && (!tag || tag === 'all')) {
                            this.setData({ searchLoading: false, searched: true, total: 0, hasMore: false, questions: [] });
                            return [2 /*return*/];
                        }
                        source = kind === 'mistakes' ? 'mistakes' : kind === 'favorites' ? 'favorites' : 'all';
                        per_page = Number(this.data.perPage || 20) || 20;
                        data = null;
                        if (!(sourceType === 'public')) return [3 /*break*/, 2];
                        params = { keyword: keyword, subject: subject, page: page, per_page: per_page };
                        if (qType && qType !== 'all')
                            params.q_type = qType;
                        if (source !== 'all')
                            params.source = source;
                        if (tag && tag !== 'all')
                            params.tag = tag;
                        return [4 /*yield*/, api_1.api.searchQuestions(params)];
                    case 1:
                        data = _d.sent();
                        return [3 /*break*/, 4];
                    case 2:
                        params = { keyword: keyword, page: page, per_page: per_page };
                        if (qType && qType !== 'all')
                            params.q_type = qType;
                        if (source !== 'all')
                            params.source = source;
                        if (tag && tag !== 'all')
                            params.tag = tag;
                        return [4 /*yield*/, api_1.api.searchBankQuestions(bankId, params)];
                    case 3:
                        data = _d.sent();
                        _d.label = 4;
                    case 4:
                        questions = (data && (data.questions || ((_a = data.data) === null || _a === void 0 ? void 0 : _a.questions))) ? (data.questions || ((_b = data.data) === null || _b === void 0 ? void 0 : _b.questions)) : [];
                        total = Number((data === null || data === void 0 ? void 0 : data.total) || ((_c = data === null || data === void 0 ? void 0 : data.data) === null || _c === void 0 ? void 0 : _c.total) || 0) || 0;
                        nextList = append ? (this.data.questions || []).concat(questions) : questions;
                        hasMore = nextList.length < total;
                        this.setData({ page: page, questions: nextList, total: total, hasMore: hasMore });
                        return [3 /*break*/, 7];
                    case 5:
                        e_4 = _d.sent();
                        wx.showToast({ title: (e_4 && e_4.message) || '搜索失败', icon: 'none' });
                        this.setData({ total: 0, hasMore: false });
                        return [3 /*break*/, 7];
                    case 6:
                        this.setData({ searchLoading: false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    onToggleTap: function (e) {
        var _a;
        var _this = this;
        var _b, _c;
        var key = (_c = (_b = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _b === void 0 ? void 0 : _b.dataset) === null || _c === void 0 ? void 0 : _c.key;
        if (!key)
            return;
        if (key === 'shuffleOptions' && this.data.shuffleOptionsDisabled)
            return;
        var current = this.data[key];
        var next = !current;
        this.setData((_a = {}, _a[key] = next, _a), function () { return _this.refreshComputed(); });
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
