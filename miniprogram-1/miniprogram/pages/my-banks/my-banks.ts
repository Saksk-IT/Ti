// my-banks.ts - 我的题库页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

interface Bank {
  id: number;
  name: string;
  description?: string;
  question_count: number;
  is_public?: boolean;
  category_name?: string;
  permission?: string;
  access_type?: string;
  owner_nickname?: string;
}

Page({
  data: {
    activeTab: 'my' as 'my' | 'shared',
    myBanks: [] as Bank[],
    sharedBanks: [] as Bank[],
    loading: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    this.loadBanks();
  },

  async loadBanks() {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      if (this.data.activeTab === 'my') {
        const res: any = await api.getMyBanks();
        const banks = res.banks || [];
        this.setData({ myBanks: banks });
      } else {
        const res: any = await api.getSharedBanks();
        const banks = res.banks || [];
        this.setData({ sharedBanks: banks });
      }
    } catch (err: any) {
      console.error('加载题库失败:', err);
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onTabChange(e: any) {
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.activeTab) return;
    this.setData({ activeTab: tab }, () => {
      this.loadBanks();
    });
  },

  onBankTap(e: any) {
    const bankId = e.currentTarget.dataset.id;
    if (!bankId) return;
    wx.navigateTo({
      url: `/pages/bank-detail/bank-detail?id=${bankId}`
    });
  },

  onJoinTap() {
    wx.navigateTo({ url: '/pages/bank-join/bank-join' });
  },

  onPullDownRefresh() {
    this.loadBanks().finally(() => wx.stopPullDownRefresh());
  }
});
