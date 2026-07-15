"use strict";
Component({
    properties: {
        isDarkMode: { type: Boolean, value: false },
        themeMode: { type: String, value: 'light' },
    },
    methods: {
        onHamburger: function () {
            this.triggerEvent('hamburger');
        },
        onCycleTheme: function () {
            this.triggerEvent('cycletheme');
        },
    },
});
