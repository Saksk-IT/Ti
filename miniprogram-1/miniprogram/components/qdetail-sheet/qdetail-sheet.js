"use strict";
Component({
    properties: {
        open: { type: Boolean, value: false },
        loading: { type: Boolean, value: false },
        error: { type: String, value: '' },
        meta: { type: String, value: '' },
        contentLines: { type: Array, value: [] },
        options: { type: Array, value: [] },
        answerLines: { type: Array, value: [] },
        explanationLines: { type: Array, value: [] },
    },
    methods: {
        onClose: function () {
            this.triggerEvent('close');
        },
        onSheetTap: function () {
            // prevent bubble to overlay
        },
        onGoQuiz: function () {
            this.triggerEvent('goquiz');
        },
    },
});
