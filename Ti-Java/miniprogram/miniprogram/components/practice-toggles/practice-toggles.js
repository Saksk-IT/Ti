"use strict";
Component({
    properties: {
        shuffleQuestions: { type: Boolean, value: false },
        shuffleOptions: { type: Boolean, value: false },
        shuffleOptionsDisabled: { type: Boolean, value: false },
        compact: { type: Boolean, value: false },
    },
    methods: {
        onToggleQuestions: function () {
            this.triggerEvent('togglequestions');
        },
        onToggleOptions: function () {
            this.triggerEvent('toggleoptions');
        },
    },
});
