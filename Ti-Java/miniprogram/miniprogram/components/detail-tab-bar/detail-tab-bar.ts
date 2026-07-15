Component({
  properties: {
    tabs: { type: Array, value: [] },
    activeTab: { type: String, value: '' },
    reinforceSubTab: { type: String, value: 'wrong' },
    showReinforceBar: { type: Boolean, value: false },
  },
  methods: {
    onTabTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('tabtap', { tab: e.currentTarget.dataset.tab });
    },
    onOpenTabOrder() {
      this.triggerEvent('openorder');
    },
    onReinforceSubTabTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('reinforcesubtab', { subtab: e.currentTarget.dataset.subtab });
    },
  },
});
