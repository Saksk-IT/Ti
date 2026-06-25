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
Object.defineProperty(exports, "__esModule", { value: true });
exports.campusFriendlyError = campusFriendlyError;
exports.buildCampusTerms = buildCampusTerms;
exports.normalizeScheduleSnapshots = normalizeScheduleSnapshots;
exports.normalizeGradeSnapshots = normalizeGradeSnapshots;
exports.normalizeTermResults = normalizeTermResults;
exports.buildTodayScheduleSummary = buildTodayScheduleSummary;
exports.buildLatestGradeSummary = buildLatestGradeSummary;
exports.buildCampusActions = buildCampusActions;
exports.buildCampusHighlights = buildCampusHighlights;
var DAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
var DATE_DAY_NAMES = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
var SEMESTER_ORDER = { '3': 1, '12': 2, '16': 3 };
function toInteger(value) {
    var num = Number(value);
    return Number.isInteger(num) ? num : NaN;
}
function cleanText(value, fallback) {
    if (fallback === void 0) { fallback = ''; }
    var text = String(value || '').trim();
    return text || fallback;
}
function campusFriendlyError(error, fallback) {
    var source = error && typeof error === 'object' && 'message' in error
        ? error.message
        : error;
    var message = cleanText(source, fallback);
    var lower = message.toLowerCase();
    if (lower.includes('requested url was not found')
        || lower.includes('not found on the server')
        || lower.includes('请求失败: 404')
        || lower === '404') {
        return '教务接口暂不可用，请检查 API 地址或稍后重试';
    }
    return message;
}
function normalizeList(value) {
    return Array.isArray(value) ? value : [];
}
function unwrapPayload(row) {
    if (row && typeof row === 'object' && row.payload && typeof row.payload === 'object') {
        return row.payload;
    }
    return row && typeof row === 'object' ? row : {};
}
function trimNumberText(value) {
    var text = cleanText(value, '0');
    if (!text.includes('.'))
        return text;
    return text.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}
function termYearValue(row) {
    var year = Number((row === null || row === void 0 ? void 0 : row.xnm) || 0);
    return Number.isFinite(year) ? year : 0;
}
function termSemesterRank(row) {
    var xqm = cleanText(row === null || row === void 0 ? void 0 : row.xqm);
    return SEMESTER_ORDER[xqm] || Number(xqm) || 0;
}
function compareTermDesc(a, b) {
    var yearDiff = termYearValue(b) - termYearValue(a);
    if (yearDiff !== 0)
        return yearDiff;
    return termSemesterRank(b) - termSemesterRank(a);
}
function firstMeaningfulRow(rows) {
    var candidates = normalizeList(rows)
        .filter(function (row) { return row && typeof row === 'object'; })
        .slice()
        .sort(compareTermDesc);
    return candidates[0] || null;
}
function courseDetail(course) {
    var teacher = cleanText(course === null || course === void 0 ? void 0 : course.teacher, '-');
    var location = cleanText(course === null || course === void 0 ? void 0 : course.location, '-');
    var weeks = cleanText(course === null || course === void 0 ? void 0 : course.weeks, '-');
    return "".concat(teacher, " / ").concat(location, " / ").concat(weeks);
}
function gradeTermFallback(row) {
    var title = cleanText(row === null || row === void 0 ? void 0 : row.title);
    if (title)
        return title;
    var xnm = cleanText(row === null || row === void 0 ? void 0 : row.xnm);
    var xqm = semesterLabelFromValue(row === null || row === void 0 ? void 0 : row.xqm);
    if (xnm && /^\d+$/.test(xnm))
        return "".concat(xnm, "~").concat(Number(xnm) + 1).concat(xqm ? " ".concat(xqm) : '');
    return xqm || '最近成绩';
}
function semesterLabelFromValue(value) {
    var xqm = cleanText(value);
    if (xqm === '3')
        return '第一学期';
    if (xqm === '12')
        return '第二学期';
    return xqm ? "\u7B2C".concat(xqm, "\u5B66\u671F") : '';
}
function normalizeTermMeta(termInput, fallbackTitle) {
    var term = termInput && typeof termInput === 'object' ? termInput : {};
    var xnm = cleanText(term.xnm || term.XNM);
    var xqm = cleanText(term.xqm || term.XQM);
    var yearLabel = xnm && /^\d+$/.test(xnm) ? "".concat(xnm, "~").concat(Number(xnm) + 1) : cleanText(term.year_label);
    var semesterLabel = cleanText(term.semester_label) || semesterLabelFromValue(xqm);
    var title = cleanText(term.label, [yearLabel, semesterLabel].filter(Boolean).join(' ') || fallbackTitle);
    return {
        xnm: xnm,
        xqm: xqm,
        termKey: [xnm, xqm].filter(Boolean).join('-') || title,
        yearLabel: yearLabel,
        semesterLabel: semesterLabel,
        title: title,
    };
}
function normalizeCourse(row) {
    var item = row && typeof row === 'object' ? row : {};
    var section = cleanText(item.section, '');
    return {
        course_name: cleanText(item.course_name, '-'),
        teacher: cleanText(item.teacher, ''),
        location: cleanText(item.location, ''),
        weeks: cleanText(item.weeks, ''),
        assessment: cleanText(item.assessment, ''),
        credits: cleanText(item.credits, ''),
        section: section,
    };
}
function sectionRank(value) {
    var matched = /^(\d+)/.exec(cleanText(value));
    return matched ? Number(matched[1]) : 999;
}
function collectDaySections(dayTable) {
    var source = dayTable && typeof dayTable === 'object' ? dayTable : {};
    return Object.keys(source)
        .map(function (section) { return cleanText(section); })
        .filter(function (section) { return section && normalizeList(source[section]).length > 0; })
        .sort(function (a, b) {
        var rankDiff = sectionRank(a) - sectionRank(b);
        return rankDiff !== 0 ? rankDiff : a.localeCompare(b, 'zh-Hans-CN');
    });
}
function normalizeGrade(row) {
    var item = row && typeof row === 'object' ? row : {};
    return {
        course_name: cleanText(item.course_name, '-'),
        course_code: cleanText(item.course_code, ''),
        score: cleanText(item.score, '-'),
        credits: cleanText(item.credits, '-'),
        grade_point: cleanText(item.grade_point, '-'),
        credit_grade_point: cleanText(item.credit_grade_point, ''),
        assessment: cleanText(item.assessment, ''),
        exam_type: cleanText(item.exam_type, ''),
        teacher: cleanText(item.teacher, ''),
    };
}
function buildCampusTerms(startYearInput, endYearInput, semesterInput) {
    var startYear = toInteger(startYearInput);
    var endYear = toInteger(endYearInput);
    if (!Number.isInteger(startYear) || !Number.isInteger(endYear)) {
        throw new Error('学年范围不正确');
    }
    if (startYear < 2000 || endYear > 2100 || startYear > endYear) {
        throw new Error('学年范围不正确');
    }
    var semester = String(semesterInput || 'all');
    var xqmValues = semester === 'all' ? ['3', '12'] : [semester];
    if (!xqmValues.every(function (item) { return item === '3' || item === '12'; })) {
        throw new Error('学期参数不正确');
    }
    var terms = [];
    var _loop_1 = function (year) {
        xqmValues.forEach(function (xqm) {
            terms.push({ xnm: String(year), xqm: xqm });
        });
    };
    for (var year = startYear; year <= endYear; year += 1) {
        _loop_1(year);
    }
    if (terms.length > 12) {
        throw new Error('一次最多查询 12 个学期');
    }
    return terms;
}
function normalizeScheduleSnapshots(rows) {
    return normalizeList(rows)
        .map(function (row) {
        var payload = unwrapPayload(row);
        var term = payload.term && typeof payload.term === 'object' ? payload.term : {};
        var termMeta = normalizeTermMeta(term, '课表');
        var student = payload.student && typeof payload.student === 'object' ? payload.student : {};
        var weekTable = payload.week_table && typeof payload.week_table === 'object' ? payload.week_table : {};
        var weekRows = DAY_NAMES.map(function (day) {
            var dayTable = weekTable[day] && typeof weekTable[day] === 'object' ? weekTable[day] : {};
            var sections = collectDaySections(dayTable).map(function (section) { return ({
                section: section,
                courses: normalizeList(dayTable[section]).map(normalizeCourse),
            }); });
            return { day: day, sections: sections };
        }).filter(function (dayRow) { return dayRow.sections.length > 0; });
        return __assign(__assign({}, termMeta), { studentText: [student.name, student.class_name, student.major_name].map(function (item) { return cleanText(item); }).filter(Boolean).join(' / '), weekRows: weekRows, practice_courses: normalizeList(payload.practice_courses).map(normalizeCourse) });
    })
        .filter(function (item) { return item.weekRows.length > 0 || item.practice_courses.length > 0 || item.title !== '课表'; });
}
function normalizeGradeSnapshots(rows) {
    return normalizeList(rows)
        .map(function (row) {
        var payload = unwrapPayload(row);
        var term = payload.term && typeof payload.term === 'object' ? payload.term : {};
        var termMeta = normalizeTermMeta(term, '成绩');
        var summary = payload.summary && typeof payload.summary === 'object' ? payload.summary : {};
        var courseCount = trimNumberText(summary.course_count);
        var credits = trimNumberText(summary.total_credits);
        var gpa = trimNumberText(summary.gpa);
        return __assign(__assign({}, termMeta), { summaryText: "".concat(courseCount, " \u95E8\u8BFE / ").concat(credits, " \u5B66\u5206 / GPA ").concat(gpa), courseCount: courseCount, totalCredits: credits, gpa: gpa, grades: normalizeList(payload.grades).map(normalizeGrade) });
    })
        .filter(function (item) { return item.grades.length > 0 || item.title !== '成绩'; });
}
function normalizeTermResults(input, mode) {
    var payload = input && typeof input === 'object' ? input : {};
    var rows = Array.isArray(payload.results) ? payload.results : normalizeList(input);
    return mode === 'grades' ? normalizeGradeSnapshots(rows) : normalizeScheduleSnapshots(rows);
}
function buildTodayScheduleSummary(rows, dateInput) {
    if (dateInput === void 0) { dateInput = new Date(); }
    var dayLabel = DATE_DAY_NAMES[dateInput.getDay()] || '今天';
    var scheduleRows = normalizeList(rows)
        .filter(function (row) { return row && typeof row === 'object'; })
        .slice()
        .sort(compareTermDesc);
    var mapped = scheduleRows
        .map(function (row) {
        var dayRow = normalizeList(row.weekRows).find(function (item) { return cleanText(item === null || item === void 0 ? void 0 : item.day) === dayLabel; });
        return dayRow ? { row: row, dayRow: dayRow } : null;
    });
    var matched = mapped.find(Boolean) || null;
    var courses = [];
    if (matched) {
        normalizeList(matched.dayRow.sections).forEach(function (sectionRow) {
            normalizeList(sectionRow === null || sectionRow === void 0 ? void 0 : sectionRow.courses).forEach(function (course, index) {
                var section = cleanText(sectionRow === null || sectionRow === void 0 ? void 0 : sectionRow.section, cleanText(course === null || course === void 0 ? void 0 : course.section, '-'));
                var name = cleanText(course === null || course === void 0 ? void 0 : course.course_name, '未命名课程');
                courses.push({
                    key: "".concat(matched.row.termKey || matched.row.title || 'today', "-").concat(section, "-").concat(name, "-").concat(index),
                    section: section,
                    course_name: name,
                    teacher: cleanText(course === null || course === void 0 ? void 0 : course.teacher, ''),
                    location: cleanText(course === null || course === void 0 ? void 0 : course.location, ''),
                    weeks: cleanText(course === null || course === void 0 ? void 0 : course.weeks, ''),
                    detail: courseDetail(course),
                });
            });
        });
    }
    var fallbackRow = (matched === null || matched === void 0 ? void 0 : matched.row) || firstMeaningfulRow(scheduleRows);
    var termTitle = cleanText(fallbackRow === null || fallbackRow === void 0 ? void 0 : fallbackRow.title, '最近课表');
    return {
        title: '今天要上的课',
        subtitle: courses.length ? "".concat(dayLabel, " \u00B7 ").concat(termTitle) : "".concat(dayLabel, " \u00B7 \u6682\u65E0\u5339\u914D\u8BFE\u7A0B"),
        dayLabel: dayLabel,
        termTitle: termTitle,
        emptyText: '最近课表暂无今天课程，刷新课表后会自动展示。',
        courseCount: courses.length,
        hasCourses: courses.length > 0,
        courses: courses.slice(0, 4),
    };
}
function buildLatestGradeSummary(rows) {
    var gradeRows = normalizeList(rows)
        .filter(function (row) { return row && typeof row === 'object'; })
        .slice()
        .sort(compareTermDesc);
    var latest = gradeRows.find(function (row) { return normalizeList(row.grades).length > 0; }) || gradeRows[0] || null;
    if (!latest) {
        return {
            title: '最近一学期成绩',
            subtitle: '暂无成绩快照',
            termTitle: '暂无成绩',
            summaryText: '刷新成绩后展示课程、学分与 GPA',
            emptyText: '还没有成绩记录，点击成绩查询同步最近一学期信息。',
            courseCount: 0,
            totalCredits: '-',
            gpa: '-',
            hasGrades: false,
            grades: [],
        };
    }
    var grades = normalizeList(latest.grades);
    var courseCount = cleanText(latest.courseCount, String(grades.length || 0));
    var totalCredits = cleanText(latest.totalCredits, '-');
    var gpa = cleanText(latest.gpa, '-');
    return {
        title: '最近一学期成绩',
        subtitle: gradeTermFallback(latest),
        termTitle: gradeTermFallback(latest),
        summaryText: cleanText(latest.summaryText, "".concat(courseCount, " \u95E8\u8BFE / ").concat(totalCredits, " \u5B66\u5206 / GPA ").concat(gpa)),
        emptyText: '该学期暂无成绩明细，刷新成绩后会自动补全。',
        courseCount: Number(courseCount) || grades.length,
        totalCredits: totalCredits,
        gpa: gpa,
        hasGrades: grades.length > 0,
        grades: grades.slice(0, 3),
    };
}
function buildCampusActions(eduBound, statusFailed) {
    return [
        {
            key: 'schedule',
            title: '课表查询',
            subtitle: eduBound ? '刷新学期课表' : '绑定后查询课表',
            icon: '/images/icons/book-open.svg',
            tone: 'primary',
            disabled: statusFailed,
        },
        {
            key: 'grades',
            title: '成绩查询',
            subtitle: eduBound ? '同步成绩与 GPA' : '绑定后同步成绩',
            icon: '/images/icons/chart.svg',
            tone: 'normal',
            disabled: statusFailed,
        },
        {
            key: 'binding',
            title: '教务绑定',
            subtitle: eduBound ? '更换或删除账号' : '先绑定教务账号',
            icon: '/images/icons/settings.svg',
            tone: 'normal',
            disabled: false,
        },
        {
            key: 'evaluation',
            title: '一键教评',
            subtitle: '功能建设中',
            icon: '/images/icons/clipboard-check.svg',
            tone: 'muted',
            disabled: true,
        },
        {
            key: 'more',
            title: '更多校园',
            subtitle: '考试安排等后续接入',
            icon: '/images/icons/list.svg',
            tone: 'muted',
            disabled: true,
        },
    ];
}
function buildCampusHighlights(today, latestGrade, eduBound) {
    return [
        {
            key: 'today',
            label: '今日课程',
            value: String(today.courseCount),
            hint: today.hasCourses ? today.dayLabel : '待刷新',
        },
        {
            key: 'grade',
            label: '最新 GPA',
            value: latestGrade.gpa || '-',
            hint: latestGrade.hasGrades ? latestGrade.termTitle : '待同步',
        },
        {
            key: 'binding',
            label: '教务账号',
            value: eduBound ? '已绑定' : '待绑定',
            hint: eduBound ? '可直接查询' : '先完成绑定',
        },
    ];
}
