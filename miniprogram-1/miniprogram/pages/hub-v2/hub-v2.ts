import { api, resolveUploadUrl } from '../../utils/api';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeStyle, ThemeMode } from '../../utils/theme';
import { decorateAvatarUrl } from '../../utils/avatar';

interface CheckinData {
  checked_in_today: boolean;
  streak_days: number;
  total_days: number;
}

interface LastPracticeData {
  has_practice: boolean;
  last_at: string | null;
  subject_id: number | null;
  subject_name: string | null;
  path: string | null;
  last_at_display?: string;
  // 本地会话增强字段
  source_type?: 'public' | 'bank' | '';
  source_id?: string | number;
  display_name?: string;
  mode?: string;
  has_local_session?: boolean;  // 是否有本地精确会话
}

interface WeaknessItem {
  subject: string;
  q_type: string;
  answered: number;
  accuracy: number;
}

interface StatsData {
  answered: number;
  accuracy: number;
  favorites: number;
  mistakes: number;
}

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr.replace(' ', 'T'));
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin}分钟前`;
    if (diffHour < 24) return `${diffHour}小时前`;
    if (diffDay < 7) return `${diffDay}天前`;
    return dateStr.slice(0, 10);
  } catch {
    return '';
  }
}

/** 根据时间戳计算相对时间（避免时区问题） */
function formatTimeAgoFromTimestamp(timestamp: number): string {
  if (!timestamp) return '';
  try {
    const now = Date.now();
    const diffMs = now - timestamp;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin}分钟前`;
    if (diffHour < 24) return `${diffHour}小时前`;
    if (diffDay < 7) return `${diffDay}天前`;

    // 超过7天显示日期
    const date = new Date(timestamp);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  } catch {
    return '';
  }
}

/** 根据当前时间生成问候语 */
function getGreetingText(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 9) return '早上好';
  if (hour >= 9 && hour < 12) return '上午好';
  if (hour >= 12 && hour < 14) return '中午好';
  if (hour >= 14 && hour < 18) return '下午好';
  if (hour >= 18 && hour < 22) return '晚上好';
  return '夜深了';
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,
    isLoggedIn: false, // 是否已登录

    // 用户信息
    userName: '',
    userAvatar: '',
    greetingText: '你好',

    // 签到
    checkin: {
      checked_in_today: false,
      streak_days: 0,
      total_days: 0,
    } as CheckinData,

    // 继续练习
    lastPractice: {
      has_practice: false,
      last_at: null,
      subject_id: null,
      subject_name: null,
      path: null,
      last_at_display: '',
      source_type: '',
      source_id: '',
      display_name: '',
      mode: '',
      has_local_session: false,
    } as LastPracticeData,

    // 薄弱环节（最多2条）
    weakness: [] as WeaknessItem[],

    // 学习统计
    stats: {
      answered: 0,
      accuracy: 0,
      favorites: 0,
      mistakes: 0,
    } as StatsData,

    // 主题
    isDarkMode: false,
    themeClass: '',
    themeStyle: 'default' as ThemeStyle,
    themeStyleClass: '',
    themeMode: 'light' as ThemeMode,

    // 页面进入动画
    pageVisible: false,

    // 新用户资料设置弹窗
    showProfileSetupModal: false,
    setupStep: 'profile' as 'profile' | 'password',
    setupAvatarTempPath: '',
    setupNickName: '',
    savingProfile: false,
    // 昵称检查状态
    usernameStatus: '' as '' | 'checking' | 'ok' | 'error',
    usernameStatusText: '',
    usernameCheckTimer: null as ReturnType<typeof setTimeout> | null,
    // 密码设置
    setupPassword: '',
    setupPasswordConfirm: '',
    showPassword: false,
    savingPassword: false,
  },

  onLoad() {
    // 初始化主题
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}
    
    // 设置问候语
    this.setData({ greetingText: getGreetingText() });

    // 页面进入动画：延迟触发，防止白屏
    setTimeout(() => {
      this.setData({ pageVisible: true });
    }, 50);
  },

  onShow() {
    const isLoggedIn = checkLogin();
    this.setData({ isLoggedIn });

    // 隐藏tabBar
    try {
      wx.hideTabBar({ animation: false });
    } catch (e) {}

    // 更新主题
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    // 更新问候语（可能跨时段）
    this.setData({ greetingText: getGreetingText() });

    // 加载数据（无论是否登录都加载，但内容不同）
    this.loadAllData();

    // 检查是否为新用户，显示资料设置引导
    this.checkNewUserSetup();
  },

  onHide() {
    try {
      wx.showTabBar({ animation: false });
    } catch (e) {}
  },

  onUnload() {
    try {
      wx.showTabBar({ animation: false });
    } catch (e) {}
  },

  async loadAllData() {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      const isLoggedIn = this.data.isLoggedIn;

      // 未登录时显示默认信息
      if (!isLoggedIn) {
        this.setData({
          userName: '游客',
          userAvatar: '',
          checkin: { checked_in_today: false, streak_days: 0, total_days: 0 },
          lastPractice: { has_practice: false, last_at: null, subject_id: null, subject_name: null, path: null, last_at_display: '' },
          stats: { answered: 0, accuracy: 0, favorites: 0, mistakes: 0 },
          weakness: [],
          inited: true,
          loading: false,
        });
        return;
      }

      // 已登录：并行加载所有数据
      const [profile, checkinStatus, lastPractice, historyStats] = await Promise.all([
        api.getProfile().catch(() => null),
        api.getCheckinStatus().catch(() => null),
        api.getLastPractice().catch(() => null),
        api.getHistoryStats(30).catch(() => null),
      ]);

      // 用户信息
      if (profile) {
        const nextAvatar = profile.avatar ? decorateAvatarUrl(resolveUploadUrl(profile.avatar)) : '';
        const self = this;
        self.__userAvatarDlTried = false;
        this.setData({
          userName: profile.username || '用户',
          userAvatar: nextAvatar,
        });
        this.maybePromptPasswordSetup(profile);
      }

      // 签到状态
      if (checkinStatus) {
        this.setData({
          checkin: {
            checked_in_today: checkinStatus.checked_in_today || false,
            streak_days: checkinStatus.streak_days || 0,
            total_days: checkinStatus.total_days || 0,
          },
        });
      }

      // 继续练习：优先使用本地精确会话，其次使用服务端数据
      const localSession = this.getLocalLastSession();

      if (localSession && localSession.has_practice) {
        // 本地有精确会话信息，优先使用
        this.setData({
          lastPractice: localSession,
        });
      } else if (lastPractice && lastPractice.has_practice) {
        // 兜底：使用服务端返回的数据
        this.setData({
          lastPractice: {
            has_practice: true,
            last_at: lastPractice.last_at,
            subject_id: lastPractice.subject_id,
            subject_name: lastPractice.subject_name,
            path: lastPractice.path,
            last_at_display: formatTimeAgo(lastPractice.last_at),
            has_local_session: false,
          },
        });
      }

      // 学习统计 + 薄弱环节
      if (historyStats) {
        const data = historyStats as Record<string, unknown>;
        this.setData({
          stats: {
            answered: data.answered_count || 0,
            accuracy: data.accuracy || 0,
            favorites: data.favorites_count || 0,
            mistakes: data.mistakes_count || 0,
          },
        });

        // 薄弱环节（取前2条）
        const weaknessRows = (data.weakness_rows || []).slice(0, 2);
        this.setData({ weakness: weaknessRows });
      }

      this.setData({ inited: true });
    } catch (e: any) {
      console.error('加载首页数据失败:', e);
      // 如果是401错误，清除登录状态但不跳转
      const errorMsg = (e && e.message) || '';
      if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期') || errorMsg.includes('unauthorized')) {
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        this.setData({ isLoggedIn: false, userName: '游客', userAvatar: '' });
      } else {
        wx.showToast({ title: e?.message || '加载失败', icon: 'none' });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  // 签到
  async onCheckinTap() {
    // 未登录时提示登录
    if (!this.data.isLoggedIn) {
      this.showLoginPrompt('登录后可签到');
      return;
    }

    if (this.data.checkin.checked_in_today) {
      wx.showToast({ title: '今日已签到', icon: 'none' });
      return;
    }

    try {
      const result = await api.doCheckin();
      this.setData({
        checkin: {
          checked_in_today: true,
          streak_days: result.streak_days || 1,
          total_days: result.total_days || 1,
        },
      });

      if (result.just_checked_in) {
        wx.showToast({ title: '签到成功', icon: 'success' });
      }
    } catch (e: any) {
      wx.showToast({ title: e?.message || '签到失败', icon: 'none' });
    }
  },

  // 继续练习
  onContinuePractice() {
    // 未登录时提示登录
    if (!this.data.isLoggedIn) {
      this.showLoginPrompt('登录后可查看练习记录');
      return;
    }

    const lp = this.data.lastPractice;

    // 优先使用本地精确会话构建完整路径
    if (lp.has_local_session && lp.source_type && lp.source_id) {
      const params: string[] = [];

      if (lp.source_type === 'bank') {
        params.push(`bank_id=${lp.source_id}`);
      } else {
        params.push(`subject=${lp.source_id}`);
      }

      if (lp.mode) params.push(`mode=${lp.mode}`);

      const path = `/pages/quiz/quiz?${params.join('&')}`;
      safeNavigate(path, 'redirectTo');
      return;
    }

    // 兜底：使用服务端返回的 path
    if (lp.path) {
      safeNavigate(lp.path, 'redirectTo');
    } else {
      safeNavigate('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
    }
  },

  // 显示登录提示
  showLoginPrompt(message: string) {
    wx.showModal({
      title: '提示',
      content: message,
      confirmText: '去登录',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({ url: '/pages/login/login' });
        }
      }
    });
  },

  // 跳转登录页
  onGoLoginTap() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  // 获取本地保存的上次练习会话
  getLocalLastSession(): LastPracticeData | null {
    try {
      const raw = wx.getStorageSync('last_practice_session');
      if (!raw || typeof raw !== 'object') return null;

      const session = raw as Record<string, unknown>;
      const sourceType = session.source_type || '';
      const sourceId = session.source_id || session.subject || session.bank_id;

      if (!sourceType || !sourceId) return null;

      // 计算时间显示（直接用时间戳计算，避免时区问题）
      const timestamp = session.timestamp || 0;
      let lastAtDisplay = '';
      if (timestamp) {
        lastAtDisplay = formatTimeAgoFromTimestamp(timestamp);
      }

      // 直接使用保存的显示名称，无名称时使用默认
      const subjectName = session.display_name || (sourceType === 'bank' ? '个人题库' : '公共题库');

      return {
        has_practice: true,
        last_at: timestamp ? new Date(timestamp).toISOString() : null,
        subject_id: sourceType === 'public' ? Number(sourceId) : null,
        subject_name: subjectName,
        path: null,  // 由 onContinuePractice 动态构建
        last_at_display: lastAtDisplay,
        source_type: sourceType,
        source_id: sourceId,
        display_name: subjectName,
        mode: session.mode,
        has_local_session: true,
      };
    } catch (e) {
      return null;
    }
  },

  // 薄弱环节点击
  onWeaknessItemTap(e: any) {
    const item = e.currentTarget.dataset.item as WeaknessItem;
    if (!item) return;
    // 跳转到对应科目的练习页
    safeNavigate('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
  },

  // 侧边栏
  onHamburgerTap() {
    this.setData({ drawerOpen: true });
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false });
  },

  onDrawerNavigate(e: any) {
    const url = e?.detail?.url;
    const navType = e?.detail?.navType;
    this.setData({ drawerOpen: false });
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e: any) {
    const style = (e?.detail?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  // 主题切换
  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  // 快捷入口
  onGoPublicBank() {
    safeNavigate('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
  },

  onGoMyBanks() {
    safeNavigate('/pages/my-banks-v2/my-banks-v2', 'redirectTo');
  },

  onGoFavorites() {
    safeNavigate('/pages/favorites-v2/favorites-v2', 'redirectTo');
  },

  onGoHistory() {
    safeNavigate('/packages/data/pages/data-center-v2/data-center-v2', 'redirectTo');
  },

  onGoReview() {
    safeNavigate('/pages/review-hub-v3/review-hub-v3', 'redirectTo');
  },

  onGoExamCenter() {
    safeNavigate('/pages/exams-select-v2/exams-select-v2', 'redirectTo');
  },

  onAboutTap() {
    safeNavigate('/pages/settings-center-v2/settings-center-v2?navKey=about', 'redirectTo');
  },

  // 头像点击 - 跳转个人资料
  onAvatarTap() {
    safeNavigate('/pages/profile-view-v2/profile-view-v2', 'navigateTo');
  },

  onUserAvatarError() {
    const url = String(this.data.userAvatar || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) {
      this.setData({ userAvatar: '' });
      return;
    }

    const self = this;
    if (self.__userAvatarDlTried) {
      this.setData({ userAvatar: '' });
      return;
    }
    self.__userAvatarDlTried = true;

    wx.downloadFile({
      url,
      timeout: 15000,
      success: (res) => {
        const tempFilePath = String((res && res.tempFilePath) || '').trim();
        this.setData({ userAvatar: tempFilePath || '' });
      },
      fail: () => {
        this.setData({ userAvatar: '' });
      }
    });
  },

  // 通知
  onGoNotifications() {
    safeNavigate('/pages/notifications-v2/notifications-v2', 'navigateTo');
  },

  // 设置
  onGoSettings() {
    safeNavigate('/pages/settings-center-v2/settings-center-v2', 'redirectTo');
  },

  // 检查是否为新用户，显示资料设置引导
  checkNewUserSetup() {
    const isNewUser = wx.getStorageSync('isNewUser');
    if (isNewUser && this.data.isLoggedIn) {
      // 延迟显示弹窗，等页面加载完成
      setTimeout(() => {
        if (!this.data.isLoggedIn || this.data.showProfileSetupModal) return;
        this.setData({ showProfileSetupModal: true, setupStep: 'profile' });
      }, 500);
    }
  },

  // 登录后自动检测：未设置密码则弹出设置密码弹窗
  maybePromptPasswordSetup(profile: any) {
    if (!this.data.isLoggedIn || !profile) return;
    const hasPasswordSet = !!profile.has_password_set;
    if (hasPasswordSet) return;
    this.setData({
      showProfileSetupModal: true,
      setupStep: 'password',
      setupPassword: '',
      setupPasswordConfirm: ''
    });
  },

  // 选择头像回调
  onSetupChooseAvatar(e: any) {
    const avatarUrl = e.detail?.avatarUrl || '';
    if (avatarUrl) {
      this.setData({ setupAvatarTempPath: avatarUrl });
    }
  },

  // 昵称实时输入回调（用于防抖检查）
  onSetupNickNameInput(e: any) {
    const nickName = e.detail?.value || '';
    this.setData({ setupNickName: nickName });

    // 清除之前的定时器
    if (this.data.usernameCheckTimer) {
      clearTimeout(this.data.usernameCheckTimer);
    }

    if (!nickName.trim()) {
      this.setData({ usernameStatus: '', usernameStatusText: '' });
      return;
    }

    if (nickName.trim().length < 2) {
      this.setData({ usernameStatus: 'error', usernameStatusText: '至少2个字符' });
      return;
    }

    // 防抖检查用户名
    this.setData({ usernameStatus: 'checking', usernameStatusText: '检查中...' });
    const timer = setTimeout(() => {
      this.checkUsernameAvailable(nickName.trim());
    }, 500);
    this.setData({ usernameCheckTimer: timer });
  },

  // 昵称输入完成回调
  onSetupNickNameChange(e: any) {
    const nickName = e.detail?.value || '';
    this.setData({ setupNickName: nickName });
    if (nickName.trim() && nickName.trim().length >= 2) {
      this.checkUsernameAvailable(nickName.trim());
    }
  },

  // 检查用户名是否可用
  async checkUsernameAvailable(username: string) {
    try {
      const res = await api.checkUsername(username);
      if (res.available) {
        this.setData({ usernameStatus: 'ok', usernameStatusText: '可以使用' });
      } else {
        this.setData({ usernameStatus: 'error', usernameStatusText: res.message || '已被使用' });
      }
    } catch (err: any) {
      this.setData({ usernameStatus: 'error', usernameStatusText: err?.message || '检查失败' });
    }
  },

  // 关闭资料设置弹窗
  onCloseProfileSetupModal() {
    this.setData({ showProfileSetupModal: false });
    wx.removeStorageSync('isNewUser');
  },

  // 阻止事件冒泡
  preventBubble() {
    // 空函数
  },

  // 跳过资料设置
  onSkipProfileSetup() {
    this.setData({ showProfileSetupModal: false });
    wx.removeStorageSync('isNewUser');
    wx.showToast({ title: '可在设置中修改', icon: 'none' });
  },

  // 保存资料设置
  async onSaveProfileSetup() {
    if (this.data.savingProfile) return;

    const { setupAvatarTempPath, setupNickName, usernameStatus } = this.data;
    if (!setupAvatarTempPath && !setupNickName) {
      wx.showToast({ title: '请选择头像或输入昵称', icon: 'none' });
      return;
    }

    // 如果有昵称但检查未通过
    if (setupNickName && usernameStatus === 'error') {
      wx.showToast({ title: '请修改昵称后再保存', icon: 'none' });
      return;
    }

    this.setData({ savingProfile: true });

    try {
      // 上传头像
      if (setupAvatarTempPath) {
        try {
          const uploadRes = await api.uploadProfileAvatar(setupAvatarTempPath);
          if (uploadRes && uploadRes.avatar_url) {
            this.setData({ userAvatar: resolveUploadUrl(uploadRes.avatar_url) });
            const cachedUserInfo = wx.getStorageSync('userInfo') || {};
            wx.setStorageSync('userInfo', { ...cachedUserInfo, avatar: uploadRes.avatar_url });
          }
        } catch (uploadErr: any) {
          console.warn('头像上传失败:', uploadErr?.message || uploadErr);
        }
      }

      // 更新昵称
      if (setupNickName) {
        try {
          await api.updateProfile({ username: setupNickName });
          this.setData({ userName: setupNickName });
          const cachedUserInfo = wx.getStorageSync('userInfo') || {};
          wx.setStorageSync('userInfo', { ...cachedUserInfo, username: setupNickName });
        } catch (nicknameErr: any) {
          wx.showToast({ title: nicknameErr?.message || '昵称设置失败', icon: 'none' });
          this.setData({ savingProfile: false });
          return;
        }
      }

      wx.showToast({ title: '资料已保存', icon: 'success' });
      // 进入密码设置步骤
      setTimeout(() => {
        this.setData({ setupStep: 'password', savingProfile: false });
      }, 500);
    } catch (e: any) {
      wx.showToast({ title: e?.message || '保存失败', icon: 'none' });
      this.setData({ savingProfile: false });
    }
  },

  // 密码输入
  onSetupPasswordInput(e: any) {
    this.setData({ setupPassword: e.detail?.value || '' });
  },

  // 确认密码输入
  onSetupPasswordConfirmInput(e: any) {
    this.setData({ setupPasswordConfirm: e.detail?.value || '' });
  },

  // 切换密码显示
  onToggleShowPassword() {
    this.setData({ showPassword: !this.data.showPassword });
  },

  // 跳过密码设置
  onSkipPasswordSetup() {
    this.setData({ showProfileSetupModal: false });
    wx.removeStorageSync('isNewUser');
    wx.showToast({ title: '可在设置中设置密码', icon: 'none' });
  },

  // 保存密码设置
  async onSavePasswordSetup() {
    if (this.data.savingPassword) return;

    const { setupPassword, setupPasswordConfirm } = this.data;

    if (!setupPassword) {
      wx.showToast({ title: '请输入密码', icon: 'none' });
      return;
    }

    if (setupPassword.length < 8) {
      wx.showToast({ title: '密码至少8位', icon: 'none' });
      return;
    }

    // 检查密码格式：必须包含字母和数字
    const hasLetter = /[a-zA-Z]/.test(setupPassword);
    const hasDigit = /\d/.test(setupPassword);
    if (!hasLetter || !hasDigit) {
      wx.showToast({ title: '密码必须包含字母和数字', icon: 'none' });
      return;
    }

    if (setupPassword !== setupPasswordConfirm) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' });
      return;
    }

    this.setData({ savingPassword: true });

    try {
      await api.updateProfilePassword({
        new_password: setupPassword,
        is_set_password: true
      });

      wx.showToast({ title: '密码设置成功', icon: 'success' });
      const cachedUserInfo = wx.getStorageSync('userInfo') || {};
      wx.setStorageSync('userInfo', { ...cachedUserInfo, has_password_set: true });
      this.setData({
        showProfileSetupModal: false,
        setupStep: 'profile',
        setupPassword: '',
        setupPasswordConfirm: '',
        showPassword: false
      });
      wx.removeStorageSync('isNewUser');
    } catch (e: any) {
      wx.showToast({ title: e?.message || '设置失败', icon: 'none' });
    } finally {
      this.setData({ savingPassword: false });
    }
  },
});
