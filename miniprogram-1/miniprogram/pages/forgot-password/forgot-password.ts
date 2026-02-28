import { api } from '../../utils/api';

Page({
  data: {
    email: '',
    code: '',
    newPassword: '',
    loading: false,
    codeSending: false,
    countdown: 60
  },

  onEmailInput(e: any) {
    this.setData({ email: e.detail.value || '' });
  },

  onCodeInput(e: any) {
    this.setData({ code: e.detail.value || '' });
  },

  onPasswordInput(e: any) {
    this.setData({ newPassword: e.detail.value || '' });
  },

  async onSendCodeTap() {
    if (this.data.codeSending || this.data.loading) return;
    const email = (this.data.email || '').trim();
    if (!email) {
      wx.showToast({ title: '请输入邮箱', icon: 'none' });
      return;
    }
    try {
      await api.miniSendForgotPasswordCode(email);
      wx.showToast({ title: '已发送', icon: 'success' });
      this.startCountdown();
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '发送失败', icon: 'none' });
    }
  },

  startCountdown() {
    this.setData({ codeSending: true, countdown: 60 });
    const timer = setInterval(() => {
      const next = (this.data.countdown || 0) - 1;
      if (next <= 0) {
        clearInterval(timer);
        (this as any)._countdownTimer = null;
        this.setData({ codeSending: false, countdown: 60 });
        return;
      }
      this.setData({ countdown: next });
    }, 1000);
    (this as any)._countdownTimer = timer;
  },

  onUnload() {
    if ((this as any)._countdownTimer) {
      clearInterval((this as any)._countdownTimer);
      (this as any)._countdownTimer = null;
    }
  },

  async onResetTap() {
    if (this.data.loading) return;
    const email = (this.data.email || '').trim();
    const code = (this.data.code || '').trim();
    const newPassword = this.data.newPassword || '';

    if (!email) {
      wx.showToast({ title: '请输入邮箱', icon: 'none' });
      return;
    }
    if (!code) {
      wx.showToast({ title: '请输入验证码', icon: 'none' });
      return;
    }
    if (newPassword.length < 8) {
      wx.showToast({ title: '密码至少8位', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      await api.miniResetPassword(email, code, newPassword);
      wx.showToast({ title: '重置成功', icon: 'success' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (e: any) {
      wx.showToast({
        title: (e && (e.message || e.errMsg)) || '重置失败',
        icon: 'none'
      });
      this.setData({ loading: false });
    }
  }
});
