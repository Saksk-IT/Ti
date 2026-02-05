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
// subject-stats.ts - 学习统计
// 支持公有题库（subject参数）和个人题库（bank_id参数）双数据源
var auth_1 = require("../../utils/auth");
var quiz_source_1 = require("../../utils/quiz-source");
// 数据源实例（页面级别）
var quizSource = null;
Page({
    data: {
        // 数据源信息
        sourceType: '',
        sourceId: '',
        displayName: '',
        loading: false,
        stats: {
            totalCount: 0,
            doneCount: 0,
            wrongCount: 0,
            favoriteCount: 0,
            lastActivity: '',
            accuracyText: '0%'
        }
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        // 使用工厂函数创建数据源
        quizSource = (0, quiz_source_1.createSourceFromOptions)(options);
        if (!quizSource) {
            console.error('数据源参数缺失（需要 subject 或 bank_id）');
            wx.showToast({ title: '参数缺失', icon: 'none' });
            setTimeout(function () { return wx.navigateBack(); }, 1200);
            return;
        }
        console.log('统计页面数据源类型:', quizSource.sourceType, '标识:', quizSource.sourceId);
        this.setData({
            sourceType: quizSource.sourceType,
            sourceId: quizSource.sourceId,
            displayName: quizSource.displayName || String(quizSource.sourceId)
        });
        this.loadStats();
    },
    onShow: function () {
        // 返回该页时刷新一次（例如从收藏/错题返回）
        if (quizSource) {
            this.loadStats();
        }
    },
    loadStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var info, totalCount, userCounts, myStats, doneCount, wrongCount, favoriteCount, accuracy, accuracyText, err_1, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading || !quizSource)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 5, , 6]);
                        return [4 /*yield*/, quizSource.getInfo()];
                    case 2:
                        info = _a.sent();
                        totalCount = info.question_count || 0;
                        // 更新显示名称
                        if (info.name) {
                            this.setData({ displayName: info.name });
                        }
                        return [4 /*yield*/, quizSource.getUserCounts()];
                    case 3:
                        userCounts = _a.sent();
                        return [4 /*yield*/, quizSource.getMyStats()];
                    case 4:
                        myStats = _a.sent();
                        doneCount = myStats.total_answered || 0;
                        wrongCount = userCounts.mistakes || myStats.wrong_count || 0;
                        favoriteCount = userCounts.favorites || 0;
                        accuracy = doneCount > 0 ? Math.max(0, (doneCount - wrongCount) / doneCount) : 0;
                        accuracyText = "".concat(Math.round(accuracy * 100), "%");
                        this.setData({
                            stats: {
                                totalCount: totalCount,
                                doneCount: doneCount,
                                wrongCount: wrongCount,
                                favoriteCount: favoriteCount,
                                lastActivity: '', // 数据源适配器暂未提供此字段
                                accuracyText: accuracyText
                            },
                            loading: false
                        });
                        return [3 /*break*/, 6];
                    case 5:
                        err_1 = _a.sent();
                        console.error('加载学习统计失败:', err_1);
                        msg = (err_1 && err_1.message) || '加载失败';
                        wx.showToast({ title: msg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    formatDateTime: function (dateTimeStr) {
        if (!dateTimeStr)
            return '';
        try {
            var date = new Date(dateTimeStr);
            var month = String(date.getMonth() + 1).padStart(2, '0');
            var day = String(date.getDate()).padStart(2, '0');
            var hours = String(date.getHours()).padStart(2, '0');
            var minutes = String(date.getMinutes()).padStart(2, '0');
            return "".concat(month, "-").concat(day, " ").concat(hours, ":").concat(minutes);
        }
        catch (e) {
            return '';
        }
    }
});
