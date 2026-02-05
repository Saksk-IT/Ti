import { api } from '../../utils/api';
import { logout } from '../../utils/auth';
import { ThemeStyle, themeManager } from '../../utils/theme';
import { FontStyle, fontManager, FONT_STYLE_CONFIG } from '../../utils/font';
import { syncUserSettingsToServer } from '../../utils/user-settings';

function summarizeUserName(userInfo: any): string {
  const raw = userInfo?.username || userInfo?.name || userInfo?.nickname || userInfo?.email;
  const name = (raw == null) ? '' : String(raw).trim();
  return name || '未登录';
}

Component({
  properties: {
    open: {
      type: Boolean,
      value: false,
      observer(this: any, v: boolean) {
        if (v) {
          this.refreshUnreadCount(false);
          this.refreshUserName();
          this.refreshThemeData();
          return;
        }
        this.closeQuickMenus();
      }
    },
    themeStyle: { type: String, value: 'default' },
    activeKey: { type: String, value: '' }
  },
  data: {
    searchKeyword: '',
    unreadNotiCount: 0,
    unreadNotiText: '',
    userName: '未登录',
    actionMenuOpen: false,
    themeMenuOpen: false,
    fontMenuOpen: false,
    themeStyle: 'dune' as ThemeStyle,
    fontStyle: 'modern' as FontStyle,
    isDarkMode: false,
    themeClass: 'theme-light',
    themeStyleClass: ''
  },
  lifetimes: {
    attached() {
      this.refreshUserName();
      this.refreshThemeData();
      try {
        const off = themeManager.onThemeChange(() => {
          this.refreshThemeData();
        });
        const self: any = this as any;
        self.__offThemeChange = off;
      } catch (e) {}
    },
    detached() {
      const self: any = this as any;
      try {
        if (typeof self.__offThemeChange === 'function') self.__offThemeChange();
      } catch (e) {}
      self.__offThemeChange = null;
    }
  },
  methods: {
    onClose() {
      this.closeQuickMenus();
      this.triggerEvent('close');
    },
    stopTap() {},
    closeQuickMenus() {
      if (!(this.data as any).actionMenuOpen && !(this.data as any).themeMenuOpen && !(this.data as any).fontMenuOpen) return;
      this.setData({ actionMenuOpen: false, themeMenuOpen: false, fontMenuOpen: false });
    },
    refreshThemeData() {
      try {
        const p: any = themeManager.getPageData() as any;
        const f: any = fontManager.getPageData() as any;
        this.setData({
          themeStyle: p?.themeStyle || themeManager.getStyle(),
          fontStyle: f?.fontStyle || fontManager.getStyle(),
          isDarkMode: !!p?.isDarkMode,
          themeClass: String(p?.themeClass || ''),
          themeStyleClass: String(p?.themeStyleClass || '')
        });
      } catch (e) {}
    },
    refreshUserName() {
      try {
        const userInfo = wx.getStorageSync('userInfo') || {};
        this.setData({ userName: summarizeUserName(userInfo) });
      } catch (e) {
        this.setData({ userName: '未登录' });
      }
    },
    async refreshUnreadCount(force = false) {
      const token = wx.getStorageSync('token') || '';
      if (!token) {
        this.setData({ unreadNotiCount: 0, unreadNotiText: '' });
        return;
      }

      const self: any = this as any;
      const now = Date.now();
      const lastAt = Number(self.__unreadFetchedAt || 0) || 0;
      if (!force && now - lastAt < 15000) return;
      self.__unreadFetchedAt = now;

      try {
        const res: any = await api.getUnreadNotificationCount();
        const count = Number(res?.count || 0) || 0;
        const text = count > 99 ? '99+' : String(count);
        this.setData({ unreadNotiCount: count, unreadNotiText: count > 0 ? text : '' });
      } catch (e) {
        // 忽略错误：抽屉仅用于辅助显示角标
      }
    },
    onNavTap(e: any) {
      const url = e?.currentTarget?.dataset?.url;
      const navType = e?.currentTarget?.dataset?.navType;
      this.triggerEvent('navigate', { url, navType });
    },
    onMoreTap() {
      const opened = !!(this.data as any).actionMenuOpen;
      this.setData({ actionMenuOpen: !opened, themeMenuOpen: false });
      if (!opened) this.refreshThemeData();
    },
    onQuickMenuMaskTap() {
      this.closeQuickMenus();
    },
    onQuickNavTap(e: any) {
      const url = e?.currentTarget?.dataset?.url;
      const navType = e?.currentTarget?.dataset?.navType;
      this.closeQuickMenus();
      this.triggerEvent('navigate', { url, navType });
    },
    onOpenThemeMenu() {
      this.setData({ actionMenuOpen: false, themeMenuOpen: true, fontMenuOpen: false });
      this.refreshThemeData();
    },
    onOpenFontMenu() {
      this.setData({ actionMenuOpen: false, themeMenuOpen: false, fontMenuOpen: true });
      this.refreshThemeData();
    },
    onBackToQuickMenu() {
      this.setData({ actionMenuOpen: true, themeMenuOpen: false, fontMenuOpen: false });
    },
    async onThemeStyleTap(e: any) {
      const style = String(e?.currentTarget?.dataset?.style || 'default') as ThemeStyle;
      themeManager.setStyle(style);
      this.closeQuickMenus();
      await syncUserSettingsToServer();
    },
    async onFontStyleTap(e: any) {
      const style = String(e?.currentTarget?.dataset?.style || 'system') as FontStyle;
      await fontManager.setStyle(style);
      this.refreshThemeData();
      this.closeQuickMenus();
      await syncUserSettingsToServer();
    },
    onLogoutTap() {
      this.closeQuickMenus();
      wx.showModal({
        title: '退出登录',
        content: '确定要退出登录吗？',
        confirmText: '退出',
        confirmColor: '#FF3B30',
        success: (r) => {
          if (!r.confirm) return;
          try {
            logout();
          } catch (e) {}
          this.triggerEvent('navigate', { url: '/pages/login/login', navType: 'reLaunch' });
        }
      });
    },
    onStyleTap(e: any) {
      const style = e?.currentTarget?.dataset?.style;
      this.triggerEvent('selectstyle', { style });
    },
    onSearchInput(e: any) {
      const v = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
      this.setData({ searchKeyword: v });
    },
    onSearchSubmit() {
      const kw = String((this.data as any).searchKeyword || '').trim();
      if (!kw) {
        this.triggerEvent('navigate', { url: '/pages/search-v2/search-v2', navType: 'navigateTo' });
        return;
      }
      const url = `/pages/search-v2/search-v2?keyword=${encodeURIComponent(kw)}`;
      this.triggerEvent('navigate', { url, navType: 'navigateTo' });
    }
  }
});
