"use strict";
Component({
    properties: {
        keyword: { type: String, value: '' },
        searchType: { type: String, value: 'all' },
        types: { type: Array, value: [] },
        results: { type: Array, value: [] },
        total: { type: Number, value: 0 },
        loading: { type: Boolean, value: false },
        searched: { type: Boolean, value: false },
        scopeLabel: { type: String, value: '当前科目' },
        searchError: { type: String, value: '' },
    },
    methods: {
        onInput: function (e) {
            this.triggerEvent('input', { value: e.detail.value });
        },
        onSearch: function () {
            this.triggerEvent('search');
        },
        onTypeTap: function (e) {
            this.triggerEvent('typetap', { type: e.currentTarget.dataset.type });
        },
        onResultTap: function (e) {
            this.triggerEvent('resulttap', { id: e.currentTarget.dataset.id });
        },
        onLoadMore: function () {
            this.triggerEvent('loadmore');
        },
        onClear: function () {
            this.triggerEvent('clear');
        },
    },
});
