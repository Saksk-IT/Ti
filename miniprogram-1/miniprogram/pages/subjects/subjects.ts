// subjects.ts - 科目页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subjects: [] as string[],
    filteredSubjects: [] as string[],
    keyword: '',
    loading: false,
    isLoggedIn: false
  },

  onShow() {
    const isLoggedIn = checkLogin();
    this.setData({ isLoggedIn });
    // 无论是否登录都加载科目列表
    this.loadSubjects();
  },

  async loadSubjects() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const res: any = await api.getSubjects();
      const list = (res && res.subjects) ? res.subjects : [];
      const subjects = Array.isArray(list) ? list.filter((x: any) => typeof x === 'string' && x.trim()) : [];
      this.setData({ subjects }, () => {
        this.applyFilter();
      });
    } catch (err: any) {
      console.error('加载科目失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onKeywordInput(e: any) {
    const keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
    this.setData({ keyword }, () => this.applyFilter());
  },

  onClearKeyword() {
    this.setData({ keyword: '' }, () => this.applyFilter());
  },

  applyFilter() {
    const kw = (this.data.keyword || '').trim().toLowerCase();
    const list = this.data.subjects || [];
    const filteredSubjects = kw
      ? list.filter((s) => String(s).toLowerCase().includes(kw))
      : list.slice();
    this.setData({ filteredSubjects });
  },

  onSubjectTap(e: any) {
    const subject = e.currentTarget.dataset.subject;
    if (!subject) return;

    // 未登录时提示登录
    if (!this.data.isLoggedIn) {
      wx.showModal({
        title: '提示',
        content: '登录后可进入科目详情',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/login/login' });
          }
        }
      });
      return;
    }

    wx.navigateTo({ url: `/pages/subject-detail/subject-detail?subject=${encodeURIComponent(subject)}` });
  },

  onPullDownRefresh() {
    this.loadSubjects().finally(() => wx.stopPullDownRefresh());
  }
});

