"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeHubStats = normalizeHubStats;
exports.buildStudyAdvice = buildStudyAdvice;
exports.buildRecentBanks = buildRecentBanks;
exports.buildWeaknessEmptyActions = buildWeaknessEmptyActions;
var DEFAULT_RECENT_LIMIT = 3;
var DEFAULT_ADVICE_LIMIT = 3;
function toNumber(value) {
    var num = Number(value || 0);
    return Number.isFinite(num) ? num : 0;
}
function cleanText(value, fallback) {
    var text = String(value || '').trim();
    return text || fallback;
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
