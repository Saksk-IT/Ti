/**
 * theme.ts - 主题管理工具
 *
 * 主题风格：
 * - 'dark': 深色主题
 * - 'default': 默认浅色
 * - 'mist': 雾蓝
 * - 'dune': 暖砂
 * - 'pine': 岩松
 * - 'celadon': 影青
 */

const THEME_STYLE_STORAGE_KEY = 'app_theme_style_v1';
const THEME_PREV_STYLE_KEY = 'app_theme_prev_style_v1'; // 记录切换深色前的风格

export type ThemeStyle = 'dark' | 'default' | 'mist' | 'dune' | 'pine' | 'celadon';

// 兼容旧代码的 ThemeMode 类型（实际上不再使用独立的模式概念）
export type ThemeMode = 'light' | 'dark' | 'system';

const THEME_STYLE_LIST: ThemeStyle[] = ['dark', 'default', 'mist', 'dune', 'pine', 'celadon'];
const LIGHT_STYLE_LIST: ThemeStyle[] = ['default', 'mist', 'dune', 'pine', 'celadon'];

interface ThemeInfo {
  isDark: boolean;        // 当前是否为深色
}

// 全局主题风格
let currentThemeStyle: ThemeStyle = 'dune';
let prevLightStyle: ThemeStyle = 'dune'; // 切换深色前的浅色风格

// 全局主题状态
let currentThemeInfo: ThemeInfo = {
  isDark: false
};

let bootstrapped = false;

// 主题变更回调列表
const themeChangeCallbacks: Array<(isDark: boolean) => void> = [];

function getStoredThemeStyle(): ThemeStyle {
  try {
    const stored = wx.getStorageSync(THEME_STYLE_STORAGE_KEY);
    if (stored && THEME_STYLE_LIST.includes(stored)) {
      return stored as ThemeStyle;
    }
  } catch (e) {
    console.warn('读取主题风格失败:', e);
  }
  return 'dune';
}

function getStoredPrevLightStyle(): ThemeStyle {
  try {
    const stored = wx.getStorageSync(THEME_PREV_STYLE_KEY);
    if (stored && LIGHT_STYLE_LIST.includes(stored)) {
      return stored as ThemeStyle;
    }
  } catch (e) {
    console.warn('读取上次浅色风格失败:', e);
  }
  return 'dune';
}

function saveThemeStyle(style: ThemeStyle): void {
  try {
    wx.setStorageSync(THEME_STYLE_STORAGE_KEY, style);
  } catch (e) {
    console.warn('保存主题风格失败:', e);
  }
}

function savePrevLightStyle(style: ThemeStyle): void {
  try {
    wx.setStorageSync(THEME_PREV_STYLE_KEY, style);
  } catch (e) {
    console.warn('保存上次浅色风格失败:', e);
  }
}

/**
 * 判断风格是否为深色
 */
function isDarkStyle(style: ThemeStyle): boolean {
  return style === 'dark';
}

function getThemeClass(style: ThemeStyle): string {
  return isDarkStyle(style) ? 'theme-dark' : 'theme-light';
}

function getThemeStyleClass(style: ThemeStyle): string {
  if (!style || style === 'default' || style === 'dark') return '';
  return `theme-style-${style}`;
}

function getCtaColorHex(style: ThemeStyle): string {
  const isDark = isDarkStyle(style);
  if (style === 'mist') return '#F97316';
  if (style === 'dune') return isDark ? '#E7A46A' : '#EA580C';
  if (style === 'pine') return isDark ? '#63D29C' : '#2DBA7D';
  if (style === 'celadon') return '#EA580C';
  if (style === 'dark') return '#007AFF';
  return '#007AFF';
}

function getBackgroundColorHex(style: ThemeStyle): string {
  const isDark = isDarkStyle(style);
  if (style === 'dark') return '#000000';
  if (style === 'mist') return isDark ? '#0C111A' : '#EEF2FF';
  if (style === 'dune') return isDark ? '#15110D' : '#FDFBF7';
  if (style === 'pine') return isDark ? '#0E1411' : '#F3F7F4';
  if (style === 'celadon') return isDark ? '#0D1314' : '#F0FDFA';
  return isDark ? '#000000' : '#F2F2F7';
}

function applyBackgroundStyle(style: ThemeStyle, done?: () => void): void {
  const bg = getBackgroundColorHex(style);
  const isDark = isDarkStyle(style);
  let doneCalled = false;
  const callDone = () => {
    if (!done || doneCalled) return;
    doneCalled = true;
    try {
      done();
    } catch (e) {}
  };

  if (done) {
    try {
      setTimeout(callDone, 80);
    } catch (e) {}
  }

  if (typeof wx.setBackgroundColor === 'function') {
    try {
      wx.setBackgroundColor({
        backgroundColor: bg,
        backgroundColorTop: bg,
        backgroundColorBottom: bg,
        success: () => callDone(),
        fail: () => callDone()
      });
    } catch (e) {
      // 忽略 setBackgroundColor 异常
      callDone();
    }
  } else {
    callDone();
  }

  if (typeof wx.setBackgroundTextStyle === 'function') {
    try {
      wx.setBackgroundTextStyle({ textStyle: isDark ? 'light' : 'dark', fail: () => {} });
    } catch (e) {
      // 忽略 setBackgroundTextStyle 异常
    }
  }
}

function applyTabBarStyle(style: ThemeStyle): void {
  const isDark = isDarkStyle(style);
  if (typeof wx.setTabBarStyle !== 'function') return;
  try {
    wx.setTabBarStyle({
      color: isDark ? '#8E8E93' : '#7A7E83',
      selectedColor: '#007AFF',
      backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
      borderStyle: isDark ? 'white' : 'black',
      fail: () => {}
    });
  } catch (e) {
    // 忽略 setTabBarStyle 异常
  }
}

/**
 * 通知所有页面主题变更
 */
function notifyThemeChange(): void {
  const style = currentThemeStyle;
  const isDark = isDarkStyle(style);
  const themeClass = getThemeClass(style);
  const themeStyleClass = getThemeStyleClass(style);
  const themeCtaColor = getCtaColorHex(style);

  currentThemeInfo.isDark = isDark;

  // 调用所有注册的回调
  themeChangeCallbacks.forEach(callback => {
    try {
      callback(isDark);
    } catch (e) {
      console.error('主题变更回调执行失败:', e);
    }
  });

  // 获取所有页面并尝试更新
  const pages = getCurrentPages();
  pages.forEach(page => {
    if (page && typeof (page as any).onThemeChange === 'function') {
      try {
        (page as any).onThemeChange(isDark);
      } catch (e) {
        console.error('页面主题变更处理失败:', e);
      }
    }
    // 更新页面主题数据
    if (page && page.setData) {
      try {
        page.setData({
          isDarkMode: isDark,
          themeClass,
          themeStyle: style,
          themeStyleClass,
          themeCtaColor
        });
      } catch (e) {
        // 忽略setData失败
      }
    }
  });

  applyTabBarStyle(style);
  applyBackgroundStyle(style);
}

/**
 * 主题管理器
 */
export const themeManager = {
  /**
   * 启动期提前读取本地配置并同步系统 UI。
   * 目的：让 Page 注册阶段注入的默认主题数据就是正确的，避免手动深色下切页"先白后黑"闪烁。
   */
  bootstrap(): ThemeInfo {
    if (bootstrapped) return { ...currentThemeInfo };
    bootstrapped = true;

    currentThemeStyle = getStoredThemeStyle();
    prevLightStyle = getStoredPrevLightStyle();
    const isDark = isDarkStyle(currentThemeStyle);

    currentThemeInfo = {
      isDark
    };

    applyTabBarStyle(currentThemeStyle);
    applyBackgroundStyle(currentThemeStyle);

    return { ...currentThemeInfo };
  },

  /**
   * 初始化主题系统（应在 app.ts onLaunch 中调用）
   */
  init(): ThemeInfo {
    this.bootstrap();
    return { ...currentThemeInfo };
  },

  /**
   * 获取当前主题信息
   */
  getThemeInfo(): ThemeInfo {
    this.bootstrap();
    return { ...currentThemeInfo };
  },

  /**
   * 获取当前是否为深色模式
   */
  isDarkMode(): boolean {
    return currentThemeInfo.isDark;
  },

  getStyle(): ThemeStyle {
    return currentThemeStyle;
  },

  setStyle(style: ThemeStyle): void {
    if (!style || !THEME_STYLE_LIST.includes(style)) {
      console.warn('无效的主题风格:', style);
      return;
    }
    const prev = currentThemeStyle;

    // 如果从浅色切换到深色，记录当前浅色风格
    if (!isDarkStyle(prev) && isDarkStyle(style)) {
      prevLightStyle = prev;
      savePrevLightStyle(prev);
    }

    currentThemeStyle = style;
    saveThemeStyle(style);
    if (prev !== style) {
      notifyThemeChange();
    }
  },

  /**
   * 在浅色风格之间循环（不包括深色）
   */
  cycleStyle(): ThemeStyle {
    const idx = LIGHT_STYLE_LIST.indexOf(currentThemeStyle as any);
    const next = LIGHT_STYLE_LIST[(idx + 1) % LIGHT_STYLE_LIST.length];
    this.setStyle(next);
    return next;
  },

  /**
   * 在所有风格之间循环（包括深色）
   */
  cycleAllStyles(): ThemeStyle {
    const idx = THEME_STYLE_LIST.indexOf(currentThemeStyle);
    const next = THEME_STYLE_LIST[(idx + 1) % THEME_STYLE_LIST.length];
    this.setStyle(next);
    return next;
  },

  getStyleName(style?: ThemeStyle): string {
    const s = style || currentThemeStyle;
    switch (s) {
      case 'dark':
        return '深色';
      case 'mist':
        return '雾蓝';
      case 'dune':
        return '暖砂';
      case 'pine':
        return '岩松';
      case 'celadon':
        return '影青';
      default:
        return '灰白';
    }
  },

  /**
   * 切换深色/暖砂
   * 顶部按钮固定在"暖砂"和"深色"之间切换
   * 太阳 = 暖砂，月亮 = 深色
   */
  toggleDark(): boolean {
    if (isDarkStyle(currentThemeStyle)) {
      // 从深色切换到暖砂
      this.setStyle('dune');
      return false;
    } else {
      // 从任何浅色切换到深色
      this.setStyle('dark');
      return true;
    }
  },

  /**
   * 注册主题变更回调
   */
  onThemeChange(callback: (isDark: boolean) => void): () => void {
    themeChangeCallbacks.push(callback);
    // 返回取消注册的函数
    return () => {
      const index = themeChangeCallbacks.indexOf(callback);
      if (index > -1) {
        themeChangeCallbacks.splice(index, 1);
      }
    };
  },

  /**
   * 获取用于页面的主题相关数据
   * 可在页面 onLoad/onShow 中调用并 setData
   */
  getPageData(): { isDarkMode: boolean; themeClass: string; themeStyle: ThemeStyle; themeStyleClass: string; themeCtaColor: string } {
    this.bootstrap();
    return {
      isDarkMode: currentThemeInfo.isDark,
      themeClass: getThemeClass(currentThemeStyle),
      themeStyle: currentThemeStyle,
      themeStyleClass: getThemeStyleClass(currentThemeStyle),
      themeCtaColor: getCtaColorHex(currentThemeStyle)
    };
  },

  /**
   * 应用主题到系统 UI（如 tabBar）
   */
  applySystemUI(): void {
    this.bootstrap();
    applyTabBarStyle(currentThemeStyle);
    applyBackgroundStyle(currentThemeStyle);
  },

  applySystemUIAsync(): Promise<void> {
    return new Promise((resolve) => {
      this.bootstrap();
      try {
        applyTabBarStyle(currentThemeStyle);
      } catch (e) {}
      try {
        applyBackgroundStyle(currentThemeStyle, () => resolve());
      } catch (e) {
        resolve();
      }
    });
  },

  /**
   * 获取主题相关的导航栏配置
   */
  getNavBarStyle(): { background: string; color: 'black' | 'white' } {
    return {
      background: currentThemeInfo.isDark ? '#1C1C1E' : '#FFFFFF',
      color: currentThemeInfo.isDark ? 'white' : 'black'
    };
  },

  /**
   * 获取主题图标（用于UI显示）
   */
  getThemeIcon(): string {
    return currentThemeInfo.isDark ? '🌙' : '☀';
  },

  // ========== 兼容旧代码的方法 ==========

  /**
   * 获取当前模式（兼容旧代码）
   * 新系统中不再区分 mode，深色作为风格之一
   */
  getMode(): ThemeMode {
    return isDarkStyle(currentThemeStyle) ? 'dark' : 'light';
  },

  /**
   * 设置模式（兼容旧代码）
   * 新系统中：dark -> 切换到深色风格，light -> 切换回上次浅色风格，system -> 同 light
   */
  setMode(mode: ThemeMode): void {
    if (mode === 'dark') {
      this.setStyle('dark');
    } else {
      // light 或 system 都切换回浅色
      if (isDarkStyle(currentThemeStyle)) {
        this.setStyle(prevLightStyle);
      }
    }
  },

  /**
   * 循环切换模式（兼容旧代码）
   * 新系统中：直接切换深色/浅色
   */
  cycleMode(): ThemeMode {
    this.toggleDark();
    return this.getMode();
  },

  /**
   * 获取模式名称（兼容旧代码）
   */
  getModeName(): string {
    return isDarkStyle(currentThemeStyle) ? '深色' : '浅色';
  }
};

export default themeManager;
