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
// 题目列表页面
var api_1 = require("../../utils/api");
Page({
    data: {
        questions: [],
        subject: 'all',
        loading: false,
        page: 1,
        hasMore: true,
        total: 0
    },
    onLoad: function (options) {
        if (options.subject) {
            this.setData({ subject: decodeURIComponent(options.subject) });
        }
        this.loadQuestions(true);
    },
    // 加载题目列表
    loadQuestions: function () {
        return __awaiter(this, arguments, void 0, function (reset) {
            var page, result, resultQuestions, questions, err_1;
            if (reset === void 0) { reset = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        page = reset ? 1 : this.data.page;
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getQuestions({
                                subject: this.data.subject === 'all' ? undefined : this.data.subject,
                                page: page,
                                per_page: 20
                            })];
                    case 2:
                        result = _a.sent();
                        resultQuestions = result.questions || [];
                        questions = reset ? resultQuestions : this.data.questions.concat(resultQuestions);
                        this.setData({
                            questions: questions,
                            total: result.total || 0,
                            page: page + 1,
                            hasMore: resultQuestions.length === 20,
                            loading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        wx.showToast({ title: err_1.message || '加载失败', icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    // 下拉刷新
    onPullDownRefresh: function () {
        this.loadQuestions(true).then(function () {
            wx.stopPullDownRefresh();
        });
    },
    // 上拉加载
    onReachBottom: function () {
        if (this.data.hasMore && !this.data.loading) {
            this.loadQuestions();
        }
    },
    // 点击题目
    onQuestionTap: function (e) {
        var id = e.currentTarget.dataset.id;
        wx.navigateTo({
            url: "/pages/practice/practice?id=".concat(id)
        });
    }
});
