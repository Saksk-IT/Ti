Component({
  properties: {
    shuffleQuestions: { type: Boolean, value: false },
    shuffleOptions: { type: Boolean, value: false },
    shuffleOptionsDisabled: { type: Boolean, value: false },
    compact: { type: Boolean, value: false },
  },
  methods: {
    onToggleQuestions() {
      this.triggerEvent('togglequestions');
    },
    onToggleOptions() {
      this.triggerEvent('toggleoptions');
    },
  },
});
