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
// exam-setup.ts - 考试设置
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        subject: '',
        duration: 60,
        total: 50,
        types: [],
        computedTotal: 0,
        computedScoreText: '0',
        loading: false,
        creating: false,
        warnText: ''
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var subject = options.subject || '';
        if (!subject) {
            wx.showToast({ title: '科目参数缺失', icon: 'none' });
            setTimeout(function () { return wx.navigateBack(); }, 1200);
            return;
        }
        try {
            subject = decodeURIComponent(subject);
        }
        catch (e) { }
        this.setData({ subject: subject });
        this.loadTypeCounts();
    },
    onDurationInput: function (e) {
        var v = Number(e.detail.value);
        var duration = isFinite(v) ? Math.max(1, Math.min(24 * 60, v)) : 60;
        this.setData({ duration: duration });
    },
    onTotalInput: function (e) {
        var _this = this;
        var v = Number(e.detail.value);
        var total = isFinite(v) ? Math.max(1, Math.min(500, v)) : 50;
        this.setData({ total: total }, function () {
            _this.refreshSummary();
        });
    },
    loadTypeCounts: function () {
        return __awaiter(this, void 0, void 0, function () {
            var baseTypes, subject_1, counts, types, enabled, defaultCounts_1, seeded, err_1;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true, warnText: '' });
                        baseTypes = ['选择题', '多选题', '判断题', '填空题', '简答题', '计算题'];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        subject_1 = this.data.subject;
                        return [4 /*yield*/, Promise.all(baseTypes.map(function (t) { return __awaiter(_this, void 0, void 0, function () {
                                var res, e_1;
                                return __generator(this, function (_a) {
                                    switch (_a.label) {
                                        case 0:
                                            _a.trys.push([0, 2, , 3]);
                                            return [4 /*yield*/, api_1.api.getQuestionsCount({ subject: subject_1, type: t })];
                                        case 1:
                                            res = _a.sent();
                                            return [2 /*return*/, { name: t, available: Number(res.count || 0) }];
                                        case 2:
                                            e_1 = _a.sent();
                                            return [2 /*return*/, { name: t, available: 0 }];
                                        case 3: return [2 /*return*/];
                                    }
                                });
                            }); }))];
                    case 2:
                        counts = _a.sent();
                        types = counts
                            .filter(function (x) { return x.available > 0; })
                            .map(function (x, idx) { return ({
                            name: x.name,
                            available: x.available,
                            enabled: idx < 2,
                            count: 0,
                            score: 1
                        }); });
                        enabled = types.filter(function (t) { return t.enabled; });
                        defaultCounts_1 = this.distributeCounts(this.data.total, enabled);
                        seeded = types.map(function (t) {
                            if (!t.enabled)
                                return t;
                            var c = Number(defaultCounts_1[t.name] || 0);
                            var count = Math.max(0, Math.min(t.available, isFinite(c) ? c : 0));
                            return Object.assign({}, t, { count: count, score: 1 });
                        });
                        this.setData({ types: seeded, loading: false }, function () {
                            _this.refreshSummary();
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载题型失败:', err_1);
                        this.setData({ types: [], loading: false, computedTotal: 0, computedScoreText: '0' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onToggleTypeSwitch: function (e) {
        var name = e.currentTarget.dataset.name;
        var value = !!(e && e.detail && e.detail.value);
        this.setTypeEnabled(name, value);
    },
    setTypeEnabled: function (name, enabled) {
        var _this = this;
        var next = (this.data.types || []).map(function (t) {
            if (t.name !== name)
                return t;
            if (!enabled) {
                return Object.assign({}, t, { enabled: false, count: 0 });
            }
            // 启用：默认至少 1 题（若可用）
            var count = t.count > 0 ? t.count : Math.min(1, t.available);
            var scoreRaw = Number(t.score);
            var score = isFinite(scoreRaw) ? Math.max(0, Math.min(1000, scoreRaw)) : 1;
            return Object.assign({}, t, { enabled: true, count: count, score: score });
        });
        this.setData({ types: next }, function () {
            _this.refreshSummary();
        });
    },
    onTypeConfigInput: function (e) {
        var _this = this;
        var name = e.currentTarget.dataset.name;
        var field = e.currentTarget.dataset.field;
        if (!name || !field)
            return;
        var next = (this.data.types || []).map(function (t) {
            if (t.name !== name)
                return t;
            if (field === 'count') {
                var raw = Number(e.detail.value);
                var v = isFinite(raw) ? Math.max(0, Math.floor(raw)) : 0;
                var count = Math.min(v, t.available);
                return Object.assign({}, t, { count: count });
            }
            if (field === 'score') {
                var raw = Number(e.detail.value);
                var v = isFinite(raw) ? Math.max(0, Math.min(1000, raw)) : 0;
                return Object.assign({}, t, { score: v });
            }
            return t;
        });
        this.setData({ types: next }, function () {
            _this.refreshSummary();
        });
    },
    refreshSummary: function () {
        var types = this.data.types || [];
        var total = 0;
        var score = 0;
        for (var _i = 0, types_1 = types; _i < types_1.length; _i++) {
            var t = types_1[_i];
            if (!t.enabled)
                continue;
            var c = Math.max(0, Math.min(t.available, Math.floor(Number(t.count) || 0)));
            var s = Math.max(0, Math.min(1000, Number(t.score) || 0));
            if (c <= 0)
                continue;
            total += c;
            score += c * s;
        }
        var scoreText = this.formatScore(score);
        var warnText = '';
        if (types.length > 0 && total > 0 && total !== this.data.total) {
            warnText = "\u5F53\u524D\u5DF2\u8BBE\u7F6E ".concat(total, " \u9898\uFF0C\u4E0E\u76EE\u6807 ").concat(this.data.total, " \u9898\u4E0D\u4E00\u81F4");
        }
        this.setData({ computedTotal: total, computedScoreText: scoreText, warnText: warnText });
    },
    formatScore: function (v) {
        var n = Number(v) || 0;
        if (Math.abs(n - Math.round(n)) < 1e-6) {
            return String(Math.round(n));
        }
        return n.toFixed(1).replace(/\.0$/, '');
    },
    stopPropagation: function () { },
    onStartExam: function () {
        return __awaiter(this, void 0, void 0, function () {
            var enabledTypes, duration, _a, typesConfig, scoresConfig, actualTotal, mismatch, ok, res, examId, err_2;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.creating || this.data.loading)
                            return [2 /*return*/];
                        enabledTypes = (this.data.types || []).filter(function (t) { return t.enabled; });
                        if (enabledTypes.length === 0) {
                            wx.showToast({ title: '请选择题型', icon: 'none' });
                            return [2 /*return*/];
                        }
                        duration = this.data.duration;
                        _a = this.buildExamConfig(enabledTypes), typesConfig = _a.typesConfig, scoresConfig = _a.scoresConfig, actualTotal = _a.actualTotal;
                        if (actualTotal <= 0) {
                            wx.showToast({ title: '题目不足，无法组卷', icon: 'none' });
                            return [2 /*return*/];
                        }
                        mismatch = actualTotal !== this.data.total;
                        if (!mismatch) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.confirmModal('题目数量不一致', "\u5F53\u524D\u9898\u578B\u9898\u6570\u5408\u8BA1\u4E3A ".concat(actualTotal, " \u9898\uFF0C\u4E0E\u76EE\u6807 ").concat(this.data.total, " \u9898\u4E0D\u4E00\u81F4\uFF0C\u5C06\u6309 ").concat(actualTotal, " \u9898\u7EC4\u5377\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F"))];
                    case 1:
                        ok = _b.sent();
                        if (!ok)
                            return [2 /*return*/];
                        _b.label = 2;
                    case 2:
                        this.setData({ creating: true });
                        wx.showLoading({ title: '创建考试...' });
                        _b.label = 3;
                    case 3:
                        _b.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, api_1.api.createExam({
                                subject: this.data.subject,
                                duration: duration,
                                types: typesConfig,
                                scores: scoresConfig
                            })];
                    case 4:
                        res = _b.sent();
                        examId = Number(res.exam_id);
                        if (!isFinite(examId) || examId <= 0) {
                            throw new Error('创建考试失败');
                        }
                        wx.hideLoading();
                        this.setData({ creating: false });
                        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                        return [3 /*break*/, 6];
                    case 5:
                        err_2 = _b.sent();
                        console.error('创建考试失败:', err_2);
                        wx.hideLoading();
                        this.setData({ creating: false });
                        wx.showToast({ title: (err_2 && err_2.message) || '创建失败', icon: 'none' });
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    buildExamConfig: function (enabledTypes) {
        var typesConfig = {};
        var scoresConfig = {};
        enabledTypes.forEach(function (t) {
            var c = Math.max(0, Math.min(t.available, Math.floor(Number(t.count) || 0)));
            var s = Math.max(0, Math.min(1000, Number(t.score) || 0));
            if (c > 0) {
                typesConfig[t.name] = c;
                scoresConfig[t.name] = s;
            }
        });
        var assignedTotal = Object.values(typesConfig).reduce(function (sum, v) { return sum + (Number(v) || 0); }, 0);
        return { typesConfig: typesConfig, scoresConfig: scoresConfig, actualTotal: assignedTotal };
    },
    distributeCounts: function (total, enabledTypes) {
        var cfg = {};
        var n = enabledTypes.length;
        if (n <= 0)
            return cfg;
        var target = Math.max(1, Math.min(500, Math.floor(Number(total) || 0)));
        var base = Math.floor(target / n);
        var rem = target % n;
        enabledTypes.forEach(function (t) {
            var want = base + (rem > 0 ? 1 : 0);
            if (rem > 0)
                rem -= 1;
            cfg[t.name] = Math.min(want, t.available);
        });
        // 尝试补齐剩余
        var assignedTotal = Object.values(cfg).reduce(function (s, v) { return s + (Number(v) || 0); }, 0);
        var remaining = target - assignedTotal;
        var safety = 5000;
        while (remaining > 0 && safety-- > 0) {
            var progressed = false;
            for (var _i = 0, enabledTypes_1 = enabledTypes; _i < enabledTypes_1.length; _i++) {
                var t = enabledTypes_1[_i];
                if (remaining <= 0)
                    break;
                var cap = t.available - (cfg[t.name] || 0);
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
                cfg[t.name] = Math.min(1, t.available);
            });
        }
        return cfg;
    },
    confirmModal: function (title, content) {
        return new Promise(function (resolve) {
            wx.showModal({
                title: title,
                content: content,
                confirmText: '继续',
                cancelText: '取消',
                success: function (res) { return resolve(!!res.confirm); },
                fail: function () { return resolve(false); }
            });
        });
    }
});
