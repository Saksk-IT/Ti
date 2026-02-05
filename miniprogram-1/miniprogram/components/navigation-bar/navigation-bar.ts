type NavBarLayoutData = {
  ios: boolean;
  innerPaddingRight: string;
  leftWidth: string;
  safeAreaTop: string;
};

function buildLayout(compact: boolean): NavBarLayoutData {
  let rectLeft = 0;
  try {
    const rect = wx.getMenuButtonBoundingClientRect();
    rectLeft = Number((rect as any)?.left) || 0;
  } catch (e) {}

  // wx.getSystemInfo 已废弃：优先使用 getDeviceInfo/getWindowInfo
  let platform = '';
  try {
    const di = (wx as any).getDeviceInfo ? (wx as any).getDeviceInfo() : null;
    if (di && (di as any).platform) platform = String((di as any).platform);
  } catch (e) {}

  let windowWidth = 0;
  let safeAreaTop = 0;
  try {
    const wi = (wx as any).getWindowInfo ? (wx as any).getWindowInfo() : null;
    const ww = wi && (wi as any).windowWidth;
    const st = wi && (wi as any).safeArea && (wi as any).safeArea.top;
    windowWidth = Number(ww);
    safeAreaTop = Number(st);
  } catch (e) {}

  // 兼容旧基础库：兜底使用 getSystemInfoSync（旧版不算废弃）
  if (!Number.isFinite(windowWidth) || windowWidth <= 0) {
    try {
      const si = wx.getSystemInfoSync();
      windowWidth = Number((si as any).windowWidth);
      safeAreaTop = Number((si as any).safeArea && (si as any).safeArea.top);
      if (!platform) platform = String((si as any).platform || '');
    } catch (e) {}
  }

  const isAndroid = platform === 'android';
  const isDevtools = platform === 'devtools';
  const padRight = Math.max(0, (Number.isFinite(windowWidth) ? windowWidth : 0) - rectLeft);
  const top = Number.isFinite(safeAreaTop) && safeAreaTop > 0 ? safeAreaTop : 0;
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
