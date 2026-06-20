type NavBarLayoutData = {
  ios: boolean;
  innerPaddingRight: string;
  leftWidth: string;
  safeAreaTop: string;
};

function toPositiveNumber(value: unknown): number {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? num : 0;
}

function buildLayout(compact: boolean): NavBarLayoutData {
  let rectLeft = 0;
  let rectTop = 0;
  let rectHeight = 0;
  try {
    const rect = wx.getMenuButtonBoundingClientRect();
    rectLeft = toPositiveNumber(rect?.left);
    rectTop = toPositiveNumber(rect?.top);
    rectHeight = toPositiveNumber(rect?.height);
  } catch (e) {}

  // wx.getSystemInfo 已废弃：优先使用 getDeviceInfo/getWindowInfo
  let platform = '';
  try {
    const di = wx.getDeviceInfo ? wx.getDeviceInfo() : null;
    if (di && di.platform) platform = String(di.platform);
  } catch (e) {}

  let windowWidth = 0;
  let safeAreaTop = 0;
  let statusBarHeight = 0;
  try {
    const wi = wx.getWindowInfo ? wx.getWindowInfo() : null;
    windowWidth = toPositiveNumber(wi && wi.windowWidth);
    safeAreaTop = toPositiveNumber(wi && wi.safeArea && wi.safeArea.top);
    statusBarHeight = toPositiveNumber(wi && wi.statusBarHeight);
  } catch (e) {}

  // 兼容旧基础库：兜底使用 getSystemInfoSync（旧版不算废弃）
  if (windowWidth <= 0 || safeAreaTop <= 0 || statusBarHeight <= 0) {
    try {
      const si = wx.getSystemInfoSync();
      if (windowWidth <= 0) windowWidth = toPositiveNumber(si.windowWidth);
      if (safeAreaTop <= 0) safeAreaTop = toPositiveNumber(si.safeArea && si.safeArea.top);
      if (statusBarHeight <= 0) statusBarHeight = toPositiveNumber(si.statusBarHeight);
      if (!platform) platform = String(si.platform || '');
    } catch (e) {}
  }

  const isAndroid = platform === 'android';
  const isDevtools = platform === 'devtools';
  const navHeight = isAndroid ? 48 : 44;
  const topFromMenu = rectTop > 0 ? Math.max(0, rectTop - Math.max(0, (navHeight - rectHeight) / 2)) : 0;
  const padRight = windowWidth > 0 && rectLeft > 0 ? Math.max(0, windowWidth - rectLeft) : 0;
  const top = Math.max(statusBarHeight, safeAreaTop, topFromMenu);
  const styleVars = `--nb-pad-right: ${padRight}px;${top > 0 ? `--nb-safe-top: ${top}px;` : ''}`;

  return {
    ios: !isAndroid,
    innerPaddingRight: `${styleVars}padding-right: ${padRight}px`,
    leftWidth: compact ? '' : `width: ${padRight}px`,
    safeAreaTop: isDevtools || isAndroid ? `height: calc(var(--height) + ${top}px); padding-top: ${top}px` : ``
  };
}

const DEFAULT_LAYOUT = buildLayout(false);

Component({
  options: {
    multipleSlots: true // 在组件定义时的选项中启用多slot支持
  },
  /**
   * 组件的属性列表
   */
  properties: {
    extClass: {
      type: String,
      value: ''
    },
    compact: {
      type: Boolean,
      value: false
    },
    title: {
      type: String,
      value: ''
    },
    background: {
      type: String,
      value: ''
    },
    color: {
      type: String,
      value: ''
    },
    back: {
      type: Boolean,
      value: true
    },
    loading: {
      type: Boolean,
      value: false
    },
    homeButton: {
      type: Boolean,
      value: false,
    },
    animated: {
      // 显示隐藏的时候opacity动画效果
      type: Boolean,
      value: true
    },
    show: {
      // 显示隐藏导航，隐藏的时候navigation-bar的高度占位还在
      type: Boolean,
      value: true,
      observer: '_showChange'
    },
    // back为true的时候，返回的页面深度
    delta: {
      type: Number,
      value: 1
    },
  },
  /**
   * 组件的初始数据
   */
  data: {
    displayStyle: '',
    ios: DEFAULT_LAYOUT.ios,
    innerPaddingRight: DEFAULT_LAYOUT.innerPaddingRight,
    leftWidth: DEFAULT_LAYOUT.leftWidth,
    safeAreaTop: DEFAULT_LAYOUT.safeAreaTop
  },
  lifetimes: {
    attached() {
      const next = buildLayout(!!this.properties.compact)
      const cur: any = this.data || {}
      if (
        cur.ios === next.ios &&
        cur.innerPaddingRight === next.innerPaddingRight &&
        cur.leftWidth === next.leftWidth &&
        cur.safeAreaTop === next.safeAreaTop
      ) return
      this.setData(next)
    },
  },
  /**
   * 组件的方法列表
   */
  methods: {
    _showChange(show: boolean) {
      const animated = this.data.animated
      let displayStyle = ''
      if (animated) {
        displayStyle = `opacity: ${
          show ? '1' : '0'
        };transition:opacity 0.5s;`
      } else {
        displayStyle = `display: ${show ? '' : 'none'}`
      }
      this.setData({
        displayStyle
      })
    },
    back() {
      const data = this.data
      if (data.delta) {
        wx.navigateBack({
          delta: data.delta
        })
      }
      this.triggerEvent('back', { delta: data.delta }, {})
    }
  },
})
