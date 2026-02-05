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
// subject-detail.ts
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        subject: '',
        subjectInfo: {
            totalCount: 0,
            author: '',
            doneCount: 0,
            wrongCount: 0,
            favoriteCount: 0,
            noteCount: 0,
            lastActivity: ''
        },
        loading: false
    },
    onLoad: function (options) {
        var subject = options.subject || '';
        if (!subject) {
            wx.showToast({ title: '科目参数缺失', icon: 'none' });
            setTimeout(function () {
                wx.navigateBack();
            }, 1500);
            return;
        }
        // 显式解码URL参数（微信小程序会自动解码，但显式解码更安全）
        try {
            subject = decodeURIComponent(subject);
        }
        catch (e) {
            // 如果解码失败，使用原始值
            console.warn('URL参数解码失败，使用原始值:', e);
        }
        this.setData({ subject: subject });
        wx.showShareMenu({ withShareTicket: true });
        this.loadSubjectInfo();
    },
    onShow: function () {
        // 从刷题/收藏/错题等页面返回后刷新统计
        if (this.data.subject) {
            this.loadSubjectInfo();
        }
    },
    loadSubjectInfo: function () {
        return __awaiter(this, void 0, void 0, function () {
            var data, subjectInfo, userStats, err_1, errorMsg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!(0, auth_1.checkLogin)()) {
                            wx.redirectTo({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSubjectInfo(this.data.subject)];
                    case 2:
                        data = _a.sent();
                        subjectInfo = (data && data.data) ? data.data : (data || {});
                        userStats = subjectInfo.user_stats || {};
                        this.setData({
                            subjectInfo: {
                                totalCount: subjectInfo.total_count || 0,
                                author: subjectInfo.author || '',
                                doneCount: userStats.done_count || 0,
                                wrongCount: userStats.wrong_count || 0,
                                favoriteCount: userStats.favorite_count || 0,
                                noteCount: userStats.note_count || 0,
                                lastActivity: this.formatDateTime(userStats.last_activity || '')
                            },
                            loading: false
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载科目信息失败:', err_1);
                        errorMsg = (err_1 && err_1.message) || '加载失败';
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            wx.reLaunch({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: errorMsg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
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
    },
    onStartPracticeTap: function () {
        var subject = this.data.subject;
        console.log('准备跳转到练习设置页面:', subject);
        if (!subject) {
            wx.showToast({ title: '科目信息缺失', icon: 'none' });
            return;
        }
        var url = "/pages/practice-setup/practice-setup?subject=".concat(encodeURIComponent(subject));
        console.log('跳转URL:', url);
        wx.navigateTo({
            url: url,
            success: function () {
                console.log('跳转成功');
            },
            fail: function (err) {
                console.error('跳转失败:', err);
                wx.showToast({ title: '跳转失败: ' + (err.errMsg || '未知错误'), icon: 'none', duration: 3000 });
            }
        });
    },
    onButtonTap: function (e) {
        var action = e.currentTarget.dataset.action;
        console.log('按钮点击，action:', action);
        if (action === 'practice') {
            console.log('跳转到练习页面，subject:', this.data.subject);
            this.onStartPracticeTap();
            return;
        }
        if (action === 'exam') {
            wx.navigateTo({
                url: "/pages/exam-setup/exam-setup?subject=".concat(encodeURIComponent(this.data.subject))
            });
            return;
        }
        if (action === 'search') {
            wx.navigateTo({
                url: "/pages/search/search?subject=".concat(encodeURIComponent(this.data.subject))
            });
            return;
        }
        if (action === 'update') {
            this.onUpdateQuestionsTap();
            return;
        }
        if (action === 'favorites') {
            this.goToQuestionBank('favorites');
            return;
        }
        if (action === 'mistakes') {
            this.goToQuestionBank('mistakes');
            return;
        }
        if (action === 'stats') {
            wx.navigateTo({
                url: "/pages/subject-stats/subject-stats?subject=".concat(encodeURIComponent(this.data.subject))
            });
            return;
        }
        wx.showToast({ title: '功能开发中', icon: 'none' });
    },
    onUpdateQuestionsTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        wx.showLoading({ title: '同步中...' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, this.loadSubjectInfo()];
                    case 2:
                        _a.sent();
                        wx.hideLoading();
                        wx.showToast({ title: '已同步', icon: 'success' });
                        return [3 /*break*/, 4];
                    case 3:
                        e_1 = _a.sent();
                        wx.hideLoading();
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    goToQuestionBank: function (source) {
        var subject = this.data.subject;
        if (!subject)
            return;
        var saved = wx.getStorageSync("practice_settings_".concat(subject)) || {};
        var shuffleQuestions = !!saved.shuffleQuestions;
        var shuffleOptions = !!saved.shuffleOptions;
        var params = [];
        params.push("subject=".concat(encodeURIComponent(subject)));
        params.push('mode=quiz');
        params.push("source=".concat(source));
        if (shuffleQuestions)
            params.push('shuffle_questions=1');
        if (shuffleOptions)
            params.push('shuffle_options=1');
        wx.navigateTo({ url: "/pages/quiz/quiz?".concat(params.join('&')) });
    },
    onShareAppMessage: function () {
        var subject = this.data.subject || '科目';
        return {
            title: "\u4E00\u8D77\u5237\u9898\uFF1A".concat(subject),
            path: "/pages/subject-detail/subject-detail?subject=".concat(encodeURIComponent(subject))
        };
    },
    onShareTimeline: function () {
        var subject = this.data.subject || '科目';
        return {
            title: "\u4E00\u8D77\u5237\u9898\uFF1A".concat(subject),
            query: "subject=".concat(encodeURIComponent(subject))
        };
    }
});
