"use strict";
function clamp(value, min, max) {
    if (!Number.isFinite(value))
        return min;
    return Math.max(min, Math.min(max, value));
}
function computeQuadrantLabel(accuracyPct, completionPct) {
    var accHigh = accuracyPct >= 70;
    var compHigh = completionPct >= 70;
    if (accHigh && compHigh) {
        return { label: '收敛巩固', hint: '保持节奏，开始做错因归纳与系统性查漏补缺。' };
    }
    if (accHigh && !compHigh) {
        return { label: '扩面覆盖', hint: '正确率不错，优先扩大覆盖面并补齐薄弱题型。' };
    }
    if (!accHigh && compHigh) {
        return { label: '修正错因', hint: '覆盖已广但正确率偏低，建议按题型/知识点专题纠错。' };
    }
    return { label: '夯基起步', hint: '先小范围高质量刷题，建立稳定正确率再扩面。' };
}
Component({
    options: {
        styleIsolation: 'apply-shared',
        addGlobalClass: true
    },
    properties: {
        contextName: { type: String, value: '' },
        statsDays: { type: Number, value: 14 },
        statsLoading: { type: Boolean, value: false },
        statsError: { type: String, value: '' },
        statsOverview: { type: Object, value: {} },
        statsTrend: { type: Array, value: [] },
        displayTypes: { type: Array, value: [] },
        statsHasDifficulty: { type: Boolean, value: false },
        statsByDifficulty: { type: Array, value: [] },
        heatCells: { type: Array, value: [] },
        statsAdvice: { type: Array, value: [] },
        ringAccuracy: {
            type: Number,
            value: 0,
            observer: function () {
                this.computeQuadrant();
            }
        },
        ringCompletion: {
            type: Number,
            value: 0,
            observer: function () {
                this.computeQuadrant();
            }
        },
        ringActive: { type: Number, value: 0 },
        activeDaysRate: { type: Number, value: 0 }
    },
    data: {
        quadDotLeft: 50,
        quadDotTop: 50,
        quadLabel: '夯基起步',
        quadHint: '先小范围高质量刷题，建立稳定正确率再扩面。'
    },
    lifetimes: {
        attached: function () {
            this.computeQuadrant();
        }
    },
    methods: {
        computeQuadrant: function () {
            var accuracy = clamp(Number(this.data.ringAccuracy || 0), 0, 100);
            var completion = clamp(Number(this.data.ringCompletion || 0), 0, 100);
            var dotLeft = clamp(completion, 6, 94);
            var dotTop = clamp(100 - accuracy, 6, 94);
            var _a = computeQuadrantLabel(accuracy, completion), label = _a.label, hint = _a.hint;
            this.setData({ quadDotLeft: dotLeft, quadDotTop: dotTop, quadLabel: label, quadHint: hint });
        }
    }
});
