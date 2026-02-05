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
// bank-exam-setup.ts - 个人题库考试设置
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
function normalizeTypeList(input) {
    var list = Array.isArray(input) ? input : [];
    return list
        .filter(function (t) { return typeof t === 'string' && t.trim(); })
        .map(function (t) { return String(t).trim(); });
}
Page({
    data: {
        bankId: 0,
        bankName: '',
        totalQuestions: 0,
        availableTypes: [],
        duration: 60, // 考试时长（分钟）
        questionCount: 20, // 题目数量
        scorePerQuestion: 5, // 每题分值
        totalScore: 100, // 总分
        shuffleQuestions: true, // 随机抽题
        loading: false,
        creating: false,
        warnText: ''
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var bankId = Number(options.bank_id || 0);
        if (!bankId) {
            wx.showToast({ title: '题库参数缺失', icon: 'none' });
            setTimeout(function () { return wx.navigateBack(); }, 1500);
            return;
        }
        this.setData({ bankId: bankId });
        this.loadBankInfo();
    },
    loadBankInfo: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, bankData, totalQuestions, questionCount, availableTypes, err_1;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        this.setData({ loading: true });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getBankDetail(this.data.bankId)];
                    case 2:
                        res = _c.sent();
                        bankData = res.data || res || {};
                        totalQuestions = bankData.question_count || 0;
                        questionCount = Math.min(20, totalQuestions);
                        availableTypes = normalizeTypeList(bankData.available_types);
                        this.setData({
                            bankName: bankData.name || '题库',
                            totalQuestions: totalQuestions,
                            questionCount: questionCount,
                            availableTypes: availableTypes,
                            loading: false
                        });
                        this.updateTotalScore();
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _c.sent();
                        console.error('加载题库信息失败:', err_1);
                        if (((_a = err_1.message) === null || _a === void 0 ? void 0 : _a.includes('401')) || ((_b = err_1.message) === null || _b === void 0 ? void 0 : _b.includes('登录'))) {
                            wx.reLaunch({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: err_1.message || '加载失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onDurationInput: function (e) {
        var v = Number(e.detail.value);
        var duration = isFinite(v) ? Math.max(1, Math.min(240, v)) : 60;
        this.setData({ duration: duration });
    },
    onQuestionCountInput: function (e) {
        var _this = this;
        var v = Number(e.detail.value);
        var max = this.data.totalQuestions;
        var questionCount = isFinite(v) ? Math.max(1, Math.min(max, v)) : 20;
        this.setData({ questionCount: questionCount }, function () {
            _this.updateTotalScore();
            _this.checkWarn();
        });
    },
    onScoreInput: function (e) {
        var _this = this;
        var v = Number(e.detail.value);
        var scorePerQuestion = isFinite(v) ? Math.max(0.5, Math.min(100, v)) : 5;
        this.setData({ scorePerQuestion: scorePerQuestion }, function () {
            _this.updateTotalScore();
        });
    },
    onShuffleChange: function (e) {
        this.setData({ shuffleQuestions: !!e.detail.value });
    },
    updateTotalScore: function () {
        var total = this.data.questionCount * this.data.scorePerQuestion;
        this.setData({ totalScore: Math.round(total * 10) / 10 });
    },
    checkWarn: function () {
        var _a = this.data, questionCount = _a.questionCount, totalQuestions = _a.totalQuestions;
        if (questionCount > totalQuestions) {
            this.setData({ warnText: "\u9898\u76EE\u6570\u91CF\u8D85\u8FC7\u53EF\u7528\u9898\u76EE\u6570\uFF08".concat(totalQuestions, "\uFF09") });
        }
        else {
            this.setData({ warnText: '' });
        }
    },
    onStartExam: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, bankId, questionCount, duration, scorePerQuestion, totalQuestions, typesList, baseTypes, n, base_1, rem_1, typesCfg_1, scoresCfg_1, res, examId, err_2;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, bankId = _a.bankId, questionCount = _a.questionCount, duration = _a.duration, scorePerQuestion = _a.scorePerQuestion, totalQuestions = _a.totalQuestions;
                        if (questionCount > totalQuestions) {
                            wx.showToast({ title: '题目数量超过可用数量', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (questionCount <= 0) {
                            wx.showToast({ title: '请设置题目数量', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ creating: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        wx.showLoading({ title: '创建考试...' });
                        typesList = (this.data.availableTypes || []).filter(Boolean);
                        baseTypes = typesList.length ? typesList : ['选择题', '多选题', '判断题', '填空题'];
                        n = Math.max(1, baseTypes.length);
                        base_1 = Math.floor(questionCount / n);
                        rem_1 = questionCount % n;
                        typesCfg_1 = {};
                        scoresCfg_1 = {};
                        baseTypes.forEach(function (t) {
                            var c = base_1 + (rem_1 > 0 ? 1 : 0);
                            if (rem_1 > 0)
                                rem_1 -= 1;
                            if (c > 0) {
                                typesCfg_1[t] = c;
                                scoresCfg_1[t] = Math.max(0, Number(scorePerQuestion) || 0);
                            }
                        });
                        return [4 /*yield*/, api_1.api.createExam({
                                subject: 'all',
                                duration: duration,
                                types: typesCfg_1,
                                scores: scoresCfg_1,
                                source: 'user_bank',
                                bank_id: bankId
                            })];
                    case 2:
                        res = _b.sent();
                        examId = Number(res === null || res === void 0 ? void 0 : res.exam_id);
                        if (!isFinite(examId) || examId <= 0) {
                            throw new Error('创建考试失败');
                        }
                        wx.hideLoading();
                        this.setData({ creating: false });
                        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(examId) });
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _b.sent();
                        console.error('创建考试失败:', err_2);
                        wx.hideLoading();
                        wx.showToast({ title: err_2.message || '创建失败', icon: 'none' });
                        this.setData({ creating: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    }
});
