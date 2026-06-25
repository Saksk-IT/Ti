"use strict";
Component({
    properties: {
        open: { type: Boolean, value: false },
        tabs: { type: Array, value: [] },
    },
    methods: {
        onClose: function () {
            this.triggerEvent('close');
        },
        onSheetTap: function () {
            // prevent bubble to overlay
        },
        onReset: function () {
            this.triggerEvent('reset');
        },
        onMove: function (e) {
            var _a = e.currentTarget.dataset, key = _a.key, act = _a.act;
            this.triggerEvent('move', { key: key, act: act });
        },
    },
});
