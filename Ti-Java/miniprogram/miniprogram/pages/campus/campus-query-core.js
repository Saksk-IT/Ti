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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getScheduleStartDateStorageKey = getScheduleStartDateStorageKey;
exports.filterScheduleRowsByWeek = filterScheduleRowsByWeek;
exports.createCampusQueryPage = createCampusQueryPage;
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
var campus_content_1 = require("./campus-content");
var SEMESTER_LABELS = ['第一学期', '第二学期'];
var SEMESTER_VALUES = ['3', '12'];
var ACADEMIC_YEAR_PAST_COUNT = 6;
var ACADEMIC_YEAR_FUTURE_COUNT = 2;
var ACTIVE_TASK_STATUSES = ['pending', 'running', 'retrying', 'webvpn_refresh_required'];
var POLL_INTERVAL_MS = 2000;
var WEEK_COUNT = 25;
var SCHEDULE_VIEW_STORAGE_KEY = 'campus_schedule_view_mode_v1';
var SCHEDULE_START_DATE_STORAGE_PREFIX = 'campus_schedule_start_date_v1';
var SCHEDULE_VIEW_MODES = {
    list: '列表',
    table: '课程表',
};
function defaultAcademicYear() {
    var now = new Date();
    var month = now.getMonth() + 1;
    return month >= 9 ? now.getFullYear() : now.getFullYear() - 1;
}
function defaultSemesterIndex() {
    var month = new Date().getMonth() + 1;
    return month >= 2 && month <= 8 ? 1 : 0;
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
function academicYearIndexForValue(value) {
    var year = String(value || '').trim();
    var index = ACADEMIC_YEAR_OPTIONS.findIndex(function (item) { return item.value === year; });
    return index >= 0 ? index : DEFAULT_ACADEMIC_YEAR_INDEX;
}
function semesterIndexForValue(value) {
    var semester = String(value || '').trim();
    var index = SEMESTER_VALUES.findIndex(function (item) { return item === semester; });
    return index >= 0 ? index : defaultSemesterIndex();
}
function selectedSemesterValue(index) {
    return SEMESTER_VALUES[Math.max(0, Math.min(index, SEMESTER_VALUES.length - 1))] || '3';
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
    var byKey = {};
    (Array.isArray(existing) ? existing : []).forEach(function (row, index) {
        byKey[rowKey(row, index)] = __assign({}, row);
    });
    (Array.isArray(incoming) ? incoming : []).forEach(function (row, index) {
        var key = rowKey(row, index);
        byKey[key] = byKey[key] ? __assign(__assign({}, byKey[key]), row) : __assign({}, row);
    });
    return Object.keys(byKey).map(function (key) { return byKey[key]; }).sort(compareTermRows);
}
function rowTermValue(row) {
    var year = rowYearValue(row);
    var semester = rowSemesterValue(row);
    return year && semester ? "".concat(year, "-").concat(semester) : '';
}
function termLabel(year, semester) {
    return "".concat(formatAcademicYearLabel(Number(year)), " ").concat(xqmLabel(semester));
}
function buildSnapshotTermOptions(rows, selectedTermKey) {
    var counts = {};
    rows.forEach(function (row) {
        var value = rowTermValue(row);
        if (!value)
            return;
        counts[value] = (counts[value] || 0) + 1;
    });
    return Object.keys(counts)
        .sort(function (a, b) {
        var _a = a.split('-'), yearA = _a[0], semesterA = _a[1];
        var _b = b.split('-'), yearB = _b[0], semesterB = _b[1];
        var yearDiff = (Number(yearB) || 0) - (Number(yearA) || 0);
        if (yearDiff !== 0)
            return yearDiff;
        var order = { '12': 2, '3': 1 };
        return (order[semesterB] || Number(semesterB) || 0) - (order[semesterA] || Number(semesterA) || 0);
    })
        .map(function (value) {
        var _a = value.split('-'), year = _a[0], semester = _a[1];
        return {
            value: value,
            label: termLabel(year, semester),
            count: counts[value],
            active: value === selectedTermKey,
        };
    });
}
function buildSnapshotTermLabels(options) {
    return options.map(function (item) { return "".concat(item.label, "\uFF08").concat(item.count, "\uFF09"); });
}
function filterSnapshotRows(rows, selectedTermKey) {
    return rows.filter(function (row) { return rowTermValue(row) === selectedTermKey; });
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
function formatTaskMeta(mode, terms) {
    return formatTaskTerms(terms);
}
function buildSelectedTerm(yearInput, semesterIndexInput) {
    var year = Number(yearInput) || defaultYear;
    var xnm = Number.isInteger(year) && year >= 2000 && year <= 2100 ? year : defaultYear;
    var semester = selectedSemesterValue(Number(semesterIndexInput) || 0);
    return (0, campus_content_1.buildCampusTerms)(String(xnm), String(xnm), semester);
}
function termKeyFromSelection(yearInput, semesterIndexInput) {
    var year = String(yearInput || '').trim();
    var semester = selectedSemesterValue(Number(semesterIndexInput) || 0);
    return year && semester ? "".concat(year, "-").concat(semester) : '';
}
function termLabelFromSelection(yearInput, semesterIndexInput) {
    var year = Number(yearInput) || defaultYear;
    return "".concat(formatAcademicYearLabel(year), " ").concat(xqmLabel(selectedSemesterValue(Number(semesterIndexInput) || 0)));
}
function termSelectionPatchFromKey(termKey) {
    var _a = String(termKey || '').split('-'), year = _a[0], semester = _a[1];
    if (!year || !semester)
        return {};
    var academicYearIndex = academicYearIndexForValue(year);
    var semesterIndex = semesterIndexForValue(semester);
    var academicYear = academicYearValueAt(academicYearIndex);
    return {
        academicYearIndex: academicYearIndex,
        academicYear: academicYear,
        semesterIndex: semesterIndex,
        selectedTermLabel: termLabelFromSelection(academicYear, semesterIndex),
    };
}
function pad2(value) {
    return value < 10 ? "0".concat(value) : String(value);
}
function formatDateValue(date) {
    return "".concat(date.getFullYear(), "-").concat(pad2(date.getMonth() + 1), "-").concat(pad2(date.getDate()));
}
function parseDateValue(value) {
    var text = String(value || '').trim();
    var matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
    if (!matched)
        return new Date(defaultYear, 8, 1);
    var date = new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]));
    return Number.isNaN(date.getTime()) ? new Date(defaultYear, 8, 1) : date;
}
function addDays(date, days) {
    var next = new Date(date.getTime());
    next.setDate(next.getDate() + days);
    return next;
}
function displayDate(date) {
    return "".concat(date.getMonth() + 1, "\u6708").concat(date.getDate(), "\u65E5");
}
function semesterValueFromTermKey(termKey) {
    var parts = String(termKey || '').split('-');
    return parts[1] || selectedSemesterValue(DEFAULT_SEMESTER_INDEX);
}
function yearValueFromTermKey(termKey) {
    var parts = String(termKey || '').split('-');
    return parts[0] || String(defaultYear);
}
function defaultScheduleStartDate(yearInput, semesterInput) {
    if (semesterInput === void 0) { semesterInput = '3'; }
    var year = Number(yearInput) || defaultYear;
    var semester = String(semesterInput || '3').trim();
    if (semester === '12')
        return formatDateValue(new Date(year + 1, 2, 1));
    return formatDateValue(new Date(year, 8, 1));
}
function getScheduleStartDateStorageKey(yearInput, semesterInput) {
    var year = String(yearInput || '').trim() || String(defaultYear);
    var semester = String(semesterInput || '').trim() || '3';
    return "".concat(SCHEDULE_START_DATE_STORAGE_PREFIX, "_").concat(year, "_").concat(semester);
}
function readStoredScheduleStartDate(yearInput, semesterInput) {
    try {
        var stored = String(wx.getStorageSync(getScheduleStartDateStorageKey(yearInput, semesterInput)) || '').trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(stored))
            return stored;
    }
    catch (e) { }
    return defaultScheduleStartDate(yearInput, semesterInput);
}
function scheduleStartPatchForTerm(yearInput, semesterInput, weekInput) {
    var weekStartDate = readStoredScheduleStartDate(yearInput, semesterInput);
    return {
        weekStartDate: weekStartDate,
        selectedWeekDateRange: weekDateRangeText(weekStartDate, weekInput),
    };
}
function readStoredScheduleViewMode() {
    try {
        var mode = String(wx.getStorageSync(SCHEDULE_VIEW_STORAGE_KEY) || '').trim();
        if (mode === 'table')
            return 'table';
    }
    catch (e) { }
    return 'list';
}
function buildWeekLabels() {
    var labels = [];
    for (var week = 1; week <= WEEK_COUNT; week += 1)
        labels.push("\u7B2C ".concat(week, " \u5468"));
    return labels;
}
function weekDateRangeText(startDateValue, weekInput) {
    var week = Math.max(1, Math.min(Number(weekInput) || 1, WEEK_COUNT));
    var start = addDays(parseDateValue(startDateValue), (week - 1) * 7);
    var end = addDays(start, 6);
    return "".concat(displayDate(start), " - ").concat(displayDate(end));
}
function parseCourseWeeks(value) {
    var text = String(value || '').trim();
    if (!text)
        return [];
    var normalized = text
        .replace(/[，、]/g, ',')
        .replace(/第/g, '')
        .replace(/周/g, '');
    var oddEven = /单/.test(text) ? 'odd' : (/双/.test(text) ? 'even' : '');
    var ranges = [];
    normalized.split(',').forEach(function (part) {
        var matched = /(\d+)(?:\s*[-~至]\s*(\d+))?/.exec(part);
        if (!matched)
            return;
        var start = Number(matched[1]);
        var end = Number(matched[2] || matched[1]);
        if (!Number.isFinite(start) || !Number.isFinite(end))
            return;
        ranges.push({ start: Math.min(start, end), end: Math.max(start, end), oddEven: oddEven });
    });
    return ranges;
}
function courseMatchesWeek(course, weekInput) {
    var week = Math.max(1, Math.min(Number(weekInput) || 1, WEEK_COUNT));
    var ranges = parseCourseWeeks(course === null || course === void 0 ? void 0 : course.weeks);
    if (!ranges.length)
        return true;
    return ranges.some(function (range) {
        if (week < range.start || week > range.end)
            return false;
        if (range.oddEven === 'odd')
            return week % 2 === 1;
        if (range.oddEven === 'even')
            return week % 2 === 0;
        return true;
    });
}
function markCourseWeekStatus(course, weekInput) {
    var isCurrentWeek = courseMatchesWeek(course, weekInput);
    return __assign(__assign({}, (course || {})), { isCurrentWeek: isCurrentWeek, inactiveWeek: !isCurrentWeek });
}
function filterScheduleRowsByWeek(rows, weekInput) {
    return (Array.isArray(rows) ? rows : []).map(function (term) {
        var weekRows = (Array.isArray(term.weekRows) ? term.weekRows : []).map(function (dayRow) { return (__assign(__assign({}, dayRow), { sections: (Array.isArray(dayRow.sections) ? dayRow.sections : []).map(function (sectionRow) { return (__assign(__assign({}, sectionRow), { courses: (Array.isArray(sectionRow.courses) ? sectionRow.courses : []).map(function (course) { return markCourseWeekStatus(course, weekInput); }) })); }).filter(function (sectionRow) { return Array.isArray(sectionRow.courses) && sectionRow.courses.length; }) })); }).filter(function (dayRow) { return Array.isArray(dayRow.sections) && dayRow.sections.length; });
        var practiceCourses = Array.isArray(term.practice_courses) ? term.practice_courses.slice() : [];
        return __assign(__assign({}, term), { weekRows: weekRows, practice_courses: practiceCourses });
    }).filter(function (term) { return (term.weekRows || []).length || (term.practice_courses || []).length; });
}
function buildScheduleTable(rows, weekInput) {
    var firstTerm = (Array.isArray(rows) ? rows : [])[0] || {};
    var days = (Array.isArray(firstTerm.weekRows) ? firstTerm.weekRows : []).map(function (dayRow) { return String(dayRow.day || '').trim(); }).filter(Boolean);
    var sectionMap = {};
    (firstTerm.weekRows || []).forEach(function (dayRow) {
        var day = String(dayRow.day || '').trim();
        (dayRow.sections || []).forEach(function (sectionRow) {
            var _a;
            var section = String(sectionRow.section || '').trim();
            if (!section)
                return;
            var current = sectionMap[section] || { section: section, dayCourses: {} };
            sectionMap[section] = {
                section: section,
                dayCourses: __assign(__assign({}, current.dayCourses), (_a = {}, _a[day] = (Array.isArray(sectionRow.courses) ? sectionRow.courses : []).map(function (course) { return markCourseWeekStatus(course, weekInput); }), _a)),
            };
        });
    });
    var tableRows = Object.keys(sectionMap).map(function (section) { return ({
        key: section,
        section: section,
        cells: days.map(function (day) {
            var courses = sectionMap[section].dayCourses[day] || [];
            return {
                key: "".concat(section, "-").concat(day),
                day: day,
                courses: courses,
                hasCourses: courses.length > 0,
                hasCurrentWeek: courses.some(function (course) { return (course === null || course === void 0 ? void 0 : course.isCurrentWeek) !== false; }),
            };
        }),
    }); });
    return { days: days, tableRows: tableRows };
}
function taskRowsSource(task, data) {
    var credential = (data === null || data === void 0 ? void 0 : data.credential) || (task === null || task === void 0 ? void 0 : task.credential) || {};
    var gradeMetadata = __assign(__assign({}, (Object.prototype.hasOwnProperty.call(data || {}, 'grade_overview')
        ? { grade_overview: data.grade_overview }
        : Object.prototype.hasOwnProperty.call(task || {}, 'grade_overview')
            ? { grade_overview: task.grade_overview }
            : {})), (Object.prototype.hasOwnProperty.call(data || {}, 'academic_year_averages')
        ? { academic_year_averages: data.academic_year_averages }
        : Object.prototype.hasOwnProperty.call(task || {}, 'academic_year_averages')
            ? { academic_year_averages: task.academic_year_averages }
            : {}));
    if (Array.isArray(task === null || task === void 0 ? void 0 : task.results) && task.results.length)
        return __assign({ results: task.results, credential: credential }, gradeMetadata);
    if (Array.isArray(task === null || task === void 0 ? void 0 : task.snapshots) && task.snapshots.length)
        return __assign({ results: task.snapshots, credential: credential }, gradeMetadata);
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
var DEFAULT_SEMESTER_INDEX = defaultSemesterIndex();
var WEEK_LABELS = buildWeekLabels();
function createCampusQueryPage(config) {
    var fixedMode = config.mode;
    var fixedPageTitle = config.pageTitle;
    var defaultAcademicYearValue = academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX);
    var defaultTermLabel = termLabelFromSelection(defaultAcademicYearValue, DEFAULT_SEMESTER_INDEX);
    return {
        data: {
            mode: fixedMode,
            queryPageKind: fixedMode,
            academicYearLabels: ACADEMIC_YEAR_OPTIONS.map(function (item) { return item.label; }),
            academicYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
            semesterLabels: SEMESTER_LABELS,
            semesterIndex: DEFAULT_SEMESTER_INDEX,
            academicYear: defaultAcademicYearValue,
            selectedTermLabel: defaultTermLabel,
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
            gradeOverview: null,
            academicYearAverages: [],
            gradeMetrics: (0, campus_content_1.buildGradeMetrics)([], null, []),
            scheduleResults: [],
            gradeResults: [],
            visibleScheduleResults: [],
            scheduleViewMode: 'list',
            scheduleViewModeLabel: SCHEDULE_VIEW_MODES.list,
            scheduleTableDays: [],
            scheduleTableRows: [],
            scheduleTermSheetVisible: false,
            scheduleTermSheetMode: 'switch',
            weekLabels: WEEK_LABELS,
            selectedWeekIndex: 0,
            selectedWeek: 1,
            weekStartDate: defaultScheduleStartDate(defaultAcademicYearValue, selectedSemesterValue(DEFAULT_SEMESTER_INDEX)),
            selectedWeekDateRange: weekDateRangeText(defaultScheduleStartDate(defaultAcademicYearValue, selectedSemesterValue(DEFAULT_SEMESTER_INDEX)), 1),
            isQueryPage: true,
            pageTitle: fixedPageTitle,
            snapshotTerms: [],
            snapshotTermLabels: [],
            snapshotTermIndex: 0,
            snapshotSelectedTermKey: '',
            snapshotDrawerOpen: false,
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
        onLoad: function () {
            var _this = this;
            var weekStartDate = fixedMode === 'schedule'
                ? readStoredScheduleStartDate(this.data.academicYear, selectedSemesterValue(this.data.semesterIndex))
                : this.data.weekStartDate;
            var scheduleViewMode = fixedMode === 'schedule' ? readStoredScheduleViewMode() : 'list';
            this.setData({
                mode: fixedMode,
                queryPageKind: fixedMode,
                pageTitle: fixedPageTitle,
                scheduleViewMode: scheduleViewMode,
                scheduleViewModeLabel: SCHEDULE_VIEW_MODES[scheduleViewMode],
                weekStartDate: weekStartDate,
                selectedWeekDateRange: weekDateRangeText(weekStartDate, this.data.selectedWeek),
            }, function () { return _this.rebuildScheduleDisplay(); });
        },
        onShow: function () {
            if (!(0, auth_1.checkLogin)()) {
                wx.redirectTo({ url: '/pages/login/login' });
                return;
            }
            try {
                this.setData(__assign({}, theme_1.themeManager.getPageData()));
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
        onAcademicYearChange: function (e) {
            var _a;
            var academicYearIndex = clampAcademicYearIndex((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, this.data.academicYearIndex);
            var academicYear = academicYearValueAt(academicYearIndex);
            this.setData(__assign({ academicYearIndex: academicYearIndex, academicYear: academicYear, selectedTermLabel: termLabelFromSelection(academicYear, this.data.semesterIndex) }, (fixedMode === 'schedule' ? scheduleStartPatchForTerm(academicYear, selectedSemesterValue(this.data.semesterIndex), this.data.selectedWeek) : {})));
        },
        onSemesterChange: function (e) {
            var _a, _b;
            var value = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : 0);
            var max = SEMESTER_LABELS.length - 1;
            var semesterIndex = Math.max(0, Math.min(value, max));
            this.setData(__assign({ semesterIndex: semesterIndex, selectedTermLabel: termLabelFromSelection(this.data.academicYear, semesterIndex) }, (fixedMode === 'schedule' ? scheduleStartPatchForTerm(this.data.academicYear, selectedSemesterValue(semesterIndex), this.data.selectedWeek) : {})));
        },
        onGoEduBindingTap: function () {
            (0, nav_1.safeNavigate)('/pages/settings-account-bindings-v2/settings-account-bindings-v2', 'navigateTo');
        },
        applyEduStatus: function (data) {
            var _this = this;
            var credential = normalizeCredential(data === null || data === void 0 ? void 0 : data.credential);
            var allScheduleResults = (0, campus_content_1.normalizeScheduleSnapshots)((data === null || data === void 0 ? void 0 : data.snapshots) || []);
            var allGradeResults = (0, campus_content_1.normalizeGradeSnapshots)((data === null || data === void 0 ? void 0 : data.grade_snapshots) || []);
            this.setData({
                statusReady: true,
                statusFailed: false,
                eduBound: credential.has_credentials,
                eduUsernameHint: credential.username_hint,
                statusMsg: credential.has_credentials ? "\u5DF2\u7ED1\u5B9A\u6559\u52A1\u7CFB\u7EDF\u8D26\u53F7\uFF1A".concat(credential.username_hint || '已保存') : '未绑定教务系统账号',
                allScheduleResults: allScheduleResults,
                allGradeResults: allGradeResults,
                gradeOverview: (data === null || data === void 0 ? void 0 : data.grade_overview) || null,
                academicYearAverages: Array.isArray(data === null || data === void 0 ? void 0 : data.academic_year_averages) ? data.academic_year_averages : [],
            }, function () {
                _this.syncSnapshotBrowserForMode(fixedMode);
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
            var mode = modeInput || fixedMode;
            var rows = mode === 'grades' ? this.data.allGradeResults : this.data.allScheduleResults;
            var terms = buildSnapshotTermOptions(rows, this.data.snapshotSelectedTermKey);
            var selectedTermKey = terms.some(function (item) { return item.value === _this.data.snapshotSelectedTermKey; })
                ? this.data.snapshotSelectedTermKey
                : (((_a = terms[0]) === null || _a === void 0 ? void 0 : _a.value) || '');
            var selectedTerms = buildSnapshotTermOptions(rows, selectedTermKey);
            var selectedTermIndex = Math.max(0, selectedTerms.findIndex(function (item) { return item.value === selectedTermKey; }));
            var patch = {
                snapshotSelectedTermKey: selectedTermKey,
                snapshotTerms: selectedTerms,
                snapshotTermLabels: buildSnapshotTermLabels(selectedTerms),
                snapshotTermIndex: selectedTermIndex,
                snapshotDrawerOpen: false,
            };
            var selectedRows = selectedTermKey
                ? filterSnapshotRows(rows, selectedTermKey)
                : [];
            patch[mode === 'grades' ? 'gradeResults' : 'scheduleResults'] = selectedRows;
            if (mode === 'grades') {
                patch.gradeMetrics = (0, campus_content_1.buildGradeMetrics)(selectedRows, this.data.gradeOverview, this.data.academicYearAverages);
            }
            this.setData(__assign(__assign({}, patch), (selectedTermKey ? __assign(__assign({}, termSelectionPatchFromKey(selectedTermKey)), scheduleStartPatchForTerm(yearValueFromTermKey(selectedTermKey), semesterValueFromTermKey(selectedTermKey), this.data.selectedWeek)) : {})), function () {
                if (mode === 'schedule')
                    _this.rebuildScheduleDisplay();
            });
        },
        onSnapshotTermTap: function (e) {
            var _this = this;
            var _a, _b, _c;
            var options = this.data.snapshotTerms || [];
            var value = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.value) || '').trim();
            var index = options.findIndex(function (item) { return item.value === value; });
            var selectedTermKey = String(((_c = options[index]) === null || _c === void 0 ? void 0 : _c.value) || '').trim();
            if (!selectedTermKey)
                return;
            this.setData(__assign(__assign({ snapshotSelectedTermKey: selectedTermKey, snapshotTermIndex: index, snapshotDrawerOpen: false }, termSelectionPatchFromKey(selectedTermKey)), scheduleStartPatchForTerm(yearValueFromTermKey(selectedTermKey), semesterValueFromTermKey(selectedTermKey), this.data.selectedWeek)), function () { return _this.syncSnapshotBrowserForMode(fixedMode); });
        },
        rebuildScheduleDisplay: function () {
            if (fixedMode !== 'schedule')
                return;
            var selectedWeek = Math.max(1, Math.min(Number(this.data.selectedWeek) || 1, WEEK_COUNT));
            var visibleScheduleResults = filterScheduleRowsByWeek(this.data.scheduleResults || [], selectedWeek);
            var table = buildScheduleTable(this.data.scheduleResults || [], selectedWeek);
            this.setData({
                visibleScheduleResults: visibleScheduleResults,
                scheduleTableDays: table.days,
                scheduleTableRows: table.tableRows,
                selectedWeek: selectedWeek,
                selectedWeekDateRange: weekDateRangeText(this.data.weekStartDate, selectedWeek),
            });
        },
        onScheduleViewToggleTap: function () {
            var _this = this;
            if (fixedMode !== 'schedule')
                return;
            var scheduleViewMode = this.data.scheduleViewMode === 'table' ? 'list' : 'table';
            try {
                wx.setStorageSync(SCHEDULE_VIEW_STORAGE_KEY, scheduleViewMode);
            }
            catch (e) { }
            this.setData({
                scheduleViewMode: scheduleViewMode,
                scheduleViewModeLabel: SCHEDULE_VIEW_MODES[scheduleViewMode],
            }, function () { return _this.rebuildScheduleDisplay(); });
        },
        onWeekChange: function (e) {
            var _this = this;
            var _a, _b;
            var value = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : 0);
            var selectedWeekIndex = Math.max(0, Math.min(value, WEEK_COUNT - 1));
            var selectedWeek = selectedWeekIndex + 1;
            this.setData({
                selectedWeekIndex: selectedWeekIndex,
                selectedWeek: selectedWeek,
                selectedWeekDateRange: weekDateRangeText(this.data.weekStartDate, selectedWeek),
            }, function () { return _this.rebuildScheduleDisplay(); });
        },
        onWeekStartDateChange: function (e) {
            var _this = this;
            var _a;
            var semester = selectedSemesterValue(this.data.semesterIndex);
            var weekStartDate = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '').trim() || defaultScheduleStartDate(this.data.academicYear, semester);
            try {
                wx.setStorageSync(getScheduleStartDateStorageKey(this.data.academicYear, semester), weekStartDate);
            }
            catch (err) { }
            this.setData({
                weekStartDate: weekStartDate,
                selectedWeekDateRange: weekDateRangeText(weekStartDate, this.data.selectedWeek),
            }, function () { return _this.rebuildScheduleDisplay(); });
        },
        onOpenScheduleTermSheetTap: function () {
            if (fixedMode !== 'schedule')
                return;
            this.setData({ scheduleTermSheetVisible: true, scheduleTermSheetMode: 'switch' });
        },
        onOpenScheduleQuerySheetTap: function () {
            if (fixedMode !== 'schedule')
                return;
            this.setData({ scheduleTermSheetVisible: true, scheduleTermSheetMode: 'query' });
        },
        onCloseScheduleTermSheetTap: function () {
            this.setData({ scheduleTermSheetVisible: false });
        },
        onScheduleTermSheetConfirmTap: function () {
            var _this = this;
            if (this.data.scheduleTermSheetMode === 'query') {
                this.setData({ scheduleTermSheetVisible: false }, function () { return _this.executeCampusQuery(); });
                return;
            }
            var selectedTermKey = termKeyFromSelection(this.data.academicYear, this.data.semesterIndex);
            var options = this.data.snapshotTerms || [];
            var index = options.findIndex(function (item) { return item.value === selectedTermKey; });
            if (index < 0) {
                wx.showToast({ title: '暂无该学期课表记录', icon: 'none' });
                this.setData({ scheduleTermSheetVisible: false });
                return;
            }
            this.setData({
                scheduleTermSheetVisible: false,
                snapshotSelectedTermKey: selectedTermKey,
                snapshotTermIndex: index,
            }, function () { return _this.syncSnapshotBrowserForMode('schedule'); });
        },
        applyQueryRows: function (data, mode, statusMsg) {
            var _this = this;
            if (statusMsg === void 0) { statusMsg = ''; }
            var rows = (0, campus_content_1.normalizeTermResults)(data || {}, mode);
            var sourceKey = mode === 'grades' ? 'allGradeResults' : 'allScheduleResults';
            var patch = {};
            var mergedRows = mergeCampusRows(this.data[sourceKey] || [], rows);
            var credential = (data === null || data === void 0 ? void 0 : data.credential) ? normalizeCredential(data.credential) : null;
            patch[sourceKey] = mergedRows;
            if (mode === 'grades' && Object.prototype.hasOwnProperty.call(data || {}, 'grade_overview')) {
                patch.gradeOverview = data.grade_overview || null;
            }
            if (mode === 'grades' && Object.prototype.hasOwnProperty.call(data || {}, 'academic_year_averages')) {
                patch.academicYearAverages = Array.isArray(data.academic_year_averages) ? data.academic_year_averages : [];
            }
            if (statusMsg)
                patch.statusMsg = statusMsg;
            if (credential) {
                patch.eduBound = credential.has_credentials;
                patch.eduUsernameHint = credential.username_hint;
            }
            this.setData(patch, function () {
                if (fixedMode === mode)
                    _this.syncSnapshotBrowserForMode(mode);
            });
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
                queryProgressDetail: String((task === null || task === void 0 ? void 0 : task.message) || (mode === 'grades' ? '正在刷新全部成绩' : '正在后台查询课表')),
                queryProgressMeta: formatTaskMeta(mode, Array.isArray(task === null || task === void 0 ? void 0 : task.terms) ? task.terms : []),
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
                    this.setData({ statusMsg: mode === 'grades' ? '全部成绩已同步' : '课表查询完成' });
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
            var task = recentTasks === null || recentTasks === void 0 ? void 0 : recentTasks[fixedMode];
            if (isActiveTask(task)) {
                var payload = { terms: Array.isArray(task.terms) ? task.terms : [] };
                var finished = this.handleTaskState(task, payload, fixedMode, { task: task });
                if (!finished)
                    this.startTaskPolling(String(task.task_id), fixedMode, payload);
                return;
            }
            this.refreshProgressForMode(fixedMode);
        },
        confirmReplacingActiveTask: function (mode) {
            var label = mode === 'grades' ? '成绩' : '课表';
            return new Promise(function (resolve) {
                wx.showModal({
                    title: '停止上次查询？',
                    content: mode === 'grades'
                        ? '发起本次刷新会停止上次的成绩刷新，确定继续吗？'
                        : "\u53D1\u8D77\u672C\u6B21\u67E5\u8BE2\u4F1A\u505C\u6B62\u4E0A\u6B21\u7684".concat(label, "\u67E5\u8BE2\uFF0C\u786E\u5B9A\u7EE7\u7EED\u5417\uFF1F"),
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
                                statusMsg: mode === 'grades' ? '全部成绩刷新已提交，正在连接教务系统...' : '课表查询已提交，正在连接教务系统...',
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
                            this.applyQueryRows(data || {}, mode, mode === 'grades' ? '全部成绩已同步' : '课表查询完成');
                            this.setProgressForTask({ status: 'succeeded', message: mode === 'grades' ? '全部成绩已同步' : '查询完成', terms: payload.terms }, mode);
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
        executeCampusQuery: function () {
            return __awaiter(this, void 0, void 0, function () {
                var message, mode, terms, confirmed;
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
                            mode = fixedMode;
                            try {
                                terms = buildSelectedTerm(this.data.academicYear, this.data.semesterIndex);
                            }
                            catch (e) {
                                this.setData({ errorMsg: (e === null || e === void 0 ? void 0 : e.message) || '学年或学期不正确' });
                                return [2 /*return*/];
                            }
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
        onQueryTap: function () {
            return __awaiter(this, void 0, void 0, function () {
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (fixedMode === 'schedule') {
                                this.onOpenScheduleQuerySheetTap();
                                return [2 /*return*/];
                            }
                            return [4 /*yield*/, this.executeCampusQuery()];
                        case 1:
                            _a.sent();
                            return [2 /*return*/];
                    }
                });
            });
        },
    };
}
