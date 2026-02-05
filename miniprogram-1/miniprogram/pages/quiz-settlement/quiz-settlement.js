"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// quiz-settlement.ts - 刷题/背题/加强 结算页
var auth_1 = require("../../utils/auth");
var theme_1 = require("../../utils/theme");
function formatSeconds(seconds) {
    var s = Math.max(0, Math.floor(Number(seconds) || 0));
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var r = s % 60;
    if (h > 0)
        return "".concat(String(h).padStart(2, '0'), ":").concat(String(m).padStart(2, '0'), ":").concat(String(r).padStart(2, '0'));
    return "".concat(String(m).padStart(2, '0'), ":").concat(String(r).padStart(2, '0'));
}
function modeLabel(mode, reinforceKind) {
    if (mode === 'memo')
        return '背题';
    if (mode === 'reinforce') {
        if (reinforceKind === 'similar')
            return '相似题加强';
        return '错题加强';
    }
    return '刷题';
}
function sourceLabel(source) {
    if (source === 'favorites')
        return '收藏';
    if (source === 'mistakes')
        return '错题';
    return '全部';
}
Page({
    data: {
        loading: false,
        errorText: '',
        payload: null,
        title: '本次结算',
        // 主题（深浅/风格）
        isDarkMode: false,
        themeMode: 'system',
        themeClass: '',
        themeStyle: 'default',
        themeStyleClass: '',
        themeCtaColor: '#007AFF',
        modeText: '',
        sourceText: '',
        qTypeText: '',
        tagText: '',
        subText: '',
        subChips: [],
        total: 0,
        answered: 0,
        correct: 0,
        wrong: 0,
        accuracy: 0,
        usedText: '--',
        usedTextClass: '',
        answeredPercent: 0,
        hasWrong: false
    },
    onLoad: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        // 初始化主题（保证进入页面即命中 themeClass / themeStyleClass）
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        try {
            wx.showShareMenu({ withShareTicket: true });
        }
        catch (e) { }
        var payload = null;
        try {
            var raw = wx.getStorageSync('quiz_settlement_payload_v1');
            if (raw && typeof raw === 'object') {
                payload = raw;
            }
        }
        catch (e) { }
        if (!payload || !payload.ts) {
            this.setData({ errorText: '结算数据已过期，请返回重试。' });
            return;
        }
        var modeText = modeLabel(payload.mode, payload.reinforceKind);
        var sourceText = sourceLabel(payload.source);
        var qTypeText = payload.qType && payload.qType !== 'all' ? payload.qType : '全部题型';
        var tagText = payload.tag && payload.tag !== 'all' ? payload.tag : '';
        var subText = "".concat(modeText, " \u00B7 ").concat(sourceText, " \u00B7 ").concat(qTypeText).concat(tagText ? " \u00B7 ".concat(tagText) : '');
        var subChips = [modeText, sourceText, qTypeText].concat(tagText ? [tagText] : []);
        var usedText = formatSeconds(payload.usedSec);
        var usedTextClass = usedText.length >= 8 ? 'v--sm' : '';
        var total = Number(payload.total || 0) || 0;
        var answered = Number(payload.answered || 0) || 0;
        var answeredPercent = total > 0 ? Math.max(0, Math.min(100, Math.round((answered * 100) / total))) : 0;
        this.setData({
            payload: payload,
            modeText: modeText,
            sourceText: sourceText,
            qTypeText: qTypeText,
            tagText: tagText,
            subText: subText,
            subChips: subChips,
            total: total,
            answered: answered,
            correct: payload.correct,
            wrong: payload.wrong,
            accuracy: payload.accuracy,
            usedText: usedText,
            usedTextClass: usedTextClass,
            answeredPercent: answeredPercent,
            hasWrong: Array.isArray(payload.wrongIds) && payload.wrongIds.length > 0
        });
    },
    buildQuizUrl: function (mode) {
        var p = this.data.payload;
        if (!p)
            return '/pages/hub-v2/hub-v2';
        var params = [];
        if (p.sourceType === 'bank')
            params.push("bank_id=".concat(encodeURIComponent(String(p.sourceId))));
        else
            params.push("subject=".concat(encodeURIComponent(String(p.sourceId))));
        params.push("mode=".concat(encodeURIComponent(String(mode))));
        if (mode !== 'reinforce') {
            params.push("source=".concat(encodeURIComponent(String(p.source || 'all'))));
            if (p.qType && p.qType !== 'all')
                params.push("type=".concat(encodeURIComponent(String(p.qType))));
            if (p.tag && p.tag !== 'all')
                params.push("tag=".concat(encodeURIComponent(String(p.tag))));
            if (p.shuffleQuestions)
                params.push('shuffle_questions=1');
            if (p.shuffleOptions)
                params.push('shuffle_options=1');
            return "/pages/quiz/quiz?".concat(params.join('&'));
        }
        var ids = (p.wrongIds || []).slice(0, 200);
        params.push('mode=reinforce');
        params.push('rk=wrong');
        params.push("ids=".concat(encodeURIComponent(ids.join(','))));
        return "/pages/quiz/quiz?".concat(params.join('&'));
    },
    onTapContinue: function () {
        var pages = getCurrentPages();
        if (pages && pages.length > 1) {
            wx.navigateBack({ delta: 1 });
            return;
        }
        var p = this.data.payload;
        if (!p)
            return;
        wx.navigateTo({ url: this.buildQuizUrl(p.mode) });
    },
    onTapReinforceWrong: function () {
        var p = this.data.payload;
        if (!p)
            return;
        if (!Array.isArray(p.wrongIds) || p.wrongIds.length === 0) {
            wx.showToast({ title: '本次没有错题', icon: 'none' });
            return;
        }
        wx.navigateTo({ url: this.buildQuizUrl('reinforce') });
    },
    onTapMistakesCenter: function () {
        var p = this.data.payload;
        if (!p)
            return;
        if (p.sourceType === 'bank') {
            wx.navigateTo({ url: "/pages/review-center-v2/review-center-v2?kind=mistakes&bank_id=".concat(encodeURIComponent(String(p.sourceId))) });
            return;
        }
        wx.navigateTo({ url: "/pages/review-center-v2/review-center-v2?kind=mistakes&subject=".concat(encodeURIComponent(String(p.sourceId))) });
    },
    onTapExam: function () {
        wx.navigateTo({ url: '/pages/exams-select-v2/exams-select-v2' });
    },
    onTapExit: function () {
        wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
    },
    onShareAppMessage: function () {
        var p = this.data.payload;
        var name = p ? String(p.displayName || '').trim() : '';
        var scope = name || '本次练习';
        var title = "".concat(scope, "\uFF5C").concat(this.data.modeText, "\uFF1A\u6B63\u786E\u7387 ").concat(this.data.accuracy, "%");
        return { title: title, path: '/pages/hub-v2/hub-v2' };
    }
});
