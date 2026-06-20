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
var request_state_1 = require("./behaviors/request-state");
var set_data_batcher_1 = require("./utils/set-data-batcher");
var index_v2_helpers_1 = require("./modules/index-v2-helpers");
var examPresetApplied = false;
Page({
    behaviors: [request_state_1.requestStateBehavior],
    data: {
        tab: 'new',
        inited: false,
        bootstrapping: false,
        subjectOptions: [],
        bankOptions: [],
        examSource: 'public',
        examSubject: 'all',
        examSubjectLabel: '全部科目',
        examSubjectIndex: 0,
        examBankId: null,
        examBankLabel: '请选择题库',
        examBankIndex: 0,
        examDuration: 60,
        examTargetTotal: 30,
        quickPresets: index_v2_helpers_1.QUICK_PRESETS,
        examTypes: [],
        examLoading: false,
        examCreating: false,
        examStartDisabled: true,
        examMsg: '',
        examMsgKind: '',
        examSumScope: '-',
        examSumDuration: '-',
        examSumAssigned: '-',
        examSumScore: '-',
        examSumTypes: [],
        tplSource: 'public',
        tplSubject: 'all',
        tplSubjectLabel: '全部科目',
        tplSubjectIndex: 0,
        tplBankId: null,
        tplBankLabel: '请选择题库',
        tplBankIndex: 0,
        systemTemplates: index_v2_helpers_1.SYSTEM_TEMPLATES,
        userTemplateCards: [],
        userTemplateConfigById: {},
        userTemplatesLoaded: false,
        templatesLoading: false,
        templateMsg: '',
        templateMsgKind: '',
        saveModalOpen: false,
        saveTemplateTitle: '',
        savingTemplate: false,
        // === 考试记录（tab=records） ===
        recordsSource: 'all',
        recordsSubject: 'all',
        recordsSubjectLabel: '全部科目',
        recordsSubjectIndex: 0,
        recordsBankOptions: [],
        recordsBankId: 0,
        recordsBankLabel: '全部题库',
        recordsBankIndex: 0,
        recordsSizeOptions: [
            { value: 10, label: '10/页' },
            { value: 20, label: '20/页' },
            { value: 50, label: '50/页' }
        ],
        recordsSize: 10,
        recordsSizeIndex: 0,
        recordsSizeLabel: '10/页',
        recordsPage: 1,
        recordsTotal: 0,
        recordsTotalPages: 1,
        recordsOngoing: [],
        recordsSubmitted: [],
        recordsLoading: false,
        recordsMsg: '',
        recordsMsgKind: '',
        // === 考试数据（tab=data） ===
        statsLoading: false,
        statsLoaded: false,
        statsOverview: {
            submitted_count: 0,
            avg_score: 0,
            avg_accuracy: 0,
            last7_count: 0,
            last7_avg_accuracy: 0
        },
        recentExams: [],
        typeDist: [],
        statsFilterKey: '',
        statsScopeText: '',
        statsAdvice: [],
        statsMsg: '',
        statsMsgKind: ''
    },
    setDataBatcher: null,
    ensureSetDataBatcher: function () {
        if (this.setDataBatcher)
            return;
        this.setDataBatcher = (0, set_data_batcher_1.createSetDataBatcher)(this.setData.bind(this));
    },
    patchData: function (patch, callback, immediate) {
        if (immediate === void 0) { immediate = false; }
        this.ensureSetDataBatcher();
        var fn = this.setDataBatcher;
        if (typeof fn === 'function') {
            fn(patch, callback, { immediate: immediate });
            return;
        }
        this.setData(patch, callback);
    },
    onLoad: function (options) {
        this.ensureSetDataBatcher();
        var tab = options && options.tab ? String(options.tab) : '';
        var patch = {};
        if (tab === 'templates' || tab === 'new' || tab === 'records' || tab === 'data' || tab === 'settings') {
            patch.tab = tab;
        }
        // exams-select-v2 -> index-v2：tab=new 时，把 source/subject/bank_id 解释为「新建考试」的预选条件
        if (patch.tab === 'new') {
            var navSource = ((options === null || options === void 0 ? void 0 : options.source) || '').toString().trim().toLowerCase();
            if (navSource === 'public' || navSource === 'user_bank') {
                patch.examSource = navSource;
            }
            var navSubject = (options === null || options === void 0 ? void 0 : options.subject) ? String(options.subject) : '';
            if (navSubject) {
                try {
                    navSubject = decodeURIComponent(navSubject);
                }
                catch (e) { }
                patch.examSubject = navSubject;
            }
            var navBankId = Number((options === null || options === void 0 ? void 0 : options.bank_id) || 0);
            if (Number.isFinite(navBankId) && navBankId > 0) {
                patch.examBankId = navBankId;
            }
        }
        else if (patch.tab === 'templates') {
            // 题库详情页 -> 考试中心：tab=templates 时，把 source/subject/bank_id 解释为「模板范围」的预选条件
            var tplSource = ((options === null || options === void 0 ? void 0 : options.source) || '').toString().trim().toLowerCase();
            if (tplSource === 'public' || tplSource === 'user_bank') {
                patch.tplSource = tplSource;
            }
            var tplSubject = (options === null || options === void 0 ? void 0 : options.subject) ? String(options.subject) : '';
            if (tplSubject) {
                try {
                    tplSubject = decodeURIComponent(tplSubject);
                }
                catch (e) { }
                patch.tplSubject = tplSubject;
            }
            var tplBankId = Number((options === null || options === void 0 ? void 0 : options.bank_id) || 0);
            if (Number.isFinite(tplBankId) && tplBankId > 0) {
                patch.tplBankId = tplBankId;
            }
        }
        else {
            // 兼容 Web /exams?tab=records 的 query：source/subject/bank_id/page/size
            var recSource = ((options === null || options === void 0 ? void 0 : options.source) || '').toString().trim().toLowerCase();
            if (recSource === 'all' || recSource === 'public' || recSource === 'user_bank') {
                patch.recordsSource = recSource;
            }
            var recSubject = (options === null || options === void 0 ? void 0 : options.subject) ? String(options.subject) : '';
            if (recSubject) {
                try {
                    recSubject = decodeURIComponent(recSubject);
                }
                catch (e) { }
                patch.recordsSubject = recSubject;
            }
            var recBankId = Number((options === null || options === void 0 ? void 0 : options.bank_id) || 0);
            if (Number.isFinite(recBankId) && recBankId > 0) {
                patch.recordsBankId = recBankId;
            }
            var recPage = (0, index_v2_helpers_1.clampInt)(options === null || options === void 0 ? void 0 : options.page, 1, 1, 9999);
            if (recPage > 1)
                patch.recordsPage = recPage;
            var recSize = (0, index_v2_helpers_1.clampInt)(options === null || options === void 0 ? void 0 : options.size, 10, 5, 50);
            if (recSize === 10 || recSize === 20 || recSize === 50) {
                patch.recordsSize = recSize;
            }
        }
        if (Object.keys(patch).length) {
            this.patchData(patch, undefined, true);
        }
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.patchData(theme_1.themeManager.getPageData(), undefined, true);
        }
        catch (e) { }
        if (!this.data.inited && !this.data.bootstrapping) {
            this.bootstrap();
        }
    },
    bootstrap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, subjectsRes, myBanksRes, sharedBanksRes, subjectListRaw, subjects, subjectOptions, banks, bankOptions, firstBankId, recordsBankOptions, sizeList, wantedSize, wantedSizeIndex, wantedSizeLabel, firstBankLabel, desiredExamSource, desiredExamSubject_1, exists, desiredExamSubjectIndex, desiredExamSubjectLabel, desiredExamBankId_1, wantedBankId_1, exists, desiredExamBankIndex, desiredExamBankLabel, desiredTplSource, desiredTplSubject_1, exists, desiredTplSubjectIndex, desiredTplSubjectLabel, desiredTplBankId_1, wantedTplBankId_1, exists, desiredTplBankIndex, desiredTplBankLabel, e_1;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.patchData({ bootstrapping: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 5, 6, 7]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getSubjects(),
                                api_1.api.getMyBanks().catch(function () { return ({ banks: [] }); }),
                                api_1.api.getSharedBanks().catch(function () { return ({ banks: [] }); })
                            ])];
                    case 2:
                        _a = _b.sent(), subjectsRes = _a[0], myBanksRes = _a[1], sharedBanksRes = _a[2];
                        subjectListRaw = (subjectsRes === null || subjectsRes === void 0 ? void 0 : subjectsRes.subjects) || [];
                        subjects = Array.isArray(subjectListRaw)
                            ? subjectListRaw.filter(function (x) { return typeof x === 'string' && x.trim(); }).map(function (s) { return String(s).trim(); })
                            : [];
                        subjectOptions = (0, index_v2_helpers_1.buildSubjectOptions)(subjects);
                        banks = (0, index_v2_helpers_1.uniqueBanks)(__spreadArray(__spreadArray([], (myBanksRes === null || myBanksRes === void 0 ? void 0 : myBanksRes.banks) || [], true), (sharedBanksRes === null || sharedBanksRes === void 0 ? void 0 : sharedBanksRes.banks) || [], true));
                        bankOptions = (0, index_v2_helpers_1.buildBankOptions)(banks);
                        firstBankId = bankOptions.length ? bankOptions[0].value : null;
                        recordsBankOptions = __spreadArray([{ value: 0, label: '全部题库' }], bankOptions, true);
                        sizeList = [10, 20, 50];
                        wantedSize = sizeList.includes(Number(this.data.recordsSize)) ? Number(this.data.recordsSize) : 10;
                        wantedSizeIndex = Math.max(0, sizeList.indexOf(wantedSize));
                        wantedSizeLabel = wantedSize === 50 ? '50/页' : wantedSize === 20 ? '20/页' : '10/页';
                        firstBankLabel = bankOptions.length ? bankOptions[0].label : '请选择题库';
                        desiredExamSource = this.data.examSource === 'user_bank' ? 'user_bank' : 'public';
                        desiredExamSubject_1 = String(this.data.examSubject || 'all').trim() || 'all';
                        if (desiredExamSource === 'public') {
                            exists = subjectOptions.some(function (o) { return o.value === desiredExamSubject_1; });
                            if (!exists)
                                desiredExamSubject_1 = 'all';
                        }
                        else {
                            desiredExamSubject_1 = 'all';
                        }
                        desiredExamSubjectIndex = Math.max(0, subjectOptions.findIndex(function (o) { return o.value === desiredExamSubject_1; }));
                        desiredExamSubjectLabel = (0, index_v2_helpers_1.findOptionLabel)(subjectOptions, desiredExamSubject_1, '全部科目');
                        desiredExamBankId_1 = firstBankId;
                        wantedBankId_1 = this.data.examBankId != null ? Number(this.data.examBankId) : null;
                        if (wantedBankId_1 != null && Number.isFinite(wantedBankId_1)) {
                            exists = bankOptions.some(function (o) { return o.value === wantedBankId_1; });
                            if (exists)
                                desiredExamBankId_1 = wantedBankId_1;
                        }
                        desiredExamBankIndex = desiredExamBankId_1 != null ? Math.max(0, bankOptions.findIndex(function (o) { return o.value === desiredExamBankId_1; })) : 0;
                        desiredExamBankLabel = desiredExamBankId_1 != null ? (0, index_v2_helpers_1.findOptionLabel)(bankOptions, desiredExamBankId_1, firstBankLabel) : '请选择题库';
                        desiredTplSource = this.data.tplSource === 'user_bank' ? 'user_bank' : 'public';
                        desiredTplSubject_1 = String(this.data.tplSubject || 'all').trim() || 'all';
                        if (desiredTplSource === 'public') {
                            exists = subjectOptions.some(function (o) { return o.value === desiredTplSubject_1; });
                            if (!exists)
                                desiredTplSubject_1 = 'all';
                        }
                        else {
                            desiredTplSubject_1 = 'all';
                        }
                        desiredTplSubjectIndex = Math.max(0, subjectOptions.findIndex(function (o) { return o.value === desiredTplSubject_1; }));
                        desiredTplSubjectLabel = (0, index_v2_helpers_1.findOptionLabel)(subjectOptions, desiredTplSubject_1, '全部科目');
                        desiredTplBankId_1 = firstBankId;
                        wantedTplBankId_1 = this.data.tplBankId != null ? Number(this.data.tplBankId) : null;
                        if (wantedTplBankId_1 != null && Number.isFinite(wantedTplBankId_1)) {
                            exists = bankOptions.some(function (o) { return o.value === wantedTplBankId_1; });
                            if (exists)
                                desiredTplBankId_1 = wantedTplBankId_1;
                        }
                        desiredTplBankIndex = desiredTplBankId_1 != null ? Math.max(0, bankOptions.findIndex(function (o) { return o.value === desiredTplBankId_1; })) : 0;
                        desiredTplBankLabel = desiredTplBankId_1 != null ? (0, index_v2_helpers_1.findOptionLabel)(bankOptions, desiredTplBankId_1, firstBankLabel) : firstBankLabel;
                        return [4 /*yield*/, (0, index_v2_helpers_1.setDataAsync)(this, {
                                inited: true,
                                subjectOptions: subjectOptions,
                                bankOptions: bankOptions,
                                recordsBankOptions: recordsBankOptions,
                                recordsSize: wantedSize,
                                recordsSizeIndex: wantedSizeIndex,
                                recordsSizeLabel: wantedSizeLabel,
                                examSource: desiredExamSource,
                                examSubject: desiredExamSubject_1,
                                examSubjectLabel: desiredExamSubjectLabel,
                                examSubjectIndex: desiredExamSubjectIndex,
                                examBankId: desiredExamBankId_1,
                                examBankLabel: desiredExamBankLabel,
                                examBankIndex: desiredExamBankIndex,
                                tplSource: desiredTplSource,
                                tplSubject: desiredTplSubject_1,
                                tplSubjectLabel: desiredTplSubjectLabel,
                                tplSubjectIndex: desiredTplSubjectIndex,
                                tplBankId: desiredTplBankId_1,
                                tplBankLabel: desiredTplBankLabel,
                                tplBankIndex: desiredTplBankIndex
                            })];
                    case 3:
                        _b.sent();
                        return [4 /*yield*/, this.reloadExamTypes()];
                    case 4:
                        _b.sent();
                        this.syncRecordsFilters();
                        if (this.data.tab === 'templates')
                            this.loadUserTemplates();
                        if (this.data.tab === 'records')
                            this.loadExamRecords(true);
                        if (this.data.tab === 'data')
                            this.loadExamStats();
                        return [3 /*break*/, 7];
                    case 5:
                        e_1 = _b.sent();
                        wx.showToast({ title: (e_1 && e_1.message) || '初始化失败', icon: 'none' });
                        return [3 /*break*/, 7];
                    case 6:
                        this.patchData({ bootstrapping: false }, undefined, true);
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    stopTap: function () { },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.patchData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onGoNewTab: function () {
        this.patchData({ tab: 'new' });
    },
    onGoTemplatesTab: function () {
        var _this = this;
        this.patchData({ tab: 'templates' }, function () {
            _this.loadUserTemplates();
        });
    },
    onTabTap: function (e) {
        var _this = this;
        var _a, _b;
        var tab = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab;
        if (!tab || tab === this.data.tab)
            return;
        this.patchData({ tab: tab }, function () {
            if (tab === 'templates')
                _this.loadUserTemplates();
            if (tab === 'records')
                _this.loadExamRecords(true);
            if (tab === 'data')
                _this.loadExamStats();
        });
    },
    // === records（考试记录）===
    setRecordsMsg: function (text, kind) {
        if (kind === void 0) { kind = ''; }
        this.patchData({ recordsMsg: String(text || ''), recordsMsgKind: kind });
    },
    syncRecordsFilters: function () {
        var subjectOptions = this.data.subjectOptions || [];
        var bankOptions = this.data.recordsBankOptions || [];
        var recordsSource = String(this.data.recordsSource || 'all').toLowerCase();
        if (recordsSource !== 'all' && recordsSource !== 'public' && recordsSource !== 'user_bank')
            recordsSource = 'all';
        var recordsSubject = String(this.data.recordsSubject || 'all');
        if (recordsSource === 'user_bank')
            recordsSubject = 'all';
        var subjectIdx = Math.max(0, subjectOptions.findIndex(function (o) { return o && o.value === recordsSubject; }));
        var subjectOpt = subjectOptions[subjectIdx] || subjectOptions[0] || { value: 'all', label: '全部科目' };
        recordsSubject = subjectOpt.value;
        var recordsSubjectLabel = subjectOpt.label || '全部科目';
        var recordsBankId = Number(this.data.recordsBankId || 0);
        if (!Number.isFinite(recordsBankId) || recordsBankId < 0)
            recordsBankId = 0;
        if (recordsSource === 'public')
            recordsBankId = 0;
        var bankIdx = Math.max(0, bankOptions.findIndex(function (o) { return o && o.value === recordsBankId; }));
        var bankOpt = bankOptions[bankIdx] || bankOptions[0] || { value: 0, label: '全部题库' };
        recordsBankId = bankOpt.value;
        var recordsBankLabel = bankOpt.label || '全部题库';
        var sizeList = [10, 20, 50];
        var recordsSize = Number(this.data.recordsSize || 10);
        if (!sizeList.includes(recordsSize))
            recordsSize = 10;
        var recordsSizeIndex = Math.max(0, sizeList.indexOf(recordsSize));
        var recordsSizeLabel = recordsSize === 50 ? '50/页' : recordsSize === 20 ? '20/页' : '10/页';
        var total = Math.max(0, Number(this.data.recordsTotal || 0) || 0);
        var totalPages = Math.max(1, Math.ceil(total / Math.max(1, recordsSize)));
        var recordsTotalPages = totalPages;
        var recordsPage = (0, index_v2_helpers_1.clampInt)(this.data.recordsPage, 1, 1, totalPages);
        this.patchData({
            recordsSource: recordsSource,
            recordsSubject: recordsSubject,
            recordsSubjectIndex: subjectIdx,
            recordsSubjectLabel: recordsSubjectLabel,
            recordsBankId: recordsBankId,
            recordsBankIndex: bankIdx,
            recordsBankLabel: recordsBankLabel,
            recordsSize: recordsSize,
            recordsSizeIndex: recordsSizeIndex,
            recordsSizeLabel: recordsSizeLabel,
            recordsTotalPages: recordsTotalPages,
            recordsPage: recordsPage
        });
    },
    onRecordsSourceTap: function (e) {
        var _this = this;
        var _a, _b;
        var source = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.source) || '').trim().toLowerCase();
        if (source !== 'all' && source !== 'public' && source !== 'user_bank')
            return;
        if (source === this.data.recordsSource)
            return;
        this.patchData({ recordsSource: source, recordsPage: 1 }, function () {
            _this.syncRecordsFilters();
            if (_this.data.tab === 'records')
                _this.loadExamRecords(true);
            if (_this.data.tab === 'data')
                _this.loadExamStats(true);
        });
    },
    onRecordsSubjectPicker: function (e) {
        var _this = this;
        var _a;
        if (this.data.recordsSource === 'user_bank')
            return;
        var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
        var subjectOptions = this.data.subjectOptions || [];
        var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
        var opt = subjectOptions[safeIdx];
        if (!opt)
            return;
        this.patchData({
            recordsSubjectIndex: safeIdx,
            recordsSubject: opt.value,
            recordsSubjectLabel: opt.label,
            recordsPage: 1
        }, function () {
            if (_this.data.tab === 'records')
                _this.loadExamRecords(true);
            if (_this.data.tab === 'data')
                _this.loadExamStats(true);
        });
    },
    onRecordsBankPicker: function (e) {
        var _this = this;
        var _a;
        if (this.data.recordsSource === 'public')
            return;
        var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
        var bankOptions = this.data.recordsBankOptions || [];
        var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
        var opt = bankOptions[safeIdx];
        if (!opt)
            return;
        this.patchData({
            recordsBankIndex: safeIdx,
            recordsBankId: opt.value,
            recordsBankLabel: opt.label,
            recordsPage: 1
        }, function () {
            if (_this.data.tab === 'records')
                _this.loadExamRecords(true);
            if (_this.data.tab === 'data')
                _this.loadExamStats(true);
        });
    },
    onRecordsSizePicker: function (e) {
        var _this = this;
        var _a;
        var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
        var options = this.data.recordsSizeOptions || [];
        var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(options.length - 1, idx)) : 0;
        var opt = options[safeIdx];
        if (!opt)
            return;
        this.patchData({ recordsSizeIndex: safeIdx, recordsSize: opt.value, recordsSizeLabel: opt.label, recordsPage: 1 }, function () { return _this.loadExamRecords(true); });
    },
    onRecordsPrevPage: function () {
        var _this = this;
        if (this.data.recordsLoading)
            return;
        var p = (0, index_v2_helpers_1.clampInt)(this.data.recordsPage, 1, 1, 9999);
        if (p <= 1)
            return;
        this.patchData({ recordsPage: p - 1 }, function () { return _this.loadExamRecords(false); });
    },
    onRecordsNextPage: function () {
        var _this = this;
        if (this.data.recordsLoading)
            return;
        var p = (0, index_v2_helpers_1.clampInt)(this.data.recordsPage, 1, 1, 9999);
        var totalPages = (0, index_v2_helpers_1.clampInt)(this.data.recordsTotalPages, 1, 1, 9999);
        if (p >= totalPages)
            return;
        this.patchData({ recordsPage: p + 1 }, function () { return _this.loadExamRecords(false); });
    },
    loadExamRecords: function () {
        return __awaiter(this, arguments, void 0, function (resetPage) {
            var page, size, params, res, ongoing, submitted, total, page_1, size_1, totalPages, e_2;
            if (resetPage === void 0) { resetPage = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.recordsLoading)
                            return [2 /*return*/];
                        page = resetPage ? 1 : (0, index_v2_helpers_1.clampInt)(this.data.recordsPage, 1, 1, 9999);
                        size = (0, index_v2_helpers_1.clampInt)(this.data.recordsSize, 10, 5, 50);
                        if (resetPage && this.data.recordsPage !== 1)
                            this.patchData({ recordsPage: 1 }, undefined, true);
                        this.patchData({ recordsLoading: true });
                        this.setRecordsMsg('', '');
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        params = {
                            source: this.data.recordsSource || 'all',
                            page: page_1,
                            size: size_1
                        };
                        if (this.data.recordsSource !== 'user_bank' && this.data.recordsSubject && this.data.recordsSubject !== 'all') {
                            params.subject = this.data.recordsSubject;
                        }
                        if (this.data.recordsSource !== 'public' && Number(this.data.recordsBankId || 0) > 0) {
                            params.bank_id = Number(this.data.recordsBankId);
                        }
                        return [4 /*yield*/, api_1.api.getExamRecords(params)];
                    case 2:
                        res = _a.sent();
                        ongoing = Array.isArray(res === null || res === void 0 ? void 0 : res.ongoing) ? res.ongoing : [];
                        submitted = Array.isArray(res === null || res === void 0 ? void 0 : res.submitted) ? res.submitted : [];
                        total = Number((res === null || res === void 0 ? void 0 : res.total) || 0) || 0;
                        page_1 = (0, index_v2_helpers_1.clampInt)(res === null || res === void 0 ? void 0 : res.page, params.page, 1, 9999);
                        size_1 = (0, index_v2_helpers_1.clampInt)(res === null || res === void 0 ? void 0 : res.size, params.size, 5, 50);
                        totalPages = Math.max(1, Math.ceil(total / Math.max(1, size_1)));
                        this.patchData({
                            recordsOngoing: ongoing,
                            recordsSubmitted: submitted,
                            recordsTotal: total,
                            recordsPage: (0, index_v2_helpers_1.clampInt)(page_1, 1, 1, totalPages),
                            recordsSize: size_1,
                            recordsTotalPages: totalPages,
                            recordsLoading: false
                        });
                        this.syncRecordsFilters();
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        this.patchData({
                            recordsOngoing: [],
                            recordsSubmitted: [],
                            recordsTotal: 0,
                            recordsTotalPages: 1,
                            recordsLoading: false
                        });
                        this.syncRecordsFilters();
                        this.setRecordsMsg((e_2 && e_2.message) || '获取考试记录失败', 'error');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onExamContinueTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(id) });
    },
    onExamDetailTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(id) });
    },
    onExamToMistakesTap: function (e) {
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        wx.showLoading({ title: '处理中…' });
        api_1.api
            .examToMistakes(id)
            .then(function (res) {
            wx.hideLoading();
            var cnt = Number((res === null || res === void 0 ? void 0 : res.count) || 0) || 0;
            wx.showToast({ title: cnt ? "\u5DF2\u52A0\u5165 ".concat(cnt, " \u9898") : '已加入错题本', icon: 'none' });
        })
            .catch(function (err) {
            wx.hideLoading();
            wx.showToast({ title: (err && err.message) || '操作失败', icon: 'none' });
        });
    },
    onExamDeleteTap: function (e) {
        var _this = this;
        var _a, _b;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        if (!Number.isFinite(id) || id <= 0)
            return;
        wx.showModal({
            title: '删除考试',
            content: "\u786E\u5B9A\u5220\u9664\u8003\u8BD5 #".concat(id, " \u5417\uFF1F"),
            confirmText: '删除',
            confirmColor: '#FF3B30',
            success: function (res) { return __awaiter(_this, void 0, void 0, function () {
                var err_1;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (!res.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '删除中…' });
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.deleteExam(id)];
                        case 2:
                            _a.sent();
                            wx.hideLoading();
                            wx.showToast({ title: '已删除', icon: 'success' });
                            this.loadExamRecords(true);
                            return [3 /*break*/, 4];
                        case 3:
                            err_1 = _a.sent();
                            wx.hideLoading();
                            wx.showToast({ title: (err_1 && err_1.message) || '删除失败', icon: 'none' });
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    // === data（考试数据）===
    setStatsMsg: function (text, kind) {
        if (kind === void 0) { kind = ''; }
        this.patchData({ statsMsg: String(text || ''), statsMsgKind: kind });
    },
    loadExamStats: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var params, bankId, statsScopeText, filterKey, res, statsOverview, recentExams, typeDist, statsAdvice, e_3;
            var _this = this;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.statsLoading)
                            return [2 /*return*/];
                        params = { source: this.data.recordsSource || 'all' };
                        if (params.source !== 'user_bank' && this.data.recordsSubject && this.data.recordsSubject !== 'all') {
                            params.subject = this.data.recordsSubject;
                        }
                        bankId = Number(this.data.recordsBankId || 0) || 0;
                        if (params.source !== 'public' && bankId > 0) {
                            params.bank_id = bankId;
                        }
                        statsScopeText = (function () {
                            var src = String(params.source || 'all');
                            var srcLabel = src === 'public' ? '公共题库' : src === 'user_bank' ? '个人题库' : '全部';
                            var subjectLabel = String(_this.data.recordsSubjectLabel || '全部科目');
                            var bankLabel = String(_this.data.recordsBankLabel || '全部题库');
                            if (src === 'public')
                                return "".concat(srcLabel, " \u00B7 ").concat(subjectLabel);
                            if (src === 'user_bank')
                                return "".concat(srcLabel, " \u00B7 ").concat(bankLabel);
                            return "".concat(srcLabel, " \u00B7 ").concat(subjectLabel, " \u00B7 ").concat(bankLabel);
                        })();
                        filterKey = JSON.stringify(params);
                        if (this.data.statsLoaded && !force && this.data.statsFilterKey === filterKey)
                            return [2 /*return*/];
                        this.patchData({ statsLoading: true });
                        this.setStatsMsg('', '');
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getExamStats(params)];
                    case 2:
                        res = _a.sent();
                        statsOverview = (res === null || res === void 0 ? void 0 : res.stats_overview) || {};
                        recentExams = Array.isArray(res === null || res === void 0 ? void 0 : res.recent_exams) ? res.recent_exams : [];
                        typeDist = Array.isArray(res === null || res === void 0 ? void 0 : res.type_dist) ? res.type_dist : [];
                        statsAdvice = Array.isArray(res === null || res === void 0 ? void 0 : res.advice)
                            ? res.advice
                                .map(function (a) { return ({ title: String((a === null || a === void 0 ? void 0 : a.title) || '').trim(), content: String((a === null || a === void 0 ? void 0 : a.content) || '').trim() }); })
                                .filter(function (a) { return a.title && a.content; })
                            : [];
                        this.patchData({
                            statsOverview: statsOverview,
                            recentExams: recentExams,
                            typeDist: typeDist,
                            statsFilterKey: filterKey,
                            statsScopeText: statsScopeText,
                            statsAdvice: statsAdvice,
                            statsLoaded: true,
                            statsLoading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_3 = _a.sent();
                        this.patchData({
                            statsOverview: {
                                submitted_count: 0,
                                avg_score: 0,
                                avg_accuracy: 0,
                                last7_count: 0,
                                last7_avg_accuracy: 0
                            },
                            recentExams: [],
                            typeDist: [],
                            statsFilterKey: filterKey,
                            statsScopeText: statsScopeText,
                            statsAdvice: [],
                            statsLoaded: true,
                            statsLoading: false
                        });
                        this.setStatsMsg((e_3 && e_3.message) || '获取考试数据失败', 'error');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    getExamScope: function () {
        return {
            source: this.data.examSource,
            subject: this.data.examSubject || 'all',
            bank_id: this.data.examBankId
        };
    },
    getTplScope: function () {
        return {
            source: this.data.tplSource,
            subject: this.data.tplSubject || 'all',
            bank_id: this.data.tplBankId
        };
    },
    getQTypesForScope: function (scope) {
        return __awaiter(this, void 0, void 0, function () {
            var key_1, res, arr, qTypes, e_4, key, info, arr, qTypes, e_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!(scope.source === 'user_bank')) return [3 /*break*/, 4];
                        if (!scope.bank_id)
                            return [2 /*return*/, []];
                        key_1 = "bank:".concat(scope.bank_id);
                        if (index_v2_helpers_1.qTypesCache.has(key_1))
                            return [2 /*return*/, (index_v2_helpers_1.qTypesCache.get(key_1) || []).slice()];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankDetail(scope.bank_id)];
                    case 2:
                        res = _a.sent();
                        arr = Array.isArray(res === null || res === void 0 ? void 0 : res.available_types) ? res.available_types : [];
                        qTypes = arr.filter(function (x) { return typeof x === 'string' && x.trim(); }).map(function (s) { return String(s).trim(); });
                        index_v2_helpers_1.qTypesCache.set(key_1, qTypes);
                        return [2 /*return*/, qTypes.slice()];
                    case 3:
                        e_4 = _a.sent();
                        index_v2_helpers_1.qTypesCache.set(key_1, []);
                        return [2 /*return*/, []];
                    case 4:
                        if (!scope.subject || scope.subject === 'all') {
                            return [2 /*return*/, index_v2_helpers_1.FALLBACK_PUBLIC_Q_TYPES.slice()];
                        }
                        key = "subject:".concat(scope.subject);
                        if (index_v2_helpers_1.qTypesCache.has(key))
                            return [2 /*return*/, (index_v2_helpers_1.qTypesCache.get(key) || []).slice()];
                        _a.label = 5;
                    case 5:
                        _a.trys.push([5, 7, , 8]);
                        return [4 /*yield*/, api_1.api.getSubjectInfo(scope.subject)];
                    case 6:
                        info = _a.sent();
                        arr = Array.isArray(info === null || info === void 0 ? void 0 : info.available_types) ? info.available_types : [];
                        qTypes = arr.filter(function (x) { return typeof x === 'string' && x.trim(); }).map(function (s) { return String(s).trim(); });
                        index_v2_helpers_1.qTypesCache.set(key, qTypes);
                        return [2 /*return*/, qTypes.slice()];
                    case 7:
                        e_5 = _a.sent();
                        index_v2_helpers_1.qTypesCache.set(key, []);
                        return [2 /*return*/, []];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    reloadExamTypes: function (opts) {
        return __awaiter(this, void 0, void 0, function () {
            var scope, qTypes, counts, prevMap_1, rows, cfg_1, e_6;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.examLoading)
                            return [2 /*return*/];
                        this.patchData({ examLoading: true, examMsg: '', examMsgKind: '' });
                        scope = this.getExamScope();
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.getQTypesForScope(scope)];
                    case 2:
                        qTypes = (_a.sent()).filter(Boolean);
                        if (!qTypes.length) {
                            this.patchData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, Promise.all(qTypes.map(function (t) { return __awaiter(_this, void 0, void 0, function () {
                                var bankId, res_1, res, e_7;
                                return __generator(this, function (_a) {
                                    switch (_a.label) {
                                        case 0:
                                            _a.trys.push([0, 4, , 5]);
                                            if (!(scope.source === 'user_bank')) return [3 /*break*/, 2];
                                            bankId = scope.bank_id || 0;
                                            return [4 /*yield*/, api_1.api.getBankUserCounts(bankId, { q_type: t, source: 'all' })];
                                        case 1:
                                            res_1 = _a.sent();
                                            return [2 /*return*/, { name: t, available: (0, index_v2_helpers_1.clampInt)(res_1 === null || res_1 === void 0 ? void 0 : res_1.total, 0, 0, 999999) }];
                                        case 2: return [4 /*yield*/, api_1.api.getQuestionsCount({ subject: scope.subject || 'all', type: t })];
                                        case 3:
                                            res = _a.sent();
                                            return [2 /*return*/, { name: t, available: (0, index_v2_helpers_1.clampInt)(res === null || res === void 0 ? void 0 : res.count, 0, 0, 999999) }];
                                        case 4:
                                            e_7 = _a.sent();
                                            return [2 /*return*/, { name: t, available: 0 }];
                                        case 5: return [2 /*return*/];
                                    }
                                });
                            }); }))];
                    case 3:
                        counts = _a.sent();
                        prevMap_1 = new Map();
                        (this.data.examTypes || []).forEach(function (r) { return prevMap_1.set(r.name, r); });
                        rows = counts
                            .filter(function (x) { return x.available > 0; })
                            .map(function (x) {
                            var prev = prevMap_1.get(x.name);
                            var enabled = prev ? !!prev.enabled : false;
                            var score = prev ? (0, index_v2_helpers_1.clampFloat)(prev.score, 1, 0, 1000) : 1;
                            var count = enabled ? (0, index_v2_helpers_1.clampInt)(prev === null || prev === void 0 ? void 0 : prev.count, 0, 0, x.available) : 0;
                            return { name: x.name, enabled: enabled, available: x.available, count: count, score: score, subtotalText: '0' };
                        });
                        if (opts === null || opts === void 0 ? void 0 : opts.applyConfig) {
                            examPresetApplied = true;
                            cfg_1 = opts.applyConfig;
                            rows = rows.map(function (r) {
                                var want = cfg_1.types && cfg_1.types[r.name] != null ? Number(cfg_1.types[r.name]) : 0;
                                var enabled = want > 0;
                                var count = enabled ? (0, index_v2_helpers_1.clampInt)(want, 0, 0, r.available) : 0;
                                var scoreRaw = cfg_1.scores && cfg_1.scores[r.name] != null ? Number(cfg_1.scores[r.name]) : 1;
                                var score = enabled ? (0, index_v2_helpers_1.clampFloat)(scoreRaw, 1, 0, 1000) : 1;
                                return __assign(__assign({}, r), { enabled: enabled, count: count, score: score });
                            });
                        }
                        rows = this.applyDefaultPresetIfEmpty(rows);
                        rows = this.recomputeTypeSubtotals(rows);
                        this.patchData({ examTypes: rows, examLoading: false }, function () { return _this.refreshExamSummary(); });
                        return [3 /*break*/, 5];
                    case 4:
                        e_6 = _a.sent();
                        this.patchData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    recomputeTypeSubtotals: function (rows) {
        return (rows || []).map(function (r) {
            var subtotal = r.enabled ? (Number(r.count) || 0) * (Number(r.score) || 0) : 0;
            return __assign(__assign({}, r), { subtotalText: (0, index_v2_helpers_1.formatNum)(subtotal) });
        });
    },
    applyDefaultPresetIfEmpty: function (rows) {
        var assigned = (rows || []).reduce(function (sum, r) { return sum + (r.enabled ? Math.max(0, Number(r.count) || 0) : 0); }, 0);
        if (assigned > 0)
            return rows;
        if (examPresetApplied)
            return rows;
        examPresetApplied = true;
        var qTypes = rows.map(function (r) { return r.name; });
        var picked = index_v2_helpers_1.DEFAULT_PICKED_TYPES.filter(function (t) { return qTypes.includes(t); });
        var fallbackPicked = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));
        var enabledTypes = rows
            .filter(function (r) { return fallbackPicked.includes(r.name); })
            .map(function (r) { return ({ name: r.name, available: r.available }); });
        var distributed = (0, index_v2_helpers_1.distributeCounts)(this.data.examTargetTotal, enabledTypes);
        return rows.map(function (r) {
            var enabled = fallbackPicked.includes(r.name);
            var count = enabled ? (0, index_v2_helpers_1.clampInt)(distributed[r.name] || 0, 0, 0, r.available) : 0;
            return __assign(__assign({}, r), { enabled: enabled, count: count, score: 1 });
        });
    },
    refreshExamSummary: function () {
        var scope = this.getExamScope();
        var rows = this.data.examTypes || [];
        var types = {};
        var scores = {};
        var assigned = 0;
        var totalScore = 0;
        rows.forEach(function (r) {
            if (!r.enabled)
                return;
            var count = (0, index_v2_helpers_1.clampInt)(r.count, 0, 0, 500);
            var score = (0, index_v2_helpers_1.clampFloat)(r.score, 1, 0, 1000);
            if (count <= 0)
                return;
            types[r.name] = count;
            scores[r.name] = score;
            assigned += count;
            totalScore += count * score;
        });
        var scopeLabel = scope.source === 'user_bank'
            ? "\u4E2A\u4EBA\u9898\u5E93 \u00B7 ".concat(this.data.examBankLabel || '未选择')
            : "\u516C\u5171\u9898\u5E93 \u00B7 ".concat(scope.subject === 'all' ? '全部科目' : scope.subject);
        var examSumTypes = Object.keys(types).map(function (name) {
            var _a;
            var count = types[name] || 0;
            var score = (_a = scores[name]) !== null && _a !== void 0 ? _a : 1;
            return { name: name, meta: "".concat(count, " \u00D7 ").concat((0, index_v2_helpers_1.formatNum)(score)), subtotal: (0, index_v2_helpers_1.formatNum)(count * score) };
        });
        var startDisabled = assigned <= 0 || (scope.source === 'user_bank' && !scope.bank_id);
        this.setData({
            examSumScope: scopeLabel,
            examSumDuration: "".concat((0, index_v2_helpers_1.clampInt)(this.data.examDuration, 60, 1, 1440), " \u5206\u949F"),
            examSumAssigned: "".concat(assigned, " \u9898"),
            examSumScore: "".concat((0, index_v2_helpers_1.formatNum)(totalScore), " \u5206"),
            examSumTypes: examSumTypes,
            examStartDisabled: startDisabled
        });
    },
    // === 新建考试：范围 ===
    onExamSourceTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var source, next, bankOptions;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        source = (((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.source) || '').toLowerCase();
                        if (source !== 'public' && source !== 'user_bank')
                            return [2 /*return*/];
                        if (source === this.data.examSource)
                            return [2 /*return*/];
                        next = { examSource: source, examMsg: '', examMsgKind: '' };
                        if (source === 'user_bank') {
                            bankOptions = this.data.bankOptions || [];
                            if (!this.data.examBankId && bankOptions.length) {
                                next.examBankId = bankOptions[0].value;
                                next.examBankIndex = 0;
                                next.examBankLabel = bankOptions[0].label;
                            }
                        }
                        return [4 /*yield*/, (0, index_v2_helpers_1.setDataAsync)(this, next)];
                    case 1:
                        _c.sent();
                        return [4 /*yield*/, this.reloadExamTypes()];
                    case 2:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onExamSubjectPicker: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var idx, subjectOptions, safeIdx, opt;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
                        subjectOptions = this.data.subjectOptions || [];
                        safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
                        opt = subjectOptions[safeIdx];
                        if (!opt)
                            return [2 /*return*/];
                        return [4 /*yield*/, (0, index_v2_helpers_1.setDataAsync)(this, {
                                examSubjectIndex: safeIdx,
                                examSubject: opt.value,
                                examSubjectLabel: opt.label,
                                examMsg: '',
                                examMsgKind: ''
                            })];
                    case 1:
                        _b.sent();
                        return [4 /*yield*/, this.reloadExamTypes()];
                    case 2:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onExamBankPicker: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var idx, bankOptions, safeIdx, opt;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
                        bankOptions = this.data.bankOptions || [];
                        safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
                        opt = bankOptions[safeIdx];
                        if (!opt)
                            return [2 /*return*/];
                        return [4 /*yield*/, (0, index_v2_helpers_1.setDataAsync)(this, {
                                examBankIndex: safeIdx,
                                examBankId: opt.value,
                                examBankLabel: opt.label,
                                examMsg: '',
                                examMsgKind: ''
                            })];
                    case 1:
                        _b.sent();
                        return [4 /*yield*/, this.reloadExamTypes()];
                    case 2:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onExamDurationInput: function (e) {
        var _this = this;
        var _a;
        var duration = (0, index_v2_helpers_1.clampInt)((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 60, 1, 1440);
        this.setData({ examDuration: duration }, function () { return _this.refreshExamSummary(); });
    },
    onExamTargetTotalInput: function (e) {
        var _this = this;
        var _a;
        var total = (0, index_v2_helpers_1.clampInt)((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 30, 1, 300);
        this.setData({ examTargetTotal: total }, function () { return _this.refreshExamSummary(); });
    },
    // === 新建考试：题型与分值 ===
    onTypeToggleTap: function (e) {
        var _this = this;
        var _a, _b;
        var name = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.name;
        if (!name)
            return;
        var next = (this.data.examTypes || []).map(function (r) {
            if (r.name !== name)
                return r;
            var enabled = !r.enabled;
            return __assign(__assign({}, r), { enabled: enabled, count: enabled ? r.count : 0 });
        });
        this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () {
            return _this.refreshExamSummary();
        });
    },
    onTypeCountInput: function (e) {
        var _this = this;
        var _a, _b;
        var name = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.name;
        if (!name)
            return;
        var next = (this.data.examTypes || []).map(function (r) {
            var _a;
            if (r.name !== name)
                return r;
            var count = (0, index_v2_helpers_1.clampInt)((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 0, 0, r.available);
            return __assign(__assign({}, r), { count: count });
        });
        this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () {
            return _this.refreshExamSummary();
        });
    },
    onTypeScoreInput: function (e) {
        var _this = this;
        var _a, _b;
        var name = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.name;
        if (!name)
            return;
        var next = (this.data.examTypes || []).map(function (r) {
            var _a;
            if (r.name !== name)
                return r;
            var score = (0, index_v2_helpers_1.clampFloat)((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 1, 0, 1000);
            return __assign(__assign({}, r), { score: score });
        });
        this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () {
            return _this.refreshExamSummary();
        });
    },
    onQuickPresetTap: function (e) {
        var _this = this;
        var _a, _b, _c, _d;
        var duration = (0, index_v2_helpers_1.clampInt)((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.duration, 60, 1, 1440);
        var total = (0, index_v2_helpers_1.clampInt)((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.total, 30, 1, 300);
        this.setData({ examDuration: duration, examTargetTotal: total }, function () {
            _this.onAutoDistributeTap();
            _this.refreshExamSummary();
        });
    },
    onAutoDistributeTap: function () {
        var _this = this;
        var enabledRows = (this.data.examTypes || []).filter(function (r) { return r.enabled; });
        if (!enabledRows.length) {
            this.setData({ examMsg: '请先勾选至少一种题型，再进行均分。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
            return;
        }
        var distributed = (0, index_v2_helpers_1.distributeCounts)(this.data.examTargetTotal, enabledRows.map(function (r) { return ({ name: r.name, available: r.available }); }));
        var next = (this.data.examTypes || []).map(function (r) {
            if (!r.enabled)
                return __assign(__assign({}, r), { count: 0 });
            return __assign(__assign({}, r), { count: (0, index_v2_helpers_1.clampInt)(distributed[r.name] || 0, 0, 0, r.available) });
        });
        this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () {
            return _this.refreshExamSummary();
        });
    },
    onResetScoresTap: function () {
        var _this = this;
        var next = (this.data.examTypes || []).map(function (r) { return (__assign(__assign({}, r), { score: 1 })); });
        this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () {
            return _this.refreshExamSummary();
        });
    },
    collectExamConfig: function () {
        var scope = this.getExamScope();
        if (scope.source === 'user_bank' && !scope.bank_id)
            return null;
        var duration = (0, index_v2_helpers_1.clampInt)(this.data.examDuration, 60, 1, 1440);
        var targetTotal = (0, index_v2_helpers_1.clampInt)(this.data.examTargetTotal, 30, 1, 300);
        var types = {};
        var scores = {};
        var assigned = 0;
        var totalScore = 0;
        (this.data.examTypes || []).forEach(function (r) {
            if (!r.enabled)
                return;
            var count = (0, index_v2_helpers_1.clampInt)(r.count, 0, 0, 500);
            var score = (0, index_v2_helpers_1.clampFloat)(r.score, 1, 0, 1000);
            if (count <= 0)
                return;
            types[r.name] = count;
            scores[r.name] = score;
            assigned += count;
            totalScore += count * score;
        });
        return __assign(__assign({}, scope), { duration: duration, targetTotal: targetTotal, types: types, scores: scores, assigned: assigned, totalScore: totalScore });
    },
    onStartExamTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var cfg, res, examId, e_8;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.examCreating || this.data.examLoading)
                            return [2 /*return*/];
                        cfg = this.collectExamConfig();
                        if (!cfg) {
                            this.setData({ examMsg: '请选择个人题库。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
                            return [2 /*return*/];
                        }
                        if (!Object.keys(cfg.types).length) {
                            this.setData({ examMsg: '请先设置题型与题量。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
                            return [2 /*return*/];
                        }
                        this.setData({ examCreating: true, examMsg: '', examMsgKind: '' });
                        wx.showLoading({ title: '创建中…' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createExam({
                                source: cfg.source,
                                subject: cfg.subject,
                                bank_id: cfg.bank_id,
                                duration: cfg.duration,
                                types: cfg.types,
                                scores: cfg.scores
                            })];
                    case 2:
                        res = _a.sent();
                        examId = Number(res === null || res === void 0 ? void 0 : res.exam_id);
                        if (!Number.isFinite(examId) || examId <= 0)
                            throw new Error('创建考试失败');
                        wx.hideLoading();
                        this.setData({ examCreating: false });
                        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                        return [3 /*break*/, 4];
                    case 3:
                        e_8 = _a.sent();
                        wx.hideLoading();
                        this.setData({ examCreating: false, examMsg: (e_8 && e_8.message) || '创建失败', examMsgKind: 'error' }, function () {
                            return _this.refreshExamSummary();
                        });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onOpenSaveTemplate: function () {
        var _this = this;
        var cfg = this.collectExamConfig();
        if (!cfg) {
            this.setData({ examMsg: '请选择个人题库。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
            return;
        }
        if (!Object.keys(cfg.types).length) {
            this.setData({ examMsg: '请先设置题型与题量。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
            return;
        }
        var title = "\u81EA\u5B9A\u4E49\u6A21\u677F ".concat((0, index_v2_helpers_1.todayStamp)());
        this.setData({ saveModalOpen: true, saveTemplateTitle: title });
    },
    onCloseSaveModal: function () {
        if (this.data.savingTemplate)
            return;
        this.setData({ saveModalOpen: false, saveTemplateTitle: '' });
    },
    onSaveTemplateTitleInput: function (e) {
        var v = e && e.detail && e.detail.value ? String(e.detail.value) : '';
        this.setData({ saveTemplateTitle: v });
    },
    onConfirmSaveTemplate: function () {
        return __awaiter(this, void 0, void 0, function () {
            var title, cfg, e_9;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.savingTemplate)
                            return [2 /*return*/];
                        title = String(this.data.saveTemplateTitle || '').trim();
                        if (!title) {
                            wx.showToast({ title: '模板名称不能为空', icon: 'none' });
                            return [2 /*return*/];
                        }
                        cfg = this.collectExamConfig();
                        if (!cfg) {
                            wx.showToast({ title: '请选择个人题库', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (!Object.keys(cfg.types).length) {
                            wx.showToast({ title: '请先设置题型与题量', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ savingTemplate: true });
                        wx.showLoading({ title: '保存中…' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createExamTemplate({
                                title: title,
                                config: {
                                    source: cfg.source,
                                    subject: cfg.subject,
                                    bank_id: cfg.bank_id,
                                    duration: cfg.duration,
                                    targetTotal: cfg.targetTotal,
                                    types: cfg.types,
                                    scores: cfg.scores
                                }
                            })];
                    case 2:
                        _a.sent();
                        wx.hideLoading();
                        this.setData({ savingTemplate: false, saveModalOpen: false, saveTemplateTitle: '' });
                        wx.showToast({ title: '已保存为模板', icon: 'success' });
                        this.loadUserTemplates(true);
                        return [3 /*break*/, 4];
                    case 3:
                        e_9 = _a.sent();
                        wx.hideLoading();
                        this.setData({ savingTemplate: false });
                        wx.showToast({ title: (e_9 && e_9.message) || '保存失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // === 模板：范围 ===
    onTplSourceTap: function (e) {
        var _a, _b;
        var source = (((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.source) || '').toLowerCase();
        if (source !== 'public' && source !== 'user_bank')
            return;
        if (source === this.data.tplSource)
            return;
        var next = { tplSource: source };
        if (source === 'user_bank') {
            var bankOptions = this.data.bankOptions || [];
            if (!this.data.tplBankId && bankOptions.length) {
                next.tplBankId = bankOptions[0].value;
                next.tplBankIndex = 0;
                next.tplBankLabel = bankOptions[0].label;
            }
        }
        this.setData(next);
    },
    onTplSubjectPicker: function (e) {
        var _a;
        var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
        var subjectOptions = this.data.subjectOptions || [];
        var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(subjectOptions.length - 1, idx)) : 0;
        var opt = subjectOptions[safeIdx];
        if (!opt)
            return;
        this.setData({ tplSubjectIndex: safeIdx, tplSubject: opt.value, tplSubjectLabel: opt.label });
    },
    onTplBankPicker: function (e) {
        var _a;
        var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
        var bankOptions = this.data.bankOptions || [];
        var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(bankOptions.length - 1, idx)) : 0;
        var opt = bankOptions[safeIdx];
        if (!opt)
            return;
        this.setData({ tplBankIndex: safeIdx, tplBankId: opt.value, tplBankLabel: opt.label });
    },
    setTemplateMsg: function (text, kind) {
        if (kind === void 0) { kind = ''; }
        this.setData({ templateMsg: String(text || ''), templateMsgKind: kind });
    },
    loadUserTemplates: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var list, bankOptions_1, userTemplateConfigById_1, userTemplateCards_1, e_10;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.templatesLoading)
                            return [2 /*return*/];
                        if (this.data.userTemplatesLoaded && !force)
                            return [2 /*return*/];
                        this.setData({ templatesLoading: true });
                        this.setTemplateMsg('', '');
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getExamTemplates()];
                    case 2:
                        list = (_a.sent());
                        bankOptions_1 = this.data.bankOptions || [];
                        userTemplateConfigById_1 = {};
                        userTemplateCards_1 = [];
                        (Array.isArray(list) ? list : []).forEach(function (tpl) {
                            var cfg = (0, index_v2_helpers_1.normalizeTemplateConfig)((tpl === null || tpl === void 0 ? void 0 : tpl.config) || {});
                            if (!cfg)
                                return;
                            var bankLabel = cfg.bank_id ? (0, index_v2_helpers_1.findOptionLabel)(bankOptions_1, cfg.bank_id, '') : '';
                            var scopeLabel = (0, index_v2_helpers_1.buildTemplateScopeLabel)(cfg, bankLabel);
                            userTemplateConfigById_1[String(tpl.id)] = __assign(__assign({}, cfg), { label: tpl.title || '自定义模板' });
                            userTemplateCards_1.push({
                                id: tpl.id,
                                title: tpl.title || '未命名模板',
                                meta: "".concat(cfg.duration, " \u5206\u949F \u00B7 ").concat(cfg.targetTotal, " \u9898 \u00B7 ").concat(scopeLabel),
                                tags: ['我的模板']
                            });
                        });
                        this.setData({
                            userTemplateCards: userTemplateCards_1,
                            userTemplateConfigById: userTemplateConfigById_1,
                            userTemplatesLoaded: true,
                            templatesLoading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_10 = _a.sent();
                        this.setData({
                            userTemplateCards: [],
                            userTemplateConfigById: {},
                            userTemplatesLoaded: true,
                            templatesLoading: false
                        });
                        this.setTemplateMsg((e_10 && e_10.message) || '获取模板失败。', 'error');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    applyConfigToNew: function (cfg) {
        return __awaiter(this, void 0, void 0, function () {
            var subjectOptions, bankOptions, examSubject, exists, examBankId, exists, examSubjectIndex, examBankIndex, patch;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!cfg)
                            return [2 /*return*/];
                        if (cfg.source === 'user_bank' && !cfg.bank_id) {
                            this.setTemplateMsg('请选择个人题库。', 'error');
                            return [2 /*return*/];
                        }
                        subjectOptions = this.data.subjectOptions || [];
                        bankOptions = this.data.bankOptions || [];
                        examSubject = cfg.subject || 'all';
                        if (cfg.source === 'public') {
                            exists = subjectOptions.some(function (o) { return o.value === examSubject; });
                            if (!exists)
                                examSubject = 'all';
                        }
                        examBankId = cfg.source === 'user_bank' ? cfg.bank_id : this.data.examBankId;
                        if (cfg.source === 'user_bank') {
                            exists = examBankId != null && bankOptions.some(function (o) { return o.value === examBankId; });
                            if (!exists) {
                                this.setTemplateMsg('题库不可用，请先同步/加入该题库。', 'error');
                                return [2 /*return*/];
                            }
                        }
                        examSubjectIndex = Math.max(0, subjectOptions.findIndex(function (o) { return o.value === examSubject; }));
                        examBankIndex = examBankId != null ? Math.max(0, bankOptions.findIndex(function (o) { return o.value === examBankId; })) : 0;
                        patch = {
                            tab: 'new',
                            examSource: cfg.source,
                            examSubject: examSubject,
                            examSubjectIndex: examSubjectIndex,
                            examSubjectLabel: (0, index_v2_helpers_1.findOptionLabel)(subjectOptions, examSubject, '全部科目'),
                            examBankId: examBankId,
                            examBankIndex: examBankIndex,
                            examBankLabel: examBankId != null ? (0, index_v2_helpers_1.findOptionLabel)(bankOptions, examBankId, '请选择题库') : '请选择题库',
                            examDuration: (0, index_v2_helpers_1.clampInt)(cfg.duration, 60, 1, 1440),
                            examTargetTotal: (0, index_v2_helpers_1.clampInt)(cfg.targetTotal, 30, 1, 300),
                            examMsg: '',
                            examMsgKind: ''
                        };
                        examPresetApplied = true;
                        return [4 /*yield*/, (0, index_v2_helpers_1.setDataAsync)(this, patch)];
                    case 1:
                        _a.sent();
                        return [4 /*yield*/, this.reloadExamTypes({ applyConfig: cfg })];
                    case 2:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    startExamWithConfig: function (cfg) {
        return __awaiter(this, void 0, void 0, function () {
            var res, examId, e_11;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!cfg)
                            return [2 /*return*/];
                        if (cfg.source === 'user_bank' && !cfg.bank_id) {
                            this.setTemplateMsg('请选择个人题库。', 'error');
                            return [2 /*return*/];
                        }
                        if (!cfg.types || !Object.keys(cfg.types).length) {
                            this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
                            return [2 /*return*/];
                        }
                        wx.showLoading({ title: '创建中…' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createExam({
                                source: cfg.source,
                                subject: cfg.subject,
                                bank_id: cfg.bank_id,
                                duration: cfg.duration,
                                types: cfg.types,
                                scores: cfg.scores
                            })];
                    case 2:
                        res = _a.sent();
                        examId = Number(res === null || res === void 0 ? void 0 : res.exam_id);
                        if (!Number.isFinite(examId) || examId <= 0)
                            throw new Error('创建考试失败');
                        wx.hideLoading();
                        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                        return [3 /*break*/, 4];
                    case 3:
                        e_11 = _a.sent();
                        wx.hideLoading();
                        this.setTemplateMsg((e_11 && e_11.message) || '创建考试失败，请稍后再试。', 'error');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    buildSystemTemplateConfig: function (tpl) {
        return __awaiter(this, void 0, void 0, function () {
            var scope, qTypes, preferred, picked, selected, total, base, rem, types, scores;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        scope = this.getTplScope();
                        return [4 /*yield*/, this.getQTypesForScope(scope)];
                    case 1:
                        qTypes = (_a.sent()).filter(Boolean);
                        if (!qTypes.length)
                            return [2 /*return*/, null];
                        preferred = Array.isArray(tpl.preferred) ? tpl.preferred : [];
                        picked = preferred.filter(function (t) { return qTypes.includes(t); });
                        selected = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));
                        total = (0, index_v2_helpers_1.clampInt)(tpl.total, 30, 1, 300);
                        base = Math.floor(total / selected.length);
                        rem = total % selected.length;
                        types = {};
                        scores = {};
                        selected.forEach(function (t) {
                            var count = base + (rem > 0 ? 1 : 0);
                            if (rem > 0)
                                rem -= 1;
                            types[t] = count;
                            scores[t] = 1;
                        });
                        return [2 /*return*/, {
                                source: scope.source,
                                subject: scope.subject,
                                bank_id: scope.bank_id,
                                duration: (0, index_v2_helpers_1.clampInt)(tpl.duration, 45, 1, 1440),
                                targetTotal: total,
                                types: types,
                                scores: scores,
                                label: tpl.title
                            }];
                }
            });
        });
    },
    onSystemTemplateApplyTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id, tpl, cfg;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        id = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || '');
                        tpl = (this.data.systemTemplates || []).find(function (t) { return String(t.id) === id; });
                        if (!tpl)
                            return [2 /*return*/];
                        this.setTemplateMsg('', '');
                        return [4 /*yield*/, this.buildSystemTemplateConfig(tpl)];
                    case 1:
                        cfg = _c.sent();
                        if (!cfg) {
                            this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.applyConfigToNew(cfg)];
                    case 2:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onSystemTemplateStartTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id, tpl, cfg;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        id = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || '');
                        tpl = (this.data.systemTemplates || []).find(function (t) { return String(t.id) === id; });
                        if (!tpl)
                            return [2 /*return*/];
                        this.setTemplateMsg('', '');
                        return [4 /*yield*/, this.buildSystemTemplateConfig(tpl)];
                    case 1:
                        cfg = _c.sent();
                        if (!cfg) {
                            this.setTemplateMsg('当前范围暂无题型，请调整范围后重试。', 'error');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.startExamWithConfig(cfg)];
                    case 2:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onUserTemplateApplyTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id, cfg;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        id = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || '');
                        cfg = (this.data.userTemplateConfigById || {})[id];
                        if (!cfg)
                            return [2 /*return*/];
                        this.setTemplateMsg('', '');
                        return [4 /*yield*/, this.applyConfigToNew(cfg)];
                    case 1:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onUserTemplateStartTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id, cfg;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        id = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || '');
                        cfg = (this.data.userTemplateConfigById || {})[id];
                        if (!cfg)
                            return [2 /*return*/];
                        this.setTemplateMsg('', '');
                        return [4 /*yield*/, this.startExamWithConfig(cfg)];
                    case 1:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onUserTemplateDeleteTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id;
            var _this = this;
            var _a, _b;
            return __generator(this, function (_c) {
                id = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id);
                if (!Number.isFinite(id) || id <= 0)
                    return [2 /*return*/];
                wx.showModal({
                    title: '删除模板',
                    content: '确定要删除该模板吗？',
                    confirmText: '删除',
                    confirmColor: '#FF3B30',
                    success: function (res) { return __awaiter(_this, void 0, void 0, function () {
                        var e_12;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    if (!res.confirm)
                                        return [2 /*return*/];
                                    wx.showLoading({ title: '删除中…' });
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 3, , 4]);
                                    return [4 /*yield*/, api_1.api.deleteExamTemplate(id)];
                                case 2:
                                    _a.sent();
                                    wx.hideLoading();
                                    this.loadUserTemplates(true);
                                    return [3 /*break*/, 4];
                                case 3:
                                    e_12 = _a.sent();
                                    wx.hideLoading();
                                    this.setTemplateMsg((e_12 && e_12.message) || '删除模板失败。', 'error');
                                    return [3 /*break*/, 4];
                                case 4: return [2 /*return*/];
                            }
                        });
                    }); }
                });
                return [2 /*return*/];
            });
        });
    }
});
