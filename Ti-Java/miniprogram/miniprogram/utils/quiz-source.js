"use strict";
/**
 * quiz-source.ts - 统一数据源适配器
 *
 * 将公有题库(subject)和个人题库(bank)统一为相同的接口，
 * 使页面代码可以复用，只需传入不同的数据源即可。
 */
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.BankQuizSource = exports.PublicQuizSource = void 0;
exports.createQuizSource = createQuizSource;
exports.createSourceFromOptions = createSourceFromOptions;
exports.getSourceLabel = getSourceLabel;
var api_1 = require("./api");
// Fisher-Yates 洗牌算法（均匀分布）
function shuffleArray(array) {
    var shuffled = array.slice();
    for (var i = shuffled.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = shuffled[i];
        shuffled[i] = shuffled[j];
        shuffled[j] = tmp;
    }
    return shuffled;
}
var OPTION_KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
var OPTION_TYPES = new Set(['选择题', '多选题']);
function parseOptions(rawOptions) {
    var opts = rawOptions;
    if (typeof opts === 'string') {
        try {
            opts = JSON.parse(opts);
        }
        catch (e) {
            opts = [];
        }
    }
    if (!Array.isArray(opts))
        return [];
    return opts.map(function (item, index) {
        if (item && typeof item === 'object') {
            var rawKey = String(item.key || '').trim().toUpperCase();
            return {
                key: rawKey || (OPTION_KEYS[index] || String(index + 1)),
                value: String(item.value || '')
            };
        }
        return {
            key: OPTION_KEYS[index] || String(index + 1),
            value: String(item == null ? '' : item)
        };
    });
}
function shuffleChoiceOptions(question) {
    if (!OPTION_TYPES.has(String(question.q_type || '')))
        return question;
    var options = parseOptions(question.options);
    if (options.length <= 1)
        return question;
    var answerLetters = new Set(String(question.answer || '')
        .toUpperCase()
        .split('')
        .filter(function (c) { return /[A-Z]/.test(c); }));
    var answerIndexes = new Set();
    options.forEach(function (opt, index) {
        var key = String(opt.key || OPTION_KEYS[index] || '').toUpperCase().slice(0, 1);
        if (answerLetters.has(key)) {
            answerIndexes.add(index);
        }
    });
    var shuffled = shuffleArray(options.map(function (opt, index) { return ({
        originalIndex: index,
        value: String(opt.value || '')
    }); }));
    var nextOptions = shuffled.map(function (opt, index) {
        var key = OPTION_KEYS[index] || String(index + 1);
        return { key: key, value: opt.value, originalIndex: opt.originalIndex };
    });
    var nextAnswer = nextOptions
        .filter(function (opt) { return answerIndexes.has(opt.originalIndex); })
        .map(function (opt) { return opt.key; })
        .sort()
        .join('');
    return __assign(__assign({}, question), { options: nextOptions.map(function (opt) { return ({ key: opt.key, value: opt.value }); }), answer: nextAnswer });
}
var FULL_LOAD_PAGE_SIZE = 200;
var FULL_LOAD_MAX_PAGES = 100;
function normalizePageSize(value) {
    var n = Number(value || FULL_LOAD_PAGE_SIZE);
    if (!Number.isFinite(n) || n <= 0)
        return FULL_LOAD_PAGE_SIZE;
    return Math.max(1, Math.min(Math.floor(n), 1000));
}
function normalizeQuestionListResponse(res) {
    var questions = Array.isArray(res === null || res === void 0 ? void 0 : res.questions) ? res.questions : (Array.isArray(res) ? res : []);
    var totalRaw = Number(res === null || res === void 0 ? void 0 : res.total);
    var total = Number.isFinite(totalRaw) && totalRaw >= 0 ? Math.floor(totalRaw) : questions.length;
    return { questions: questions, total: total };
}
function fetchAllQuestionPages(fetchPage, perPage) {
    return __awaiter(this, void 0, void 0, function () {
        var allQuestions, total, page, data, _a, pageQuestions;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0:
                    allQuestions = [];
                    total = 0;
                    page = 1;
                    _b.label = 1;
                case 1:
                    if (!(page <= FULL_LOAD_MAX_PAGES)) return [3 /*break*/, 4];
                    _a = normalizeQuestionListResponse;
                    return [4 /*yield*/, fetchPage(page, perPage)];
                case 2:
                    data = _a.apply(void 0, [_b.sent()]);
                    pageQuestions = data.questions;
                    total = data.total || allQuestions.length + pageQuestions.length;
                    allQuestions.push.apply(allQuestions, pageQuestions);
                    if (!pageQuestions.length || allQuestions.length >= total || pageQuestions.length < perPage) {
                        return [3 /*break*/, 4];
                    }
                    _b.label = 3;
                case 3:
                    page++;
                    return [3 /*break*/, 1];
                case 4: return [2 /*return*/, {
                        questions: allQuestions,
                        total: total || allQuestions.length
                    }];
            }
        });
    });
}
function fetchFullQuestionList(fetchFull, fetchPage, perPage) {
    return __awaiter(this, void 0, void 0, function () {
        var first, _a;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0:
                    _a = normalizeQuestionListResponse;
                    return [4 /*yield*/, fetchFull()];
                case 1:
                    first = _a.apply(void 0, [_b.sent()]);
                    if (first.questions.length >= first.total || first.questions.length < perPage) {
                        return [2 /*return*/, first];
                    }
                    return [2 /*return*/, fetchAllQuestionPages(fetchPage, perPage)];
            }
        });
    });
}
// ============================================
// 公有题库数据源
// ============================================
var PublicQuizSource = /** @class */ (function () {
    function PublicQuizSource(subject) {
        this.sourceType = 'public';
        this.displayName = '';
        this.sourceId = subject;
        this.displayName = subject;
    }
    PublicQuizSource.prototype.getInfo = function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, info;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.getSubjectInfo(this.sourceId)];
                    case 1:
                        res = _a.sent();
                        info = res.data || res || {};
                        this.displayName = info.name || this.sourceId;
                        return [2 /*return*/, __assign({ name: info.name || this.sourceId, available_types: Array.isArray(info.available_types) ? info.available_types : [], question_count: info.question_count || 0 }, info)];
                }
            });
        });
    };
    PublicQuizSource.prototype.getUserCounts = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var _a, type, source, countParams, totalRes, userRes;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _a = params || {}, type = _a.type, source = _a.source;
                        countParams = { subject: this.sourceId };
                        if (type && type !== 'all') {
                            countParams.type = type;
                        }
                        if (source && source !== 'all') {
                            countParams.source = source;
                        }
                        return [4 /*yield*/, api_1.api.getQuestionsCount(countParams)];
                    case 1:
                        totalRes = _b.sent();
                        return [4 /*yield*/, api_1.api.getUserCounts({
                                subject: this.sourceId,
                                type: type && type !== 'all' ? type : undefined
                            })];
                    case 2:
                        userRes = _b.sent();
                        return [2 /*return*/, {
                                total: totalRes.count || 0,
                                favorites: userRes.favorites || 0,
                                mistakes: userRes.mistakes || 0
                            }];
                }
            });
        });
    };
    PublicQuizSource.prototype.getQuestions = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var apiParams, ids, perPage_1, res;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        apiParams = {
                            subject: this.sourceId
                        };
                        if ((params === null || params === void 0 ? void 0 : params.type) && params.type !== 'all') {
                            apiParams.q_type = params.type;
                        }
                        if ((params === null || params === void 0 ? void 0 : params.tag) && params.tag !== 'all') {
                            apiParams.tag = params.tag;
                        }
                        if ((params === null || params === void 0 ? void 0 : params.source) && params.source !== 'all') {
                            apiParams.source = params.source;
                        }
                        if (params === null || params === void 0 ? void 0 : params.mode) {
                            apiParams.mode = params.mode;
                        }
                        if (params === null || params === void 0 ? void 0 : params.shuffle_questions) {
                            apiParams.shuffle_questions = 1;
                        }
                        if (params === null || params === void 0 ? void 0 : params.shuffle_options) {
                            apiParams.shuffle_options = 1;
                        }
                        // Reinforce / 指定题目：按 ids 拉题（与 Web /quiz?ids=... 对齐）
                        if ((params === null || params === void 0 ? void 0 : params.ids) && Array.isArray(params.ids) && params.ids.length > 0) {
                            ids = params.ids
                                .map(function (x) { return Number(x); })
                                .filter(function (n) { return Number.isFinite(n) && n > 0; })
                                .map(function (n) { return Math.floor(n); });
                            apiParams.ids = ids.join(',');
                        }
                        if (params === null || params === void 0 ? void 0 : params.page) {
                            apiParams.page = params.page;
                        }
                        if (params === null || params === void 0 ? void 0 : params.per_page) {
                            apiParams.per_page = params.per_page;
                        }
                        if (params === null || params === void 0 ? void 0 : params.full_load) {
                            perPage_1 = normalizePageSize(params.per_page || params.limit);
                            return [2 /*return*/, fetchFullQuestionList(function () { return api_1.api.getQuestions(__assign(__assign({}, apiParams), { full_load: 1, page: 1, per_page: perPage_1 })); }, function (page, pageSize) { return api_1.api.getQuestions(__assign(__assign({}, apiParams), { page: page, per_page: pageSize })); }, perPage_1)];
                        }
                        return [4 /*yield*/, api_1.api.getQuestions(apiParams)];
                    case 1:
                        res = _a.sent();
                        return [2 /*return*/, normalizeQuestionListResponse(res)];
                }
            });
        });
    };
    PublicQuizSource.prototype.recordResult = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.recordResult(params.questionId, params.isCorrect)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    PublicQuizSource.prototype.toggleFavorite = function (questionId) {
        return __awaiter(this, void 0, void 0, function () {
            var res;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0: return [4 /*yield*/, api_1.api.toggleFavorite(questionId)];
                    case 1:
                        res = _b.sent();
                        return [2 /*return*/, { is_favorite: (_a = res.is_favorite) !== null && _a !== void 0 ? _a : true }];
                }
            });
        });
    };
    PublicQuizSource.prototype.searchQuestions = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var apiParams, res;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        apiParams = {
                            keyword: params.keyword,
                            subject: this.sourceId
                        };
                        if (params.type && params.type !== 'all') {
                            apiParams.q_type = params.type;
                        }
                        if (params.source && params.source !== 'all') {
                            apiParams.source = params.source;
                        }
                        if (params.tag && params.tag !== 'all') {
                            apiParams.tag = params.tag;
                        }
                        if (params.page) {
                            apiParams.page = params.page;
                        }
                        if (params.per_page) {
                            apiParams.per_page = params.per_page;
                        }
                        return [4 /*yield*/, api_1.api.searchQuestions(apiParams)];
                    case 1:
                        res = _a.sent();
                        return [2 /*return*/, {
                                questions: res.questions || res || [],
                                total: res.total || (res.questions || res || []).length
                            }];
                }
            });
        });
    };
    PublicQuizSource.prototype.getMyStats = function () {
        return __awaiter(this, void 0, void 0, function () {
            var counts;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.getUserCounts()];
                    case 1:
                        counts = _a.sent();
                        return [2 /*return*/, {
                                total_answered: 0, // 需要后端支持
                                correct_count: 0,
                                wrong_count: counts.mistakes,
                                accuracy: 0
                            }];
                }
            });
        });
    };
    PublicQuizSource.prototype.deleteProgress = function (key) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.deleteProgress(key)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    PublicQuizSource.prototype.buildProgressKey = function (mode, options) {
        var userInfo = wx.getStorageSync('userInfo') || {};
        var uid = (userInfo.id || userInfo.user_id) ? String(userInfo.id || userInfo.user_id) : 'guest';
        var subject = this.sourceId || 'all';
        var type = options.type || 'all';
        var dataScope = (options.source === 'favorites' || options.source === 'mistakes') ? options.source : 'all';
        var tag = (options.tag || '').toString();
        var tagPart = tag && tag.toLowerCase() !== 'all' ? "_tag".concat(tag) : '';
        var shuffleQ = options.shuffleQuestions ? '1' : '0';
        var shuffleO = options.shuffleOptions ? '1' : '0';
        var rkPart = '';
        if (mode === 'reinforce') {
            var rk = String(options.rk || '').trim().toLowerCase();
            if (rk === 'wrong' || rk === 'similar')
                rkPart = "_rk".concat(rk);
        }
        return "quiz_progress_".concat(uid, "_").concat(mode, "_").concat(subject, "_").concat(type, "_").concat(dataScope).concat(tagPart).concat(rkPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
    };
    return PublicQuizSource;
}());
exports.PublicQuizSource = PublicQuizSource;
// ============================================
// 个人题库数据源
// ============================================
var BankQuizSource = /** @class */ (function () {
    function BankQuizSource(bankId) {
        this.sourceType = 'bank';
        this.displayName = '';
        this.sourceId = bankId;
    }
    BankQuizSource.prototype.getInfo = function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, info;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.getBankDetail(this.sourceId)];
                    case 1:
                        res = _a.sent();
                        info = res.data || res || {};
                        this.displayName = info.name || "\u9898\u5E93".concat(this.sourceId);
                        return [2 /*return*/, __assign({ name: info.name || "\u9898\u5E93".concat(this.sourceId), available_types: Array.isArray(info.available_types) ? info.available_types : [], question_count: info.question_count || 0, permission: info.permission, access_type: info.access_type }, info)];
                }
            });
        });
    };
    BankQuizSource.prototype.getUserCounts = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var apiParams, res, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        apiParams = {};
                        if ((params === null || params === void 0 ? void 0 : params.type) && params.type !== 'all') {
                            apiParams.q_type = params.type;
                        }
                        if ((params === null || params === void 0 ? void 0 : params.source) && params.source !== 'all') {
                            apiParams.source = params.source;
                        }
                        return [4 /*yield*/, api_1.api.getBankUserCounts(this.sourceId, apiParams)];
                    case 1:
                        res = _a.sent();
                        data = res.data || res || {};
                        return [2 /*return*/, {
                                total: data.total || 0,
                                favorites: data.favorites || 0,
                                mistakes: data.mistakes || 0
                            }];
                }
            });
        });
    };
    BankQuizSource.prototype.getQuestions = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var apiParams, ids, limit, result, _a, _b, questions;
            var _this = this;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        apiParams = {};
                        // 个人题库使用不同的模式映射
                        if ((params === null || params === void 0 ? void 0 : params.source) === 'mistakes') {
                            apiParams.mode = 'wrong';
                        }
                        else if ((params === null || params === void 0 ? void 0 : params.source) === 'favorites') {
                            apiParams.mode = 'favorites';
                        }
                        else {
                            apiParams.mode = 'all';
                        }
                        // 加强训练等：指定题目列表优先
                        if ((params === null || params === void 0 ? void 0 : params.ids) && Array.isArray(params.ids) && params.ids.length > 0) {
                            ids = params.ids
                                .map(function (x) { return Number(x); })
                                .filter(function (n) { return Number.isFinite(n) && n > 0; })
                                .map(function (n) { return Math.floor(n); });
                            apiParams.ids = ids.join(',');
                        }
                        // 题型/标签筛选（与公共题库参数保持一致）
                        if ((params === null || params === void 0 ? void 0 : params.type) && params.type !== 'all') {
                            apiParams.q_type = params.type;
                        }
                        if ((params === null || params === void 0 ? void 0 : params.tag) && params.tag !== 'all') {
                            apiParams.tag = params.tag;
                        }
                        if (!(params === null || params === void 0 ? void 0 : params.full_load) && (params === null || params === void 0 ? void 0 : params.page)) {
                            apiParams.page = params.page;
                        }
                        if (!(params === null || params === void 0 ? void 0 : params.full_load) && (params === null || params === void 0 ? void 0 : params.per_page)) {
                            apiParams.per_page = params.per_page;
                        }
                        limit = (params === null || params === void 0 ? void 0 : params.limit) || (!(params === null || params === void 0 ? void 0 : params.full_load) && !(params === null || params === void 0 ? void 0 : params.per_page) ? 1000 : undefined);
                        if (limit) {
                            apiParams.limit = limit;
                        }
                        if (!(params === null || params === void 0 ? void 0 : params.full_load)) return [3 /*break*/, 2];
                        return [4 /*yield*/, fetchFullQuestionList(function () { return api_1.api.getBankQuizQuestions(_this.sourceId, __assign(__assign({}, apiParams), { full_load: 1, page: 1, per_page: normalizePageSize(params.per_page || params.limit) })); }, function (page, pageSize) { return api_1.api.getBankQuizQuestions(_this.sourceId, __assign(__assign({}, apiParams), { page: page, per_page: pageSize })); }, normalizePageSize(params.per_page || params.limit))];
                    case 1:
                        _a = _c.sent();
                        return [3 /*break*/, 4];
                    case 2:
                        _b = normalizeQuestionListResponse;
                        return [4 /*yield*/, api_1.api.getBankQuizQuestions(this.sourceId, apiParams)];
                    case 3:
                        _a = _b.apply(void 0, [_c.sent()]);
                        _c.label = 4;
                    case 4:
                        result = _a;
                        questions = result.questions || [];
                        // 如果需要打乱题目
                        if ((params === null || params === void 0 ? void 0 : params.shuffle_questions) && Array.isArray(questions)) {
                            questions = shuffleArray(questions);
                        }
                        // 如果需要打乱选项（仅选择题/多选题）
                        if ((params === null || params === void 0 ? void 0 : params.shuffle_options) && Array.isArray(questions)) {
                            questions = questions.map(function (q) {
                                return shuffleChoiceOptions(q);
                            });
                        }
                        return [2 /*return*/, {
                                questions: questions,
                                total: result.total || questions.length
                            }];
                }
            });
        });
    };
    BankQuizSource.prototype.recordResult = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.recordBankQuizResult(this.sourceId, {
                            question_id: params.questionId,
                            user_answer: params.userAnswer || '',
                            is_correct: params.isCorrect
                        })];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    BankQuizSource.prototype.toggleFavorite = function (questionId) {
        return __awaiter(this, void 0, void 0, function () {
            var res;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0: return [4 /*yield*/, api_1.api.toggleBankFavorite(this.sourceId, questionId)];
                    case 1:
                        res = _b.sent();
                        return [2 /*return*/, { is_favorite: (_a = res.is_favorite) !== null && _a !== void 0 ? _a : false }];
                }
            });
        });
    };
    BankQuizSource.prototype.searchQuestions = function (params) {
        return __awaiter(this, void 0, void 0, function () {
            var apiParams, res, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        apiParams = {
                            keyword: params.keyword
                        };
                        if (params.type && params.type !== 'all') {
                            apiParams.q_type = params.type;
                        }
                        if (params.source && params.source !== 'all') {
                            apiParams.source = params.source;
                        }
                        if (params.tag && params.tag !== 'all') {
                            apiParams.tag = params.tag;
                        }
                        if (params.page) {
                            apiParams.page = params.page;
                        }
                        if (params.per_page) {
                            apiParams.per_page = params.per_page;
                        }
                        return [4 /*yield*/, api_1.api.searchBankQuestions(this.sourceId, apiParams)];
                    case 1:
                        res = _a.sent();
                        data = res.data || res || {};
                        return [2 /*return*/, {
                                questions: data.questions || [],
                                total: data.total || (data.questions || []).length
                            }];
                }
            });
        });
    };
    BankQuizSource.prototype.getMyStats = function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.getBankMyStats(this.sourceId)];
                    case 1:
                        res = _a.sent();
                        data = res.data || res || {};
                        return [2 /*return*/, {
                                total_answered: data.total_answered || 0,
                                correct_count: data.correct_count || 0,
                                wrong_count: data.wrong_count || 0,
                                accuracy: data.accuracy || 0
                            }];
                }
            });
        });
    };
    BankQuizSource.prototype.deleteProgress = function (key) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, api_1.api.deleteProgress(key)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    BankQuizSource.prototype.buildProgressKey = function (mode, options) {
        var userInfo = wx.getStorageSync('userInfo') || {};
        var uid = (userInfo.id || userInfo.user_id) ? String(userInfo.id || userInfo.user_id) : 'guest';
        var bankId = this.sourceId || 0;
        var subject = bankId ? "bank_".concat(bankId) : 'all';
        var type = options.type || 'all';
        var dataScope = (options.source === 'favorites' || options.source === 'mistakes') ? options.source : 'all';
        var tag = (options.tag || '').toString();
        var tagPart = tag && tag.toLowerCase() !== 'all' ? "_tag".concat(tag) : '';
        var shuffleQ = options.shuffleQuestions ? '1' : '0';
        var shuffleO = options.shuffleOptions ? '1' : '0';
        var rkPart = '';
        if (mode === 'reinforce') {
            var rk = String(options.rk || '').trim().toLowerCase();
            if (rk === 'wrong' || rk === 'similar')
                rkPart = "_rk".concat(rk);
        }
        // reinforce 模式：对齐 Web 的 progressKey()（subject=bank_<id>，prefix=quiz_progress）
        if (mode === 'reinforce') {
            return "quiz_progress_".concat(uid, "_").concat(mode, "_").concat(subject, "_").concat(type, "_").concat(dataScope).concat(tagPart).concat(rkPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
        }
        return "bank_quiz_progress_".concat(uid, "_").concat(mode, "_").concat(bankId, "_").concat(type, "_").concat(dataScope).concat(tagPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
    };
    return BankQuizSource;
}());
exports.BankQuizSource = BankQuizSource;
/**
 * 创建数据源
 * @param options.subject - 公有题库科目名
 * @param options.bankId - 个人题库ID
 */
function createQuizSource(options) {
    if (options.bankId) {
        return new BankQuizSource(options.bankId);
    }
    if (options.subject) {
        return new PublicQuizSource(options.subject);
    }
    throw new Error('必须提供 subject 或 bankId');
}
/**
 * 从页面参数创建数据源
 * @param options - 页面 onLoad 的 options 参数
 */
function createSourceFromOptions(options) {
    var bankId = options.bank_id || options.bankId;
    if (bankId) {
        return new BankQuizSource(Number(bankId));
    }
    if (options.subject) {
        try {
            return new PublicQuizSource(decodeURIComponent(options.subject));
        }
        catch (_a) {
            return new PublicQuizSource(options.subject);
        }
    }
    return null;
}
/**
 * 获取数据源的显示标签
 */
function getSourceLabel(source) {
    if (source.sourceType === 'bank') {
        return '个人题库';
    }
    return '公有题库';
}
