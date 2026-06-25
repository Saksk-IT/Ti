"use strict";
Component({
    properties: {
        subTab: { type: String, value: 'wrong' },
        wrongState: { type: Object, value: {} },
        similarState: { type: Object, value: {} },
    },
    methods: {
        onStartWrong: function () {
            this.triggerEvent('startwrong');
        },
        onStartWrongAll: function () {
            this.triggerEvent('startwrongall');
        },
        onStartWrongOne: function (e) {
            this.triggerEvent('startwrongone', { id: e.currentTarget.dataset.id });
        },
        onStartSimilar: function () {
            this.triggerEvent('startsimilar');
        },
        onStartSimilarPair: function (e) {
            var _a = e.currentTarget.dataset, a = _a.a, b = _a.b;
            this.triggerEvent('startsimilarpair', { a: a, b: b });
        },
        onRetry: function () {
            this.triggerEvent('retry');
        },
    },
});
