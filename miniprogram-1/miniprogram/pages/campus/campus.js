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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var campus_content_1 = require("./campus-content");
var SEMESTER_LABELS = ['第一、二学期', '第一学期', '第二学期'];
var SEMESTER_VALUES = ['all', '3', '12'];
function defaultAcademicYear() {
    var now = new Date();
    var month = now.getMonth() + 1;
    return month >= 9 ? now.getFullYear() : now.getFullYear() - 1;
}
function normalizeCredential(credential) {
    return {
        has_credentials: !!(credential === null || credential === void 0 ? void 0 : credential.has_credentials),
        username_hint: String((credential === null || credential === void 0 ? void 0 : credential.username_hint) || '').trim(),
    };
}
var defaultYear = defaultAcademicYear();
Page({
    data: {
        mode: 'schedule',
        modeLabels: ['查询课表', '查询成绩'],
        semesterLabels: SEMESTER_LABELS,
        semesterIndex: 0,
        startYear: String(defaultYear),
        endYear: String(defaultYear),
        loading: false,
        statusLoading: false,
        statusReady: false,
        statusFailed: false,
        errorMsg: '',
        statusMsg: '',
        eduBound: false,
        eduUsernameHint: '',
        scheduleResults: [],
        gradeResults: [],
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        this.loadEduStatus(false);
    },
    onRefresh: function () {
        Promise.resolve(this.loadEduStatus(true))
            .then(function () { return wx.stopPullDownRefresh(); })
            .catch(function () { return wx.stopPullDownRefresh(); });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(Object.assign(Object.assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
    onModeTap: function (e) {
        var _a, _b;
        var mode = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.mode) || '');
        if (mode !== 'schedule' && mode !== 'grades')
            return;
        this.setData({ mode: mode, errorMsg: '' });
    },
    onStartYearInput: function (e) {
        var _a, _b;
        this.setData({ startYear: String(((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : '')).trim() });
    },
    onEndYearInput: function (e) {
        var _a, _b;
        this.setData({ endYear: String(((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : '')).trim() });
    },
    onSemesterChange: function (e) {
        var _a, _b;
        var value = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : 0);
        var max = SEMESTER_LABELS.length - 1;
        var semesterIndex = Math.max(0, Math.min(value, max));
        this.setData({ semesterIndex: semesterIndex });
    },
    onGoEduBindingTap: function () {
        (0, nav_1.safeNavigate)('/pages/settings-account-bindings-v2/settings-account-bindings-v2', 'navigateTo');
    },
    onHeroActionTap: function () {
        if (this.data.statusFailed) {
            this.loadEduStatus(true);
            return;
        }
        this.onGoEduBindingTap();
    },
    applyEduStatus: function (data) {
        var credential = normalizeCredential(data === null || data === void 0 ? void 0 : data.credential);
        this.setData({
            statusReady: true,
            statusFailed: false,
            eduBound: credential.has_credentials,
            eduUsernameHint: credential.username_hint,
            statusMsg: credential.has_credentials ? "\u5DF2\u7ED1\u5B9A\u6559\u52A1\u7CFB\u7EDF\u8D26\u53F7\uFF1A".concat(credential.username_hint || '已保存') : '未绑定教务系统账号',
            scheduleResults: (0, campus_content_1.normalizeScheduleSnapshots)((data === null || data === void 0 ? void 0 : data.snapshots) || []),
            gradeResults: (0, campus_content_1.normalizeGradeSnapshots)((data === null || data === void 0 ? void 0 : data.grade_snapshots) || []),
        });
    },
    loadEduStatus: function (force) {
        if (force === void 0) { force = false; }
        return __awaiter(this, void 0, void 0, function () {
            var self, now, lastAt, data, e_1, message;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastCampusStatusAt || 0) || 0;
                        if (!force && now - lastAt < 8000)
                            return [2 /*return*/];
                        self.__lastCampusStatusAt = now;
                        this.setData({ statusLoading: true, statusFailed: false, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getEduScheduleStatus()];
                    case 2:
                        data = _a.sent();
                        this.applyEduStatus(data || {});
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        message = (0, campus_content_1.campusFriendlyError)(e_1, '教务账号状态加载失败');
                        this.setData({
                            statusReady: true,
                            statusFailed: true,
                            eduBound: false,
                            statusMsg: message,
                            errorMsg: message,
                        });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ statusLoading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    showBindPrompt: function () {
        var _this = this;
        wx.showModal({
            title: '未绑定教务系统账号',
            content: '请先绑定教务系统账号后再查询课表和成绩。',
            confirmText: '去绑定',
            cancelText: '取消',
            success: function (res) {
                if (res.confirm)
                    _this.onGoEduBindingTap();
            },
        });
    },
    onQueryTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var message, terms, semester, e_2, mode, payload, data, rows, credential, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        if (this.data.statusLoading || !this.data.statusReady) {
                            this.setData({ errorMsg: '教务系统账号状态同步中，请稍后再试' });
                            return [2 /*return*/];
                        }
                        if (this.data.statusFailed) {
                            message = '教务接口暂不可用，请检查 API 地址或稍后重试';
                            this.setData({ statusMsg: message, errorMsg: message });
                            return [2 /*return*/];
                        }
                        if (!this.data.eduBound) {
                            this.showBindPrompt();
                            return [2 /*return*/];
                        }
                        try {
                            semester = SEMESTER_VALUES[this.data.semesterIndex] || 'all';
                            terms = (0, campus_content_1.buildCampusTerms)(this.data.startYear, this.data.endYear, semester);
                        }
                        catch (e) {
                            e_2 = e;
                            this.setData({ errorMsg: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '学年或学期不正确' });
                            return [2 /*return*/];
                        }
                        mode = this.data.mode;
                        this.setData({
                            loading: true,
                            errorMsg: '',
                            statusMsg: mode === 'grades' ? '正在查询成绩...' : '正在查询课表...',
                        });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        payload = { terms: terms };
                        if (!(mode === 'grades')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.queryEduGrades(payload)];
                    case 2:
                        data = _a.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.queryEduSchedule(payload)];
                    case 4:
                        data = _a.sent();
                        _a.label = 5;
                    case 5:
                        rows = (0, campus_content_1.normalizeTermResults)(data || {}, mode);
                        if (mode === 'grades') {
                            this.setData({ gradeResults: rows, statusMsg: '成绩查询完成' });
                        }
                        else {
                            this.setData({ scheduleResults: rows, statusMsg: '课表查询完成' });
                        }
                        if (data === null || data === void 0 ? void 0 : data.credential) {
                            credential = normalizeCredential(data.credential);
                            this.setData({
                                eduBound: credential.has_credentials,
                                eduUsernameHint: credential.username_hint,
                            });
                        }
                        return [3 /*break*/, 8];
                    case 6:
                        e_3 = _a.sent();
                        this.setData({ errorMsg: (0, campus_content_1.campusFriendlyError)(e_3, '查询失败，请稍后重试') });
                        return [3 /*break*/, 8];
                    case 7:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
});
