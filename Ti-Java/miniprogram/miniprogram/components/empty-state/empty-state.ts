Component({
  properties: {
    icon: { type: String, value: 'default' },
    title: { type: String, value: '' },
    hint: { type: String, value: '' },
    actionText: { type: String, value: '' },
    size: { type: String, value: 'normal' },
  },
  methods: {
    onAction() {
      this.triggerEvent('action');
    },
  },
});
