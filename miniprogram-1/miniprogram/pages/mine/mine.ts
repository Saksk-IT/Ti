// mine.ts - 我的
import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';
import { decorateAvatarUrl } from '../../utils/avatar';
import { safeNavigate } from '../../utils/nav';
import { restartTabPageTransition } from '../../utils/tab-transition';
import { themeManager } from '../../utils/theme';
import { fontManager } from '../../utils/font';

function canShowAdmin(userInfo: any): boolean {
  return !!(userInfo?.is_admin || userInfo?.is_subject_admin || userInfo?.is_notification_admin);
}

Page({
  data: {
    userInfo: null as Record<string, unknown> | null,
    canShowAdmin: false,
    stats: {
      favorites: 0,
      mistakes: 0
    },
    loading: false,
    tabPageTransitionClass: ''
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    restartTabPageTransition(this);
    const userInfo = wx.getStorageSync('userInfo');
    try {
      this.setData({
        ...themeManager.getPageData(),
        ...fontManager.getPageData()
      });
    } catch (e) {}
    // 将相对路径的 avatar 转为完整 URL
    if (userInfo && (userInfo.avatar || userInfo.avatar_url)) {
      const rawAvatar = userInfo.avatar || userInfo.avatar_url;
      const fullUrl = decorateAvatarUrl(resolveUploadUrl(rawAvatar));
      userInfo.avatar = fullUrl;
      userInfo.avatar_url = fullUrl;
    }
    this.setData({ userInfo, canShowAdmin: canShowAdmin(userInfo) });
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

  onGoFavoritesTap() {
    safeNavigate('/pages/favorites-v2/favorites-v2', 'navigateTo');
  },

  onGoMistakesTap() {
    safeNavigate('/pages/mistakes-v2/mistakes-v2', 'navigateTo');
  },

  onGoProfileTap() {
    safeNavigate('/pages/profile-view-v2/profile-view-v2', 'navigateTo');
  },

  onGoAccountTap() {
    safeNavigate('/pages/settings-account-security-v2/settings-account-security-v2', 'navigateTo');
  },

  onGoReviewTap() {
    safeNavigate('/pages/review-hub-v3/review-hub-v3', 'navigateTo');
  },

  onGoDataTap() {
    safeNavigate('/packages/data/pages/data-center-v2/data-center-v2', 'navigateTo');
  },

  onGoExamTap() {
    safeNavigate('/pages/exams-select-v2/exams-select-v2', 'navigateTo');
  },

  onGoCodingTap() {
    safeNavigate('/pages/coding-v2/coding-v2', 'navigateTo');
  },

  onGoNotificationsTap() {
    safeNavigate('/pages/notifications-v2/notifications-v2', 'navigateTo');
  },

  onGoThemeTap() {
    safeNavigate('/pages/settings-theme-v2/settings-theme-v2', 'navigateTo');
  },

  onGoAdminTap() {
    if (!this.data.canShowAdmin) return;
    safeNavigate('/pages/admin-v2/admin-v2', 'navigateTo');
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
