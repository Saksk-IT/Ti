Component({
  properties: {
    isDarkMode: { type: Boolean, value: false },
    themeMode: { type: String, value: 'light' },
  },
  methods: {
    onHamburger() {
      this.triggerEvent('hamburger');
    },
    onCycleTheme() {
      this.triggerEvent('cycletheme');
    },
  },
});
