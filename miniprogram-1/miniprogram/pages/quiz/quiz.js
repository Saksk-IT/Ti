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
// quiz.ts - 刷题/背题页面
// 支持公有题库（subject参数）和个人题库（bank_id参数）双数据源
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var quiz_source_1 = require("../../utils/quiz-source");
var markdown_1 = require("../../utils/markdown");
var theme_1 = require("../../utils/theme");
var request_state_1 = require("../../behaviors/request-state");
var set_data_batcher_1 = require("../../utils/set-data-batcher");
var quiz_helpers_1 = require("./modules/quiz-helpers");
// 数据源实例（页面级别）
var quizSource = null;
function buildQuestionImageFields(q) {
    var contentUrls = (0, quiz_helpers_1.uniqUrls)(__spreadArray(__spreadArray(__spreadArray([], (0, api_1.normalizeImageUrls)(q === null || q === void 0 ? void 0 : q.image_path), true), (0, api_1.normalizeImageUrls)(q === null || q === void 0 ? void 0 : q.content_images), true), (0, quiz_helpers_1.extractInlineImageUrls)(q === null || q === void 0 ? void 0 : q.content), true));
    var answerUrls = (0, quiz_helpers_1.uniqUrls)(__spreadArray([], (0, api_1.normalizeImageUrls)(q === null || q === void 0 ? void 0 : q.answer_images), true));
    var explanationUrls = (0, quiz_helpers_1.uniqUrls)(__spreadArray([], (0, api_1.normalizeImageUrls)(q === null || q === void 0 ? void 0 : q.explanation_images), true));
    return {
        image_urls: contentUrls,
        answer_image_urls: answerUrls,
        explanation_image_urls: explanationUrls,
        image_path: contentUrls.length > 0 ? contentUrls[0] : ''
    };
}
Page({
    behaviors: [request_state_1.requestStateBehavior],
    data: {
        mode: 'quiz', // 模式：'quiz' | 'memo' | 'reinforce'
        // 数据源信息
        sourceType: '', // 数据源类型
        sourceId: '', // 数据源标识
        displayName: '', // 显示名称
        source: 'all', // 数据范围：all/favorites/mistakes
        qType: 'all', // 题型筛选（用于进度key）
        tag: 'all', // 标签筛选（用于进度key & 服务端筛选）
        shuffleQuestions: false, // 打乱题目（用于进度key）
        shuffleOptions: false, // 打乱选项（用于进度key & 服务端确定性打乱）
        reinforceKind: '', // 加强：rk=wrong/similar（仅 mode=reinforce 生效，用于进度隔离）
        reinforceIds: [], // 加强：ids=1,2,3（指定题目列表）
        startId: 0, // 从搜索等入口指定起始题目ID
        questions: [], // 题目列表
        currentIndex: 0, // 当前题目索引
        currentQuestion: null, // 当前题目对象
        selectedAnswer: '', // 选中的答案（刷题模式 - 单选题/判断题/填空题）
        selectedAnswers: [], // 多选题答案数组
        showAnswer: false, // 是否显示答案（刷题模式）
        isFavorite: false, // 是否收藏
        isCorrect: false, // 回答是否正确（刷题模式）
        isJudgable: true, // 是否可自动判分（主观题为 false）
        loading: false, // 加载状态
        showQuestionList: false, // 是否显示题目列表抽屉
        displayOptions: [],
        blankAnswers: [],
        blankIndexes: [],
        blankCount: 0,
        showSubmitButton: false,
        submitDisabled: true,
        userAnswerText: '',
        // 刷题设置
        showSettings: false,
        practiceSettings: {
            autoNextOnCorrect: false, // 答对自动切题（答错不切题）
            autoFavoriteOnWrong: false, // 做错自动收藏
            vibrationFeedback: false // 答题震动反馈
        },
        // 字体大小（仅影响答题页字体）
        quizFontSize: 'md', // 'sm' | 'md' | 'lg'
        quizFontClass: 'quiz-font-md',
        themeStyleName: '默认',
        // 主题（深浅/风格）
        isDarkMode: false,
        themeMode: 'system',
        themeClass: '',
        themeStyle: 'default',
        themeStyleClass: '',
        themeCtaColor: '#007AFF',
        // AI 解析
        showAIExplain: false,
        scrollIntoView: '',
        aiLoading: false,
        aiExplainText: '',
        aiExplainRichText: '',
        aiExplainError: '',
        aiExplainQuestionId: 0,
        // 进度信息
        progress: {
            current: 0, // 当前题号
            total: 0 // 总题数
        },
        // 答题记录（用于题目列表显示状态）
        answerRecords: {},
        // 标签管理
        canEdit: false, // 是否可以编辑题目
        currentQuestionTags: [], // 当前题目的标签
        showTagModal: false, // 是否显示标签弹窗
        allTags: [], // 所有标签
        newTagName: '', // 新标签名称输入
        // 编辑题目
        showEditModal: false, // 是否显示编辑弹窗
        editForm: {
            content: '',
            options: '',
            answer: '',
            explanation: '',
            showOptions: false
        },
        editSaving: false, // 编辑保存中
        // 滑屏切题
        touchStartX: 0,
        touchStartY: 0
    },
    // === 进度同步（与 Web 端 /api/progress 互通）===
    progressKey: '',
    progressStatusMap: {},
    progressAnswerMap: {},
    progressOrder: null,
    saveProgressTimer: null,
    syncPending: false,
    lastSavedPayload: null,
    practiceSettingsKey: 'quiz_practice_settings_v1',
    quizFontSizeKey: 'quiz_font_size_v1',
    sessionStartedAt: 0,
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
    onShow: function () {
        try {
            wx.hideShareMenu();
        }
        catch (e) { }
    },
    // 统一退出：返回进入本次答题页的页面（优先 navigateBack，单页栈兜底回首页）
    navigateBackToEntry: function () {
        var pages = getCurrentPages();
        if (pages && pages.length > 1) {
            wx.navigateBack({ delta: 1 });
            return;
        }
        wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
    },
    onNavBack: function () {
        this.navigateBackToEntry();
    },
    onLoad: function (options) {
        var _this = this;
        this.ensureSetDataBatcher();
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        this.sessionStartedAt = Date.now();
        // 编辑权限初始为 false，在 loadQuestions 中根据数据源类型判断
        // 公有题库：管理员或科目管理员
        // 个人题库：题库创建者
        // 初始化主题（保证进入页面即命中 themeClass / themeStyleClass）
        try {
            this.patchData(Object.assign({ canEdit: false }, theme_1.themeManager.getPageData()), undefined, true);
            this.syncThemeStyleName();
        }
        catch (e) {
            this.patchData({ canEdit: false }, undefined, true);
        }
        // 使用工厂函数创建数据源
        quizSource = (0, quiz_source_1.createSourceFromOptions)(options);
        if (!quizSource) {
            wx.showToast({ title: '参数缺失', icon: 'none' });
            setTimeout(function () {
                _this.navigateBackToEntry();
            }, 1500);
            return;
        }
        // 解析参数
        var modeRaw = String(options.mode || 'quiz').trim().toLowerCase();
        var mode = (modeRaw === 'memo' || modeRaw === 'reinforce') ? modeRaw : 'quiz';
        var type = options.type || 'all';
        var tag = options.tag || 'all';
        var source = mode === 'reinforce' ? 'all' : (options.source || 'all');
        var shuffleQuestions = options.shuffle_questions === '1';
        var shuffleOptions = options.shuffle_options === '1';
        var startId = Number(options.start_id || 0);
        var rkRaw = String(options.rk || '').trim().toLowerCase();
        var reinforceKind = mode === 'reinforce' && (rkRaw === 'wrong' || rkRaw === 'similar') ? rkRaw : '';
        var reinforceIds = mode === 'reinforce' ? (0, quiz_helpers_1.parseIdList)(options.ids || options.question_ids, 200) : [];
        if (mode === 'reinforce' && !reinforceIds.length) {
            wx.showToast({ title: '缺少加强题目列表', icon: 'none' });
            setTimeout(function () {
                _this.navigateBackToEntry();
            }, 1200);
            return;
        }
        // 题型可能会被 encodeURIComponent（如"选择题"），需显式解码避免后端筛选不匹配
        try {
            type = decodeURIComponent(type);
        }
        catch (e) {
            // ignore decode error
        }
        // 标签可能会被 encodeURIComponent（如"重点"），需显式解码
        try {
            tag = decodeURIComponent(tag);
        }
        catch (e) {
            // ignore decode error
        }
        this.setData({
            mode: mode,
            sourceType: quizSource.sourceType,
            sourceId: quizSource.sourceId,
            displayName: quizSource.displayName || String(quizSource.sourceId),
            source: source,
            qType: type || 'all',
            tag: tag || 'all',
            shuffleQuestions: shuffleQuestions,
            shuffleOptions: shuffleOptions,
            reinforceKind: reinforceKind,
            reinforceIds: reinforceIds,
            startId: isFinite(startId) && startId > 0 ? startId : 0,
            loading: true
        });
        this.initPracticeSettings();
        this.initQuizFontSize();
        this.syncThemeStyleName();
        this.loadQuestions(type, source, shuffleQuestions, shuffleOptions, tag);
    },
    isNonEmptyAnswerValue: function (val) {
        if (val == null)
            return false;
        if (Array.isArray(val)) {
            if (!val.length)
                return false;
            return val.some(function (x) { return String(x || '').trim().length > 0; });
        }
        var s = String(val || '').trim();
        return s.length > 0;
    },
    openQuizSettlement: function () {
        var questions = Array.isArray(this.data.questions) ? this.data.questions : [];
        var total = questions.length;
        var statusMap = (this.progressStatusMap && typeof this.progressStatusMap === 'object') ? this.progressStatusMap : {};
        var answerMap = (this.progressAnswerMap && typeof this.progressAnswerMap === 'object') ? this.progressAnswerMap : {};
        var answered = 0;
        var correct = 0;
        var wrong = 0;
        var wrongIds = [];
        for (var i = 0; i < total; i++) {
            var st = statusMap[String(i)];
            if (st === 'correct')
                correct += 1;
            if (st === 'wrong')
                wrong += 1;
            var hasStatus = st === 'correct' || st === 'wrong';
            var hasAnswer = this.isNonEmptyAnswerValue(answerMap[String(i)]);
            if (hasStatus || hasAnswer) {
                answered += 1;
            }
            if (st === 'wrong') {
                var q = questions[i];
                var qid = Number(q && q.id ? q.id : 0);
                if (Number.isFinite(qid) && qid > 0)
                    wrongIds.push(qid);
            }
        }
        var accuracy = answered ? Math.round((correct * 1000) / answered) / 10 : 0;
        var usedSec = this.sessionStartedAt ? Math.max(0, Math.floor((Date.now() - Number(this.sessionStartedAt || 0)) / 1000)) : 0;
        var payload = {
            ts: Date.now(),
            sourceType: this.data.sourceType,
            sourceId: this.data.sourceId,
            displayName: this.data.displayName || '',
            mode: this.data.mode,
            source: this.data.source,
            qType: this.data.qType,
            tag: this.data.tag,
            shuffleQuestions: !!this.data.shuffleQuestions,
            shuffleOptions: !!this.data.shuffleOptions,
            reinforceKind: this.data.reinforceKind || '',
            total: total,
            answered: answered,
            correct: correct,
            wrong: wrong,
            accuracy: accuracy,
            usedSec: usedSec,
            wrongIds: wrongIds
        };
        try {
            wx.setStorageSync('quiz_settlement_payload_v1', payload);
        }
        catch (e) { }
        wx.navigateTo({
            url: '/pages/quiz-settlement/quiz-settlement',
            fail: function (e) {
                // ignore
                wx.redirectTo({ url: '/pages/quiz-settlement/quiz-settlement' });
            }
        });
    },
    initPracticeSettings: function () {
        try {
            var raw = wx.getStorageSync(this.practiceSettingsKey);
            if (raw && typeof raw === 'object') {
                var s = raw;
                var next = {
                    autoNextOnCorrect: !!s.autoNextOnCorrect,
                    autoFavoriteOnWrong: !!s.autoFavoriteOnWrong,
                    vibrationFeedback: !!s.vibrationFeedback
                };
                this.setData({ practiceSettings: next });
            }
        }
        catch (e) {
            // 忽略本地存储异常
        }
    },
    savePracticeSettings: function () {
        try {
            wx.setStorageSync(this.practiceSettingsKey, this.data.practiceSettings);
        }
        catch (e) {
            // 忽略本地存储异常
        }
    },
    normalizeQuizFontSize: function (raw) {
        var v = String(raw || '').trim().toLowerCase();
        return (v === 'sm' || v === 'md' || v === 'lg') ? v : 'md';
    },
    initQuizFontSize: function () {
        try {
            var raw = wx.getStorageSync(this.quizFontSizeKey);
            var size = this.normalizeQuizFontSize(raw);
            this.setData({ quizFontSize: size, quizFontClass: "quiz-font-".concat(size) });
        }
        catch (e) {
            // ignore
        }
    },
    saveQuizFontSize: function (size) {
        try {
            wx.setStorageSync(this.quizFontSizeKey, size);
        }
        catch (e) {
            // ignore
        }
    },
    setQuizFontSize: function (size) {
        var _this = this;
        var next = this.normalizeQuizFontSize(size);
        this.setData({ quizFontSize: next, quizFontClass: "quiz-font-".concat(next) }, function () {
            _this.saveQuizFontSize(next);
            wx.showToast({ title: '已切换字体', icon: 'none' });
        });
    },
    onFontSizeSelect: function (e) {
        var _a, _b;
        var size = (_b = (_a = e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.size;
        this.setQuizFontSize(size);
    },
    syncThemeStyleName: function () {
        try {
            this.setData({ themeStyleName: theme_1.themeManager.getStyleName() });
        }
        catch (e) {
            // ignore
        }
    },
    onThemeChange: function (_isDark) {
        this.syncThemeStyleName();
    },
    onCycleThemeStyle: function () {
        try {
            var next = theme_1.themeManager.cycleStyle();
            this.syncThemeStyleName();
            wx.showToast({ title: "\u5DF2\u5207\u6362\u5230".concat(theme_1.themeManager.getStyleName(), "\u4E3B\u9898"), icon: 'none' });
            return next;
        }
        catch (e) {
            // ignore
        }
    },
    onToggleTheme: function () {
        try {
            theme_1.themeManager.toggleDark();
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) {
            // ignore
        }
    },
    onOpenSettings: function () {
        this.setData({ showSettings: true });
    },
    onCloseSettings: function () {
        this.setData({ showSettings: false });
    },
    onSettingSwitchChange: function (e) {
        var _this = this;
        var _a, _b;
        var key = (_b = (_a = e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key;
        var value = !!(e && e.detail && e.detail.value);
        if (!key)
            return;
        var next = Object.assign({}, this.data.practiceSettings);
        next[key] = value;
        this.setData({ practiceSettings: next }, function () { return _this.savePracticeSettings(); });
    },
    onClearCurrentAnswerRecord: function () {
        var _this = this;
        var cq = this.data.currentQuestion;
        if (!cq)
            return;
        wx.showModal({
            title: '清除本题记录',
            content: '确定清除本题的作答与本地进度吗？',
            confirmText: '清除',
            confirmColor: '#ff3b30',
            success: function (res) {
                if (!res.confirm)
                    return;
                var idx = Number(_this.data.currentIndex) || 0;
                var qType = (cq.q_type || '').toString();
                // 清理本地进度缓存（answers/status）
                try {
                    if (_this.progressAnswerMap && typeof _this.progressAnswerMap === 'object') {
                        delete _this.progressAnswerMap[String(idx)];
                    }
                    if (_this.progressStatusMap && typeof _this.progressStatusMap === 'object') {
                        delete _this.progressStatusMap[String(idx)];
                    }
                }
                catch (e) { }
                // 清理题目列表状态（✓/✕）
                try {
                    var nextRecords = Object.assign({}, _this.data.answerRecords || {});
                    if (cq && typeof cq.id === 'number') {
                        delete nextRecords[cq.id];
                    }
                    _this.setData({ answerRecords: nextRecords });
                }
                catch (e) { }
                var nextBlankAnswers = qType === '填空题' ? new Array(Number(_this.data.blankCount) || 0).fill('') : [];
                _this.setData({
                    showSettings: false,
                    showAnswer: false,
                    isCorrect: false,
                    userAnswerText: '',
                    selectedAnswer: '',
                    selectedAnswers: [],
                    blankAnswers: nextBlankAnswers,
                    showAIExplain: false,
                    aiLoading: false,
                    aiExplainText: '',
                    aiExplainRichText: '',
                    aiExplainError: '',
                    aiExplainQuestionId: 0,
                    scrollIntoView: ''
                }, function () {
                    _this.refreshDisplayOptions();
                    _this.updateSubmitState();
                });
                // 立即同步到云端（仅进度/答案缓存；不回滚服务器的答题统计）
                _this.saveProgressIndex(true);
                wx.showToast({ title: '已清除', icon: 'none' });
            }
        });
    },
    // 加载题目列表（使用数据源适配器）
    loadQuestions: function (type, source, shuffleQuestions, shuffleOptions, tag) {
        return __awaiter(this, void 0, void 0, function () {
            var _a, mode, sourceType, sourceId, requestMode, reinforceIds, canEdit, userInfo, currentUserId, bankDetail, bankName, bankOwnerId, e_1, e_2, result, questions, total, questionsWithPreview, pKey, saved, savedPayload, hasHistory, nextPayload, restoredRecords, idx, startId_1, found, safeIndex, err_1, errorMsg;
            var _this = this;
            var _b, _c;
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        if (!quizSource) {
                            this.setData({ loading: false });
                            return [2 /*return*/];
                        }
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 12, , 13]);
                        _a = this.data, mode = _a.mode, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        requestMode = mode === 'reinforce' ? 'quiz' : mode;
                        reinforceIds = mode === 'reinforce' ? (this.data.reinforceIds || []) : [];
                        canEdit = false;
                        _d.label = 2;
                    case 2:
                        _d.trys.push([2, 8, , 9]);
                        userInfo = wx.getStorageSync('userInfo') || {};
                        currentUserId = userInfo.id || userInfo.user_id;
                        if (!(sourceType === 'public')) return [3 /*break*/, 3];
                        // 公有题库：管理员或科目管理员
                        canEdit = !!(userInfo.is_admin || userInfo.is_subject_admin);
                        return [3 /*break*/, 7];
                    case 3:
                        if (!(sourceType === 'bank')) return [3 /*break*/, 7];
                        _d.label = 4;
                    case 4:
                        _d.trys.push([4, 6, , 7]);
                        return [4 /*yield*/, api_1.api.getBankDetail(Number(sourceId))];
                    case 5:
                        bankDetail = _d.sent();
                        bankName = (bankDetail === null || bankDetail === void 0 ? void 0 : bankDetail.name) || ((_b = bankDetail === null || bankDetail === void 0 ? void 0 : bankDetail.data) === null || _b === void 0 ? void 0 : _b.name);
                        if (bankName && (!this.data.displayName || /^\d+$/.test(this.data.displayName))) {
                            this.setData({ displayName: bankName });
                        }
                        // 检查是否是题库创建者
                        if (currentUserId) {
                            bankOwnerId = (bankDetail === null || bankDetail === void 0 ? void 0 : bankDetail.user_id) || ((_c = bankDetail === null || bankDetail === void 0 ? void 0 : bankDetail.data) === null || _c === void 0 ? void 0 : _c.user_id);
                            canEdit = bankOwnerId && Number(bankOwnerId) === Number(currentUserId);
                        }
                        return [3 /*break*/, 7];
                    case 6:
                        e_1 = _d.sent();
                        return [3 /*break*/, 7];
                    case 7: return [3 /*break*/, 9];
                    case 8:
                        e_2 = _d.sent();
                        return [3 /*break*/, 9];
                    case 9:
                        this.setData({ canEdit: canEdit });
                        return [4 /*yield*/, quizSource.getQuestions({
                                mode: requestMode,
                                source: source,
                                type: type !== 'all' ? type : undefined,
                                tag: tag && tag !== 'all' ? tag : undefined,
                                shuffle_questions: shuffleQuestions,
                                shuffle_options: shuffleOptions,
                                ids: (reinforceIds && reinforceIds.length) ? reinforceIds : undefined,
                                per_page: 1000 // 一次性加载所有题目
                            })];
                    case 10:
                        result = _d.sent();
                        questions = result.questions || [];
                        total = result.total || questions.length;
                        // 统一 options 结构，避免不同历史数据格式导致前端无法渲染
                        questions = questions.map(function (q) {
                            var normalizedOptions = _this.normalizeOptions(q.options, q.q_type, q.answer);
                            return Object.assign({}, q, { options: normalizedOptions }, buildQuestionImageFields(q));
                        });
                        questionsWithPreview = questions.map(function (q) {
                            var content = q.content || '';
                            var textContent = content.replace(/<[^>]+>/g, ''); // 移除HTML标签
                            var preview = textContent.length > 40 ? textContent.substring(0, 40) + '...' : textContent;
                            return Object.assign({}, q, { contentPreview: preview });
                        });
                        pKey = this.buildProgressKey();
                        this.progressKey = pKey;
                        return [4 /*yield*/, this.loadProgressState(pKey)];
                    case 11:
                        saved = _d.sent();
                        savedPayload = (saved && typeof saved === 'object') ? saved : null;
                        // 初始化进度缓存
                        this.progressStatusMap = (savedPayload && savedPayload.status && typeof savedPayload.status === 'object') ? savedPayload.status : {};
                        this.progressAnswerMap = (savedPayload && savedPayload.answers && typeof savedPayload.answers === 'object') ? savedPayload.answers : {};
                        this.progressOrder = (savedPayload && Array.isArray(savedPayload.order)) ? savedPayload.order : null;
                        // 打乱题目顺序：优先使用已保存的 order；无 order 时再生成并同步到云端
                        if (shuffleQuestions && questionsWithPreview.length > 0) {
                            hasHistory = !!(savedPayload && ((savedPayload.status && Object.keys(savedPayload.status).length) || (savedPayload.answers && Object.keys(savedPayload.answers).length)));
                            if (this.progressOrder && Array.isArray(this.progressOrder)) {
                                questionsWithPreview = this.applyQuestionOrder(questionsWithPreview, this.progressOrder);
                            }
                            else {
                                // 如果已有历史答题痕迹但缺少order，兜底：把当前顺序作为order保存，避免索引错位
                                if (hasHistory) {
                                    this.progressOrder = questionsWithPreview.map(function (q) { return q.id; });
                                }
                                else {
                                    questionsWithPreview = this.shuffleArray(questionsWithPreview.slice());
                                    this.progressOrder = questionsWithPreview.map(function (q) { return q.id; });
                                }
                                nextPayload = Object.assign({}, savedPayload || {});
                                if (typeof nextPayload.index !== 'number')
                                    nextPayload.index = 0;
                                if (!nextPayload.status || typeof nextPayload.status !== 'object')
                                    nextPayload.status = this.progressStatusMap || {};
                                if (!nextPayload.answers || typeof nextPayload.answers !== 'object')
                                    nextPayload.answers = this.progressAnswerMap || {};
                                nextPayload.order = this.progressOrder;
                                nextPayload.timestamp = Date.now();
                                // 保存一次order（避免多端乱序不一致）
                                this.saveProgressState(nextPayload, true);
                            }
                        }
                        restoredRecords = this.buildAnswerRecordsFromStatus(questionsWithPreview, this.progressStatusMap);
                        this.setData({
                            questions: questionsWithPreview,
                            loading: false,
                            answerRecords: restoredRecords,
                            progress: {
                                current: 1,
                                total: total
                            }
                        });
                        // 加载第一题
                        if (questionsWithPreview.length > 0) {
                            idx = savedPayload && typeof savedPayload.index === 'number' ? savedPayload.index : 0;
                            startId_1 = this.data.startId;
                            if (startId_1 && startId_1 > 0) {
                                found = questionsWithPreview.findIndex(function (q) { return q && q.id === startId_1; });
                                if (found >= 0) {
                                    idx = found;
                                }
                            }
                            safeIndex = Math.max(0, Math.min(idx, questionsWithPreview.length - 1));
                            this.loadQuestion(safeIndex);
                        }
                        else {
                            wx.showToast({ title: '暂无题目', icon: 'none' });
                            setTimeout(function () {
                                _this.navigateBackToEntry();
                            }, 1500);
                        }
                        return [3 /*break*/, 13];
                    case 12:
                        err_1 = _d.sent();
                        errorMsg = (err_1 && err_1.message) || '加载失败';
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            wx.reLaunch({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: errorMsg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 13];
                    case 13: return [2 /*return*/];
                }
            });
        });
    },
    // 加载指定题目
    loadQuestion: function (index) {
        var _this = this;
        var questions = this.data.questions;
        if (index < 0 || index >= questions.length) {
            return;
        }
        var question = questions[index];
        var qType = question.q_type || '';
        var rawContent = (question.content || '').toString();
        var rawAnswer = (question.answer || '').toString();
        var displayContent = this.formatContentForDisplay(rawContent);
        if (qType === '填空题') {
            // 填空题挖空：仅填空题替换，避免代码里的 __ 被误改
            displayContent = displayContent.replace(/__/g, '____');
        }
        var isCode = this.looksLikeCode(displayContent);
        if (isCode) {
            displayContent = this.preserveSpacesForCode(displayContent);
        }
        var displayAnswer = this.formatAnswerForDisplay(qType, rawAnswer);
        var rawExplanation = (question.explanation || '').toString();
        var explanationIsCode = this.looksLikeCode(rawExplanation);
        var displayExplanation = explanationIsCode ? this.preserveSpacesForCode(rawExplanation) : rawExplanation;
        var normalizedOptions = this.normalizeOptions(question.options, qType, rawAnswer);
        var blankState = this.initBlankState(qType, rawContent, rawAnswer);
        var blankCount = blankState.blankCount;
        var blankAnswers = blankState.blankAnswers;
        var blankIndexes = blankState.blankIndexes;
        // 恢复当前题目的已保存作答（未提交也会恢复“草稿”）
        var savedAnswer = this.getSavedAnswerForIndex(index);
        var savedStatus = this.getSavedStatusForIndex(index);
        var selectedAnswer = '';
        var selectedAnswers = [];
        var nextBlankAnswers = blankAnswers.slice();
        var showAnswer = false;
        var isCorrect = false;
        var userAnswerText = '';
        if (Array.isArray(savedAnswer)) {
            if (qType === '多选题') {
                selectedAnswers = savedAnswer.map(function (x) { return String(x); }).filter(Boolean);
                userAnswerText = selectedAnswers.slice().sort().join('');
            }
            else if (qType === '选择题' || qType === '判断题') {
                selectedAnswer = savedAnswer.length > 0 ? String(savedAnswer[0]) : '';
                userAnswerText = selectedAnswer;
            }
            else if (qType === '填空题') {
                var trimmed_1 = savedAnswer.map(function (x) { return (x == null ? '' : String(x)); }).map(function (x) { return x.trim(); });
                // 适配空数变化
                var filledCount = Math.max(blankCount, trimmed_1.length);
                var filled = Array.from({ length: filledCount }, function (_, i) { return trimmed_1[i] || ''; });
                blankCount = filledCount;
                blankIndexes = Array.from({ length: filledCount }, function (_, i) { return i; });
                nextBlankAnswers = filled.slice(0, filledCount);
                userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
            }
        }
        else if (typeof savedAnswer === 'string') {
            if (qType === '填空题') {
                var parts_1 = savedAnswer.split(';;').map(function (x) { return x.trim(); }).filter(function (x) { return x.length > 0; });
                var filledCount = Math.max(blankCount, parts_1.length);
                var filled = Array.from({ length: filledCount }, function (_, i) { return parts_1[i] || ''; });
                blankCount = filledCount;
                blankIndexes = Array.from({ length: filledCount }, function (_, i) { return i; });
                nextBlankAnswers = filled.slice(0, filledCount);
                userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
            }
            else {
                selectedAnswer = savedAnswer;
                userAnswerText = savedAnswer;
            }
        }
        // 仅自动判分题型恢复“已批改”状态
        if ((qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题') && (savedStatus === 'correct' || savedStatus === 'wrong')) {
            showAnswer = true;
            isCorrect = savedStatus === 'correct';
        }
        this.setData({
            currentIndex: index,
            currentQuestion: Object.assign({}, question, {
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
            blankAnswers: nextBlankAnswers,
            blankIndexes: blankIndexes,
            showAnswer: showAnswer,
            isJudgable: this.isAutoJudgable(qType),
            isCorrect: isCorrect,
            userAnswerText: userAnswerText,
            isFavorite: question.is_fav === 1 || question.is_fav === true,
            showAIExplain: false,
            scrollIntoView: '',
            aiLoading: false,
            aiExplainText: '',
            aiExplainRichText: '',
            aiExplainError: '',
            aiExplainQuestionId: question.id || 0,
            progress: {
                current: index + 1,
                total: this.data.progress.total
            }
        }, function () {
            _this.refreshDisplayOptions();
            _this.updateSubmitState();
            _this.saveProgressIndex(false);
        });
    },
    // 选择答案（单选题/判断题）
    onSelectAnswer: function (e) {
        var _this = this;
        if (this.data.showAnswer || this.data.mode === 'memo') {
            return; // 已提交或背题模式不允许选择
        }
        var answer = e.currentTarget.dataset.answer || '';
        var currentQuestion = this.data.currentQuestion;
        var qType = currentQuestion.q_type || '';
        // 多选题处理
        if (qType === '多选题') {
            var selectedAnswers = this.data.selectedAnswers.slice();
            var index = selectedAnswers.indexOf(answer);
            if (index > -1) {
                selectedAnswers.splice(index, 1); // 取消选择
            }
            else {
                selectedAnswers.push(answer); // 选择
            }
            this.setData({ selectedAnswers: selectedAnswers }, function () {
                _this.refreshDisplayOptions();
                _this.updateSubmitState();
                _this.saveDraftAnswer();
            });
        }
        else {
            // 单选题/判断题
            this.setData({ selectedAnswer: answer }, function () {
                _this.refreshDisplayOptions();
                _this.updateSubmitState();
                // 选择题、判断题：点选即判
                if ((_this.data.mode === 'quiz' || _this.data.mode === 'reinforce') && !_this.data.showAnswer && (qType === '选择题' || qType === '判断题')) {
                    _this.onSubmitAnswer();
                }
            });
        }
    },
    // 输入答案（主观题：问答/计算/简答）
    onInputAnswer: function (e) {
        var _this = this;
        if (this.data.showAnswer || this.data.mode === 'memo') {
            return;
        }
        var cq = this.data.currentQuestion;
        var qType = (cq && cq.q_type) || '';
        if (qType === '填空题') {
            return;
        }
        this.setData({ selectedAnswer: e.detail.value }, function () {
            _this.updateSubmitState();
            _this.saveDraftAnswer();
        });
    },
    // 输入答案（填空题：多空）
    onBlankInput: function (e) {
        var _this = this;
        if (this.data.showAnswer || this.data.mode === 'memo') {
            return;
        }
        var cq = this.data.currentQuestion;
        var qType = (cq && cq.q_type) || '';
        if (qType !== '填空题') {
            return;
        }
        var idx = Number(e.currentTarget.dataset.index);
        if (!isFinite(idx) || idx < 0) {
            return;
        }
        var next = this.data.blankAnswers.slice();
        next[idx] = e.detail.value;
        this.setData({ blankAnswers: next }, function () {
            _this.updateSubmitState();
            _this.saveDraftAnswer();
        });
    },
    // 提交答案（刷题模式）
    onSubmitAnswer: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, currentQuestion, selectedAnswer, selectedAnswers, mode, blankAnswers, qType, isJudgable, userAnswer, userAnswerText, normalized, t, correctAnswer, isCorrect, nextRecords, questions, err_2, vibrateType;
            var _this = this;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, currentQuestion = _a.currentQuestion, selectedAnswer = _a.selectedAnswer, selectedAnswers = _a.selectedAnswers, mode = _a.mode, blankAnswers = _a.blankAnswers;
                        if (mode === 'memo') {
                            return [2 /*return*/]; // 背题模式不需要提交
                        }
                        if (!currentQuestion) {
                            return [2 /*return*/];
                        }
                        qType = currentQuestion.q_type || '';
                        isJudgable = this.isAutoJudgable(qType);
                        userAnswer = '';
                        userAnswerText = '';
                        if (qType === '多选题') {
                            if (selectedAnswers.length === 0) {
                                wx.showToast({ title: '请选择答案', icon: 'none' });
                                return [2 /*return*/];
                            }
                            userAnswer = selectedAnswers.sort().join(''); // 排序后拼接
                            userAnswerText = userAnswer;
                        }
                        else if (qType === '填空题') {
                            normalized = (blankAnswers || []).map(function (x) { return (x || '').trim(); });
                            if (normalized.length === 0 || normalized.some(function (x) { return !x; })) {
                                wx.showToast({ title: '请填写所有空', icon: 'none' });
                                return [2 /*return*/];
                            }
                            userAnswer = normalized.join(';;');
                            userAnswerText = normalized.join(' / ');
                        }
                        else if (qType === '简答题' || qType === '计算题') {
                            t = (selectedAnswer || '').trim();
                            if (!t) {
                                wx.showToast({ title: '请输入答案', icon: 'none' });
                                return [2 /*return*/];
                            }
                            userAnswer = t;
                            userAnswerText = t;
                        }
                        else {
                            if (!selectedAnswer) {
                                wx.showToast({ title: '请选择或输入答案', icon: 'none' });
                                return [2 /*return*/];
                            }
                            userAnswer = selectedAnswer.trim();
                            userAnswerText = userAnswer;
                        }
                        correctAnswer = currentQuestion.answer || '';
                        isCorrect = isJudgable ? this.checkAnswer(userAnswer, correctAnswer, qType) : false;
                        // 更新进度缓存（answers/status/order/index）
                        this.setProgressAnswerForIndex(this.data.currentIndex, qType);
                        if (isJudgable) {
                            this.progressStatusMap = this.progressStatusMap || {};
                            this.progressStatusMap[String(this.data.currentIndex)] = isCorrect ? 'correct' : 'wrong';
                        }
                        this.patchData({
                            showAnswer: true,
                            isCorrect: isCorrect,
                            isJudgable: isJudgable,
                            userAnswerText: userAnswerText
                        }, function () {
                            _this.refreshDisplayOptions();
                            _this.updateSubmitState();
                        });
                        // 记录答题结果（主观题不自动判分，避免误记错题）
                        if (isJudgable) {
                            nextRecords = Object.assign({}, this.data.answerRecords);
                            nextRecords[currentQuestion.id] = {
                                answered: true,
                                isCorrect: isCorrect
                            };
                            this.patchData({
                                answerRecords: nextRecords
                            });
                        }
                        // 更新 questions 列表里的错题标记（保证“错题本”筛选能即时生效）
                        if (isJudgable) {
                            questions = this.data.questions.map(function (q) {
                                if (q.id !== currentQuestion.id)
                                    return q;
                                return Object.assign({}, q, { is_mistake: isCorrect ? 0 : 1 });
                            });
                            this.patchData({ questions: questions });
                        }
                        // 重要操作：立即同步进度到云端
                        this.saveProgressIndex(true);
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        if (!(isJudgable && quizSource)) return [3 /*break*/, 3];
                        return [4 /*yield*/, quizSource.recordResult({
                                questionId: currentQuestion.id,
                                userAnswer: userAnswer,
                                isCorrect: isCorrect
                            })];
                    case 2:
                        _b.sent();
                        _b.label = 3;
                    case 3: return [3 /*break*/, 5];
                    case 4:
                        err_2 = _b.sent();
                        wx.showToast({ title: '记录结果失败，已忽略', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 5:
                        // 震动反馈（提交后）
                        if (isJudgable && this.data.practiceSettings.vibrationFeedback) {
                            try {
                                vibrateType = isCorrect ? 'medium' : 'heavy';
                                // @ts-ignore - 部分基础库不支持 type 参数
                                wx.vibrateShort({ type: vibrateType });
                            }
                            catch (e) {
                                try {
                                    wx.vibrateShort();
                                }
                                catch (e2) {
                                    // ignore
                                }
                            }
                        }
                        if (!(isJudgable && !isCorrect && this.data.practiceSettings.autoFavoriteOnWrong)) return [3 /*break*/, 7];
                        return [4 /*yield*/, this.autoFavoriteIfNeeded()];
                    case 6:
                        _b.sent();
                        _b.label = 7;
                    case 7:
                        // 答对自动切题（给用户一点点反馈时间）
                        if (isJudgable && isCorrect && this.data.practiceSettings.autoNextOnCorrect) {
                            setTimeout(function () {
                                // 仍在当前题且已展示答案时再切题
                                if (_this.data.showAnswer && _this.data.currentQuestion && _this.data.currentQuestion.id === currentQuestion.id) {
                                    _this.onNextQuestion();
                                }
                            }, 650);
                        }
                        return [2 /*return*/];
                }
            });
        });
    },
    autoFavoriteIfNeeded: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, currentQuestion, isFavorite, questions, err_3;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, currentQuestion = _a.currentQuestion, isFavorite = _a.isFavorite;
                        if (!currentQuestion || isFavorite || !quizSource)
                            return [2 /*return*/];
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, quizSource.toggleFavorite(currentQuestion.id)];
                    case 2:
                        _b.sent();
                        this.patchData({ isFavorite: true });
                        questions = this.data.questions.map(function (q) {
                            if (q.id === currentQuestion.id)
                                return Object.assign({}, q, { is_fav: 1 });
                            return q;
                        });
                        this.patchData({ questions: questions });
                        return [3 /*break*/, 4];
                    case 3:
                        err_3 = _b.sent();
                        wx.showToast({ title: '自动收藏失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onToggleAIExplain: function () {
        var _this = this;
        var next = !this.data.showAIExplain;
        if (!next) {
            this.patchData({ showAIExplain: false, scrollIntoView: '' });
            return;
        }
        this.patchData({ showAIExplain: true, scrollIntoView: '' }, function () {
            _this.loadAIExplain(false);
            setTimeout(function () {
                if (_this.data.showAIExplain) {
                    _this.patchData({ scrollIntoView: 'aiExplainCard' });
                }
            }, 60);
        });
    },
    onRegenerateAIExplain: function () {
        this.loadAIExplain(true);
    },
    loadAIExplain: function (force) {
        return __awaiter(this, void 0, void 0, function () {
            var cq, qid, cached, options, res, text, cleaned, finalText, err_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        cq = this.data.currentQuestion;
                        if (!cq)
                            return [2 /*return*/];
                        qid = Number(cq.id) || 0;
                        if (!force && this.data.aiExplainText && this.data.aiExplainQuestionId === qid) {
                            return [2 /*return*/];
                        }
                        if (!force && qid) {
                            cached = (0, quiz_helpers_1.readAIExplainCache)(qid);
                            if (cached) {
                                this.patchData({
                                    aiLoading: false,
                                    aiExplainError: '',
                                    aiExplainText: cached,
                                    aiExplainRichText: (0, markdown_1.markdownToRichTextHtml)(cached),
                                    aiExplainQuestionId: qid
                                });
                                return [2 /*return*/];
                            }
                        }
                        options = Array.isArray(cq.options)
                            ? cq.options.map(function (x) { return ({ key: x.key, value: x.value }); })
                            : undefined;
                        this.patchData({ aiLoading: true, aiExplainError: '', aiExplainText: '', aiExplainRichText: '', aiExplainQuestionId: qid });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.aiExplain({
                                question_id: qid || undefined,
                                content: (cq.content || '').toString(),
                                q_type: (cq.q_type || '').toString(),
                                options: options
                            })];
                    case 2:
                        res = _a.sent();
                        text = (res && res.explain) ? String(res.explain) : '';
                        cleaned = (text || '').toString().trim();
                        if (cleaned) {
                            (0, quiz_helpers_1.writeAIExplainCache)(qid, cleaned);
                        }
                        finalText = cleaned || '暂无解析内容';
                        this.patchData({
                            aiExplainText: finalText,
                            aiExplainRichText: (0, markdown_1.markdownToRichTextHtml)(finalText),
                            aiLoading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_4 = _a.sent();
                        this.patchData({ aiExplainError: (err_4 === null || err_4 === void 0 ? void 0 : err_4.message) || 'AI解析失败，请稍后重试', aiLoading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 检查答案是否正确
    checkAnswer: function (userAnswer, correctAnswer, qType) {
        if (qType === '多选题') {
            // 多选题：答案排序后比较
            var userAnswerSorted = userAnswer.split('').sort().join('');
            var correctAnswerSorted = correctAnswer.split('').sort().join('');
            return userAnswerSorted === correctAnswerSorted;
        }
        else if (qType === '填空题') {
            // 填空题：支持一题多空（;; 分隔），一空多答案（; 分隔）
            var userBlanks = userAnswer.split(';;').map(function (x) { return x.trim(); });
            var normalizedCorrect = (correctAnswer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
            var correctBlanksRaw = normalizedCorrect.split(';;').map(function (x) { return x.trim(); });
            var blankCount = Math.max(userBlanks.length, correctBlanksRaw.length, 1);
            for (var i = 0; i < blankCount; i++) {
                var userBlank = (userBlanks[i] || '').trim();
                var correctBlank = (correctBlanksRaw[i] || '').trim();
                if (!userBlank) {
                    return false;
                }
                if (!correctBlank) {
                    return false;
                }
                var correctAlternatives = correctBlank
                    .split(';')
                    .map(function (x) { return x.trim(); })
                    .filter(Boolean)
                    .map(function (x) { return x.toLowerCase(); });
                var u = userBlank.toLowerCase();
                if (correctAlternatives.length === 0) {
                    if (u !== correctBlank.toLowerCase()) {
                        return false;
                    }
                }
                else {
                    if (!correctAlternatives.includes(u)) {
                        return false;
                    }
                }
            }
            return true;
        }
        else {
            // 单选题/判断题/填空题：直接比较（忽略大小写和空格）
            var ua = userAnswer.trim().toLowerCase();
            var ca = (correctAnswer || '').toString().replace(/；/g, ';').trim().toLowerCase();
            // 支持单空多答案（; 分隔）
            if (ca.includes(';')) {
                var candidates = ca
                    .split(';')
                    .map(function (x) { return x.trim(); })
                    .filter(Boolean);
                return candidates.includes(ua);
            }
            return ua === ca;
        }
    },
    // 切换收藏（使用数据源适配器）
    onToggleFavorite: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, currentQuestion, isFavorite, result, newFavoriteState_1, questions, err_5;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, currentQuestion = _a.currentQuestion, isFavorite = _a.isFavorite;
                        if (!currentQuestion || !quizSource) {
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, quizSource.toggleFavorite(currentQuestion.id)];
                    case 2:
                        result = _b.sent();
                        newFavoriteState_1 = result.is_favorite !== undefined ? result.is_favorite : !isFavorite;
                        this.setData({
                            isFavorite: newFavoriteState_1
                        });
                        questions = this.data.questions.map(function (q) {
                            if (q.id === currentQuestion.id) {
                                return Object.assign({}, q, { is_fav: newFavoriteState_1 ? 1 : 0 });
                            }
                            return q;
                        });
                        this.setData({ questions: questions });
                        wx.showToast({
                            title: newFavoriteState_1 ? '已收藏' : '已取消收藏',
                            icon: 'none',
                            duration: 1500
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_5 = _b.sent();
                        wx.showToast({ title: err_5.message || '操作失败', icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 上一题
    onPrevQuestion: function () {
        var currentIndex = this.data.currentIndex;
        if (currentIndex > 0) {
            this.loadQuestion(currentIndex - 1);
        }
    },
    // 下一题
    onNextQuestion: function () {
        var _a = this.data, currentIndex = _a.currentIndex, questions = _a.questions;
        if (currentIndex < questions.length - 1) {
            this.loadQuestion(currentIndex + 1);
        }
        else {
            // 最后一题：进入结算页（替代答题结束弹窗）
            this.openQuizSettlement();
        }
    },
    // 打开题目列表抽屉
    onOpenQuestionList: function () {
        this.setData({ showQuestionList: true });
    },
    // 关闭题目列表抽屉
    onCloseQuestionList: function () {
        this.setData({ showQuestionList: false });
    },
    // 点击题目列表项
    onQuestionListItemTap: function (e) {
        var index = e.currentTarget.dataset.index;
        this.loadQuestion(index);
        this.onCloseQuestionList();
    },
    // 工具函数：打乱数组
    shuffleArray: function (array) {
        var shuffled = array.slice();
        for (var i = shuffled.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var tmp = shuffled[i];
            shuffled[i] = shuffled[j];
            shuffled[j] = tmp;
        }
        return shuffled;
    },
    onQuestionImageError: function (e) {
        var _this = this;
        var idx = Number((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.index) || -1);
        var field = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.field) || 'image_urls');
        if (['image_urls', 'answer_image_urls', 'explanation_image_urls'].indexOf(field) === -1)
            return;
        var q = this.data.currentQuestion;
        var urls = (q && q[field]) || [];
        if (!Array.isArray(urls) || urls.length === 0)
            return;
        if (!Number.isFinite(idx) || idx < 0 || idx >= urls.length)
            return;
        var url = String(urls[idx] || '').trim();
        if (!url || !/^https?:\/\//i.test(url))
            return;
        var self = this;
        self.__imgDlTried = self.__imgDlTried || {};
        var key = "".concat(q && q.id ? q.id : 'q', "_").concat(field, "_").concat(idx, "_").concat(url);
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
                var nextImagePatch = {};
                nextImagePatch[field] = nextUrls;
                var nextQuestion = Object.assign({}, q, nextImagePatch);
                var currentIndex = Number(_this.data.currentIndex || 0);
                var nextQuestions = Array.isArray(_this.data.questions) ? _this.data.questions.slice() : [];
                if (currentIndex >= 0 && currentIndex < nextQuestions.length) {
                    nextQuestions[currentIndex] = Object.assign({}, nextQuestions[currentIndex], nextImagePatch);
                }
                _this.setData({ currentQuestion: nextQuestion, questions: nextQuestions });
            },
            fail: function () {
                // ignore
            }
        });
    },
    // 预览图片
    previewImage: function (e) {
        var idx = Number(e.currentTarget.dataset.index || 0);
        var field = String((e.currentTarget.dataset && e.currentTarget.dataset.field) || 'image_urls');
        if (['image_urls', 'answer_image_urls', 'explanation_image_urls'].indexOf(field) === -1)
            return;
        var urls = (this.data.currentQuestion && this.data.currentQuestion[field]) || [];
        if (!Array.isArray(urls) || urls.length === 0)
            return;
        var current = urls[Math.max(0, Math.min(idx, urls.length - 1))] || urls[0];
        wx.previewImage({ urls: urls, current: current });
    },
    // 阻止事件冒泡（用于抽屉）
    stopPropagation: function () {
        // 空函数，用于阻止点击事件冒泡
    },
    // === 标签管理 ===
    onOpenTagModal: function () {
        return __awaiter(this, void 0, void 0, function () {
            var currentQuestion;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        currentQuestion = this.data.currentQuestion;
                        if (!currentQuestion)
                            return [2 /*return*/];
                        this.setData({ showTagModal: true, newTagName: '' });
                        return [4 /*yield*/, this.loadAllTags()];
                    case 1:
                        _a.sent();
                        return [4 /*yield*/, this.loadQuestionTags()];
                    case 2:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onCloseTagModal: function () {
        this.setData({ showTagModal: false });
    },
    onTagNameInput: function (e) {
        this.setData({ newTagName: (e.detail.value || '').trim() });
    },
    onCreateTag: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, newTagName, sourceType, sourceId, subject, err_6;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, newTagName = _a.newTagName, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        if (!newTagName) {
                            wx.showToast({ title: '请输入标签名', icon: 'none' });
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 7, , 8]);
                        if (!(sourceType === 'bank')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.createBankTag(Number(sourceId), newTagName)];
                    case 2:
                        _b.sent();
                        return [3 /*break*/, 5];
                    case 3:
                        subject = String(sourceId || '').trim();
                        return [4 /*yield*/, api_1.api.createTag(newTagName, { subject: subject })];
                    case 4:
                        _b.sent();
                        _b.label = 5;
                    case 5:
                        this.setData({ newTagName: '' });
                        return [4 /*yield*/, this.loadAllTags()];
                    case 6:
                        _b.sent();
                        wx.showToast({ title: '创建成功', icon: 'none' });
                        return [3 /*break*/, 8];
                    case 7:
                        err_6 = _b.sent();
                        wx.showToast({ title: err_6.message || '创建失败', icon: 'none' });
                        return [3 /*break*/, 8];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    onToggleTagSelection: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var tagName, _a, currentQuestion, allTags, currentQuestionTags, sourceType, sourceId, tagItem, isSelected, newTags, updatedAllTags, err_7;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        tagName = e.currentTarget.dataset.tag;
                        if (!tagName)
                            return [2 /*return*/];
                        _a = this.data, currentQuestion = _a.currentQuestion, allTags = _a.allTags, currentQuestionTags = _a.currentQuestionTags, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        if (!currentQuestion)
                            return [2 /*return*/];
                        tagItem = allTags.find(function (t) { return t.name === tagName; });
                        if (!tagItem)
                            return [2 /*return*/];
                        isSelected = tagItem.selected;
                        if (isSelected) {
                            // 取消选中
                            newTags = currentQuestionTags.filter(function (t) { return t !== tagName; });
                        }
                        else {
                            // 选中
                            newTags = __spreadArray(__spreadArray([], currentQuestionTags, true), [tagName], false);
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        if (!(sourceType === 'bank')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.setBankQuestionTags(Number(sourceId), currentQuestion.id, newTags)];
                    case 2:
                        _b.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.setQuestionTags(currentQuestion.id, newTags)];
                    case 4:
                        _b.sent();
                        _b.label = 5;
                    case 5:
                        updatedAllTags = allTags.map(function (t) { return (__assign(__assign({}, t), { selected: newTags.includes(t.name), count: t.name === tagName ? (isSelected ? t.count - 1 : t.count + 1) : t.count })); });
                        this.setData({
                            currentQuestionTags: newTags,
                            allTags: updatedAllTags
                        });
                        return [3 /*break*/, 7];
                    case 6:
                        err_7 = _b.sent();
                        wx.showToast({ title: err_7.message || '设置失败', icon: 'none' });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    loadAllTags: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, sourceType, sourceId, res, subject, tags, currentQuestionTags_1, allTags, err_8;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 5, , 6]);
                        _a = this.data, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        res = void 0;
                        if (!(sourceType === 'bank')) return [3 /*break*/, 2];
                        return [4 /*yield*/, api_1.api.getBankTags(Number(sourceId))];
                    case 1:
                        res = _b.sent();
                        return [3 /*break*/, 4];
                    case 2:
                        subject = String(sourceId || '').trim();
                        return [4 /*yield*/, api_1.api.getTags({ subject: subject })];
                    case 3:
                        res = _b.sent();
                        _b.label = 4;
                    case 4:
                        tags = res.tags || res || [];
                        currentQuestionTags_1 = this.data.currentQuestionTags;
                        allTags = tags.map(function (t) { return ({
                            name: t.name || t,
                            count: t.count || 0,
                            selected: currentQuestionTags_1.includes(t.name || t)
                        }); });
                        this.setData({ allTags: allTags });
                        return [3 /*break*/, 6];
                    case 5:
                        err_8 = _b.sent();
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    loadQuestionTags: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, currentQuestion, sourceType, sourceId, res, tags, tagNames_1, allTags, updatedAllTags, err_9;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, currentQuestion = _a.currentQuestion, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        if (!currentQuestion)
                            return [2 /*return*/];
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        res = void 0;
                        if (!(sourceType === 'bank')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.getBankQuestionTags(Number(sourceId), currentQuestion.id)];
                    case 2:
                        res = _b.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.getQuestionTags(currentQuestion.id)];
                    case 4:
                        res = _b.sent();
                        _b.label = 5;
                    case 5:
                        tags = res.tags || res || [];
                        tagNames_1 = tags.map(function (t) { return t.name || t; });
                        allTags = this.data.allTags;
                        updatedAllTags = allTags.map(function (t) { return (__assign(__assign({}, t), { selected: tagNames_1.includes(t.name) })); });
                        this.setData({
                            currentQuestionTags: tagNames_1,
                            allTags: updatedAllTags
                        });
                        return [3 /*break*/, 7];
                    case 6:
                        err_9 = _b.sent();
                        this.setData({ currentQuestionTags: [] });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    // === 编辑题目 ===
    onEditQuestion: function () {
        var _a = this.data, currentQuestion = _a.currentQuestion, canEdit = _a.canEdit;
        if (!currentQuestion || !canEdit)
            return;
        var qType = currentQuestion.q_type || '';
        var showOptions = qType === '选择题' || qType === '多选题' || qType === '判断题';
        // 格式化选项为文本
        var optionsText = '';
        if (showOptions && Array.isArray(currentQuestion.options)) {
            optionsText = currentQuestion.options
                .map(function (opt) { return "".concat(opt.key, ". ").concat(opt.value); })
                .join('\n');
        }
        this.setData({
            showEditModal: true,
            editForm: {
                content: currentQuestion.content || '',
                options: optionsText,
                answer: currentQuestion.answer || '',
                explanation: currentQuestion.explanation || '',
                showOptions: showOptions
            }
        });
    },
    onCloseEditModal: function () {
        this.setData({ showEditModal: false });
    },
    onEditContentInput: function (e) {
        this.setData({ 'editForm.content': e.detail.value });
    },
    onEditOptionsInput: function (e) {
        this.setData({ 'editForm.options': e.detail.value });
    },
    onEditAnswerInput: function (e) {
        this.setData({ 'editForm.answer': e.detail.value });
    },
    onEditExplanationInput: function (e) {
        this.setData({ 'editForm.explanation': e.detail.value });
    },
    onSaveQuestion: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, currentQuestion, editForm, editSaving, sourceType, sourceId, options, updateData, updatedQuestion_1, questions, err_10;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, currentQuestion = _a.currentQuestion, editForm = _a.editForm, editSaving = _a.editSaving, sourceType = _a.sourceType, sourceId = _a.sourceId;
                        if (!currentQuestion || editSaving)
                            return [2 /*return*/];
                        if (!editForm.content.trim()) {
                            wx.showToast({ title: '题干不能为空', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (!editForm.answer.trim()) {
                            wx.showToast({ title: '答案不能为空', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ editSaving: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        options = void 0;
                        if (editForm.showOptions && editForm.options.trim()) {
                            options = editForm.options
                                .split('\n')
                                .map(function (line) { return line.trim(); })
                                .filter(function (line) { return line; })
                                .map(function (line) {
                                var match = line.match(/^([A-Za-z0-9]{1,3})\s*[、.．:：]\s*(.+)$/);
                                if (match) {
                                    return { key: match[1].toUpperCase(), value: match[2].trim() };
                                }
                                return { key: '', value: line };
                            });
                        }
                        updateData = {
                            content: editForm.content.trim(),
                            options: options,
                            answer: editForm.answer.trim(),
                            explanation: editForm.explanation.trim() || undefined
                        };
                        if (!(sourceType === 'bank')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.updateBankQuestion(Number(sourceId), currentQuestion.id, updateData)];
                    case 2:
                        _b.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.updateQuestion(currentQuestion.id, updateData)];
                    case 4:
                        _b.sent();
                        _b.label = 5;
                    case 5:
                        updatedQuestion_1 = __assign(__assign({}, currentQuestion), { content: editForm.content.trim(), answer: editForm.answer.trim(), explanation: editForm.explanation.trim() });
                        if (options) {
                            updatedQuestion_1.options = options;
                        }
                        questions = this.data.questions.map(function (q) {
                            if (q.id === currentQuestion.id) {
                                return __assign(__assign({}, q), updatedQuestion_1);
                            }
                            return q;
                        });
                        this.setData({
                            currentQuestion: updatedQuestion_1,
                            questions: questions,
                            showEditModal: false,
                            editSaving: false
                        });
                        // 刷新显示
                        this.refreshDisplayOptions();
                        wx.showToast({ title: '保存成功', icon: 'success' });
                        return [3 /*break*/, 7];
                    case 6:
                        err_10 = _b.sent();
                        this.setData({ editSaving: false });
                        wx.showToast({ title: err_10.message || '保存失败', icon: 'none' });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    normalizeOptions: function (rawOptions, qType, correctAnswer) {
        if (qType === '判断题') {
            var ans = (correctAnswer || '').toString().trim();
            // 如果答案是字母（少数历史格式），优先使用题目自带 options
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
        return (0, quiz_helpers_1.normalizeOptionItems)(rawOptions, quiz_helpers_1.stripHtmlToText);
    },
    refreshDisplayOptions: function () {
        var _this = this;
        var _a = this.data, currentQuestion = _a.currentQuestion, selectedAnswer = _a.selectedAnswer, selectedAnswers = _a.selectedAnswers, showAnswer = _a.showAnswer, mode = _a.mode;
        if (!currentQuestion) {
            this.setData({ displayOptions: [] });
            return;
        }
        var qType = currentQuestion.q_type || '';
        var correctAnswer = (currentQuestion.answer || '').toString();
        var correctAnswerNormalized = correctAnswer.trim().toLowerCase();
        var shouldShowResult = showAnswer || mode === 'memo';
        var normalizedOptions = this.normalizeOptions(currentQuestion.options, qType, currentQuestion.answer);
        var displayOptions = normalizedOptions.map(function (opt) {
            var isSelected = qType === '多选题' ? selectedAnswers.indexOf(opt.answerValue) > -1 : selectedAnswer === opt.answerValue;
            var isCorrect = shouldShowResult
                ? correctAnswerNormalized.indexOf(opt.answerValue.toString().trim().toLowerCase()) > -1
                : false;
            var isWrong = showAnswer ? isSelected && !isCorrect : false;
            var classParts = [];
            if (isSelected)
                classParts.push('selected');
            if (isCorrect)
                classParts.push('correct');
            if (isWrong)
                classParts.push('wrong');
            var displayValue = _this.looksLikeCode(opt.value) ? _this.preserveSpacesForCode(opt.value) : opt.value;
            return {
                key: opt.key,
                value: displayValue,
                answerValue: opt.answerValue,
                isSelected: isSelected,
                isCorrect: isCorrect,
                isWrong: isWrong,
                className: classParts.join(' ')
            };
        });
        this.setData({
            displayOptions: displayOptions,
            currentQuestion: Object.assign({}, currentQuestion, { options: normalizedOptions })
        });
    },
    isAutoJudgable: function (qType) {
        return qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题';
    },
    updateSubmitState: function () {
        var _a = this.data, currentQuestion = _a.currentQuestion, mode = _a.mode, showAnswer = _a.showAnswer, selectedAnswers = _a.selectedAnswers, selectedAnswer = _a.selectedAnswer, blankAnswers = _a.blankAnswers;
        if (!currentQuestion || (mode !== 'quiz' && mode !== 'reinforce') || showAnswer) {
            this.setData({ showSubmitButton: false, submitDisabled: true });
            return;
        }
        var qType = currentQuestion.q_type || '';
        var showSubmit = qType === '多选题' || qType === '填空题' || qType === '简答题' || qType === '问答题' || qType === '计算题';
        var disabled = true;
        if (qType === '多选题') {
            disabled = selectedAnswers.length === 0;
        }
        else if (qType === '填空题') {
            disabled = !blankAnswers.length || blankAnswers.some(function (x) { return !(x || '').trim(); });
        }
        else if (qType === '简答题' || qType === '问答题' || qType === '计算题') {
            disabled = !(selectedAnswer || '').trim();
        }
        else {
            disabled = true;
        }
        this.setData({ showSubmitButton: showSubmit, submitDisabled: showSubmit ? disabled : true });
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
        return (0, quiz_helpers_1.stripHtmlToText)(content);
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
        // 小程序 <text> 会折叠连续空格；代码场景将空格替换为 NBSP 保留缩进/对齐
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
    buildProgressKey: function () {
        // 使用数据源适配器构建进度key
        if (quizSource) {
            return quizSource.buildProgressKey(this.data.mode, {
                type: this.data.qType,
                source: this.data.source,
                tag: this.data.tag,
                rk: this.data.reinforceKind,
                shuffleQuestions: this.data.shuffleQuestions,
                shuffleOptions: this.data.shuffleOptions
            });
        }
        // 兜底：手动构建（不应该到达这里）
        var userInfo = wx.getStorageSync('userInfo') || {};
        var uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';
        var mode = (this.data.mode || 'quiz').toString();
        var rawSourceId = String(this.data.sourceId || 'all');
        var sourceId = (this.data.sourceType === 'bank' && mode === 'reinforce') ? "bank_".concat(rawSourceId) : rawSourceId;
        var type = (this.data.qType || 'all').toString();
        var sourceParam = (this.data.source || '').toString();
        var dataScope = (sourceParam === 'favorites' || sourceParam === 'mistakes') ? sourceParam : 'all';
        var tag = (this.data.tag || '').toString();
        var tagPart = tag && tag.toLowerCase() !== 'all' ? "_tag".concat(tag) : '';
        var shuffleQ = this.data.shuffleQuestions ? '1' : '0';
        var shuffleO = this.data.shuffleOptions ? '1' : '0';
        var prefix = this.data.sourceType === 'bank' ? 'bank_quiz_progress' : 'quiz_progress';
        var rkPart = '';
        if (mode === 'reinforce') {
            var rk = String(this.data.reinforceKind || '').trim().toLowerCase();
            if (rk === 'wrong' || rk === 'similar')
                rkPart = "_rk".concat(rk);
        }
        // reinforce 模式：对齐 Web 的 progressKey()（user_bank 也使用 quiz_progress）
        if (mode === 'reinforce') {
            return "quiz_progress_".concat(uid, "_").concat(mode, "_").concat(sourceId, "_").concat(type, "_").concat(dataScope).concat(tagPart).concat(rkPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
        }
        return "".concat(prefix, "_").concat(uid, "_").concat(mode, "_").concat(sourceId, "_").concat(type, "_").concat(dataScope).concat(tagPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
    },
    loadProgressState: function (key) {
        return __awaiter(this, void 0, Promise, function () {
            var local, remote, e_3, merged;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!key)
                            return [2 /*return*/, null];
                        local = this.safeParseStorage(wx.getStorageSync(key));
                        remote = null;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getProgress(key)];
                    case 2:
                        remote = _a.sent();
                        return [3 /*break*/, 4];
                    case 3:
                        e_3 = _a.sent();
                        remote = null;
                        return [3 /*break*/, 4];
                    case 4:
                        merged = this.pickLatestProgress(local, remote);
                        if (merged) {
                            try {
                                wx.setStorageSync(key, merged);
                            }
                            catch (e) { }
                        }
                        return [2 /*return*/, merged];
                }
            });
        });
    },
    safeParseStorage: function (val) {
        if (!val)
            return null;
        if (typeof val === 'string') {
            try {
                return JSON.parse(val);
            }
            catch (e) {
                return null;
            }
        }
        if (typeof val === 'object')
            return val;
        return null;
    },
    pickLatestProgress: function (a, b) {
        if (!a && !b)
            return null;
        if (a && !b)
            return a;
        if (!a && b)
            return b;
        var ta = Number(a && a.timestamp) || 0;
        var tb = Number(b && b.timestamp) || 0;
        return tb >= ta ? b : a;
    },
    applyQuestionOrder: function (questions, order) {
        try {
            var map_1 = new Map();
            questions.forEach(function (q) {
                if (q && typeof q.id === 'number')
                    map_1.set(q.id, q);
            });
            var ordered_1 = [];
            order.forEach(function (id) {
                var qid = Number(id);
                if (!isFinite(qid))
                    return;
                var hit = map_1.get(qid);
                if (hit) {
                    ordered_1.push(hit);
                    map_1.delete(qid);
                }
            });
            if (map_1.size > 0) {
                ordered_1.push.apply(ordered_1, Array.from(map_1.values()));
            }
            return ordered_1;
        }
        catch (e) {
            return questions;
        }
    },
    buildAnswerRecordsFromStatus: function (questions, status) {
        var records = {};
        if (!status || typeof status !== 'object')
            return records;
        Object.keys(status).forEach(function (k) {
            var idx = Number(k);
            if (!isFinite(idx) || idx < 0 || idx >= questions.length)
                return;
            var v = status[k];
            if (v !== 'correct' && v !== 'wrong')
                return;
            var q = questions[idx];
            if (!q || typeof q.id !== 'number')
                return;
            records[q.id] = { answered: true, isCorrect: v === 'correct' };
        });
        return records;
    },
    getSavedAnswerForIndex: function (index) {
        var map = this.progressAnswerMap;
        if (!map || typeof map !== 'object')
            return null;
        return map[String(index)];
    },
    getSavedStatusForIndex: function (index) {
        var map = this.progressStatusMap;
        if (!map || typeof map !== 'object')
            return null;
        return map[String(index)];
    },
    setProgressAnswerForIndex: function (index, qType) {
        if (!this.progressAnswerMap || typeof this.progressAnswerMap !== 'object') {
            this.progressAnswerMap = {};
        }
        if (qType === '多选题') {
            this.progressAnswerMap[String(index)] = (this.data.selectedAnswers || []).slice();
            return;
        }
        if (qType === '选择题' || qType === '判断题') {
            var a = (this.data.selectedAnswer || '').trim();
            this.progressAnswerMap[String(index)] = a ? [a] : [];
            return;
        }
        if (qType === '填空题') {
            this.progressAnswerMap[String(index)] = (this.data.blankAnswers || []).slice();
            return;
        }
        // 问答/简答/计算
        this.progressAnswerMap[String(index)] = (this.data.selectedAnswer || '').toString();
    },
    saveDraftAnswer: function () {
        if ((this.data.mode !== 'quiz' && this.data.mode !== 'reinforce') || this.data.showAnswer)
            return;
        if (!this.data.currentQuestion)
            return;
        var qType = this.data.currentQuestion.q_type || '';
        this.setProgressAnswerForIndex(this.data.currentIndex, qType);
        this.saveProgressIndex(false);
    },
    saveProgressIndex: function (immediate) {
        var key = this.progressKey || this.buildProgressKey();
        if (!key)
            return;
        var payload = {
            index: this.data.currentIndex,
            status: this.progressStatusMap || {},
            answers: this.progressAnswerMap || {},
            timestamp: Date.now()
        };
        if (this.progressOrder) {
            payload.order = this.progressOrder;
        }
        this.saveProgressState(payload, immediate);
    },
    saveProgressState: function (payload, immediate) {
        var _this = this;
        var key = this.progressKey || this.buildProgressKey();
        if (!key)
            return;
        try {
            wx.setStorageSync(key, payload);
        }
        catch (e) { }
        this.lastSavedPayload = payload;
        this.syncPending = true;
        if (immediate) {
            if (this.saveProgressTimer) {
                clearTimeout(this.saveProgressTimer);
                this.saveProgressTimer = null;
            }
            this.syncToServer(payload);
            return;
        }
        if (this.saveProgressTimer) {
            clearTimeout(this.saveProgressTimer);
        }
        this.saveProgressTimer = setTimeout(function () {
            _this.saveProgressTimer = null;
            _this.syncToServer(payload);
        }, 200);
    },
    syncToServer: function (payload) {
        return __awaiter(this, void 0, void 0, function () {
            var key, e_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!payload)
                            return [2 /*return*/];
                        key = this.progressKey || this.buildProgressKey();
                        if (!key)
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.saveProgress(key, payload)];
                    case 2:
                        _a.sent();
                        this.syncPending = false;
                        return [3 /*break*/, 4];
                    case 3:
                        e_4 = _a.sent();
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 保存"上次练习"指针（云端 + 本地），用于首页一键继续
    saveLastSession: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var _a, sourceType, sourceId, displayName, payload, key, e_5;
            if (force === void 0) { force = false; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = this.data, sourceType = _a.sourceType, sourceId = _a.sourceId, displayName = _a.displayName;
                        if (!sourceId)
                            return [2 /*return*/];
                        payload = {
                            source_type: sourceType,
                            source_id: sourceId,
                            display_name: displayName,
                            mode: (this.data.mode || 'quiz').toString(),
                            type: (this.data.qType || 'all').toString(),
                            source: (this.data.source || 'all').toString(),
                            shuffle_questions: this.data.shuffleQuestions ? 1 : 0,
                            shuffle_options: this.data.shuffleOptions ? 1 : 0,
                            progress_key: this.progressKey || this.buildProgressKey(),
                            timestamp: Date.now()
                        };
                        // 兼容旧格式：如果是公有题库，仍保存 subject 字段
                        if (sourceType === 'public') {
                            payload.subject = String(sourceId);
                        }
                        else if (sourceType === 'bank') {
                            payload.bank_id = Number(sourceId);
                        }
                        key = 'last_practice_session';
                        try {
                            wx.setStorageSync(key, payload);
                        }
                        catch (e) { }
                        // 避免频繁写云端：仅在强制 flush 时写一次
                        if (!force)
                            return [2 /*return*/];
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.saveProgress(key, payload)];
                    case 2:
                        _b.sent();
                        return [3 /*break*/, 4];
                    case 3:
                        e_5 = _b.sent();
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onHide: function () {
        if (this.syncPending && this.lastSavedPayload) {
            this.saveProgressState(this.lastSavedPayload, true);
        }
        this.saveLastSession(true);
    },
    onUnload: function () {
        if (this.syncPending && this.lastSavedPayload) {
            this.saveProgressState(this.lastSavedPayload, true);
        }
        if (this.saveProgressTimer) {
            clearTimeout(this.saveProgressTimer);
            this.saveProgressTimer = null;
        }
        this.saveLastSession(true);
    },
    // === 滑屏切题 ===
    onTouchStart: function (e) {
        if (!e.touches || !e.touches.length)
            return;
        var touch = e.touches[0];
        this.setData({
            touchStartX: touch.clientX,
            touchStartY: touch.clientY
        });
    },
    onTouchEnd: function (e) {
        if (!e.changedTouches || !e.changedTouches.length)
            return;
        var touch = e.changedTouches[0];
        var _a = this.data, touchStartX = _a.touchStartX, touchStartY = _a.touchStartY, loading = _a.loading, currentQuestion = _a.currentQuestion;
        // 未加载完成或无题目时不处理
        if (loading || !currentQuestion)
            return;
        var deltaX = touch.clientX - touchStartX;
        var deltaY = touch.clientY - touchStartY;
        var absDeltaX = Math.abs(deltaX);
        var absDeltaY = Math.abs(deltaY);
        // 水平滑动距离 > 80px 且水平距离 > 垂直距离的 1.5 倍（避免误触）
        var swipeThreshold = 80;
        if (absDeltaX > swipeThreshold && absDeltaX > absDeltaY * 1.5) {
            if (deltaX > 0) {
                // 右滑 → 上一题
                this.onPrevQuestion();
            }
            else {
                // 左滑 → 下一题
                this.onNextQuestion();
            }
        }
    }
});
