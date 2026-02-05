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
// exam-run.ts - 模拟考试
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        examId: 0,
        loading: false,
        submitted: false,
        exam: null,
        questions: [],
        currentIndex: 0,
        currentQuestion: null,
        selectedAnswer: '',
        selectedAnswers: [],
        displayOptions: [],
        blankAnswers: [],
        blankIndexes: [],
        blankCount: 0,
        answers: {},
        showQuestionList: false,
        timeLeft: 0,
        timeText: '00:00'
    },
    draftTimer: null,
    tickTimer: null,
    goSettlement: function (opts) {
        var examId = Number(this.data.examId || 0);
        if (!Number.isFinite(examId) || examId <= 0)
            return;
        var params = [];
        params.push("exam_id=".concat(encodeURIComponent(String(examId))));
        var usedRaw = opts && typeof opts.usedSecHint !== 'undefined' ? Number(opts.usedSecHint) : 0;
        if (Number.isFinite(usedRaw) && usedRaw > 0) {
            params.push("used_sec=".concat(encodeURIComponent(String(Math.floor(usedRaw)))));
        }
        var autoSubmitted = !!(opts && opts.autoSubmitted);
        params.push("silent=".concat(autoSubmitted ? '1' : '0'));
        var url = "/pages/exam-settlement/exam-settlement?".concat(params.join('&'));
        var replace = opts && opts.replace === false ? false : true;
        var finalFail = function () {
            wx.showToast({ title: '无法打开结算页', icon: 'none' });
            wx.reLaunch({ url: '/pages/hub-v2/hub-v2' });
        };
        if (replace) {
            wx.redirectTo({
                url: url,
                fail: function (e) {
                    console.warn('redirectTo 结算页失败，尝试 navigateTo:', e);
                    wx.navigateTo({
                        url: url,
                        fail: function (e2) {
                            console.warn('navigateTo 结算页失败:', e2);
                            finalFail();
                        }
                    });
                }
            });
            return;
        }
        wx.navigateTo({
            url: url,
            fail: function (e) {
                console.warn('navigateTo 结算页失败，尝试 redirectTo:', e);
                wx.redirectTo({
                    url: url,
                    fail: function (e2) {
                        console.warn('redirectTo 结算页失败:', e2);
                        finalFail();
                    }
                });
            }
        });
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        var examId = Number(options.exam_id);
        if (!isFinite(examId) || examId <= 0) {
            wx.showToast({ title: '考试参数缺失', icon: 'none' });
            setTimeout(function () { return wx.navigateBack(); }, 1200);
            return;
        }
        this.setData({ examId: examId });
        this.loadExam();
    },
    onHide: function () {
        this.flushDraft();
    },
    onUnload: function () {
        this.flushDraft();
        if (this.tickTimer) {
            clearInterval(this.tickTimer);
            this.tickTimer = null;
        }
        if (this.draftTimer) {
            clearTimeout(this.draftTimer);
            this.draftTimer = null;
        }
    },
    loadExam: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, exam, questions_1, answers_1, submitted_1, durationMin, timeLeft, err_1;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getExam(this.data.examId)];
                    case 2:
                        res = _a.sent();
                        exam = res.exam || {};
                        questions_1 = (res.questions || []);
                        // 预览内容
                        questions_1 = questions_1.map(function (q) {
                            var content = q.content || '';
                            var text = String(content).replace(/<[^>]+>/g, '').replace(/\n/g, ' ').trim();
                            var preview = text.length > 40 ? text.slice(0, 40) + '...' : text;
                            var imageUrls = (0, api_1.normalizeImageUrls)(q.image_path);
                            var imagePath = imageUrls.length > 0 ? imageUrls[0] : '';
                            return Object.assign({}, q, { contentPreview: preview, image_urls: imageUrls, image_path: imagePath });
                        });
                        answers_1 = {};
                        questions_1.forEach(function (q) {
                            var ua = (q.user_answer || '').toString();
                            if (ua && q.id) {
                                answers_1[q.id] = ua;
                            }
                        });
                        submitted_1 = exam.status === 'submitted';
                        durationMin = Number(exam.duration_minutes) || 60;
                        timeLeft = submitted_1 ? 0 : this.computeRemainingSeconds(exam.started_at, durationMin);
                        this.setData({
                            exam: exam,
                            questions: questions_1,
                            answers: answers_1,
                            submitted: submitted_1,
                            timeLeft: timeLeft,
                            timeText: this.formatTime(timeLeft),
                            loading: false
                        }, function () {
                            if (questions_1.length > 0) {
                                _this.loadQuestion(0);
                            }
                            if (!submitted_1) {
                                _this.startTimer();
                            }
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载考试失败:', err_1);
                        this.setData({ loading: false });
                        wx.showToast({ title: (err_1 && err_1.message) || '加载失败', icon: 'none' });
                        setTimeout(function () { return wx.navigateBack(); }, 1200);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    computeRemainingSeconds: function (startedAt, durationMin) {
        var total = Math.max(1, durationMin) * 60;
        if (!startedAt)
            return total;
        var raw = String(startedAt || '').trim();
        if (!raw)
            return total;
        // 后端 sqlite CURRENT_TIMESTAMP 默认返回 UTC（无时区），这里按 UTC 解析，避免本地时区导致剩余时间直接变为 0
        var iso = raw.replace(' ', 'T');
        var hasTimezone = /[zZ]|([+-]\d{2}:?\d{2})$/.test(iso);
        var looksLikeNoTz = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(iso) ||
            /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(iso) ||
            /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+$/.test(iso);
        if (!hasTimezone && looksLikeNoTz) {
            iso = "".concat(iso, "Z");
        }
        var d = new Date(iso);
        if (isNaN(d.getTime()))
            return total;
        var elapsed = Math.floor((Date.now() - d.getTime()) / 1000);
        return Math.max(0, total - Math.max(0, elapsed));
    },
    startTimer: function () {
        var _this = this;
        if (this.tickTimer) {
            clearInterval(this.tickTimer);
        }
        this.tickTimer = setInterval(function () {
            var next = Math.max(0, (_this.data.timeLeft || 0) - 1);
            _this.setData({ timeLeft: next, timeText: _this.formatTime(next) });
            if (next <= 0) {
                clearInterval(_this.tickTimer);
                _this.tickTimer = null;
                _this.autoSubmitWhenTimeout();
            }
        }, 1000);
    },
    formatTime: function (sec) {
        var s = Math.max(0, Number(sec) || 0);
        var m = Math.floor(s / 60);
        var r = s % 60;
        return "".concat(String(m).padStart(2, '0'), ":").concat(String(r).padStart(2, '0'));
    },
    autoSubmitWhenTimeout: function () {
        if (this.data.submitted)
            return;
        wx.showToast({ title: '时间到，正在交卷', icon: 'none' });
        this.doSubmitExam(true);
    },
    loadQuestion: function (index) {
        var _this = this;
        var questions = this.data.questions;
        if (index < 0 || index >= questions.length)
            return;
        var q = questions[index];
        var qType = q.q_type || '';
        var rawContent = (q.content || '').toString();
        var rawAnswer = (q.answer || '').toString();
        var displayContent = this.formatContentForDisplay(rawContent);
        if (qType === '填空题') {
            displayContent = displayContent.replace(/__/g, '____');
        }
        var isCode = this.looksLikeCode(displayContent);
        if (isCode) {
            displayContent = this.preserveSpacesForCode(displayContent);
        }
        var displayAnswer = this.formatAnswerForDisplay(qType, rawAnswer);
        var rawExplanation = (q.explanation || '').toString();
        var explanationIsCode = this.looksLikeCode(rawExplanation);
        var displayExplanation = explanationIsCode ? this.preserveSpacesForCode(rawExplanation) : rawExplanation;
        var normalizedOptions = this.normalizeOptions(q.options, qType, rawAnswer);
        var blankState = this.initBlankState(qType, rawContent, rawAnswer);
        // 恢复草稿答案
        var ua = (this.data.answers && q.id) ? (this.data.answers[q.id] || '') : '';
        var selectedAnswer = '';
        var selectedAnswers = [];
        var blankAnswers = blankState.blankAnswers.slice();
        var blankCount = blankState.blankCount;
        var blankIndexes = blankState.blankIndexes.slice();
        if (ua) {
            if (qType === '多选题') {
                selectedAnswers = ua.split('').filter(Boolean);
            }
            else if (qType === '选择题' || qType === '判断题') {
                selectedAnswer = ua;
            }
            else if (qType === '填空题') {
                var normalized = ua.replace(/；；/g, ';;').replace(/；/g, ';');
                // 多空：后端保存可能是 JSON 数组字符串
                try {
                    var tmp_1 = JSON.parse(normalized);
                    if (Array.isArray(tmp_1)) {
                        var filledCount = Math.max(blankCount, tmp_1.length);
                        blankCount = filledCount;
                        blankIndexes = Array.from({ length: filledCount }, function (_, i) { return i; });
                        blankAnswers = Array.from({ length: filledCount }, function (_, i) { return String(tmp_1[i] || ''); });
                    }
                }
                catch (e) {
                    var parts_1 = normalized.split(';;').map(function (x) { return x.trim(); }).filter(function (x) { return x.length > 0; });
                    if (parts_1.length > 0) {
                        var filledCount = Math.max(blankCount, parts_1.length);
                        blankCount = filledCount;
                        blankIndexes = Array.from({ length: filledCount }, function (_, i) { return i; });
                        blankAnswers = Array.from({ length: filledCount }, function (_, i) { return parts_1[i] || ''; });
                    }
                }
            }
            else if (qType === '简答题' || qType === '计算题') {
                selectedAnswer = ua;
            }
        }
        this.setData({
            currentIndex: index,
            currentQuestion: Object.assign({}, q, {
                displayContent: displayContent,
                displayAnswer: displayAnswer,
                options: normalizedOptions,
                isCode: isCode,
                explanationIsCode: explanationIsCode,
                displayExplanation: displayExplanation
            }),
            selectedAnswer: selectedAnswer,
            selectedAnswers: selectedAnswers,
            blankCount: blankCount,
            blankAnswers: blankAnswers,
            blankIndexes: blankIndexes
        }, function () {
            _this.refreshDisplayOptions();
        });
    },
    onSelectAnswer: function (e) {
        var _this = this;
        if (this.data.submitted)
            return;
        var answer = e.currentTarget.dataset.answer || '';
        var cq = this.data.currentQuestion;
        if (!cq)
            return;
        var qType = cq.q_type || '';
        if (qType === '多选题') {
            var next = (this.data.selectedAnswers || []).slice();
            var i = next.indexOf(answer);
            if (i > -1)
                next.splice(i, 1);
            else
                next.push(answer);
            this.setData({ selectedAnswers: next }, function () {
                _this.refreshDisplayOptions();
                _this.saveCurrentAnswerDraft();
            });
            return;
        }
        this.setData({ selectedAnswer: answer }, function () {
            _this.refreshDisplayOptions();
            _this.saveCurrentAnswerDraft();
        });
    },
    onInputAnswer: function (e) {
        var _this = this;
        if (this.data.submitted)
            return;
        this.setData({ selectedAnswer: e.detail.value || '' }, function () {
            _this.saveCurrentAnswerDraft();
        });
    },
    onBlankInput: function (e) {
        var _this = this;
        if (this.data.submitted)
            return;
        var idx = Number(e.currentTarget.dataset.index);
        if (!isFinite(idx) || idx < 0)
            return;
        var next = (this.data.blankAnswers || []).slice();
        next[idx] = e.detail.value;
        this.setData({ blankAnswers: next }, function () {
            _this.saveCurrentAnswerDraft();
        });
    },
    saveCurrentAnswerDraft: function () {
        var _this = this;
        var cq = this.data.currentQuestion;
        if (!cq || !cq.id)
            return;
        var qType = cq.q_type || '';
        var qid = cq.id;
        var ua = this.serializeCurrentAnswer(qType);
        var nextAnswers = Object.assign({}, this.data.answers);
        nextAnswers[qid] = ua;
        this.setData({ answers: nextAnswers }, function () {
            _this.queueDraftSave(qid, ua);
        });
    },
    serializeCurrentAnswer: function (qType) {
        if (qType === '多选题') {
            return (this.data.selectedAnswers || []).slice().sort().join('');
        }
        if (qType === '选择题' || qType === '判断题') {
            return (this.data.selectedAnswer || '').trim();
        }
        if (qType === '填空题') {
            var blanks = (this.data.blankAnswers || []).map(function (x) { return (x || '').trim(); });
            if (blanks.length <= 1) {
                return (blanks[0] || '').trim();
            }
            return JSON.stringify(blanks);
        }
        // 主观题
        return (this.data.selectedAnswer || '').toString();
    },
    queueDraftSave: function (qid, ua) {
        var _this = this;
        if (this.draftTimer) {
            clearTimeout(this.draftTimer);
            this.draftTimer = null;
        }
        this.draftTimer = setTimeout(function () {
            _this.draftTimer = null;
            _this.flushDraftSingle(qid, ua);
        }, 250);
    },
    flushDraftSingle: function (qid, ua) {
        return __awaiter(this, void 0, void 0, function () {
            var e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.submitted)
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.saveExamDraft(this.data.examId, [{ question_id: qid, user_answer: ua || '' }])];
                    case 2:
                        _a.sent();
                        return [3 /*break*/, 4];
                    case 3:
                        e_1 = _a.sent();
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    flushDraft: function () {
        // 简化处理：交由单题保存的防抖完成；卸载时不做批量提交，避免卡顿
        if (this.draftTimer) {
            clearTimeout(this.draftTimer);
            this.draftTimer = null;
        }
    },
    onPrevQuestion: function () {
        if (this.data.currentIndex > 0)
            this.loadQuestion(this.data.currentIndex - 1);
    },
    onNextQuestion: function () {
        var idx = this.data.currentIndex;
        if (idx < this.data.questions.length - 1) {
            this.loadQuestion(idx + 1);
        }
        else {
            if (this.data.submitted) {
                this.goSettlement({ replace: false });
                return;
            }
            // 最后一题：引导直接交卷
            this.submitExam(false);
        }
    },
    onOpenQuestionList: function () {
        this.setData({ showQuestionList: true });
    },
    onCloseQuestionList: function () {
        this.setData({ showQuestionList: false });
    },
    onQuestionListItemTap: function (e) {
        var index = Number(e.currentTarget.dataset.index);
        if (!isFinite(index))
            return;
        this.loadQuestion(index);
        this.onCloseQuestionList();
    },
    stopPropagation: function () { },
    onSubmitExam: function () {
        if (this.data.submitted) {
            this.goSettlement({ replace: false });
            return;
        }
        this.submitExam(false);
    },
    submitExam: function (silent) {
        var _this = this;
        if (this.data.submitted)
            return;
        if (silent) {
            this.doSubmitExam(true);
            return;
        }
        wx.showModal({
            title: '确认交卷',
            content: '交卷后将无法继续修改答案，是否继续？',
            confirmText: '交卷',
            confirmColor: '#FF3B30',
            success: function (res) {
                if (!res.confirm)
                    return;
                _this.doSubmitExam(false);
            }
        });
    },
    doSubmitExam: function (silent) {
        return __awaiter(this, void 0, void 0, function () {
            var autoSubmitted, durationMin, timeLeftBefore, usedSecHint, answers, res, total, correct, score, err_2;
            var _this = this;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (this.data.submitted)
                            return [2 /*return*/];
                        wx.showLoading({ title: '提交中...' });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        autoSubmitted = !!silent;
                        durationMin = Number(((_a = this.data.exam) === null || _a === void 0 ? void 0 : _a.duration_minutes) || 0) || 0;
                        timeLeftBefore = Math.max(0, Number(this.data.timeLeft || 0) || 0);
                        usedSecHint = durationMin > 0 ? Math.max(0, durationMin * 60 - timeLeftBefore) : 0;
                        answers = this.data.questions.map(function (q) { return ({
                            question_id: q.id,
                            user_answer: (_this.data.answers && q.id) ? (_this.data.answers[q.id] || '') : ''
                        }); });
                        return [4 /*yield*/, api_1.api.submitExam(this.data.examId, answers)];
                    case 2:
                        res = _b.sent();
                        wx.hideLoading();
                        if (this.tickTimer) {
                            clearInterval(this.tickTimer);
                            this.tickTimer = null;
                        }
                        this.setData({ submitted: true, timeLeft: 0, timeText: '00:00' });
                        total = res.total || 0;
                        correct = res.correct || 0;
                        score = res.total_score || 0;
                        try {
                            wx.setStorageSync('exam_settlement_payload_v1', {
                                exam_id: this.data.examId,
                                total: total,
                                correct: correct,
                                score: score,
                                used_sec: usedSecHint,
                                auto_submitted: autoSubmitted ? 1 : 0,
                                ts: Date.now()
                            });
                        }
                        catch (e) { }
                        this.goSettlement({ usedSecHint: usedSecHint, autoSubmitted: autoSubmitted, replace: true });
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _b.sent();
                        console.error('提交考试失败:', err_2);
                        wx.hideLoading();
                        wx.showToast({ title: (err_2 && err_2.message) || '提交失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // ====== 工具函数（复用 quiz 页） ======
    refreshDisplayOptions: function () {
        var _a = this.data, currentQuestion = _a.currentQuestion, selectedAnswer = _a.selectedAnswer, selectedAnswers = _a.selectedAnswers;
        if (!currentQuestion) {
            this.setData({ displayOptions: [] });
            return;
        }
        var qType = currentQuestion.q_type || '';
        var normalizedOptions = this.normalizeOptions(currentQuestion.options, qType, currentQuestion.answer);
        var displayOptions = normalizedOptions.map(function (opt) {
            var isSelected = qType === '多选题' ? selectedAnswers.indexOf(opt.answerValue) > -1 : selectedAnswer === opt.answerValue;
            var className = isSelected ? 'selected' : '';
            return Object.assign({}, opt, { isSelected: isSelected, className: className });
        });
        this.setData({ displayOptions: displayOptions, currentQuestion: Object.assign({}, currentQuestion, { options: normalizedOptions }) });
    },
    normalizeOptions: function (rawOptions, qType, correctAnswer) {
        var optList = rawOptions;
        if (typeof optList === 'string') {
            var s = optList.trim();
            if (!s) {
                optList = [];
            }
            else {
                try {
                    optList = JSON.parse(s);
                }
                catch (e) {
                    optList = [s];
                }
            }
        }
        if (!Array.isArray(optList)) {
            optList = [];
        }
        if (qType === '判断题') {
            var ans = (correctAnswer || '').toString().trim();
            if (!/^[A-Za-z]$/.test(ans)) {
                var normalized = ans.toLowerCase();
                var trueText = '正确';
                var falseText = '错误';
                if (normalized === '对' || normalized === '错') {
                    trueText = '对';
                    falseText = '错';
                }
                else if (normalized === '是' || normalized === '否') {
                    trueText = '是';
                    falseText = '否';
                }
                else if (normalized === 'true' || normalized === 'false') {
                    trueText = 'True';
                    falseText = 'False';
                }
                return [
                    { key: 'A', value: trueText, answerValue: trueText },
                    { key: 'B', value: falseText, answerValue: falseText }
                ];
            }
        }
        var options = [];
        for (var _i = 0, optList_1 = optList; _i < optList_1.length; _i++) {
            var item = optList_1[_i];
            if (item && typeof item === 'object') {
                var rawKey = item.key;
                var rawValue = item.value;
                var key = String(rawKey == null ? '' : rawKey).trim();
                var value = String(rawValue == null ? '' : rawValue).trim();
                if (key || value) {
                    options.push({ key: key, value: value, answerValue: key || value });
                }
                continue;
            }
            var s = String(item == null ? '' : item).trim();
            if (!s)
                continue;
            var m = s.match(/^([A-Za-z0-9]+)[、.．:：\s]+(.+)$/);
            if (m) {
                var key = m[1].trim().slice(0, 1).toUpperCase();
                var value = m[2].trim();
                options.push({ key: key, value: value, answerValue: key });
                continue;
            }
            var first = s.slice(0, 1).toUpperCase();
            if (first && 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.includes(first)) {
                var value = s.slice(1).replace(/^[\s:：.,、]+/, '').trim();
                options.push({ key: first, value: value, answerValue: first });
                continue;
            }
            options.push({ key: '', value: s, answerValue: s });
        }
        if (options.length > 0 && options.every(function (x) { return !(x.key || '').trim(); })) {
            var seed_1 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            options.forEach(function (x, i) {
                x.key = seed_1[i] || String(i + 1);
            });
        }
        return options;
    },
    initBlankState: function (qType, content, answer) {
        if (qType !== '填空题') {
            return { blankCount: 0, blankAnswers: [], blankIndexes: [] };
        }
        var contentCount = (content.match(/__/g) || []).length;
        var normalizedAnswer = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
        var answerCount = normalizedAnswer.split(';;').length;
        var blankCount = Math.max(1, contentCount || 0, answerCount || 0);
        return {
            blankCount: blankCount,
            blankAnswers: Array.from({ length: blankCount }, function () { return ''; }),
            blankIndexes: Array.from({ length: blankCount }, function (_, i) { return i; })
        };
    },
    formatContentForDisplay: function (content) {
        return (content || '').toString();
    },
    looksLikeCode: function (text) {
        var s = (text || '').toString();
        if (!s.includes('\n'))
            return false;
        var hasIndent = /(^|\n)[ \t]{2,}\S/.test(s);
        var hasCodeTokens = /\b(for|while|if|else|elif|def|class|print|return|break|continue|import|from|int|float|public|private|static|void|main)\b/.test(s);
        var hasSymbols = /[{}();=<>]/.test(s);
        return hasIndent || hasCodeTokens || hasSymbols;
    },
    preserveSpacesForCode: function (text) {
        var s = (text || '').toString().replace(/\t/g, '  ');
        return s
            .split('\n')
            .map(function (line) { return line.replace(/ /g, '\u00A0'); })
            .join('\n');
    },
    formatAnswerForDisplay: function (qType, answer) {
        var a = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
        if (qType === '填空题') {
            return a.replace(/;;/g, ' / ').replace(/;/g, ' 或 ');
        }
        return a;
    },
    onQuestionImageError: function (e) {
        var idx = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.index) || -1);
        var q = this.data.currentQuestion;
        var urls = (q && q.image_urls) || [];
        if (!Array.isArray(urls) || urls.length === 0)
            return;
        if (!Number.isFinite(idx) || idx < 0 || idx >= urls.length)
            return;
        var url = String(urls[idx] || '').trim();
        if (!url || !/^https?:\/\//i.test(url))
            return;
        var self = this;
        self.__imgDlTried = self.__imgDlTried || {};
        var key = "".concat(q && q.id ? q.id : 'q', "_").concat(idx, "_").concat(url);
        if (self.__imgDlTried[key])
            return;
        self.__imgDlTried[key] = true;
        wx.downloadFile({
            url: url,
            timeout: 15000,
            success: function (res) {
                var tempFilePath = String((res && res.tempFilePath) || '').trim();
                if (!tempFilePath)
                    return;
                var nextUrls = urls.slice();
                nextUrls[idx] = tempFilePath;
                var nextQuestion = Object.assign({}, q, { image_urls: nextUrls });
                var currentIndex = Number(self.data.currentIndex || 0);
                var nextQuestions = Array.isArray(self.data.questions) ? self.data.questions.slice() : [];
                if (currentIndex >= 0 && currentIndex < nextQuestions.length) {
                    nextQuestions[currentIndex] = Object.assign({}, nextQuestions[currentIndex], { image_urls: nextUrls });
                }
                self.setData({ currentQuestion: nextQuestion, questions: nextQuestions });
            },
            fail: function (err) {
                console.warn('downloadFile 题目图片失败:', url, err);
            }
        });
    },
    previewImage: function (e) {
        var idx = Number(e.currentTarget.dataset.index || 0);
        var urls = (this.data.currentQuestion && this.data.currentQuestion.image_urls) || [];
        if (!Array.isArray(urls) || urls.length === 0)
            return;
        var current = urls[Math.max(0, Math.min(idx, urls.length - 1))] || urls[0];
        wx.previewImage({ urls: urls, current: current });
    }
});
