Component({
  properties: {
    open: { type: Boolean, value: false },
    tabs: { type: Array, value: [] },
  },
  methods: {
    onClose() {
      this.triggerEvent('close');
    },
    onSheetTap() {
      // prevent bubble to overlay
    },
    onReset() {
      this.triggerEvent('reset');
    },
    onMove(e: WechatMiniprogram.TouchEvent) {
      const { key, act } = e.currentTarget.dataset;
      this.triggerEvent('move', { key, act });
    },
  },
});
