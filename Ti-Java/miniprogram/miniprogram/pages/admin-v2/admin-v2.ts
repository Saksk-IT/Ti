import { checkLogin } from '../../utils/auth';
import { themeManager, ThemeMode } from '../../utils/theme';

function isDevEnv(): boolean {
  try {
    return wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
  } catch (e) {
    return false;
  }
}

Page({
  data: {
    showDevTools: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData({ showDevTools: isDevEnv() });
      this.setData(themeManager.getPageData());
    } catch (e) {}
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onGoDevSettings() {
    if (!isDevEnv()) return;
    wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
  }
});
