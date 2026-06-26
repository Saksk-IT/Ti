import { themeManager } from '../utils/theme';

const SWITCH_DELAY_MS = 90;

Component({
  data: {
    selected: 0,
    switching: false,
    switchingIndex: -1,
    isDarkMode: false,
    themeClass: '',
    themeStyleClass: '',
    list: [
      {
        pagePath: '/pages/hub-v2/hub-v2',
        iconPath: '/images/tabbar/home.png',
        selectedIconPath: '/images/tabbar/home-active.png',
        text: '首页'
      },
      {
        pagePath: '/pages/public-bank-v2/public-bank-v2',
        iconPath: '/images/tabbar/plaza.png',
        selectedIconPath: '/images/tabbar/plaza-active.png',
        text: '题库广场'
      },
      {
        pagePath: '/pages/my-banks-v2/my-banks-v2',
        iconPath: '/images/tabbar/banks.png',
        selectedIconPath: '/images/tabbar/banks-active.png',
        text: '我的题库'
      },
      {
        pagePath: '/pages/campus/campus',
        iconPath: '/images/tabbar/campus.png',
        selectedIconPath: '/images/tabbar/campus-active.png',
        text: '校园'
      },
      {
        pagePath: '/pages/mine/mine',
        iconPath: '/images/tabbar/mine.png',
        selectedIconPath: '/images/tabbar/mine-active.png',
        text: '我的'
      }
    ]
  },

  lifetimes: {
    attached() {
      this.syncTheme();
      const off = themeManager.onThemeChange(() => this.syncTheme());
      (this as any).__themeOff = off;
    },

    detached() {
      const off = (this as any).__themeOff;
      if (typeof off === 'function') off();
    }
  },

  methods: {
    syncTheme() {
      try {
        const themeData = themeManager.getPageData();
        this.setData({
          isDarkMode: themeData.isDarkMode,
          themeClass: themeData.themeClass,
          themeStyleClass: themeData.themeStyleClass
        });
      } catch (e) {}
    },

    onTabTap(e: WechatMiniprogram.TouchEvent) {
      if (this.data.switching) return;
      const index = Number(e.currentTarget.dataset.index);
      const path = String(e.currentTarget.dataset.path || '');
      if (!Number.isInteger(index) || !path) return;
      if (index === this.data.selected) return;

      this.setData({
        selected: index,
        switching: true,
        switchingIndex: index
      });

      setTimeout(() => {
        wx.switchTab({
          url: path,
          fail: () => {
            this.setData({
              switching: false,
              switchingIndex: -1
            });
          }
        });
      }, SWITCH_DELAY_MS);
    }
  }
});
