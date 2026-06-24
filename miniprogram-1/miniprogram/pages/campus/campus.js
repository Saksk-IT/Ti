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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var campus_content_1 = require("./campus-content");
var SEMESTER_LABELS = ['第一、二学期', '第一学期', '第二学期'];
var SEMESTER_VALUES = ['all', '3', '12'];
var ACADEMIC_YEAR_PAST_COUNT = 6;
var ACADEMIC_YEAR_FUTURE_COUNT = 2;
var ACTIVE_TASK_STATUSES = ['pending', 'running', 'retrying', 'webvpn_refresh_required'];
var POLL_INTERVAL_MS = 2000;
function defaultAcademicYear() {
    var now = new Date();
    var month = now.getMonth() + 1;
    return month >= 9 ? now.getFullYear() : now.getFullYear() - 1;
}
function formatAcademicYearLabel(year) {
    return "".concat(year, "~").concat(year + 1);
}
function buildAcademicYearOptions(defaultYear) {
    var options = [];
    for (var year = defaultYear - ACADEMIC_YEAR_PAST_COUNT; year <= defaultYear + ACADEMIC_YEAR_FUTURE_COUNT; year += 1) {
        options.push({ label: formatAcademicYearLabel(year), value: String(year) });
    }
    return options;
}
function clampAcademicYearIndex(value, fallback) {
    var index = Number(value);
    if (!Number.isInteger(index))
        return fallback;
    return Math.max(0, Math.min(index, ACADEMIC_YEAR_OPTIONS.length - 1));
}
function academicYearValueAt(index) {
    var _a;
    return ((_a = ACADEMIC_YEAR_OPTIONS[index]) === null || _a === void 0 ? void 0 : _a.value) || String(defaultYear);
}
function normalizeCredential(credential) {
    return {
        has_credentials: !!(credential === null || credential === void 0 ? void 0 : credential.has_credentials),
        username_hint: String((credential === null || credential === void 0 ? void 0 : credential.username_hint) || '').trim(),
    };
}
function ensureRuntimeState(self) {
    if (!self.__campusTaskTimers)
        self.__campusTaskTimers = { schedule: null, grades: null };
    if (!self.__activeCampusTasks)
        self.__activeCampusTasks = { schedule: null, grades: null };
    if (!self.__lastCampusProgress)
        self.__lastCampusProgress = { schedule: null, grades: null };
    return self;
}
function isActiveTask(task) {
    return !!(task === null || task === void 0 ? void 0 : task.task_id) && ACTIVE_TASK_STATUSES.indexOf(String(task.status || '')) !== -1;
}
function taskStatusLabel(status) {
    if (status === 'pending')
        return '排队中';
    if (status === 'running')
        return '查询中';
    if (status === 'retrying')
        return '自动重试中';
    if (status === 'webvpn_refresh_required')
        return '等待验证码';
    if (status === 'succeeded')
        return '已完成';
    if (status === 'cancelled')
        return '已停止';
    if (status === 'failed')
        return '查询失败';
    return '查询中';
}
function taskProgressPercent(task) {
    var status = String((task === null || task === void 0 ? void 0 : task.status) || '');
    if (status === 'succeeded' || status === 'cancelled' || status === 'failed')
        return 100;
    if (status === 'webvpn_refresh_required')
        return 72;
    var attempt = Math.max(0, Number((task === null || task === void 0 ? void 0 : task.attempt) || (task === null || task === void 0 ? void 0 : task.attempt_count) || 0) || 0);
    return Math.max(16, Math.min(92, 24 + attempt * 7));
}
function xqmLabel(value) {
    var xqm = String(value || '').trim();
    if (xqm === '3')
        return '第一学期';
    if (xqm === '12')
        return '第二学期';
    return xqm ? "\u7B2C".concat(xqm, "\u5B66\u671F") : '未知学期';
}
function rowYearValue(row) {
    return String((row === null || row === void 0 ? void 0 : row.xnm) || '').trim();
}
function rowSemesterValue(row) {
    return String((row === null || row === void 0 ? void 0 : row.xqm) || '').trim();
}
function rowKey(row, index) {
    return String((row === null || row === void 0 ? void 0 : row.termKey) || [rowYearValue(row), rowSemesterValue(row)].filter(Boolean).join('-') || "".concat((row === null || row === void 0 ? void 0 : row.title) || 'term', "-").concat(index));
}
function compareTermRows(a, b) {
    var yearDiff = (Number(rowYearValue(b)) || 0) - (Number(rowYearValue(a)) || 0);
    if (yearDiff !== 0)
        return yearDiff;
    var order = { '12': 2, '3': 1 };
    return (order[rowSemesterValue(b)] || 0) - (order[rowSemesterValue(a)] || 0);
}
function mergeCampusRows(existing, incoming) {
    var next = (Array.isArray(existing) ? existing : []).slice();
    (Array.isArray(incoming) ? incoming : []).forEach(function (row, index) {
        var key = rowKey(row, index);
        var found = next.findIndex(function (item, itemIndex) { return rowKey(item, itemIndex) === key; });
        if (found >= 0) {
            next.splice(found, 1, __assign(__assign({}, next[found]), row));
        }
        else {
            next.push(__assign({}, row));
        }
    });
    return next.sort(compareTermRows);
}
function buildSnapshotYearOptions(rows, selectedYear) {
    var counts = {};
    rows.forEach(function (row) {
        var year = rowYearValue(row);
        if (!year)
            return;
        counts[year] = (counts[year] || 0) + 1;
    });
    return Object.keys(counts)
        .sort(function (a, b) { return (Number(b) || 0) - (Number(a) || 0); })
        .map(function (year) { return ({
        value: year,
        label: formatAcademicYearLabel(Number(year)),
        count: counts[year],
        active: year === selectedYear,
    }); });
}
function buildSnapshotTermOptions(rows, selectedYear, selectedSemester) {
    var counts = {};
    rows.forEach(function (row) {
        if (rowYearValue(row) !== selectedYear)
            return;
        var semester = rowSemesterValue(row);
        if (!semester)
            return;
        counts[semester] = (counts[semester] || 0) + 1;
    });
    var terms = Object.keys(counts).sort(function (a, b) {
        var order = { '12': 2, '3': 1 };
        return (order[b] || Number(b) || 0) - (order[a] || Number(a) || 0);
    });
    var total = terms.reduce(function (sum, semester) { return sum + counts[semester]; }, 0);
    return __spreadArray([
        { value: 'all', label: '全部学期', count: total, active: selectedSemester === 'all' }
    ], terms.map(function (semester) { return ({
        value: semester,
        label: xqmLabel(semester),
        count: counts[semester],
        active: semester === selectedSemester,
    }); }), true);
}
function filterSnapshotRows(rows, selectedYear, selectedSemester) {
    return rows.filter(function (row) {
        if (selectedYear && rowYearValue(row) !== selectedYear)
            return false;
        if (selectedSemester !== 'all' && rowSemesterValue(row) !== selectedSemester)
            return false;
        return true;
    });
}
function formatTaskTerms(terms) {
    var normalized = Array.isArray(terms) ? terms : [];
    if (!normalized.length)
        return '';
    return normalized
        .slice(0, 3)
        .map(function (term) { return "".concat(formatAcademicYearLabel(Number(term === null || term === void 0 ? void 0 : term.xnm) || 0), " ").concat(xqmLabel(term === null || term === void 0 ? void 0 : term.xqm)); })
        .join('、') + (normalized.length > 3 ? " \u7B49 ".concat(normalized.length, " \u4E2A\u5B66\u671F") : '');
}
function taskRowsSource(task, data) {
    var credential = (data === null || data === void 0 ? void 0 : data.credential) || (task === null || task === void 0 ? void 0 : task.credential) || {};
    if (Array.isArray(task === null || task === void 0 ? void 0 : task.results) && task.results.length)
        return { results: task.results, credential: credential };
    if (Array.isArray(task === null || task === void 0 ? void 0 : task.snapshots) && task.snapshots.length)
        return { results: task.snapshots, credential: credential };
    return data || {};
}
function emptyProgress() {
    return {
        queryProgressVisible: false,
        queryProgressStatus: '',
        queryProgressPercent: 0,
        queryProgressDetail: '',
        queryProgressMeta: '',
    };
}
var defaultYear = defaultAcademicYear();
var ACADEMIC_YEAR_OPTIONS = buildAcademicYearOptions(defaultYear);
var DEFAULT_ACADEMIC_YEAR_INDEX = ACADEMIC_YEAR_PAST_COUNT;
Page({
    data: {
        mode: 'schedule',
        modeLabels: ['查询课表', '查询成绩'],
        academicYearLabels: ACADEMIC_YEAR_OPTIONS.map(function (item) { return item.label; }),
        academicYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
        semesterLabels: SEMESTER_LABELS,
        semesterIndex: 0,
        academicYear: academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX),
        loading: false,
        statusLoading: false,
        statusReady: false,
        statusFailed: false,
        errorMsg: '',
        statusMsg: '',
        eduBound: false,
        eduUsernameHint: '',
        allScheduleResults: [],
        allGradeResults: [],
        scheduleResults: [],
        gradeResults: [],
        snapshotYears: [],
        snapshotTerms: [],
        snapshotSelectedYear: '',
        snapshotSelectedSemester: 'all',
        snapshotDrawerOpen: false,
        snapshotDrawerTitle: '',
        queryProgressVisible: false,
        queryProgressStatus: '',
        queryProgressPercent: 0,
        queryProgressDetail: '',
        queryProgressMeta: '',
        captchaVisible: false,
        captchaMode: 'schedule',
        captchaChallengeId: '',
        captchaImage: '',
        captchaCode: '',
        captchaMessage: '',
        captchaSubmitting: false,
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
    onUnload: function () {
        this.clearAllTaskPolling();
    },
    onRefresh: function () {
        Promise.resolve(this.loadEduStatus(true))
            .then(function () { return wx.stopPullDownRefresh(); })
            .catch(function () { return wx.stopPullDownRefresh(); });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onModeTap: function (e) {
        var _this = this;
        var _a, _b;
        var mode = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.mode) || '');
        if (mode !== 'schedule' && mode !== 'grades')
            return;
        this.setData({ mode: mode, errorMsg: '', snapshotDrawerOpen: false }, function () {
            _this.syncSnapshotBrowserForMode(mode);
            _this.refreshProgressForMode(mode);
        });
    },
    onAcademicYearChange: function (e) {
        var _a;
        var academicYearIndex = clampAcademicYearIndex((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, this.data.academicYearIndex);
        this.setData({
            academicYearIndex: academicYearIndex,
            academicYear: academicYearValueAt(academicYearIndex),
        });
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
        var _this = this;
        var credential = normalizeCredential(data === null || data === void 0 ? void 0 : data.credential);
        this.setData({
            statusReady: true,
            statusFailed: false,
            eduBound: credential.has_credentials,
            eduUsernameHint: credential.username_hint,
            statusMsg: credential.has_credentials ? "\u5DF2\u7ED1\u5B9A\u6559\u52A1\u7CFB\u7EDF\u8D26\u53F7\uFF1A".concat(credential.username_hint || '已保存') : '未绑定教务系统账号',
            allScheduleResults: (0, campus_content_1.normalizeScheduleSnapshots)((data === null || data === void 0 ? void 0 : data.snapshots) || []),
            allGradeResults: (0, campus_content_1.normalizeGradeSnapshots)((data === null || data === void 0 ? void 0 : data.grade_snapshots) || []),
        }, function () {
            _this.syncSnapshotBrowserForMode(_this.data.mode);
            _this.restoreRecentCampusTasks((data === null || data === void 0 ? void 0 : data.recent_tasks) || {});
        });
    },
    loadEduStatus: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, data, e_1, message;
            if (force === void 0) { force = false; }
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
    syncSnapshotBrowserForMode: function (modeInput) {
        var _this = this;
        var _a;
        var mode = modeInput || this.data.mode;
        var rows = mode === 'grades' ? this.data.allGradeResults : this.data.allScheduleResults;
        var years = buildSnapshotYearOptions(rows, this.data.snapshotSelectedYear);
        var selectedYear = years.some(function (item) { return item.value === _this.data.snapshotSelectedYear; })
            ? this.data.snapshotSelectedYear
            : (((_a = years[0]) === null || _a === void 0 ? void 0 : _a.value) || '');
        var terms = selectedYear ? buildSnapshotTermOptions(rows, selectedYear, this.data.snapshotSelectedSemester) : [];
        var selectedSemester = terms.some(function (item) { return item.value === _this.data.snapshotSelectedSemester; })
            ? this.data.snapshotSelectedSemester
            : 'all';
        var patch = {
            snapshotSelectedYear: selectedYear,
            snapshotSelectedSemester: selectedSemester,
            snapshotYears: buildSnapshotYearOptions(rows, selectedYear),
            snapshotTerms: selectedYear ? buildSnapshotTermOptions(rows, selectedYear, selectedSemester) : [],
            snapshotDrawerTitle: selectedYear ? "".concat(formatAcademicYearLabel(Number(selectedYear)), " \u5B66\u671F") : '',
            snapshotDrawerOpen: selectedYear ? this.data.snapshotDrawerOpen : false,
        };
        patch[mode === 'grades' ? 'gradeResults' : 'scheduleResults'] = selectedYear
            ? filterSnapshotRows(rows, selectedYear, selectedSemester)
            : [];
        this.setData(patch);
    },
    onSnapshotYearTap: function (e) {
        var _this = this;
        var _a, _b;
        var year = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.year) || '').trim();
        if (!year)
            return;
        this.setData({
            snapshotSelectedYear: year,
            snapshotSelectedSemester: 'all',
            snapshotDrawerOpen: true,
        }, function () { return _this.syncSnapshotBrowserForMode(_this.data.mode); });
    },
    onSnapshotTermTap: function (e) {
        var _this = this;
        var _a, _b;
        var semester = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.semester) || 'all').trim() || 'all';
        this.setData({
            snapshotSelectedSemester: semester,
            snapshotDrawerOpen: false,
        }, function () { return _this.syncSnapshotBrowserForMode(_this.data.mode); });
    },
    applyQueryRows: function (data, mode, statusMsg) {
        var _this = this;
        if (statusMsg === void 0) { statusMsg = ''; }
        var rows = (0, campus_content_1.normalizeTermResults)(data || {}, mode);
        var sourceKey = mode === 'grades' ? 'allGradeResults' : 'allScheduleResults';
        var patch = {};
        patch[sourceKey] = mergeCampusRows(this.data[sourceKey] || [], rows);
        if (statusMsg)
            patch.statusMsg = statusMsg;
        this.setData(patch, function () {
            if (_this.data.mode === mode)
                _this.syncSnapshotBrowserForMode(mode);
        });
        if (data === null || data === void 0 ? void 0 : data.credential) {
            var credential = normalizeCredential(data.credential);
            this.setData({
                eduBound: credential.has_credentials,
                eduUsernameHint: credential.username_hint,
            });
        }
        return rows;
    },
    getActiveCampusTask: function (mode) {
        var self = ensureRuntimeState(this);
        return self.__activeCampusTasks[mode];
    },
    setActiveCampusTask: function (mode, task) {
        var self = ensureRuntimeState(this);
        self.__activeCampusTasks[mode] = task || null;
    },
    setProgressForTask: function (task, mode) {
        var status = String((task === null || task === void 0 ? void 0 : task.status) || 'running');
        var progress = {
            queryProgressVisible: true,
            queryProgressStatus: taskStatusLabel(status),
            queryProgressPercent: taskProgressPercent(task),
            queryProgressDetail: String((task === null || task === void 0 ? void 0 : task.message) || (mode === 'grades' ? '正在后台查询成绩' : '正在后台查询课表')),
            queryProgressMeta: formatTaskTerms(Array.isArray(task === null || task === void 0 ? void 0 : task.terms) ? task.terms : []),
        };
        var self = ensureRuntimeState(this);
        self.__lastCampusProgress[mode] = progress;
        if (this.data.mode === mode)
            this.setData(progress);
    },
    refreshProgressForMode: function (mode) {
        var self = ensureRuntimeState(this);
        var progress = self.__lastCampusProgress[mode] || emptyProgress();
        this.setData(progress);
    },
    clearTaskPolling: function (mode) {
        var self = ensureRuntimeState(this);
        var timer = self.__campusTaskTimers[mode];
        if (timer)
            clearTimeout(timer);
        self.__campusTaskTimers[mode] = null;
    },
    clearAllTaskPolling: function () {
        this.clearTaskPolling('schedule');
        this.clearTaskPolling('grades');
    },
    startTaskPolling: function (taskId, mode, payload) {
        var _this = this;
        this.clearTaskPolling(mode);
        var poll = function () { return __awaiter(_this, void 0, void 0, function () {
            var data, task, finished, self, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, api_1.api.getEduQueryTask(taskId)];
                    case 1:
                        data = _a.sent();
                        task = data === null || data === void 0 ? void 0 : data.task;
                        finished = this.handleTaskState(task, payload, mode, data || {});
                        if (!finished) {
                            self = ensureRuntimeState(this);
                            self.__campusTaskTimers[mode] = setTimeout(poll, POLL_INTERVAL_MS);
                        }
                        return [3 /*break*/, 3];
                    case 2:
                        e_2 = _a.sent();
                        this.clearTaskPolling(mode);
                        this.setActiveCampusTask(mode, null);
                        if (this.data.mode === mode) {
                            this.setData({ errorMsg: (0, campus_content_1.campusFriendlyError)(e_2, '查询任务状态获取失败') });
                        }
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        }); };
        poll();
    },
    handleTaskState: function (task, payload, mode, data) {
        if (data === void 0) { data = {}; }
        if (!task)
            throw new Error('查询任务状态不正确');
        var status = String(task.status || '');
        this.setProgressForTask(task, mode);
        if (isActiveTask(task)) {
            this.setActiveCampusTask(mode, task);
        }
        else {
            this.setActiveCampusTask(mode, null);
            this.clearTaskPolling(mode);
        }
        var rows = this.applyQueryRows(taskRowsSource(task, data), mode);
        if (status === 'cancelled') {
            if (this.data.mode === mode)
                this.setData({ statusMsg: task.message || '查询已停止' });
            return true;
        }
        if (status === 'webvpn_refresh_required') {
            this.clearTaskPolling(mode);
            this.showWebvpnCaptcha(task, payload, mode);
            return true;
        }
        if (status === 'succeeded') {
            if (this.data.mode === mode)
                this.setData({ statusMsg: mode === 'grades' ? '成绩查询完成' : '课表查询完成' });
            return true;
        }
        if (status === 'failed') {
            var message = task.message || '教务系统繁忙，请稍后重试';
            if (this.data.mode === mode)
                this.setData({ statusMsg: message, errorMsg: rows.length ? '' : message });
            return true;
        }
        var suffix = rows.length ? '，当前显示上次成功结果' : '';
        if (this.data.mode === mode)
            this.setData({ statusMsg: "".concat(task.message || '正在后台查询教务系统').concat(suffix) });
        return false;
    },
    restoreRecentCampusTasks: function (recentTasks) {
        var _this = this;
        var pairs = [
            { mode: 'schedule', task: recentTasks === null || recentTasks === void 0 ? void 0 : recentTasks.schedule },
            { mode: 'grades', task: recentTasks === null || recentTasks === void 0 ? void 0 : recentTasks.grades },
        ];
        var restoredCurrent = false;
        pairs.forEach(function (_a) {
            var mode = _a.mode, task = _a.task;
            if (!isActiveTask(task))
                return;
            var payload = { terms: Array.isArray(task.terms) ? task.terms : [] };
            var finished = _this.handleTaskState(task, payload, mode, { task: task });
            if (!finished)
                _this.startTaskPolling(String(task.task_id), mode, payload);
            if (mode === _this.data.mode)
                restoredCurrent = true;
        });
        if (!restoredCurrent)
            this.refreshProgressForMode(this.data.mode);
    },
    confirmReplacingActiveTask: function (mode) {
        var label = mode === 'grades' ? '成绩' : '课表';
        return new Promise(function (resolve) {
            wx.showModal({
                title: '停止上次查询？',
                content: "\u53D1\u8D77\u672C\u6B21\u67E5\u8BE2\u4F1A\u505C\u6B62\u4E0A\u6B21\u7684".concat(label, "\u67E5\u8BE2\uFF0C\u786E\u5B9A\u7EE7\u7EED\u5417\uFF1F"),
                confirmText: '继续',
                cancelText: '取消',
                success: function (res) { return resolve(!!res.confirm); },
                fail: function () { return resolve(false); },
            });
        });
    },
    cancelActiveQueryTask: function (mode) {
        return __awaiter(this, void 0, void 0, function () {
            var task, data, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        task = this.getActiveCampusTask(mode);
                        if (!(task === null || task === void 0 ? void 0 : task.task_id))
                            return [2 /*return*/];
                        this.clearTaskPolling(mode);
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.cancelEduQueryTask(String(task.task_id))];
                    case 2:
                        data = _a.sent();
                        this.handleTaskState((data === null || data === void 0 ? void 0 : data.task) || __assign(__assign({}, task), { status: 'cancelled', message: '查询已停止' }), { terms: task.terms || [] }, mode, data || {});
                        return [3 /*break*/, 5];
                    case 3:
                        e_3 = _a.sent();
                        if (this.data.mode === mode)
                            this.setData({ errorMsg: (0, campus_content_1.campusFriendlyError)(e_3, '停止上次查询失败') });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setActiveCampusTask(mode, null);
                        if (this.data.captchaMode === mode)
                            this.hideWebvpnCaptcha();
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    submitCampusQuery: function (mode, payload) {
        return __awaiter(this, void 0, void 0, function () {
            var data, _a, task, finished, e_4;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.setData({
                            loading: true,
                            errorMsg: '',
                            statusMsg: mode === 'grades' ? '成绩查询已提交，正在连接教务系统...' : '课表查询已提交，正在连接教务系统...',
                        });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, 7, 8]);
                        if (!(mode === 'grades')) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.queryEduGrades(payload)];
                    case 2:
                        _a = _b.sent();
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.queryEduSchedule(payload)];
                    case 4:
                        _a = _b.sent();
                        _b.label = 5;
                    case 5:
                        data = _a;
                        task = data === null || data === void 0 ? void 0 : data.task;
                        if (task === null || task === void 0 ? void 0 : task.task_id) {
                            finished = this.handleTaskState(task, payload, mode, data || {});
                            if (!finished)
                                this.startTaskPolling(String(task.task_id), mode, payload);
                            return [2 /*return*/];
                        }
                        this.applyQueryRows(data || {}, mode, mode === 'grades' ? '成绩查询完成' : '课表查询完成');
                        this.setProgressForTask({ status: 'succeeded', message: '查询完成', terms: payload.terms }, mode);
                        return [3 /*break*/, 8];
                    case 6:
                        e_4 = _b.sent();
                        this.setData({ errorMsg: (0, campus_content_1.campusFriendlyError)(e_4, '查询失败，请稍后重试') });
                        return [3 /*break*/, 8];
                    case 7:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    showWebvpnCaptcha: function (task, payload, mode) {
        var self = ensureRuntimeState(this);
        var challenge = (task === null || task === void 0 ? void 0 : task.challenge) || {};
        self.__pendingCampusCaptcha = { payload: payload, mode: mode };
        this.setData({
            captchaVisible: true,
            captchaMode: mode,
            captchaChallengeId: String(challenge.challenge_id || ''),
            captchaImage: String(challenge.captcha_image || ''),
            captchaCode: '',
            captchaMessage: (task === null || task === void 0 ? void 0 : task.message) || 'WebVPN 登录态失效，请输入验证码后继续查询。',
            captchaSubmitting: false,
        });
    },
    hideWebvpnCaptcha: function () {
        var self = ensureRuntimeState(this);
        self.__pendingCampusCaptcha = null;
        this.setData({
            captchaVisible: false,
            captchaChallengeId: '',
            captchaImage: '',
            captchaCode: '',
            captchaMessage: '',
            captchaSubmitting: false,
        });
    },
    onCaptchaInput: function (e) {
        var _a;
        this.setData({ captchaCode: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '').trim() });
    },
    onCaptchaCancelTap: function () {
        this.hideWebvpnCaptcha();
    },
    onCaptchaSubmitTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var challengeId, captchaCode, self, pending, e_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        challengeId = String(this.data.captchaChallengeId || '').trim();
                        captchaCode = String(this.data.captchaCode || '').trim();
                        if (!challengeId || !captchaCode) {
                            this.setData({ captchaMessage: '请输入验证码' });
                            return [2 /*return*/];
                        }
                        self = ensureRuntimeState(this);
                        pending = self.__pendingCampusCaptcha || { mode: this.data.captchaMode, payload: null };
                        this.setData({ captchaSubmitting: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 5, , 6]);
                        return [4 /*yield*/, api_1.api.completeEduWebvpnSession(challengeId, captchaCode)];
                    case 2:
                        _a.sent();
                        this.setActiveCampusTask(pending.mode, null);
                        this.hideWebvpnCaptcha();
                        if (!pending.payload) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.submitCampusQuery(pending.mode, pending.payload)];
                    case 3:
                        _a.sent();
                        _a.label = 4;
                    case 4: return [3 /*break*/, 6];
                    case 5:
                        e_5 = _a.sent();
                        this.setData({
                            captchaSubmitting: false,
                            captchaMessage: (0, campus_content_1.campusFriendlyError)(e_5, '刷新 WebVPN 登录态失败，请重新输入验证码'),
                        });
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onQueryTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var message, terms, semester, mode, confirmed;
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
                            terms = (0, campus_content_1.buildCampusTerms)(this.data.academicYear, this.data.academicYear, semester);
                        }
                        catch (e) {
                            this.setData({ errorMsg: (e === null || e === void 0 ? void 0 : e.message) || '学年或学期不正确' });
                            return [2 /*return*/];
                        }
                        mode = this.data.mode;
                        if (!isActiveTask(this.getActiveCampusTask(mode))) return [3 /*break*/, 3];
                        return [4 /*yield*/, this.confirmReplacingActiveTask(mode)];
                    case 1:
                        confirmed = _a.sent();
                        if (!confirmed)
                            return [2 /*return*/];
                        return [4 /*yield*/, this.cancelActiveQueryTask(mode)];
                    case 2:
                        _a.sent();
                        _a.label = 3;
                    case 3: return [4 /*yield*/, this.submitCampusQuery(mode, { terms: terms })];
                    case 4:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
});
