Component({
  properties: {
    subTab: { type: String, value: 'wrong' },
    wrongState: { type: Object, value: {} },
    similarState: { type: Object, value: {} },
  },
  methods: {
    onStartWrong() {
      this.triggerEvent('startwrong');
    },
    onStartWrongAll() {
      this.triggerEvent('startwrongall');
    },
    onStartWrongOne(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('startwrongone', { id: e.currentTarget.dataset.id });
    },
    onStartSimilar() {
      this.triggerEvent('startsimilar');
    },
    onStartSimilarPair(e: WechatMiniprogram.TouchEvent) {
      const { a, b } = e.currentTarget.dataset;
      this.triggerEvent('startsimilarpair', { a, b });
    },
    onRetry() {
      this.triggerEvent('retry');
    },
  },
});
