"use strict";
function clamp(value, min, max) {
    if (!Number.isFinite(value))
        return min;
    return Math.max(min, Math.min(max, value));
}
function computeQuadrantLabel(purityPct, coveragePct) {
    var purityHigh = purityPct >= 80;
    var covHigh = coveragePct >= 70;
    if (purityHigh && covHigh) {
        return { label: '优质资产', hint: '保持收藏纪律，定期清洗“含错率”偏高的题型。' };
    }
    if (purityHigh && !covHigh) {
        return { label: '精选扩面', hint: '收藏池很干净，继续扩面收藏以补齐关键题型结构。' };
    }
    if (!purityHigh && covHigh) {
        return { label: '高噪资产', hint: '覆盖已大但噪声偏高，建议先清洗再补齐，避免越收越乱。' };
    }
    return { label: '待清洗', hint: '先建立收藏标准：只收典型错因/高价值题，再逐步扩面。' };
}
Component({
    options: {
        styleIsolation: 'apply-shared',
        addGlobalClass: true
    },
    properties: {
        contextName: { type: String, value: '' },
        statsLoading: { type: Boolean, value: false },
        statsError: { type: String, value: '' },
        statsOverview: {
            type: Object,
            value: {},
            observer: function () {
                this.computeQuadrant();
            }
        },
        statsTrend: { type: Array, value: [] },
        displayTypes: { type: Array, value: [] },
        heatCells: { type: Array, value: [] },
        statsAdvice: { type: Array, value: [] },
        ringAccuracy: { type: Number, value: 0 },
        ringCompletion: {
            type: Number,
            value: 0,
            observer: function () {
                this.computeQuadrant();
            }
        },
        ringActive: { type: Number, value: 0 },
        activeDaysRate: { type: Number, value: 0 },
        favMistakeRateText: { type: String, value: '0%' }
    },
    data: {
        quadDotLeft: 50,
        quadDotTop: 50,
        quadLabel: '待清洗',
        quadHint: '先建立收藏标准：只收典型错因/高价值题，再逐步扩面。',
        purityText: '0%'
    },
    lifetimes: {
        attached: function () {
            this.computeQuadrant();
        }
    },
    methods: {
        computeQuadrant: function () {
            var coverage = clamp(Number(this.data.ringCompletion || 0), 0, 100);
            var overview = this.data.statsOverview || {};
            var total = Number((overview === null || overview === void 0 ? void 0 : overview.total) || 0) || 0;
            var mistakes = Number((overview === null || overview === void 0 ? void 0 : overview.mistakes) || 0) || 0;
            var purity = total > 0 ? clamp(((total - mistakes) / total) * 100, 0, 100) : 0;
            var dotLeft = clamp(coverage, 6, 94);
            var dotTop = clamp(100 - purity, 6, 94);
            var _a = computeQuadrantLabel(purity, coverage), label = _a.label, hint = _a.hint;
            this.setData({
                quadDotLeft: dotLeft,
                quadDotTop: dotTop,
                quadLabel: label,
                quadHint: hint,
                purityText: "".concat(purity.toFixed(0), "%")
            });
        }
    }
});
