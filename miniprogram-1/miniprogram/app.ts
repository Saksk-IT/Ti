// app.ts
import { themeManager } from './utils/theme';
import { fontManager } from './utils/font';
import { syncUserSettingsFromServer } from './utils/user-settings';

// 启动期尽早读取用户手动主题和字体（避免 Page 首帧使用默认导致闪烁）
try {
  themeManager.bootstrap();
  fontManager.bootstrap();
} catch (e) {}

let lastSettingsSyncAt = 0;
function maybeSyncUserSettings(): void {
  const token = wx.getStorageSync('token');
  if (!token) return;
  const now = Date.now();
  if (now - lastSettingsSyncAt < 30000) return;
  lastSettingsSyncAt = now;
  syncUserSettingsFromServer();
}

let subpackagePreloaded = false;
function preloadCriticalSubpackages(): void {
  if (subpackagePreloaded) return;
  subpackagePreloaded = true;
  try {
    const loadSubpackage = (wx as any).loadSubpackage;
    if (typeof loadSubpackage !== 'function') return;
    const targets = ['packages/data', 'pages/index-v2', 'pages/subject-detail-v2'];
    setTimeout(() => {
      targets.forEach((name, idx) => {
        setTimeout(() => {
          try {
            loadSubpackage({ name, fail: () => {} });
          } catch (e) {}
        }, idx * 180);
      });
    }, 200);
  } catch (e) {}
}

function patchPageThemeOnce() {
  const g = globalThis as any;
  if (g.__appThemePagePatched) return;
  g.__appThemePagePatched = true;

  const originalPage = g.Page;
  if (typeof originalPage !== 'function') return;

  g.Page = (options: any) => {
    // 注入主题和字体数据，避免组件在首帧拿到 null/undefined（如 v2-drawer 的 themeStyle）
    try {
      const themeData = themeManager.getPageData();
      const fontData = fontManager.getPageData();
      const base = options && options.data && typeof options.data === 'object' ? options.data : {};
      options.data = { ...base, ...themeData, ...fontData };
    } catch (e) {
      // 忽略异常
    }

    const originalOnLoad = options.onLoad;
    const originalOnShow = options.onShow;

    options.onLoad = function (...args: any[]) {
      try {
        themeManager.applySystemUI();
      } catch (e) {
        // 忽略 applySystemUI 失败
      }
      try {
        this.setData({ ...themeManager.getPageData(), ...fontManager.getPageData() });
      } catch (e) {
        // 忽略 setData 失败
      }
      return typeof originalOnLoad === 'function' ? originalOnLoad.apply(this, args) : undefined;
    };

    options.onShow = function (...args: any[]) {
      try {
        themeManager.applySystemUI();
      } catch (e) {
        // 忽略 applySystemUI 失败
      }
      try {
        this.setData({ ...themeManager.getPageData(), ...fontManager.getPageData() });
      } catch (e) {
        // 忽略 setData 失败
      }
      return typeof originalOnShow === 'function' ? originalOnShow.apply(this, args) : undefined;
    };

    return originalPage(options);
  };
}

patchPageThemeOnce();

App<IAppOption>({
  globalData: {
    isDarkMode: false,
    themeMode: 'system' as 'light' | 'dark' | 'system',
    themeStyle: 'dune' as 'default' | 'mist' | 'dune' | 'pine' | 'celadon',
    fontStyle: 'modern' as 'system' | 'elegant' | 'modern' | 'rounded' | 'classic'
  },
  onLaunch() {
    // 初始化主题系统
    const themeInfo = themeManager.init();
    this.globalData.isDarkMode = themeInfo.isDark;
    this.globalData.themeMode = themeInfo.mode;
    this.globalData.themeStyle = themeManager.getStyle();

    // 初始化字体系统
    fontManager.init();
    this.globalData.fontStyle = fontManager.getStyle();

    maybeSyncUserSettings();
    preloadCriticalSubpackages();

    // 监听主题变化，更新全局数据
    themeManager.onThemeChange((isDark) => {
      this.globalData.isDarkMode = isDark;
      this.globalData.themeMode = themeManager.getMode();
      this.globalData.themeStyle = themeManager.getStyle();
    });

    // 监听字体变化，更新全局数据
    fontManager.onFontChange((style) => {
      this.globalData.fontStyle = style;
    });

    // 路由变化时同步系统 UI（兜底覆盖非 safeNavigate 的跳转时机）
    try {
      const g = globalThis as any;
      if (!g.__appThemeRouteHooked && typeof (wx as any).onAppRoute === 'function') {
        g.__appThemeRouteHooked = true;
        (wx as any).onAppRoute(() => {
          try {
            themeManager.applySystemUI();
          } catch (e) {}
          try {
            const nextTick = (wx as any).nextTick;
            if (typeof nextTick === 'function') {
              nextTick(() => {
                try {
                  themeManager.applySystemUI();
                } catch (e) {}
              });
            }
          } catch (e) {}
        });
      }
    } catch (e) {}

    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    wx.setStorageSync('logs', logs);

    // 登录
    wx.login({
      success: res => {
        void res.code;
      },
    });
  },
  onShow() {
    themeManager.applySystemUI();
    maybeSyncUserSettings();
  },
});
