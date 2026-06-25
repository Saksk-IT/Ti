"use strict";
Component({
    properties: {
        tabs: { type: Array, value: [] },
        activeTab: { type: String, value: '' },
        reinforceSubTab: { type: String, value: 'wrong' },
        showReinforceBar: { type: Boolean, value: false },
    },
    methods: {
        onTabTap: function (e) {
            this.triggerEvent('tabtap', { tab: e.currentTarget.dataset.tab });
        },
        onOpenTabOrder: function () {
            this.triggerEvent('openorder');
        },
        onReinforceSubTabTap: function (e) {
            this.triggerEvent('reinforcesubtab', { subtab: e.currentTarget.dataset.subtab });
        },
    },
});
