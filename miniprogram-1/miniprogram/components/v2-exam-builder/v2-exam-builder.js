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
var QUICK_PRESETS = [
    { duration: 15, total: 20, label: '15min/20题' },
    { duration: 30, total: 30, label: '30min/30题' },
    { duration: 60, total: 50, label: '60min/50题' }
];
var FALLBACK_PUBLIC_Q_TYPES = ['单选题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
var DEFAULT_PICKED_TYPES = ['单选题', '多选题', '判断题'];
function todayStamp() {
    var now = new Date();
    var y = String(now.getFullYear());
    var m = String(now.getMonth() + 1).padStart(2, '0');
    var d = String(now.getDate()).padStart(2, '0');
    return "".concat(y, "-").concat(m, "-").concat(d);
}
function clampInt(v, fallback, minV, maxV) {
    var n = Math.floor(Number(v));
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(minV, Math.min(maxV, n));
}
function clampFloat(v, fallback, minV, maxV) {
    var n = Number(v);
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(minV, Math.min(maxV, n));
}
function formatNum(n) {
    var v = Number(n);
    if (!Number.isFinite(v))
        return '0';
    if (Math.abs(v - Math.round(v)) < 1e-6)
        return String(Math.round(v));
    return String(v.toFixed(2)).replace(/\.?0+$/, '');
}
function distributeCounts(targetTotal, enabledTypes) {
    var cfg = {};
    var n = enabledTypes.length;
    if (n <= 0)
        return cfg;
    var target = clampInt(targetTotal, 30, 1, 300);
    var base = Math.floor(target / n);
    var rem = target % n;
    enabledTypes.forEach(function (t) {
        var want = base + (rem > 0 ? 1 : 0);
        if (rem > 0)
            rem -= 1;
        cfg[t.name] = Math.min(want, Math.max(0, t.available));
    });
    var assignedTotal = Object.values(cfg).reduce(function (s, v) { return s + (Number(v) || 0); }, 0);
    var remaining = target - assignedTotal;
    var safety = 5000;
    while (remaining > 0 && safety-- > 0) {
        var progressed = false;
        for (var _i = 0, enabledTypes_1 = enabledTypes; _i < enabledTypes_1.length; _i++) {
            var t = enabledTypes_1[_i];
            if (remaining <= 0)
                break;
            var cap = Math.max(0, t.available) - (cfg[t.name] || 0);
            if (cap > 0) {
                cfg[t.name] = (cfg[t.name] || 0) + 1;
                remaining -= 1;
                progressed = true;
            }
        }
        if (!progressed)
            break;
    }
    assignedTotal = Object.values(cfg).reduce(function (s, v) { return s + (Number(v) || 0); }, 0);
    if (assignedTotal <= 0) {
        enabledTypes.forEach(function (t) {
            cfg[t.name] = Math.min(1, Math.max(0, t.available));
        });
    }
    return cfg;
}
function normalizeTemplateConfig(raw) {
    var _a, _b;
    if (!raw || typeof raw !== 'object')
        return null;
    var source = String(raw.source || 'public').toLowerCase() === 'user_bank' ? 'user_bank' : 'public';
    var subject = String(raw.subject || 'all').trim() || 'all';
    var bank_id = raw.bank_id != null && raw.bank_id !== '' ? Number(raw.bank_id) : null;
    var duration = clampInt(raw.duration, 60, 1, 1440);
    var typesRaw = raw.types && typeof raw.types === 'object' ? raw.types : {};
    var scoresRaw = raw.scores && typeof raw.scores === 'object' ? raw.scores : {};
    var types = {};
    var scores = {};
    Object.keys(typesRaw || {}).forEach(function (k) {
        var name = String(k || '').trim();
        if (!name)
            return;
        var c = clampInt(typesRaw[k], 0, 0, 500);
        if (c <= 0)
            return;
        types[name] = c;
        scores[name] = clampFloat(scoresRaw[k], 1, 0, 1000);
    });
    var targetTotal = (_b = (_a = raw.targetTotal) !== null && _a !== void 0 ? _a : raw.total) !== null && _b !== void 0 ? _b : raw.target_total;
    targetTotal = clampInt(targetTotal, 0, 0, 300);
    if (!targetTotal) {
        targetTotal = Object.values(types).reduce(function (sum, v) { return sum + (Number(v) || 0); }, 0);
        targetTotal = clampInt(targetTotal, 0, 0, 300);
    }
    return {
        source: source,
        subject: subject,
        bank_id: source === 'user_bank' ? (Number.isFinite(bank_id) ? bank_id : null) : null,
        duration: duration,
        targetTotal: targetTotal,
        types: types,
        scores: scores
    };
}
function buildTemplateMeta(cfg) {
    var duration = clampInt(cfg.duration, 60, 1, 1440);
    var total = clampInt(cfg.targetTotal, 0, 0, 300);
    return total ? "".concat(duration, " \u5206\u949F \u00B7 ").concat(total, " \u9898") : "".concat(duration, " \u5206\u949F");
}
function isSameScope(cfg, source, subject, bankId) {
    if (source === 'user_bank')
        return cfg.source === 'user_bank' && Number(cfg.bank_id || 0) === bankId;
    var s = subject || 'all';
    return cfg.source === 'public' && String(cfg.subject || 'all') === s;
}
Component({
    properties: {
        source: {
            type: String,
            value: 'public'
        },
        subject: {
            type: String,
            value: ''
        },
        bankId: {
            type: Number,
            value: 0
        },
        bankName: {
            type: String,
            value: ''
        }
    },
    data: {
        quickPresets: QUICK_PRESETS,
        scopeText: '',
        emptyText: '暂无题型数据',
        examDuration: 60,
        examTargetTotal: 30,
        examTypes: [],
        examLoading: false,
        examCreating: false,
        examMsg: '',
        examMsgKind: '',
        examSumScope: '',
        examSumDuration: '',
        examSumAssigned: '',
        examSumScore: '',
        examSumTypes: [],
        examStartDisabled: true,
        templatesLoading: false,
        templateOptions: [{ id: 0, label: '不使用模板' }],
        templateIndex: 0,
        templateLabel: '不使用模板',
        templateMeta: '',
        templateMsg: '',
        templateMsgKind: '',
        presetApplied: false,
        saveModalOpen: false,
        saveTemplateTitle: '',
        savingTemplate: false
    },
    lifetimes: {
        attached: function () {
            this.bootstrap();
        }
    },
    pageLifetimes: {
        show: function () {
            this.loadUserTemplates();
        }
    },
    observers: {
        'source,subject,bankId,bankName': function () {
            this.bootstrap();
        }
    },
    methods: {
        normalizeSource: function () {
            var raw = String(this.properties.source || '').trim().toLowerCase();
            return raw === 'user_bank' ? 'user_bank' : 'public';
        },
        buildScopeText: function () {
            var source = this.normalizeSource();
            if (source === 'user_bank') {
                var bankId = Number(this.properties.bankId || 0) || 0;
                var bankName = String(this.properties.bankName || '').trim() || (bankId > 0 ? "\u9898\u5E93#".concat(bankId) : '未选择题库');
                return "\u4E2A\u4EBA\u9898\u5E93 \u00B7 ".concat(bankName);
            }
            var subject = String(this.properties.subject || '').trim() || '全部科目';
            return "\u516C\u5171\u9898\u5E93 \u00B7 ".concat(subject);
        },
        bootstrap: function () {
            return __awaiter(this, void 0, void 0, function () {
                var scopeText, source, subject, bankId, emptyText;
                var _this = this;
                return __generator(this, function (_a) {
                    scopeText = this.buildScopeText();
                    source = this.normalizeSource();
                    subject = String(this.properties.subject || '').trim();
                    bankId = Number(this.properties.bankId || 0) || 0;
                    emptyText = '暂无题型数据';
                    if (source === 'user_bank' && bankId <= 0)
                        emptyText = '请先选择一个题库';
                    if (source === 'public' && !subject)
                        emptyText = '缺少科目参数';
                    this.setData({
                        scopeText: scopeText,
                        emptyText: emptyText,
                        presetApplied: false,
                        examMsg: '',
                        examMsgKind: '',
                        examTypes: [],
                        templatesLoading: false,
                        templateOptions: [{ id: 0, label: '不使用模板' }],
                        templateIndex: 0,
                        templateLabel: '不使用模板',
                        templateMeta: '',
                        templateMsg: '',
                        templateMsgKind: ''
                    }, function () {
                        _this.__tplCfgById = {};
                        _this.__tplMetaById = {};
                        _this.__lastTplLoadAt = 0;
                        _this.reloadExamTypes();
                        _this.loadUserTemplates(true);
                    });
                    return [2 /*return*/];
                });
            });
        },
        setTemplateMsg: function (text, kind) {
            if (kind === void 0) { kind = ''; }
            this.setData({ templateMsg: String(text || ''), templateMsgKind: kind });
        },
        onGoExamCenterTemplates: function () {
            var source = this.normalizeSource();
            var subject = String(this.properties.subject || '').trim() || 'all';
            var bankId = Number(this.properties.bankId || 0) || 0;
            var qs = ['tab=templates', "source=".concat(source)];
            if (source === 'public')
                qs.push("subject=".concat(encodeURIComponent(subject)));
            if (source === 'user_bank' && bankId > 0)
                qs.push("bank_id=".concat(bankId));
            wx.navigateTo({ url: "/pages/index-v2/index-v2?".concat(qs.join('&')) });
        },
        loadUserTemplates: function () {
            return __awaiter(this, arguments, void 0, function (force) {
                var rawSubject, source, subject, bankId, now, lastAt, res, list, options_1, cfgById_1, metaById_1, currentId_1, templateIndex, foundIdx, finalPicked, finalId, e_1;
                var _a;
                if (force === void 0) { force = false; }
                return __generator(this, function (_b) {
                    switch (_b.label) {
                        case 0:
                            rawSubject = String(this.properties.subject || '').trim();
                            source = this.normalizeSource();
                            subject = rawSubject || 'all';
                            bankId = Number(this.properties.bankId || 0) || 0;
                            if (source === 'public' && !rawSubject) {
                                this.__tplCfgById = {};
                                this.__tplMetaById = {};
                                this.setData({
                                    templatesLoading: false,
                                    templateOptions: [{ id: 0, label: '不使用模板' }],
                                    templateIndex: 0,
                                    templateLabel: '不使用模板',
                                    templateMeta: ''
                                });
                                return [2 /*return*/];
                            }
                            if (source === 'user_bank' && bankId <= 0) {
                                this.__tplCfgById = {};
                                this.__tplMetaById = {};
                                this.setData({
                                    templatesLoading: false,
                                    templateOptions: [{ id: 0, label: '不使用模板' }],
                                    templateIndex: 0,
                                    templateLabel: '不使用模板',
                                    templateMeta: ''
                                });
                                return [2 /*return*/];
                            }
                            now = Date.now();
                            lastAt = Number(this.__lastTplLoadAt || 0) || 0;
                            if (!force && now - lastAt < 5000 && (this.data.templateOptions || []).length > 1)
                                return [2 /*return*/];
                            if (this.data.templatesLoading)
                                return [2 /*return*/];
                            this.setData({ templatesLoading: true, templateMsg: '', templateMsgKind: '' });
                            _b.label = 1;
                        case 1:
                            _b.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.getExamTemplates()];
                        case 2:
                            res = (_b.sent());
                            list = Array.isArray(res) ? res : [];
                            options_1 = [{ id: 0, label: '不使用模板' }];
                            cfgById_1 = {};
                            metaById_1 = {};
                            list.forEach(function (tpl) {
                                var id = Number((tpl === null || tpl === void 0 ? void 0 : tpl.id) || 0);
                                if (!Number.isFinite(id) || id <= 0)
                                    return;
                                var title = String((tpl === null || tpl === void 0 ? void 0 : tpl.title) || '').trim() || "\u6A21\u677F #".concat(id);
                                var cfg = normalizeTemplateConfig(tpl === null || tpl === void 0 ? void 0 : tpl.config);
                                if (!cfg)
                                    return;
                                if (!isSameScope(cfg, source, subject, bankId))
                                    return;
                                cfgById_1[String(id)] = __assign(__assign({}, cfg), { label: title });
                                metaById_1[String(id)] = buildTemplateMeta(cfg);
                                options_1.push({ id: id, label: title });
                            });
                            this.__tplCfgById = cfgById_1;
                            this.__tplMetaById = metaById_1;
                            this.__lastTplLoadAt = now;
                            currentId_1 = Number(((_a = (this.data.templateOptions || [])[this.data.templateIndex]) === null || _a === void 0 ? void 0 : _a.id) || 0);
                            templateIndex = 0;
                            if (currentId_1 > 0) {
                                foundIdx = options_1.findIndex(function (o) { return Number((o === null || o === void 0 ? void 0 : o.id) || 0) === currentId_1; });
                                if (foundIdx >= 0)
                                    templateIndex = foundIdx;
                            }
                            finalPicked = options_1[templateIndex] || options_1[0];
                            finalId = Number((finalPicked === null || finalPicked === void 0 ? void 0 : finalPicked.id) || 0);
                            this.setData({
                                templateOptions: options_1,
                                templateIndex: templateIndex,
                                templateLabel: (finalPicked === null || finalPicked === void 0 ? void 0 : finalPicked.label) || '不使用模板',
                                templateMeta: finalId > 0 ? String(metaById_1[String(finalId)] || '') : '',
                                templatesLoading: false
                            });
                            return [3 /*break*/, 4];
                        case 3:
                            e_1 = _b.sent();
                            this.__tplCfgById = {};
                            this.__tplMetaById = {};
                            this.__lastTplLoadAt = now;
                            this.setData({
                                templatesLoading: false,
                                templateOptions: [{ id: 0, label: '不使用模板' }],
                                templateIndex: 0,
                                templateLabel: '不使用模板',
                                templateMeta: ''
                            });
                            this.setTemplateMsg((e_1 && e_1.message) || '模板加载失败，请稍后重试', 'error');
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            });
        },
        onTemplatePickerChange: function (e) {
            var _this = this;
            var _a;
            var idx = Number((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value);
            var options = (this.data.templateOptions || []);
            var safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(options.length - 1, idx)) : 0;
            var opt = options[safeIdx] || { id: 0, label: '不使用模板' };
            var metaById = (this.__tplMetaById || {});
            var meta = opt.id > 0 ? String(metaById[String(opt.id)] || '') : '';
            this.setData({
                templateIndex: safeIdx,
                templateLabel: opt.label || '不使用模板',
                templateMeta: meta,
                templateMsg: '',
                templateMsgKind: ''
            });
            if (!opt.id) {
                this.setData({ examTypes: [], presetApplied: false }, function () { return _this.reloadExamTypes(); });
                return;
            }
            var cfgById = (this.__tplCfgById || {});
            var cfg = cfgById[String(opt.id)];
            if (!cfg) {
                this.setTemplateMsg('模板不可用，请稍后刷新', 'error');
                return;
            }
            this.setData({
                examDuration: clampInt(cfg.duration, 60, 1, 1440),
                examTargetTotal: clampInt(cfg.targetTotal, 30, 1, 300),
                presetApplied: true,
                examMsg: '',
                examMsgKind: ''
            }, function () { return _this.reloadExamTypes({ applyConfig: cfg }); });
        },
        getQTypesForScope: function () {
            return __awaiter(this, void 0, void 0, function () {
                var source, subject, bankId, info_1, infoData_1, arr_1, info, infoData, arr, _a;
                return __generator(this, function (_b) {
                    switch (_b.label) {
                        case 0:
                            source = this.normalizeSource();
                            subject = String(this.properties.subject || '').trim();
                            bankId = Number(this.properties.bankId || 0) || 0;
                            _b.label = 1;
                        case 1:
                            _b.trys.push([1, 5, , 6]);
                            if (!(source === 'user_bank')) return [3 /*break*/, 3];
                            if (bankId <= 0)
                                return [2 /*return*/, []];
                            return [4 /*yield*/, api_1.api.getBankDetail(bankId)];
                        case 2:
                            info_1 = _b.sent();
                            infoData_1 = (info_1 === null || info_1 === void 0 ? void 0 : info_1.data) || info_1 || {};
                            arr_1 = Array.isArray(infoData_1 === null || infoData_1 === void 0 ? void 0 : infoData_1.available_types) ? infoData_1.available_types : [];
                            return [2 /*return*/, (arr_1 || []).filter(function (x) { return typeof x === 'string' && String(x).trim(); }).map(function (s) { return String(s).trim(); })];
                        case 3:
                            if (!subject || subject === 'all')
                                return [2 /*return*/, FALLBACK_PUBLIC_Q_TYPES.slice()];
                            return [4 /*yield*/, api_1.api.getSubjectInfo(subject)];
                        case 4:
                            info = _b.sent();
                            infoData = (info === null || info === void 0 ? void 0 : info.data) || info || {};
                            arr = Array.isArray(infoData === null || infoData === void 0 ? void 0 : infoData.available_types) ? infoData.available_types : [];
                            return [2 /*return*/, (arr || []).filter(function (x) { return typeof x === 'string' && String(x).trim(); }).map(function (s) { return String(s).trim(); })];
                        case 5:
                            _a = _b.sent();
                            return [2 /*return*/, []];
                        case 6: return [2 /*return*/];
                    }
                });
            });
        },
        recomputeTypeSubtotals: function (rows) {
            return (rows || []).map(function (r) {
                var subtotal = r.enabled ? (Number(r.count) || 0) * (Number(r.score) || 0) : 0;
                return __assign(__assign({}, r), { subtotalText: formatNum(subtotal) });
            });
        },
        applyDefaultPresetIfEmpty: function (rows) {
            var assigned = (rows || []).reduce(function (sum, r) { return sum + (r.enabled ? Math.max(0, Number(r.count) || 0) : 0); }, 0);
            if (assigned > 0)
                return rows;
            if (this.data.presetApplied)
                return rows;
            var qTypes = rows.map(function (r) { return r.name; });
            var picked = DEFAULT_PICKED_TYPES.filter(function (t) { return qTypes.includes(t); });
            var fallbackPicked = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));
            var enabledTypes = rows
                .filter(function (r) { return fallbackPicked.includes(r.name); })
                .map(function (r) { return ({ name: r.name, available: r.available }); });
            var distributed = distributeCounts(this.data.examTargetTotal, enabledTypes);
            return rows.map(function (r) {
                var enabled = fallbackPicked.includes(r.name);
                var count = enabled ? clampInt(distributed[r.name] || 0, 0, 0, r.available) : 0;
                return __assign(__assign({}, r), { enabled: enabled, count: count, score: 1 });
            });
        },
        refreshExamSummary: function () {
            var source = this.normalizeSource();
            var subject = String(this.properties.subject || '').trim();
            var bankId = Number(this.properties.bankId || 0) || 0;
            var scopeText = this.buildScopeText();
            var rows = this.data.examTypes || [];
            var types = {};
            var scores = {};
            var assigned = 0;
            var totalScore = 0;
            rows.forEach(function (r) {
                if (!r.enabled)
                    return;
                var count = clampInt(r.count, 0, 0, 500);
                var score = clampFloat(r.score, 1, 0, 1000);
                if (count <= 0)
                    return;
                types[r.name] = count;
                scores[r.name] = score;
                assigned += count;
                totalScore += count * score;
            });
            var examSumTypes = Object.keys(types).map(function (name) {
                var _a;
                var count = types[name] || 0;
                var score = (_a = scores[name]) !== null && _a !== void 0 ? _a : 1;
                return { name: name, meta: "".concat(count, " \u00D7 ").concat(formatNum(score)), subtotal: formatNum(count * score) };
            });
            var startDisabled = assigned <= 0 ||
                (source === 'public' && !subject) ||
                (source === 'user_bank' && bankId <= 0) ||
                this.data.examLoading ||
                this.data.examCreating;
            this.setData({
                examSumScope: scopeText,
                examSumDuration: "".concat(clampInt(this.data.examDuration, 60, 1, 1440), " \u5206\u949F"),
                examSumAssigned: "".concat(assigned, " \u9898"),
                examSumScore: "".concat(formatNum(totalScore), " \u5206"),
                examSumTypes: examSumTypes,
                examStartDisabled: startDisabled
            });
        },
        reloadExamTypes: function (opts) {
            return __awaiter(this, void 0, void 0, function () {
                var source, subject, bankId, qTypes, counts, prevMap_1, applyConfig_1, rows, _a;
                var _this = this;
                return __generator(this, function (_b) {
                    switch (_b.label) {
                        case 0:
                            if (this.data.examLoading)
                                return [2 /*return*/];
                            this.setData({ examLoading: true, examMsg: '', examMsgKind: '' });
                            source = this.normalizeSource();
                            subject = String(this.properties.subject || '').trim();
                            bankId = Number(this.properties.bankId || 0) || 0;
                            if (source === 'public' && !subject) {
                                this.setData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                                return [2 /*return*/];
                            }
                            if (source === 'user_bank' && bankId <= 0) {
                                this.setData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                                return [2 /*return*/];
                            }
                            _b.label = 1;
                        case 1:
                            _b.trys.push([1, 4, , 5]);
                            return [4 /*yield*/, this.getQTypesForScope()];
                        case 2:
                            qTypes = (_b.sent()).filter(Boolean);
                            if (!qTypes.length) {
                                this.setData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                                return [2 /*return*/];
                            }
                            return [4 /*yield*/, Promise.all(qTypes.map(function (t) { return __awaiter(_this, void 0, void 0, function () {
                                    var res_1, res, _a;
                                    return __generator(this, function (_b) {
                                        switch (_b.label) {
                                            case 0:
                                                _b.trys.push([0, 4, , 5]);
                                                if (!(source === 'user_bank')) return [3 /*break*/, 2];
                                                return [4 /*yield*/, api_1.api.getBankUserCounts(bankId, { q_type: t, source: 'all' })];
                                            case 1:
                                                res_1 = _b.sent();
                                                return [2 /*return*/, { name: t, available: clampInt(res_1 === null || res_1 === void 0 ? void 0 : res_1.total, 0, 0, 999999) }];
                                            case 2: return [4 /*yield*/, api_1.api.getQuestionsCount({ subject: subject || 'all', type: t })];
                                            case 3:
                                                res = _b.sent();
                                                return [2 /*return*/, { name: t, available: clampInt(res === null || res === void 0 ? void 0 : res.count, 0, 0, 999999) }];
                                            case 4:
                                                _a = _b.sent();
                                                return [2 /*return*/, { name: t, available: 0 }];
                                            case 5: return [2 /*return*/];
                                        }
                                    });
                                }); }))];
                        case 3:
                            counts = _b.sent();
                            prevMap_1 = new Map();
                            (this.data.examTypes || []).forEach(function (r) { return prevMap_1.set(r.name, r); });
                            applyConfig_1 = opts === null || opts === void 0 ? void 0 : opts.applyConfig;
                            rows = counts
                                .filter(function (x) { return x.available > 0; })
                                .map(function (x) {
                                if (applyConfig_1) {
                                    var cfgTypes = applyConfig_1.types || {};
                                    var cfgScores = applyConfig_1.scores || {};
                                    var cfgCount = clampInt(cfgTypes[x.name], 0, 0, x.available);
                                    var enabled_1 = cfgCount > 0;
                                    var score_1 = enabled_1 ? clampFloat(cfgScores[x.name], 1, 0, 1000) : 1;
                                    return { name: x.name, enabled: enabled_1, available: x.available, count: enabled_1 ? cfgCount : 0, score: score_1, subtotalText: '0' };
                                }
                                var prev = prevMap_1.get(x.name);
                                var enabled = prev ? !!prev.enabled : false;
                                var score = prev ? clampFloat(prev.score, 1, 0, 1000) : 1;
                                var count = enabled ? clampInt(prev === null || prev === void 0 ? void 0 : prev.count, 0, 0, x.available) : 0;
                                return { name: x.name, enabled: enabled, available: x.available, count: count, score: score, subtotalText: '0' };
                            });
                            if (!applyConfig_1)
                                rows = this.applyDefaultPresetIfEmpty(rows);
                            rows = this.recomputeTypeSubtotals(rows);
                            this.setData({ examTypes: rows, examLoading: false, presetApplied: true }, function () { return _this.refreshExamSummary(); });
                            return [3 /*break*/, 5];
                        case 4:
                            _a = _b.sent();
                            this.setData({ examTypes: [], examLoading: false }, function () { return _this.refreshExamSummary(); });
                            return [3 /*break*/, 5];
                        case 5: return [2 /*return*/];
                    }
                });
            });
        },
        onExamDurationInput: function (e) {
            var _this = this;
            var _a;
            var duration = clampInt((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 60, 1, 1440);
            this.setData({ examDuration: duration }, function () { return _this.refreshExamSummary(); });
        },
        onExamTargetTotalInput: function (e) {
            var _this = this;
            var _a;
            var total = clampInt((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 30, 1, 300);
            this.setData({ examTargetTotal: total }, function () { return _this.refreshExamSummary(); });
        },
        onQuickPresetTap: function (e) {
            var _this = this;
            var _a, _b, _c, _d;
            var duration = clampInt((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.duration, 60, 1, 1440);
            var total = clampInt((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.total, 30, 1, 300);
            this.setData({ examDuration: duration, examTargetTotal: total }, function () {
                _this.onAutoDistributeTap();
                _this.refreshExamSummary();
            });
        },
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
            this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () { return _this.refreshExamSummary(); });
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
                var count = clampInt((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 0, 0, r.available);
                return __assign(__assign({}, r), { count: count });
            });
            this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () { return _this.refreshExamSummary(); });
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
                var score = clampFloat((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 1, 0, 1000);
                return __assign(__assign({}, r), { score: score });
            });
            this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () { return _this.refreshExamSummary(); });
        },
        onAutoDistributeTap: function () {
            var _this = this;
            var enabledRows = (this.data.examTypes || []).filter(function (r) { return r.enabled; });
            if (!enabledRows.length) {
                this.setData({ examMsg: '请先勾选至少一种题型，再进行均分。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
                return;
            }
            var distributed = distributeCounts(this.data.examTargetTotal, enabledRows.map(function (r) { return ({ name: r.name, available: r.available }); }));
            var next = (this.data.examTypes || []).map(function (r) {
                if (!r.enabled)
                    return __assign(__assign({}, r), { count: 0 });
                return __assign(__assign({}, r), { count: clampInt(distributed[r.name] || 0, 0, 0, r.available) });
            });
            this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () { return _this.refreshExamSummary(); });
        },
        onResetScoresTap: function () {
            var _this = this;
            var next = (this.data.examTypes || []).map(function (r) { return (__assign(__assign({}, r), { score: 1 })); });
            this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, function () { return _this.refreshExamSummary(); });
        },
        stopTap: function () { },
        onOpenSaveTemplate: function () {
            if (this.data.savingTemplate)
                return;
            var cfg = this.collectTemplateConfig();
            if (!cfg) {
                wx.showToast({ title: '缺少范围参数', icon: 'none' });
                return;
            }
            if (!Object.keys(cfg.types).length) {
                wx.showToast({ title: '请先设置题型与题量', icon: 'none' });
                return;
            }
            var title = "\u81EA\u5B9A\u4E49\u6A21\u677F ".concat(todayStamp());
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
        collectTemplateConfig: function () {
            var source = this.normalizeSource();
            var subjectRaw = String(this.properties.subject || '').trim();
            var bankId = Number(this.properties.bankId || 0) || 0;
            if (source === 'public' && !subjectRaw)
                return null;
            if (source === 'user_bank' && bankId <= 0)
                return null;
            var duration = clampInt(this.data.examDuration, 60, 1, 1440);
            var targetTotal = clampInt(this.data.examTargetTotal, 30, 1, 300);
            var types = {};
            var scores = {};
            (this.data.examTypes || []).forEach(function (r) {
                if (!r.enabled)
                    return;
                var count = clampInt(r.count, 0, 0, 500);
                var score = clampFloat(r.score, 1, 0, 1000);
                if (count <= 0)
                    return;
                types[r.name] = count;
                scores[r.name] = score;
            });
            var cfg = {
                source: source,
                subject: source === 'public' ? subjectRaw : 'all',
                bank_id: source === 'user_bank' ? bankId : null,
                duration: duration,
                targetTotal: targetTotal,
                types: types,
                scores: scores
            };
            return cfg;
        },
        onConfirmSaveTemplate: function () {
            return __awaiter(this, void 0, void 0, function () {
                var title, cfg, e_2;
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
                            cfg = this.collectTemplateConfig();
                            if (!cfg) {
                                wx.showToast({ title: '缺少范围参数', icon: 'none' });
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
                            return [4 /*yield*/, api_1.api.createExamTemplate({ title: title, config: cfg })];
                        case 2:
                            _a.sent();
                            wx.hideLoading();
                            this.setData({ savingTemplate: false, saveModalOpen: false, saveTemplateTitle: '' });
                            wx.showToast({ title: '已设为模板', icon: 'success' });
                            this.loadUserTemplates(true);
                            return [3 /*break*/, 4];
                        case 3:
                            e_2 = _a.sent();
                            wx.hideLoading();
                            this.setData({ savingTemplate: false });
                            wx.showToast({ title: (e_2 && e_2.message) || '保存失败', icon: 'none' });
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            });
        },
        collectExamPayload: function () {
            var source = this.normalizeSource();
            var subject = String(this.properties.subject || '').trim();
            var bankId = Number(this.properties.bankId || 0) || 0;
            if (source === 'public' && !subject)
                return null;
            if (source === 'user_bank' && bankId <= 0)
                return null;
            var duration = clampInt(this.data.examDuration, 60, 1, 1440);
            var types = {};
            var scores = {};
            (this.data.examTypes || []).forEach(function (r) {
                if (!r.enabled)
                    return;
                var count = clampInt(r.count, 0, 0, 500);
                var score = clampFloat(r.score, 1, 0, 1000);
                if (count <= 0)
                    return;
                types[r.name] = count;
                scores[r.name] = score;
            });
            return {
                source: source,
                subject: source === 'user_bank' ? (String(this.properties.bankName || '').trim() || 'all') : subject,
                bank_id: source === 'user_bank' ? bankId : null,
                duration: duration,
                types: types,
                scores: scores
            };
        },
        onStartExamTap: function () {
            return __awaiter(this, void 0, void 0, function () {
                var cfg, res, examId, e_3;
                var _this = this;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (this.data.examCreating || this.data.examLoading)
                                return [2 /*return*/];
                            cfg = this.collectExamPayload();
                            if (!cfg) {
                                this.setData({ examMsg: '缺少范围参数，无法创建考试。', examMsgKind: 'error' }, function () { return _this.refreshExamSummary(); });
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
                            examId = Number((res === null || res === void 0 ? void 0 : res.exam_id) || (res === null || res === void 0 ? void 0 : res.id) || 0);
                            if (!Number.isFinite(examId) || examId <= 0)
                                throw new Error('创建考试失败');
                            wx.hideLoading();
                            this.setData({ examCreating: false });
                            wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                            this.triggerEvent('created', { exam_id: examId }, {});
                            return [3 /*break*/, 4];
                        case 3:
                            e_3 = _a.sent();
                            wx.hideLoading();
                            this.setData({ examCreating: false, examMsg: (e_3 && e_3.message) || '创建失败', examMsgKind: 'error' }, function () {
                                return _this.refreshExamSummary();
                            });
                            return [3 /*break*/, 4];
                        case 4: return [2 /*return*/];
                    }
                });
            });
        }
    }
});
