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
// exam-settlement.ts - 考试结算页
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
function formatSeconds(seconds) {
    var s = Math.max(0, Math.floor(Number(seconds) || 0));
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var r = s % 60;
    if (h > 0)
        return "".concat(String(h).padStart(2, '0'), ":").concat(String(m).padStart(2, '0'), ":").concat(String(r).padStart(2, '0'));
    return "".concat(String(m).padStart(2, '0'), ":").concat(String(r).padStart(2, '0'));
}
function parseDateTimeMaybe(val) {
    var s = String(val || '').trim();
    if (!s)
        return NaN;
    var iso = s.includes('T') ? s : s.replace(' ', 'T');
    var d = new Date(iso);
    var t = d.getTime();
    return Number.isFinite(t) ? t : NaN;
}
function calcSecondsBetween(a, b) {
    var t1 = parseDateTimeMaybe(a);
    var t2 = parseDateTimeMaybe(b);
    if (!Number.isFinite(t1) || !Number.isFinite(t2))
        return null;
    var diff = Math.max(0, Math.floor((t2 - t1) / 1000));
    return diff;
}
function parsePositiveInt(val) {
    var n = Number(val);
    if (!Number.isFinite(n) || n <= 0)
        return null;
    return Math.floor(n);
}
Page({
    data: {
        examId: 0,
        usedSecHint: null,
        autoSubmitted: false,
        loading: false,
        errorText: '',
        exam: null,
        statusText: '',
        subChips: [],
        total: 0,
        correct: 0,
        wrong: 0,
        answered: 0,
        unanswered: 0,
        answeredPercent: 0,
        accuracy: 0,
        totalScore: 0,
        timeUsedText: '--',
        startedAt: '',
        submittedAt: '',
        toMistakesLoading: false,
        toMistakesDone: false,
        toMistakesCount: 0
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            wx.showShareMenu({ withShareTicket: true });
        }
        catch (e) { }
        var examId = Number((options === null || options === void 0 ? void 0 : options.exam_id) || 0);
        if (!Number.isFinite(examId) || examId <= 0) {
            this.setData({ errorText: '考试参数缺失' });
            return;
        }
        var usedSecHint = parsePositiveInt(options === null || options === void 0 ? void 0 : options.used_sec);
        var autoSubmitted = String((options === null || options === void 0 ? void 0 : options.silent) || '').trim() === '1';
        this.setData({ examId: examId, usedSecHint: usedSecHint, autoSubmitted: autoSubmitted });
        this.loadData();
    },
    onPullDownRefresh: function () {
        this.loadData(true);
    },
    loadData: function () {
        return __awaiter(this, arguments, void 0, function (fromPullDown) {
            var res, exam, questions, total, correct_1, wrong_1, answered_1, unanswered, accuracy, totalScore, startedAt, submittedAt, usedSec, timeUsedText, statusText, durationMinutes, subChips, answeredPercent, e_1;
            if (fromPullDown === void 0) { fromPullDown = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true, errorText: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getExam(this.data.examId)];
                    case 2:
                        res = _a.sent();
                        exam = (res && res.exam) ? res.exam : (res || {});
                        questions = Array.isArray(res === null || res === void 0 ? void 0 : res.questions) ? res.questions : [];
                        total = questions.length;
                        correct_1 = 0;
                        wrong_1 = 0;
                        answered_1 = 0;
                        questions.forEach(function (q) {
                            var ua = String((q === null || q === void 0 ? void 0 : q.user_answer) || '').trim();
                            if (ua)
                                answered_1 += 1;
                            var ic = q === null || q === void 0 ? void 0 : q.is_correct;
                            if (ic === 1 || ic === true)
                                correct_1 += 1;
                            else if (ic === 0 || ic === false)
                                wrong_1 += 1;
                        });
                        unanswered = Math.max(0, total - answered_1);
                        accuracy = total ? Math.round((correct_1 * 1000) / total) / 10 : 0;
                        totalScore = Number((exam === null || exam === void 0 ? void 0 : exam.total_score) || 0) || 0;
                        startedAt = String((exam === null || exam === void 0 ? void 0 : exam.started_at) || '').trim();
                        submittedAt = String((exam === null || exam === void 0 ? void 0 : exam.submitted_at) || '').trim();
                        usedSec = this.data.usedSecHint;
                        if (!usedSec) {
                            usedSec = calcSecondsBetween(startedAt, submittedAt);
                        }
                        timeUsedText = usedSec != null ? formatSeconds(usedSec) : '--';
                        statusText = String((exam === null || exam === void 0 ? void 0 : exam.status) || '').trim() === 'submitted' ? '已交卷' : '进行中';
                        durationMinutes = Number((exam === null || exam === void 0 ? void 0 : exam.duration_minutes) || 0) || 0;
                        subChips = [];
                        if (durationMinutes > 0)
                            subChips.push("".concat(durationMinutes, " \u5206\u949F"));
                        if (total > 0)
                            subChips.push("".concat(total, " \u9898"));
                        if (timeUsedText && timeUsedText !== '--')
                            subChips.push("\u7528\u65F6 ".concat(timeUsedText));
                        answeredPercent = total > 0 ? Math.max(0, Math.min(100, Math.round((answered_1 * 100) / total))) : 0;
                        this.setData({
                            exam: exam,
                            statusText: statusText,
                            subChips: subChips,
                            total: total,
                            correct: correct_1,
                            wrong: wrong_1,
                            answered: answered_1,
                            unanswered: unanswered,
                            answeredPercent: answeredPercent,
                            accuracy: accuracy,
                            totalScore: totalScore,
                            startedAt: startedAt || '--',
                            submittedAt: submittedAt || '--',
                            timeUsedText: timeUsedText
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        this.setData({ errorText: (e_1 && e_1.message) || '加载失败' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        if (fromPullDown) {
                            try {
                                wx.stopPullDownRefresh();
                            }
                            catch (e) { }
                        }
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onTapReview: function () {
        var examId = this.data.examId;
        if (!examId)
            return;
        var pages = getCurrentPages();
        var prev = pages && pages.length > 1 ? pages[pages.length - 2] : null;
        if (prev && prev.route === 'pages/exam-run/exam-run') {
            wx.navigateBack({ delta: 1 });
            return;
        }
        wx.navigateTo({ url: "/pages/exam-run/exam-run?exam_id=".concat(encodeURIComponent(String(examId))) });
    },
    onTapMistakes: function () {
        return __awaiter(this, void 0, void 0, function () {
            var examId, res, count, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.toMistakesLoading)
                            return [2 /*return*/];
                        examId = this.data.examId;
                        if (!examId)
                            return [2 /*return*/];
                        this.setData({ toMistakesLoading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.examToMistakes(examId)];
                    case 2:
                        res = _a.sent();
                        count = Number((res === null || res === void 0 ? void 0 : res.count) || 0) || 0;
                        this.setData({ toMistakesDone: true, toMistakesCount: count });
                        if (count > 0)
                            wx.showToast({ title: "\u5DF2\u52A0\u5165\u9519\u9898\u672C\uFF1A".concat(count, " \u9898"), icon: 'none' });
                        else
                            wx.showToast({ title: '本次没有错题', icon: 'none' });
                        wx.navigateTo({ url: '/pages/mistakes-v2/mistakes-v2' });
                        return [3 /*break*/, 5];
                    case 3:
                        e_2 = _a.sent();
                        wx.showToast({ title: (e_2 && e_2.message) || '操作失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ toMistakesLoading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onTapNewExam: function () {
        wx.navigateTo({ url: '/pages/exams-select-v2/exams-select-v2' });
    },
    onTapExit: function () {
        wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
    },
    onShareAppMessage: function () {
        var exam = this.data.exam || {};
        var scope = String((exam === null || exam === void 0 ? void 0 : exam.subject) || '').trim() || '考试';
        var score = this.data.totalScore;
        var accuracy = this.data.accuracy;
        var title = "\u6211\u5B8C\u6210\u4E86\u300C".concat(scope, "\u300D\u8003\u8BD5\uFF1A\u5F97\u5206 ").concat(score, "\uFF0C\u6B63\u786E\u7387 ").concat(accuracy, "%");
        return {
            title: title,
            path: '/pages/exams-select-v2/exams-select-v2'
        };
    }
});
