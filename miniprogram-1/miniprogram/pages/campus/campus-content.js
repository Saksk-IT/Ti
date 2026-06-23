"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildCampusTerms = buildCampusTerms;
exports.campusFriendlyError = campusFriendlyError;
exports.normalizeScheduleSnapshots = normalizeScheduleSnapshots;
exports.normalizeGradeSnapshots = normalizeGradeSnapshots;
exports.normalizeTermResults = normalizeTermResults;
var DAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
var SECTION_NAMES = ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节', '11-12节'];
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
function normalizeCourse(row) {
    var item = row && typeof row === 'object' ? row : {};
    return {
        course_name: cleanText(item.course_name, '-'),
        teacher: cleanText(item.teacher, ''),
        location: cleanText(item.location, ''),
        weeks: cleanText(item.weeks, ''),
        assessment: cleanText(item.assessment, ''),
        credits: cleanText(item.credits, ''),
        section: cleanText(item.section, ''),
    };
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
        var student = payload.student && typeof payload.student === 'object' ? payload.student : {};
        var weekTable = payload.week_table && typeof payload.week_table === 'object' ? payload.week_table : {};
        var weekRows = DAY_NAMES.map(function (day) {
            var dayTable = weekTable[day] && typeof weekTable[day] === 'object' ? weekTable[day] : {};
            var sections = SECTION_NAMES.map(function (section) { return ({
                section: section,
                courses: normalizeList(dayTable[section]).map(normalizeCourse),
            }); }).filter(function (section) { return section.courses.length > 0; });
            return { day: day, sections: sections };
        }).filter(function (dayRow) { return dayRow.sections.length > 0; });
        return {
            title: cleanText(term.label, '课表'),
            studentText: [student.name, student.class_name, student.major_name].map(function (item) { return cleanText(item); }).filter(Boolean).join(' / '),
            weekRows: weekRows,
            practice_courses: normalizeList(payload.practice_courses).map(normalizeCourse),
        };
    })
        .filter(function (item) { return item.weekRows.length > 0 || item.practice_courses.length > 0 || item.title !== '课表'; });
}
function normalizeGradeSnapshots(rows) {
    return normalizeList(rows)
        .map(function (row) {
        var payload = unwrapPayload(row);
        var term = payload.term && typeof payload.term === 'object' ? payload.term : {};
        var summary = payload.summary && typeof payload.summary === 'object' ? payload.summary : {};
        var courseCount = trimNumberText(summary.course_count);
        var credits = trimNumberText(summary.total_credits);
        var gpa = trimNumberText(summary.gpa);
        return {
            title: cleanText(term.label, '成绩'),
            summaryText: "".concat(courseCount, " \u95E8\u8BFE / ").concat(credits, " \u5B66\u5206 / GPA ").concat(gpa),
            grades: normalizeList(payload.grades).map(normalizeGrade),
        };
    })
        .filter(function (item) { return item.grades.length > 0 || item.title !== '成绩'; });
}
function normalizeTermResults(input, mode) {
    var payload = input && typeof input === 'object' ? input : {};
    var rows = Array.isArray(payload.results) ? payload.results : normalizeList(input);
    return mode === 'grades' ? normalizeGradeSnapshots(rows) : normalizeScheduleSnapshots(rows);
}
