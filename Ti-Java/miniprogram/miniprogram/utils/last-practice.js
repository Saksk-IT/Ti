"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildLastPracticeUrl = buildLastPracticeUrl;
function toBool(v) {
    if (v === true)
        return true;
    if (v === false)
        return false;
    var s = String(v !== null && v !== void 0 ? v : '').trim().toLowerCase();
    if (!s)
        return false;
    return s === '1' || s === 'true' || s === 'yes' || s === 'on';
}
function safeParseStorage(raw) {
    if (!raw)
        return null;
    if (typeof raw === 'object')
        return raw;
    var s = String(raw || '').trim();
    if (!s)
        return null;
    if (s.startsWith('{') || s.startsWith('[')) {
        try {
            return JSON.parse(s);
        }
        catch (e) {
            return null;
        }
    }
    return null;
}
function buildLastPracticeUrl() {
    var raw = wx.getStorageSync('last_practice_session');
    var js = safeParseStorage(raw);
    if (!js || typeof js !== 'object' || Array.isArray(js))
        return null;
    var subject = String(js.subject || '').trim();
    if (!subject)
        return null;
    var mode = String(js.mode || 'quiz').trim() || 'quiz';
    var type = String(js.type || 'all').trim() || 'all';
    var source = String(js.source || 'all').trim() || 'all';
    var shuffleQuestions = toBool(typeof js.shuffleQuestions !== 'undefined' ? js.shuffleQuestions : js.shuffle_questions);
    var shuffleOptions = toBool(typeof js.shuffleOptions !== 'undefined' ? js.shuffleOptions : js.shuffle_options);
    var params = [];
    params.push("subject=".concat(encodeURIComponent(subject)));
    params.push("mode=".concat(encodeURIComponent(mode)));
    if (type && type !== 'all')
        params.push("type=".concat(encodeURIComponent(type)));
    if (source && source !== 'all')
        params.push("source=".concat(encodeURIComponent(source)));
    if (shuffleQuestions)
        params.push('shuffle_questions=1');
    if (shuffleOptions)
        params.push('shuffle_options=1');
    return "/pages/quiz/quiz?".concat(params.join('&'));
}
