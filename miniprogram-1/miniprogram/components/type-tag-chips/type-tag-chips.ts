Component({
  properties: {
    types: { type: Array, value: [] },
    tags: { type: Array, value: [] },
    selectedType: { type: String, value: 'all' },
    selectedTag: { type: String, value: 'all' },
    showTypes: { type: Boolean, value: true },
    showTags: { type: Boolean, value: true },
    typeLabel: { type: String, value: '' },
    tagLabel: { type: String, value: '' },
    typeSub: { type: String, value: '' },
    tagSub: { type: String, value: '' },
  },
  methods: {
    onTypeTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('typetap', { type: e.currentTarget.dataset.type });
    },
    onTagTap(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('tagtap', { tag: e.currentTarget.dataset.tag });
    },
    onTagDelete(e: WechatMiniprogram.TouchEvent) {
      this.triggerEvent('tagdelete', { tag: e.currentTarget.dataset.tag });
    },
  },
});
