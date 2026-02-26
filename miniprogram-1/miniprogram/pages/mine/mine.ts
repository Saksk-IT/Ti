// mine.ts - 我的
import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';
import { decorateAvatarUrl } from '../../utils/avatar';

Page({
  data: {
    userInfo: null as Record<string, unknown> | null,
    stats: {
      favorites: 0,
      mistakes: 0
    },
    loading: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    const userInfo = wx.getStorageSync('userInfo');
    // 将相对路径的 avatar 转为完整 URL
    if (userInfo && (userInfo.avatar || userInfo.avatar_url)) {
      const rawAvatar = userInfo.avatar || userInfo.avatar_url;
      const fullUrl = decorateAvatarUrl(resolveUploadUrl(rawAvatar));
      userInfo.avatar = fullUrl;
      userInfo.avatar_url = fullUrl;
    }
    this.setData({ userInfo });
    this.loadStats();
  },

  async loadStats() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const userCounts: any = await api.getUserCounts({ subject: 'all' });
      this.setData({
        stats: {
          favorites: userCounts.favorites || 0,
          mistakes: userCounts.mistakes || 0
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载用户统计失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onGoSubjectsTap() {
    wx.switchTab({ url: '/pages/subjects/subjects' });
  },

  onOpenLogsTap() {
    wx.navigateTo({ url: '/pages/logs/logs' });
  },

  onOpenIndexV2Tap() {
    wx.navigateTo({ url: '/pages/index-v2/index-v2' });
  },

  onOpenHubV2Tap() {
    wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
  },

  onOpenPublicBankV2Tap() {
    wx.navigateTo({ url: '/pages/public-bank-v2/public-bank-v2' });
  },

  onOpenMyBanksV2Tap() {
    wx.navigateTo({ url: '/pages/my-banks-v2/my-banks-v2' });
  },

  onOpenSearchV2Tap() {
    wx.navigateTo({ url: '/pages/search-v2/search-v2' });
  },

  onLogoutTap() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#FF3B30',
      success: (res) => {
        if (!res.confirm) return;
        logout();
        wx.reLaunch({ url: '/pages/login/login' });
      }
    });
  }
});
