"use strict";
Component({
    properties: {
        layout: { type: String, value: 'list' },
        rows: { type: Number, value: 3 },
        showTabs: { type: Boolean, value: false },
        showCards: { type: Number, value: 2 },
    },
    observers: {
        'rows, showCards': function () {
            this.buildLists();
        },
    },
    lifetimes: {
        attached: function () {
            this.buildLists();
        },
    },
    data: {
        cardList: [],
        rowList: [],
    },
    methods: {
        buildLists: function () {
            var cards = Math.max(1, Math.min(this.data.showCards || 2, 6));
            var rows = Math.max(1, Math.min(this.data.rows || 3, 8));
            var widths = [100, 85, 70, 60, 90, 75, 65, 80];
            this.setData({
                cardList: Array.from({ length: cards }, function (_, i) { return i; }),
                rowList: widths.slice(0, rows),
            });
        },
    },
});
