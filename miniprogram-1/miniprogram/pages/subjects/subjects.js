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
// subjects.ts - 科目页
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        subjects: [],
        filteredSubjects: [],
        keyword: '',
        loading: false,
        isLoggedIn: false
    },
    onShow: function () {
        var isLoggedIn = (0, auth_1.checkLogin)();
        this.setData({ isLoggedIn: isLoggedIn });
        // 无论是否登录都加载科目列表
        this.loadSubjects();
    },
    loadSubjects: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, list, subjects, err_1;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getSubjects()];
                    case 2:
                        res = _a.sent();
                        list = (res && res.subjects) ? res.subjects : [];
                        subjects = Array.isArray(list) ? list.filter(function (x) { return typeof x === 'string' && x.trim(); }) : [];
                        this.setData({ subjects: subjects }, function () {
                            _this.applyFilter();
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        err_1 = _a.sent();
                        console.error('加载科目失败:', err_1);
                        wx.showToast({ title: (err_1 && err_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onKeywordInput: function (e) {
        var _this = this;
        var keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
        this.setData({ keyword: keyword }, function () { return _this.applyFilter(); });
    },
    onClearKeyword: function () {
        var _this = this;
        this.setData({ keyword: '' }, function () { return _this.applyFilter(); });
    },
    applyFilter: function () {
        var kw = (this.data.keyword || '').trim().toLowerCase();
        var list = this.data.subjects || [];
        var filteredSubjects = kw
            ? list.filter(function (s) { return String(s).toLowerCase().includes(kw); })
            : list.slice();
        this.setData({ filteredSubjects: filteredSubjects });
    },
    onSubjectTap: function (e) {
        var subject = e.currentTarget.dataset.subject;
        if (!subject)
            return;
        // 未登录时提示登录
        if (!this.data.isLoggedIn) {
            wx.showModal({
                title: '提示',
                content: '登录后可进入科目详情',
                confirmText: '去登录',
                cancelText: '取消',
                success: function (res) {
                    if (res.confirm) {
                        wx.navigateTo({ url: '/pages/login/login' });
                    }
                }
            });
            return;
        }
        wx.navigateTo({ url: "/pages/subject-detail-v2/subject-detail-v2?subject=".concat(encodeURIComponent(subject)) });
    },
    onPullDownRefresh: function () {
        this.loadSubjects().finally(function () { return wx.stopPullDownRefresh(); });
    }
});
