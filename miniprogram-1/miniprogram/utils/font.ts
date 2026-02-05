/**
 * font.ts - 字体样式管理工具
 *
 * 支持多套字体样式，独立于主题风格：
 * - 'system': 系统默认 - 使用系统字体栈
 * - 'elegant': 优雅 - 思源宋体标题 + 思源黑体正文
 * - 'modern': 现代 - 思源黑体 Medium
 * - 'rounded': 圆润 - 圆体风格
 * - 'classic': 经典 - 衬线标题 + 无衬线正文
 */

const FONT_STYLE_STORAGE_KEY = 'app_font_style_v1';
const FONT_LOADED_CACHE_KEY = 'app_fonts_loaded_v1';

export type FontStyle = 'system' | 'elegant' | 'modern' | 'rounded' | 'classic';

export const FONT_STYLE_LIST: FontStyle[] = ['system', 'elegant', 'modern', 'rounded', 'classic'];

// 网络字体配置
interface WebFontConfig {
  family: string;
  source: string;
  weight?: string;
  style?: string;
}

// 使用 jsDelivr CDN 加载思源字体（免费、稳定、国内可访问）
const WEB_FONTS: Record<string, WebFontConfig[]> = {
  elegant: [
    {
      family: 'Noto Serif SC',
      source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc@5.0.19/files/noto-serif-sc-chinese-simplified-400-normal.woff2") format("woff2")',
      weight: '400'
    }
  ],
  modern: [
    {
      family: 'Noto Sans SC',
      source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5.0.19/files/noto-sans-sc-chinese-simplified-500-normal.woff2") format("woff2")',
      weight: '500'
    }
  ],
  rounded: [
    {
      family: 'ZCOOL KuaiLe',
      source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/zcool-kuaile@5.0.19/files/zcool-kuaile-chinese-simplified-400-normal.woff2") format("woff2")',
      weight: '400'
    }
  ],
  classic: [
    {
      family: 'Noto Serif SC',
      source: 'url("https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc@5.0.19/files/noto-serif-sc-chinese-simplified-400-normal.woff2") format("woff2")',
      weight: '400'
    }
  ]
};

// 已加载的字体缓存
const loadedFonts = new Set<string>();

/**
 * 加载网络字体
 */
function loadWebFont(config: WebFontConfig): Promise<boolean> {
  const fontKey = `${config.family}-${config.weight || '400'}`;

  // 已加载过则跳过
  if (loadedFonts.has(fontKey)) {
    return Promise.resolve(true);
  }

  return new Promise((resolve) => {
    wx.loadFontFace({
      family: config.family,
      source: config.source,
      scopes: ['webview', 'native'],
      success: () => {
        console.log(`字体加载成功: ${config.family}`);
        loadedFonts.add(fontKey);
        resolve(true);
      },
      fail: (err) => {
        console.warn(`字体加载失败: ${config.family}`, err);
        resolve(false);
      }
    });
  });
}

/**
 * 加载指定样式所需的字体
 */
async function loadFontsForStyle(style: FontStyle): Promise<void> {
  if (style === 'system') return;

  const fonts = WEB_FONTS[style];
  if (!fonts || fonts.length === 0) return;

  const promises = fonts.map(font => loadWebFont(font));
  await Promise.all(promises);
}

export interface FontStyleInfo {
  id: FontStyle;
  name: string;
  description: string;
  titleFont: string;
  bodyFont: string;
  monoFont: string;
}

// 字体样式配置
export const FONT_STYLE_CONFIG: Record<FontStyle, FontStyleInfo> = {
  system: {
    id: 'system',
    name: '系统默认',
    description: '使用设备原生字体',
    titleFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    bodyFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    monoFont: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
  },
  elegant: {
    id: 'elegant',
    name: '优雅',
    description: '思源宋体，文艺气质',
    titleFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", serif',
    bodyFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", serif',
    monoFont: '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
  },
  modern: {
    id: 'modern',
    name: '现代',
    description: '思源黑体，简约专业',
    titleFont: '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
    bodyFont: '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
    monoFont: '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
  },
  rounded: {
    id: 'rounded',
    name: '圆润',
    description: '站酷快乐体，亲和可爱',
    titleFont: '"ZCOOL KuaiLe", "Yuanti SC", "Yuanti TC", "PingFang SC", -apple-system, BlinkMacSystemFont, sans-serif',
    bodyFont: '"ZCOOL KuaiLe", "Yuanti SC", "Yuanti TC", "PingFang SC", -apple-system, BlinkMacSystemFont, sans-serif',
    monoFont: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
  },
  classic: {
    id: 'classic',
    name: '经典',
    description: '思源宋体，传统稳重',
    titleFont: '"Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", Georgia, "Times New Roman", serif',
    bodyFont: '"Noto Serif SC", "Source Han Serif SC", "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif',
    monoFont: '"Courier New", Courier, "Liberation Mono", monospace'
  }
};

// 字体大小规范
export const FONT_SIZE = {
  // 标题
  h1: '44rpx',
  h2: '40rpx',
  h3: '36rpx',
  h4: '32rpx',
  // 正文
  body: '28rpx',
  bodyLarge: '30rpx',
  bodySmall: '26rpx',
  // 辅助
  caption: '24rpx',
  small: '22rpx',
  tiny: '20rpx',
  // 按钮
  button: '28rpx',
  buttonSmall: '24rpx',
  // 标签
  tag: '22rpx',
  tagSmall: '20rpx'
} as const;

// 字重规范
export const FONT_WEIGHT = {
  thin: 100,
  extraLight: 200,
  light: 300,
  regular: 400,
  medium: 500,
  semiBold: 600,
  bold: 700,
  extraBold: 800,
  black: 900
} as const;

// 行高规范
export const LINE_HEIGHT = {
  tight: 1.2,
  snug: 1.375,
  normal: 1.5,
  relaxed: 1.625,
  loose: 2
} as const;

// 当前字体样式
let currentFontStyle: FontStyle = 'modern';
let bootstrapped = false;

// 字体变更回调列表
const fontChangeCallbacks: Array<(style: FontStyle) => void> = [];

/**
 * 从本地存储获取保存的字体样式
 */
function getStoredFontStyle(): FontStyle {
  try {
    const stored = wx.getStorageSync(FONT_STYLE_STORAGE_KEY);
    if (stored && FONT_STYLE_LIST.includes(stored)) {
      return stored as FontStyle;
    }
  } catch (e) {
    console.warn('读取字体样式失败:', e);
  }
  return 'modern';
}

/**
 * 保存字体样式到本地存储
 */
function saveFontStyle(style: FontStyle): void {
  try {
    wx.setStorageSync(FONT_STYLE_STORAGE_KEY, style);
  } catch (e) {
    console.warn('保存字体样式失败:', e);
  }
}

/**
 * 获取字体样式对应的 CSS 类名
 */
function getFontStyleClass(style: FontStyle): string {
  if (!style || style === 'system') return '';
  return `font-style-${style}`;
}

/**
 * 通知所有页面字体变更
 */
function notifyFontChange(): void {
  const style = currentFontStyle;
  const fontStyleClass = getFontStyleClass(style);
  const config = FONT_STYLE_CONFIG[style];

  // 调用所有注册的回调
  fontChangeCallbacks.forEach(callback => {
    try {
      callback(style);
    } catch (e) {
      console.error('字体变更回调执行失败:', e);
    }
  });

  // 获取所有页面并尝试更新
  const pages = getCurrentPages();
  pages.forEach(page => {
    if (page && typeof (page as any).onFontChange === 'function') {
      try {
        (page as any).onFontChange(style);
      } catch (e) {
        console.error('页面字体变更处理失败:', e);
      }
    }
    // 更新页面字体数据
    if (page && page.setData) {
      try {
        page.setData({
          fontStyle: style,
          fontStyleClass,
          fontStyleName: config.name
        });
      } catch (e) {
        // 忽略 setData 失败
      }
    }
  });
}

/**
 * 字体管理器
 */
export const fontManager = {
  /**
   * 启动期提前读取本地配置
   */
  bootstrap(): FontStyle {
    if (bootstrapped) return currentFontStyle;
    bootstrapped = true;
    currentFontStyle = getStoredFontStyle();
    // 启动时预加载当前样式的字体
    loadFontsForStyle(currentFontStyle);
    return currentFontStyle;
  },

  /**
   * 初始化字体系统（应在 app.ts onLaunch 中调用）
   */
  init(): FontStyle {
    this.bootstrap();
    return currentFontStyle;
  },

  /**
   * 获取当前字体样式
   */
  getStyle(): FontStyle {
    this.bootstrap();
    return currentFontStyle;
  },

  /**
   * 获取当前字体样式配置
   */
  getStyleConfig(): FontStyleInfo {
    this.bootstrap();
    return FONT_STYLE_CONFIG[currentFontStyle];
  },

  /**
   * 获取当前字体样式名称
   */
  getStyleName(): string {
    return FONT_STYLE_CONFIG[currentFontStyle].name;
  },

  /**
   * 设置字体样式
   */
  async setStyle(style: FontStyle): Promise<void> {
    if (!style || !FONT_STYLE_LIST.includes(style)) {
      console.warn('无效的字体样式:', style);
      return;
    }
    const prev = currentFontStyle;
    currentFontStyle = style;
    saveFontStyle(style);

    // 加载新样式所需的字体
    await loadFontsForStyle(style);

    if (prev !== style) {
      notifyFontChange();
    }
  },

  /**
   * 循环切换字体样式
   */
  cycleStyle(): FontStyle {
    const idx = FONT_STYLE_LIST.indexOf(currentFontStyle);
    const next = FONT_STYLE_LIST[(idx + 1) % FONT_STYLE_LIST.length];
    this.setStyle(next);
    return next;
  },

  /**
   * 注册字体变更回调
   */
  onFontChange(callback: (style: FontStyle) => void): () => void {
    fontChangeCallbacks.push(callback);
    return () => {
      const index = fontChangeCallbacks.indexOf(callback);
      if (index > -1) {
        fontChangeCallbacks.splice(index, 1);
      }
    };
  },

  /**
   * 获取用于页面的字体相关数据
   */
  getPageData(): { fontStyle: FontStyle; fontStyleClass: string; fontStyleName: string } {
    this.bootstrap();
    return {
      fontStyle: currentFontStyle,
      fontStyleClass: getFontStyleClass(currentFontStyle),
      fontStyleName: FONT_STYLE_CONFIG[currentFontStyle].name
    };
  },

  /**
   * 获取所有可用的字体样式列表
   */
  getStyleList(): FontStyleInfo[] {
    return FONT_STYLE_LIST.map(id => FONT_STYLE_CONFIG[id]);
  },

  /**
   * 获取字体大小规范
   */
  getFontSize(): typeof FONT_SIZE {
    return FONT_SIZE;
  },

  /**
   * 获取字重规范
   */
  getFontWeight(): typeof FONT_WEIGHT {
    return FONT_WEIGHT;
  },

  /**
   * 获取行高规范
   */
  getLineHeight(): typeof LINE_HEIGHT {
    return LINE_HEIGHT;
  }
};

export default fontManager;
