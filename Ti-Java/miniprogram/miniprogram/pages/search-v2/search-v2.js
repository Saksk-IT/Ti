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
var auth_1 = require("../../utils/auth");
var theme_1 = require("../../utils/theme");
var FALLBACK_TYPES = ['选择题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
var questionDetailCache = new Map();
function buildOptions(list, allLabel) {
    var uniq = Array.from(new Set((list || []).filter(function (s) { return typeof s === 'string' && s.trim(); }).map(function (s) { return s.trim(); })));
    return __spreadArray([{ value: 'all', label: allLabel }], uniq.map(function (s) { return ({ value: s, label: s }); }), true);
}
function findLabel(options, value, fallback) {
    var hit = (options || []).find(function (o) { return o && o.value === value; });
    return hit ? hit.label : fallback;
}
function looksLikeCode(text) {
    var s = (text || '').toString();
    if (!s.includes('\n'))
        return false;
    var hasIndent = /(^|\n)[ \t]{2,}\S/.test(s);
    var hasCodeTokens = /\b(for|while|if|else|elif|def|class|print|return|break|continue|import|from|int|float|public|private|static|void|main)\b/.test(s);
    var hasSymbols = /[{}();=<>]/.test(s);
    return hasIndent || hasCodeTokens || hasSymbols;
}
function preserveSpacesForCode(text) {
    var s = (text || '').toString().replace(/\t/g, '  ');
    return s
        .split('\n')
        .map(function (line) { return line.replace(/ /g, '\u00A0'); })
        .join('\n');
}
function formatAnswerForDisplay(qType, answer) {
    var a = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
    if (qType === '填空题') {
        return a.replace(/;;/g, ' / ').replace(/;/g, ' 或 ');
    }
    return a;
}
Page({
    activeDetailReqId: 0,
    data: {
        loading: false,
        searched: false,
        advancedOpen: false,
        keyword: '',
        preselectSubject: '',
        preselectType: '',
        questions: [],
        page: 1,
        per_page: 20,
        total: 0,
        hasMore: true,
        subjectOptions: [],
        subjectIndex: 0,
        subject: 'all',
        subjectLabel: '全部科目',
        typeOptions: [],
        typeIndex: 0,
        qType: 'all',
        typeLabel: '全部题型',
        detailOpen: false,
        detailLoading: false,
        detailError: '',
        detailQuestionId: 0,
        detailSubjectFromList: '',
        detailQTypeFromList: '',
        detailQuestion: null,
        detailOptions: [],
        detailImages: []
    },
    onLoad: function (options) {
        var keyword = options && options.keyword ? String(options.keyword) : '';
        var preselectSubject = options && options.subject ? String(options.subject) : '';
        var preselectType = options && (options.q_type || options.type) ? String(options.q_type || options.type) : '';
        if (preselectSubject) {
            try {
                preselectSubject = decodeURIComponent(preselectSubject);
            }
            catch (e) { }
        }
        if (preselectType) {
            try {
                preselectType = decodeURIComponent(preselectType);
            }
            catch (e) { }
        }
        this.setData({
            keyword: keyword,
            preselectSubject: preselectSubject,
            preselectType: preselectType
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
        if (!this.data.subjectOptions.length) {
            this.bootstrap();
        }
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, list, subjects, subjectOptions, subjectIndex, subject, subjectLabel, wantedSubject_1, idx, typeOptions, typeIndex, qType, typeLabel, info, types, e_1, wantedType_1, idx, e_2;
            var _this = this;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 6, , 7]);
                        return [4 /*yield*/, api_1.api.getSubjects()];
                    case 1:
                        res = _b.sent();
                        list = Array.isArray(res === null || res === void 0 ? void 0 : res.subjects) ? res.subjects : [];
                        subjects = list
                            .filter(function (s) { return typeof s === 'string' && s.trim(); })
                            .map(function (s) { return String(s).trim(); });
                        subjectOptions = __spreadArray([{ value: 'all', label: '全部科目' }], subjects.map(function (s) { return ({ value: s, label: s }); }), true);
                        subjectIndex = 0;
                        subject = 'all';
                        subjectLabel = '全部科目';
                        wantedSubject_1 = String(this.data.preselectSubject || '').trim();
                        if (wantedSubject_1) {
                            idx = subjectOptions.findIndex(function (o) { return o && o.value === wantedSubject_1; });
                            if (idx >= 0) {
                                subjectIndex = idx;
                                subject = wantedSubject_1;
                                subjectLabel = findLabel(subjectOptions, wantedSubject_1, '全部科目');
                            }
                        }
                        typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
                        typeIndex = 0;
                        qType = 'all';
                        typeLabel = '全部题型';
                        if (!(subject !== 'all')) return [3 /*break*/, 5];
                        _b.label = 2;
                    case 2:
                        _b.trys.push([2, 4, , 5]);
                        return [4 /*yield*/, api_1.api.getSubjectInfo(subject)];
                    case 3:
                        info = _b.sent();
                        types = Array.isArray(info === null || info === void 0 ? void 0 : info.available_types)
                            ? info.available_types
                            : Array.isArray((_a = info === null || info === void 0 ? void 0 : info.data) === null || _a === void 0 ? void 0 : _a.available_types)
                                ? info.data.available_types
                                : [];
                        typeOptions = buildOptions(types.length ? types : FALLBACK_TYPES, '全部题型');
                        return [3 /*break*/, 5];
                    case 4:
                        e_1 = _b.sent();
                        typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
                        return [3 /*break*/, 5];
                    case 5:
                        wantedType_1 = String(this.data.preselectType || '').trim();
                        if (wantedType_1 && wantedType_1 !== 'all') {
                            idx = typeOptions.findIndex(function (o) { return o && o.value === wantedType_1; });
                            if (idx >= 0) {
                                typeIndex = idx;
                                qType = wantedType_1;
                                typeLabel = findLabel(typeOptions, wantedType_1, '全部题型');
                            }
                        }
                        this.setData({
                            subjectOptions: subjectOptions,
                            subjectIndex: subjectIndex,
                            subject: subject,
                            subjectLabel: subjectLabel,
                            typeOptions: typeOptions,
                            typeIndex: typeIndex,
                            qType: qType,
                            typeLabel: typeLabel
                        }, function () {
                            if (_this.data.keyword)
                                _this.onSearch();
                        });
                        return [3 /*break*/, 7];
                    case 6:
                        e_2 = _b.sent();
                        wx.showToast({ title: (e_2 && e_2.message) || '初始化失败', icon: 'none' });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onKeywordInput: function (e) {
        var _a;
        this.setData({ keyword: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onClearKeyword: function () {
        this.setData({ keyword: '' });
    },
    onToggleAdvanced: function () {
        this.setData({ advancedOpen: !this.data.advancedOpen });
    },
    onSubjectPicker: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var idx, options, picked, subject, typeOptions, info, types, typeOptions, e_3, typeOptions;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        idx = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || 0);
                        options = this.data.subjectOptions || [];
                        picked = options[idx] ? options[idx].value : 'all';
                        subject = picked || 'all';
                        this.setData({
                            subjectIndex: idx,
                            subject: subject,
                            subjectLabel: findLabel(options, subject, '全部科目'),
                            qType: 'all',
                            typeIndex: 0,
                            typeLabel: '全部题型'
                        });
                        if (subject === 'all') {
                            typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
                            this.setData({ typeOptions: typeOptions });
                            return [2 /*return*/];
                        }
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSubjectInfo(subject)];
                    case 2:
                        info = _c.sent();
                        types = Array.isArray(info === null || info === void 0 ? void 0 : info.available_types) ? info.available_types : Array.isArray((_b = info === null || info === void 0 ? void 0 : info.data) === null || _b === void 0 ? void 0 : _b.available_types) ? info.data.available_types : [];
                        typeOptions = buildOptions(types.length ? types : FALLBACK_TYPES, '全部题型');
                        this.setData({ typeOptions: typeOptions });
                        return [3 /*break*/, 4];
                    case 3:
                        e_3 = _c.sent();
                        typeOptions = buildOptions(FALLBACK_TYPES, '全部题型');
                        this.setData({ typeOptions: typeOptions });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onTypePicker: function (e) {
        var _a;
        var idx = Number(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || 0);
        var options = this.data.typeOptions || [];
        var picked = options[idx] ? options[idx].value : 'all';
        var qType = picked || 'all';
        this.setData({
            typeIndex: idx,
            qType: qType,
            typeLabel: findLabel(options, qType, '全部题型')
        });
    },
    onSearch: function () {
        var kw = String(this.data.keyword || '').trim();
        if (!kw) {
            wx.showToast({ title: '请输入关键词', icon: 'none' });
            return;
        }
        this.loadResults(true);
    },
    loadResults: function () {
        return __awaiter(this, arguments, void 0, function (reset) {
            var keyword, page, params, result, list, next, e_4;
            if (reset === void 0) { reset = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        keyword = String(this.data.keyword || '').trim();
                        if (!keyword)
                            return [2 /*return*/];
                        page = reset ? 1 : this.data.page;
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        params = { keyword: keyword, page: page, per_page: this.data.per_page };
                        if (this.data.subject && this.data.subject !== 'all')
                            params.subject = this.data.subject;
                        if (this.data.qType && this.data.qType !== 'all')
                            params.q_type = this.data.qType;
                        return [4 /*yield*/, api_1.api.searchQuestions(params)];
                    case 2:
                        result = _a.sent();
                        list = Array.isArray(result === null || result === void 0 ? void 0 : result.questions) ? result.questions : [];
                        next = reset ? list : (this.data.questions || []).concat(list);
                        this.setData({
                            questions: next,
                            total: Number((result === null || result === void 0 ? void 0 : result.total) || 0) || 0,
                            page: page + 1,
                            hasMore: list.length === this.data.per_page,
                            searched: true,
                            loading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_4 = _a.sent();
                        wx.showToast({ title: (e_4 && e_4.message) || '搜索失败', icon: 'none' });
                        this.setData({ loading: false, searched: true });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onPullDownRefresh: function () {
        this.loadResults(true)
            .catch(function () { })
            .then(function () { return wx.stopPullDownRefresh(); });
    },
    onReachBottom: function () {
        if (this.data.hasMore && !this.data.loading) {
            this.loadResults(false);
        }
    },
    noop: function () { },
    onDetailClose: function () {
        this.activeDetailReqId = Number(this.activeDetailReqId || 0) + 1;
        this.setData({ detailOpen: false });
    },
    onDetailRetry: function () {
        var id = Number(this.data.detailQuestionId || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        this.openQuestionDetail(id, true);
    },
    onDetailGoQuiz: function () {
        var _a, _b;
        var id = Number(this.data.detailQuestionId || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var subject = String(((_a = this.data.detailQuestion) === null || _a === void 0 ? void 0 : _a.subject) || this.data.detailSubjectFromList || '').trim();
        if (!subject) {
            wx.showToast({ title: '缺少科目信息，无法跳转', icon: 'none' });
            return;
        }
        var qType = String(((_b = this.data.detailQuestion) === null || _b === void 0 ? void 0 : _b.q_type) || this.data.detailQTypeFromList || '').trim();
        var params = [];
        params.push("subject=".concat(encodeURIComponent(subject)));
        params.push('mode=reinforce');
        params.push("ids=".concat(encodeURIComponent(String(id))));
        if (qType && qType !== 'all')
            params.push("type=".concat(encodeURIComponent(qType)));
        params.push("start_id=".concat(id));
        this.onDetailClose();
        wx.navigateTo({ url: "/pages/quiz/quiz?".concat(params.join('&')) });
    },
    prepareQuestionDetail: function (raw) {
        var q = raw || {};
        var qType = (q.q_type || '').toString();
        var displayContent = (q.content || '').toString();
        if (qType === '填空题') {
            displayContent = displayContent.replace(/__/g, '____');
        }
        var contentIsCode = looksLikeCode(displayContent);
        if (contentIsCode)
            displayContent = preserveSpacesForCode(displayContent);
        var rawExplanation = (q.explanation || '').toString();
        var explanationIsCode = looksLikeCode(rawExplanation);
        var displayExplanation = explanationIsCode ? preserveSpacesForCode(rawExplanation) : rawExplanation;
        var rawAnswer = (q.answer || '').toString();
        var displayAnswer = formatAnswerForDisplay(qType, rawAnswer);
        var detailQuestion = Object.assign({}, q, {
            displayContent: displayContent,
            contentIsCode: contentIsCode,
            displayAnswer: displayAnswer,
            displayExplanation: displayExplanation,
            explanationIsCode: explanationIsCode
        });
        var detailOptions = Array.isArray(q.options)
            ? q.options
                .map(function (opt) { return ({
                key: (opt && opt.key != null ? String(opt.key) : '').trim(),
                value: opt && opt.value != null ? String(opt.value) : ''
            }); })
                .filter(function (opt) { return opt && (opt.key || opt.value); })
            : [];
        var detailImages = (0, api_1.normalizeImageUrls)(q.image_path);
        return { detailQuestion: detailQuestion, detailOptions: detailOptions, detailImages: detailImages };
    },
    openQuestionDetail: function (questionId_1) {
        return __awaiter(this, arguments, void 0, function (questionId, forceReload, meta) {
            var id, reqId, subjectFromList, qTypeFromList, cached, q, prepared, e_5;
            if (forceReload === void 0) { forceReload = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        id = Number(questionId || 0);
                        if (!Number.isFinite(id) || id <= 0)
                            return [2 /*return*/];
                        this.activeDetailReqId = Number(this.activeDetailReqId || 0) + 1;
                        reqId = this.activeDetailReqId;
                        subjectFromList = meta && typeof meta.subject === 'string'
                            ? meta.subject
                            : String(this.data.detailSubjectFromList || '');
                        qTypeFromList = meta && typeof meta.qType === 'string'
                            ? meta.qType
                            : String(this.data.detailQTypeFromList || '');
                        this.setData({
                            detailOpen: true,
                            detailLoading: true,
                            detailError: '',
                            detailQuestionId: id,
                            detailSubjectFromList: subjectFromList,
                            detailQTypeFromList: qTypeFromList,
                            detailQuestion: null,
                            detailOptions: [],
                            detailImages: []
                        });
                        if (!forceReload && questionDetailCache.has(id)) {
                            cached = questionDetailCache.get(id);
                            this.setData(__assign({ detailLoading: false }, (cached || {})));
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getQuestionDetail(id)];
                    case 2:
                        q = _a.sent();
                        prepared = this.prepareQuestionDetail(q);
                        questionDetailCache.set(id, prepared);
                        if (reqId !== this.activeDetailReqId)
                            return [2 /*return*/];
                        this.setData(__assign({ detailLoading: false }, prepared));
                        return [3 /*break*/, 4];
                    case 3:
                        e_5 = _a.sent();
                        if (reqId !== this.activeDetailReqId)
                            return [2 /*return*/];
                        this.setData({ detailLoading: false, detailError: (e_5 && e_5.message) || '加载失败' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onResultTap: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        var subject = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.subject) || '').trim();
        var qType = String(((_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.qtype) || '').trim();
        this.openQuestionDetail(id, false, { subject: subject, qType: qType });
    }
});
