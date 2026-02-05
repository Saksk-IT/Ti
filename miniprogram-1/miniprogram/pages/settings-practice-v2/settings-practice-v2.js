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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var user_settings_1 = require("../../utils/user-settings");
var last_practice_1 = require("../../utils/last-practice");
var theme_1 = require("../../utils/theme");
var HOME_VISIBLE_SUBJECTS_KEY = 'home_visible_subjects';
var QUIZ_FAB_ENABLED_KEY = 'quiz_fab_enabled_v1';
var QUIZ_LAYOUT_THEME_KEY = 'quiz_layout_theme_v1';
function navTo(key) {
    if (key === 'account')
        return '/pages/settings-account-profile-v2/settings-account-profile-v2';
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (key === 'about')
        return '/pages/settings-about-v2/settings-about-v2';
    return '/pages/settings-practice-v2/settings-practice-v2';
}
function uniq(arr) {
    var s = new Set();
    var out = [];
    (arr || []).forEach(function (x) {
        var v = String(x || '').trim();
        if (!v || s.has(v))
            return;
        s.add(v);
        out.push(v);
    });
    return out;
}
function readVisibleSubjects() {
    try {
        var raw = wx.getStorageSync(HOME_VISIBLE_SUBJECTS_KEY);
        if (Array.isArray(raw))
            return uniq(raw.map(function (x) { return String(x || '').trim(); }).filter(Boolean));
        if (typeof raw === 'string' && raw.trim().startsWith('[')) {
            var js = JSON.parse(raw);
            if (Array.isArray(js))
                return uniq(js.map(function (x) { return String(x || '').trim(); }).filter(Boolean));
        }
    }
    catch (e) { }
    return [];
}
function writeVisibleSubjects(names) {
    try {
        wx.setStorageSync(HOME_VISIBLE_SUBJECTS_KEY, uniq(names));
    }
    catch (e) { }
}
function isQuizFabEnabled() {
    try {
        var raw = wx.getStorageSync(QUIZ_FAB_ENABLED_KEY);
        if (raw === '' || raw == null)
            return true;
        var s = String(raw).trim();
        if (s === '0' || s === 'false' || s === 'off' || s === 'no')
            return false;
        return true;
    }
    catch (e) {
        return true;
    }
}
function setQuizFabEnabled(on) {
    try {
        wx.setStorageSync(QUIZ_FAB_ENABLED_KEY, on ? '1' : '0');
    }
    catch (e) { }
}
function getQuizLayoutTheme() {
    try {
        var raw = wx.getStorageSync(QUIZ_LAYOUT_THEME_KEY);
        var s = String(raw || '').trim().toLowerCase();
        return s === 'card' ? 'card' : 'traditional';
    }
    catch (e) {
        return 'traditional';
    }
}
function setQuizLayoutTheme(theme) {
    var t = theme === 'card' ? 'card' : 'traditional';
    try {
        wx.setStorageSync(QUIZ_LAYOUT_THEME_KEY, t);
    }
    catch (e) { }
}
function buildSubjectSummary(visible, all) {
    var v = uniq(visible);
    var a = uniq(all);
    if (!v.length)
        return '全部科目';
    // 若等于全部，也视为“全部”
    if (a.length && v.length >= a.length) {
        var setV_1 = new Set(v);
        var isAll = a.every(function (x) { return setV_1.has(x); });
        if (isAll)
            return '全部科目';
    }
    if (v.length <= 4)
        return v.join('、');
    return "".concat(v.slice(0, 3).join('、'), " \u7B49 ").concat(v.length, " \u95E8");
}
Page({
    data: {
        drawerOpen: false,
        navKey: 'practice',
        msg: '',
        subjectSummary: '全部科目',
        subjectsAll: [],
        subjectsLoading: false,
        quizFabEnabled: true,
        quizLayoutTheme: 'traditional',
        subjectModalOpen: false,
        modalRows: []
    },
    onLoad: function () {
        wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=practice' });
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
        var subjectsAll = this.data.subjectsAll || [];
        var visible = readVisibleSubjects();
        this.setData({
            quizFabEnabled: isQuizFabEnabled(),
            quizLayoutTheme: getQuizLayoutTheme(),
            subjectSummary: buildSubjectSummary(visible, subjectsAll)
        });
        // 背景拉取一次科目列表，用于“全部科目”判断与弹层
        this.ensureSubjects(false);
    },
    onHamburgerTap: function () {
        this.setData({ drawerOpen: true });
    },
    onDrawerClose: function () {
        this.setData({ drawerOpen: false });
    },
    onDrawerNavigate: function (e) {
        var _a, _b;
        var url = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.url;
        var navType = (_b = e === null || e === void 0 ? void 0 : e.detail) === null || _b === void 0 ? void 0 : _b.navType;
        this.setData({ drawerOpen: false });
        if (!url)
            return;
        (0, nav_1.safeNavigate)(url, navType);
    },
    onDrawerSelectStyle: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        style = (((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        this.setData({ drawerOpen: false });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
    onContinueLast: function () {
        var url = (0, last_practice_1.buildLastPracticeUrl)();
        if (!url) {
            wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
            return;
        }
        wx.navigateTo({ url: url });
    },
    onSettingsNavTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = navTo(key);
        if (url === '/pages/settings-practice-v2/settings-practice-v2')
            return;
        wx.redirectTo({ url: url });
    },
    ensureSubjects: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var res, listRaw, subjectsAll, e_1;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.subjectsLoading)
                            return [2 /*return*/];
                        if (!force && Array.isArray(this.data.subjectsAll) && this.data.subjectsAll.length)
                            return [2 /*return*/];
                        this.setData({ subjectsLoading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getSubjects()];
                    case 2:
                        res = _a.sent();
                        listRaw = Array.isArray(res === null || res === void 0 ? void 0 : res.subjects) ? res.subjects : Array.isArray(res) ? res : [];
                        subjectsAll = uniq(listRaw.map(function (x) { return String(x || '').trim(); }).filter(Boolean));
                        this.setData({ subjectsAll: subjectsAll });
                        this.setData({ subjectSummary: buildSubjectSummary(readVisibleSubjects(), subjectsAll) });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ subjectsLoading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onOpenSubjectModal: function () {
        return __awaiter(this, void 0, void 0, function () {
            var all, visible, setV, treatAll, selected, setSel, modalRows;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.ensureSubjects(true)];
                    case 1:
                        _a.sent();
                        all = uniq(this.data.subjectsAll || []);
                        visible = uniq(readVisibleSubjects());
                        setV = new Set(visible);
                        treatAll = !visible.length || (all.length && all.every(function (x) { return setV.has(x); }));
                        selected = treatAll ? all : all.filter(function (x) { return setV.has(x); });
                        setSel = new Set(selected);
                        modalRows = all.map(function (name) { return ({ name: name, checked: setSel.has(name) }); });
                        this.setData({ subjectModalOpen: true, modalRows: modalRows });
                        return [2 /*return*/];
                }
            });
        });
    },
    onCloseSubjectModal: function () {
        this.setData({ subjectModalOpen: false });
    },
    stopTap: function () { },
    onSelectAllSubjects: function () {
        var modalRows = (this.data.modalRows || []).map(function (r) { return (__assign(__assign({}, r), { checked: true })); });
        this.setData({ modalRows: modalRows });
    },
    onClearAllSubjects: function () {
        var modalRows = (this.data.modalRows || []).map(function (r) { return (__assign(__assign({}, r), { checked: false })); });
        this.setData({ modalRows: modalRows });
    },
    onModalSubjectToggle: function (e) {
        var _a, _b;
        var name = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.name) || '').trim();
        var checked = !!(e && e.detail && e.detail.value);
        if (!name)
            return;
        var modalRows = (this.data.modalRows || []).map(function (r) { return (r.name === name ? __assign(__assign({}, r), { checked: checked }) : r); });
        this.setData({ modalRows: modalRows });
    },
    onCancelSubjectSelection: function () {
        this.setData({ subjectModalOpen: false });
    },
    onApplySubjectSelection: function () {
        return __awaiter(this, void 0, void 0, function () {
            var all, checked, next;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        all = uniq(this.data.subjectsAll || []);
                        checked = uniq((this.data.modalRows || []).filter(function (r) { return r.checked; }).map(function (r) { return r.name; }));
                        next = all.length && checked.length >= all.length ? [] : checked;
                        writeVisibleSubjects(next);
                        this.setData({
                            subjectModalOpen: false,
                            subjectSummary: buildSubjectSummary(next, all),
                            msg: '已应用'
                        });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onClearSubjectFilter: function () {
        return __awaiter(this, void 0, void 0, function () {
            var ok;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, new Promise(function (resolve) {
                            wx.showModal({
                                title: '显示全部',
                                content: '确定要显示全部科目吗？',
                                confirmText: '确定',
                                cancelText: '取消',
                                success: function (res) { return resolve(!!res.confirm); },
                                fail: function () { return resolve(false); }
                            });
                        })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        writeVisibleSubjects([]);
                        this.setData({
                            subjectSummary: buildSubjectSummary([], this.data.subjectsAll || []),
                            msg: '已设置为显示全部'
                        });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 2:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onQuizFabChange: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var on;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        on = !!(e && e.detail && e.detail.value);
                        setQuizFabEnabled(on);
                        this.setData({ quizFabEnabled: on, msg: on ? '已开启悬浮球' : '已关闭悬浮球' });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onLayoutTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var key, next;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.layout) || 'traditional');
                        next = key === 'card' ? 'card' : 'traditional';
                        setQuizLayoutTheme(next);
                        this.setData({ quizLayoutTheme: next, msg: next === 'card' ? '已切换到卡片布局' : '已切换到传统布局' });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _c.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onResetPractice: function () {
        return __awaiter(this, void 0, void 0, function () {
            var ok, all;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, new Promise(function (resolve) {
                            wx.showModal({
                                title: '恢复默认',
                                content: '确定要恢复通用设置的默认值吗？',
                                confirmText: '确定',
                                cancelText: '取消',
                                success: function (res) { return resolve(!!res.confirm); },
                                fail: function () { return resolve(false); }
                            });
                        })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        writeVisibleSubjects([]);
                        setQuizFabEnabled(true);
                        setQuizLayoutTheme('traditional');
                        all = this.data.subjectsAll || [];
                        this.setData({
                            quizFabEnabled: true,
                            quizLayoutTheme: 'traditional',
                            subjectSummary: buildSubjectSummary([], all),
                            msg: '已恢复默认'
                        });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 2:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    }
});
