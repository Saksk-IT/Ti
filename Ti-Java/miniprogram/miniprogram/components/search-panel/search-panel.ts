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
    onInput(e: WechatMiniprogram.Input) {
      this.triggerEvent('input', { value: e.detail.value });
    },
    onSearch() {
      this.triggerEvent('search');
    },
    onTypeTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('typetap', { type: e.currentTarget.dataset.type });
    },
    onResultTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('resulttap', { id: e.currentTarget.dataset.id });
    },
    onLoadMore() {
      this.triggerEvent('loadmore');
    },
    onClear() {
      this.triggerEvent('clear');
    },
  },
});
