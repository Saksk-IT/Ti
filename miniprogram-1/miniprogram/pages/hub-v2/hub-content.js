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
exports.normalizeHubStats = normalizeHubStats;
exports.buildCampusSummary = buildCampusSummary;
exports.buildStudyAdvice = buildStudyAdvice;
exports.buildRecentBanks = buildRecentBanks;
exports.buildWeaknessEmptyActions = buildWeaknessEmptyActions;
var DEFAULT_RECENT_LIMIT = 3;
var DEFAULT_ADVICE_LIMIT = 3;
var SEMESTER_ORDER = { '3': 1, '12': 2, '16': 3 };
function toNumber(value) {
    var num = Number(value || 0);
    return Number.isFinite(num) ? num : 0;
}
function cleanText(value, fallback) {
    var text = String(value || '').trim();
    return text || fallback;
}
function countRows(value) {
    return Array.isArray(value) ? value.length : 0;
}
function asRecord(value) {
    return value && typeof value === 'object' ? value : {};
}
function semesterLabel(xqm) {
    var value = String(xqm || '').trim();
    if (value === '3')
        return '第一学期';
    if (value === '12')
        return '第二学期';
    if (value === '16')
        return '第三学期';
    return value ? "\u7B2C".concat(value, "\u5B66\u671F") : '';
}
function gradePayload(row) {
    var payload = asRecord(row.payload);
    return Object.keys(payload).length > 0 ? payload : row;
}
function gradeYear(row) {
    var payload = gradePayload(row);
    var term = asRecord(payload.term);
    return toNumber(row.xnm || term.xnm);
}
function gradeSemesterRank(row) {
    var payload = gradePayload(row);
    var term = asRecord(payload.term);
    var xqm = String(row.xqm || term.xqm || '').trim();
    return SEMESTER_ORDER[xqm] || toNumber(xqm);
}
function compareGradeSnapshot(a, b) {
    var yearDiff = gradeYear(a) - gradeYear(b);
    if (yearDiff !== 0)
        return yearDiff;
    var semesterDiff = gradeSemesterRank(a) - gradeSemesterRank(b);
    if (semesterDiff !== 0)
        return semesterDiff;
    var fetchedA = Date.parse(String(a.fetched_at || '')) || 0;
    var fetchedB = Date.parse(String(b.fetched_at || '')) || 0;
    return fetchedA - fetchedB;
}
function gradeTermLabel(row, payload) {
    var term = asRecord(payload.term);
    var existingLabel = cleanText(row.term_label || term.label, '');
    if (existingLabel)
        return existingLabel;
    var year = cleanText(row.xnm || term.xnm, '');
    var semester = semesterLabel(row.xqm || term.xqm);
    if (!year)
        return semester || '最新成绩';
    var yearEnd = toNumber(year) ? String(toNumber(year) + 1) : '';
    return "".concat(year).concat(yearEnd ? "-".concat(yearEnd) : '').concat(semester ? " ".concat(semester) : '');
}
function numberText(value) {
    return String(value !== null && value !== void 0 ? value : '').trim();
}
function hasGradeSummaryData(row) {
    var payload = gradePayload(row);
    var summary = asRecord(payload.summary);
    var hasSummaryValue = Object.prototype.hasOwnProperty.call(summary, 'course_count') ||
        Object.prototype.hasOwnProperty.call(summary, 'gpa');
    var grades = Array.isArray(payload.grades) ? payload.grades : [];
    return hasSummaryValue || grades.length > 0;
}
function buildLatestGradeSummary(rows) {
    var gradeRows = Array.isArray(rows) ? rows.map(asRecord).filter(hasGradeSummaryData) : [];
    if (!gradeRows.length) {
        return {
            hasGradeSummary: false,
            latestGradeTerm: '',
            latestGradeCourseCount: 0,
            latestGradeGpa: '',
        };
    }
    var latest = gradeRows.reduce(function (best, row) { return (compareGradeSnapshot(row, best) > 0 ? row : best); });
    var payload = gradePayload(latest);
    var summary = asRecord(payload.summary);
    var grades = Array.isArray(payload.grades) ? payload.grades : [];
    var summaryCourseCount = toNumber(summary.course_count);
    return {
        hasGradeSummary: true,
        latestGradeTerm: gradeTermLabel(latest, payload),
        latestGradeCourseCount: summaryCourseCount || grades.length,
        latestGradeGpa: numberText(summary.gpa) || '--',
    };
}
function normalizeHubStats(payload) {
    var data = payload && typeof payload === 'object' ? payload : {};
    var allSummary = data.all_summary && typeof data.all_summary === 'object' ? data.all_summary : null;
    return {
        answered: toNumber(allSummary ? allSummary.answered : (data.answered_count || data.answered)),
        accuracy: toNumber(allSummary ? allSummary.accuracy : data.accuracy),
        favorites: toNumber(allSummary ? allSummary.favorites : (data.favorites_count || data.favorites)),
        mistakes: toNumber(allSummary ? allSummary.mistakes : (data.mistakes_count || data.mistakes)),
    };
}
function buildCampusSummary(payload, isLoggedIn) {
    var data = payload && typeof payload === 'object' ? payload : {};
    var scheduleCount = countRows(data.snapshots);
    var gradeCount = countRows(data.grade_snapshots);
    var latestGrade = buildLatestGradeSummary(data.grade_snapshots);
    if (!isLoggedIn) {
        return {
            title: '校园服务',
            subtitle: '登录后绑定教务系统账号，查询课表和成绩',
            statusLabel: '登录后使用',
            statusTone: 'muted',
            scheduleCount: 0,
            gradeCount: 0,
            hasGradeSummary: false,
            latestGradeTerm: '',
            latestGradeCourseCount: 0,
            latestGradeGpa: '',
            primaryAction: '去登录',
            secondaryAction: '进校园'
        };
    }
    if (data.error) {
        return __assign(__assign({ title: '校园服务', subtitle: '校园状态暂时无法同步，仍可进入校园页查看', statusLabel: '同步失败', statusTone: 'warn', scheduleCount: scheduleCount, gradeCount: gradeCount }, latestGrade), { primaryAction: '进入校园', secondaryAction: '稍后重试' });
    }
    var credential = data.credential && typeof data.credential === 'object'
        ? data.credential
        : {};
    var hasCredentials = !!credential.has_credentials;
    var usernameHint = cleanText(credential.username_hint, '已保存');
    if (hasCredentials) {
        return __assign(__assign({ title: '校园服务', subtitle: "\u5DF2\u7ED1\u5B9A ".concat(usernameHint, "\uFF0C\u53EF\u76F4\u63A5\u67E5\u8BE2\u8BFE\u8868\u548C\u6210\u7EE9"), statusLabel: '已绑定', statusTone: 'ok', scheduleCount: scheduleCount, gradeCount: gradeCount }, latestGrade), { primaryAction: '查课表', secondaryAction: '查成绩' });
    }
    return __assign(__assign({ title: '校园服务', subtitle: '绑定教务系统账号后，可在校园页查询课表和成绩', statusLabel: '待绑定', statusTone: 'warn', scheduleCount: scheduleCount, gradeCount: gradeCount }, latestGrade), { primaryAction: '去绑定', secondaryAction: '进校园' });
}
function buildStudyAdvice(stats, weakness, lastPractice, isLoggedIn) {
    var safeStats = stats || {};
    var safeWeakness = Array.isArray(weakness) ? weakness : [];
    var safeLastPractice = lastPractice || {};
    var advice = [];
    if (!isLoggedIn) {
        advice.push({
            key: 'login',
            title: '登录同步学习进度',
            subtitle: '收藏、错题和练习记录会自动保存',
            action: '去登录',
            target: 'login',
            icon: 'user'
        });
    }
    else if (safeLastPractice.has_practice) {
        advice.push({
            key: 'continue',
            title: '继续上次练习',
            subtitle: cleanText(safeLastPractice.subject_name || safeLastPractice.display_name, '回到上次题库'),
            action: '继续',
            target: 'continue',
            icon: 'play'
        });
    }
    if (isLoggedIn && safeWeakness.length > 0) {
        var firstWeakness = safeWeakness[0] || {};
        advice.push({
            key: 'weakness',
            title: '优先巩固薄弱环节',
            subtitle: cleanText(firstWeakness.subject, '从正确率较低的题型开始'),
            action: '强化',
            target: 'weakness',
            icon: 'alert'
        });
    }
    if (isLoggedIn && toNumber(safeStats.mistakes) > 0) {
        advice.push({
            key: 'mistakes',
            title: '复盘错题',
            subtitle: "\u5F53\u524D\u9519\u9898 ".concat(toNumber(safeStats.mistakes), " \u9053"),
            action: '去复盘',
            target: 'review',
            icon: 'mistake'
        });
    }
    if (isLoggedIn && advice.length < DEFAULT_ADVICE_LIMIT && toNumber(safeStats.favorites) > 0) {
        advice.push({
            key: 'favorites',
            title: '回看收藏题',
            subtitle: "\u6536\u85CF\u9898 ".concat(toNumber(safeStats.favorites), " \u9053\uFF0C\u9002\u5408\u8003\u524D\u5FEB\u901F\u8FC7\u4E00\u904D"),
            action: '查看',
            target: 'favorites',
            icon: 'favorite'
        });
    }
    if (isLoggedIn && advice.length === 0) {
        advice.push({
            key: 'start',
            title: '开始一次练习',
            subtitle: '从题库广场选择一个题库进入练习',
            action: '去选题库',
            target: 'publicBank',
            icon: 'book'
        });
    }
    return advice.slice(0, DEFAULT_ADVICE_LIMIT);
}
function buildRecentBanks(lastPractice, storageRows) {
    var rows = [];
    var safeLastPractice = lastPractice || {};
    var rawRows = Array.isArray(storageRows) ? storageRows : [];
    if (safeLastPractice.has_practice) {
        rows.push({
            key: "last-".concat(cleanText(safeLastPractice.source_type, 'practice'), "-").concat(cleanText(safeLastPractice.source_id || safeLastPractice.subject_id, 'latest')),
            title: cleanText(safeLastPractice.subject_name || safeLastPractice.display_name, '上次练习'),
            meta: cleanText(safeLastPractice.last_at_display, '最近练习'),
            source_type: safeLastPractice.source_type || '',
            source_id: safeLastPractice.source_id || safeLastPractice.subject_id || '',
            target: 'continue',
            mode: safeLastPractice.mode || ''
        });
    }
    rawRows.forEach(function (row, index) {
        if (!row || typeof row !== 'object')
            return;
        var item = row;
        var title = cleanText(item.title || item.name || item.display_name || item.subject_name, '');
        if (!title)
            return;
        rows.push({
            key: cleanText(item.key, "stored-".concat(index)),
            title: title,
            meta: cleanText(item.meta || item.last_at_display || item.subtitle, '最近使用'),
            source_type: String(item.source_type || ''),
            source_id: (item.source_id || item.subject_id || item.bank_id || ''),
            target: cleanText(item.target, 'stored'),
            mode: String(item.mode || '')
        });
    });
    var seen = {};
    return rows.filter(function (row) {
        var key = "".concat(cleanText(row.source_type, 'unknown'), ":").concat(cleanText(row.source_id, row.title));
        if (seen[key])
            return false;
        seen[key] = true;
        return true;
    }).slice(0, DEFAULT_RECENT_LIMIT);
}
function buildWeaknessEmptyActions(isLoggedIn, stats) {
    if (!isLoggedIn) {
        return [{
                key: 'login',
                title: '登录后查看薄弱环节',
                subtitle: '系统会根据练习记录生成巩固建议',
                action: '去登录',
                target: 'login'
            }];
    }
    var safeStats = stats || {};
    if (toNumber(safeStats.answered) <= 0) {
        return [{
                key: 'start',
                title: '还没有足够练习记录',
                subtitle: '先完成一次练习，首页会自动生成薄弱环节',
                action: '开始练习',
                target: 'publicBank'
            }];
    }
    return [{
            key: 'review',
            title: '暂未发现明显薄弱项',
            subtitle: '可以通过错题本或收藏题做一次主动复盘',
            action: '去复盘',
            target: 'review'
        }];
}
