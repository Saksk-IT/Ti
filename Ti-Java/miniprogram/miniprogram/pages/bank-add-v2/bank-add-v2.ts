import { api, getApiOrigin } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager, ThemeMode } from '../../utils/theme';
import { normalizeWebNextPath } from '../../utils/web';

function buildExternalWebUrl(next: any): string {
  const origin = String(getApiOrigin() || '').trim().replace(/\/$/, '');
  const path = normalizeWebNextPath(next, '/hub');
  if (!origin) return path;
  const raw = `${origin}${path}`;
  if (/([?&])from=/.test(raw)) return raw;
  return `${raw}${raw.includes('?') ? '&' : '?'}from=miniapp`;
}

Page({
  data: {
    name: '',
    description: '',
    creating: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    const self = this;
    if (!self.__webCreateHintShown) {
      self.__webCreateHintShown = true;
      wx.showToast({ title: '提示：网页端支持更完整的题库导入与管理', icon: 'none' });
    }
  },

  onNameInput(e: any) {
    this.setData({ name: String(e?.detail?.value || '') });
  },

  onDescInput(e: any) {
    this.setData({ description: String(e?.detail?.value || '') });
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onCancel() {
    wx.navigateBack();
  },

  onOpenWebCreate() {
    const url = buildExternalWebUrl('/user/banks');
    wx.showModal({
      title: '请前往网页端',
      content: '小程序内不再内嵌网页端。点击「复制链接」后在浏览器打开并登录。',
      confirmText: '复制链接',
      cancelText: '关闭',
      success: (res) => {
        if (!res.confirm) return;
        wx.setClipboardData({
          data: url,
          success: () => wx.showToast({ title: '链接已复制', icon: 'success' }),
          fail: () => wx.showToast({ title: '复制失败', icon: 'none' })
        });
      }
    });
  },

  async onSubmit() {
    if (this.data.creating) return;

    const name = String(this.data.name || '').trim();
    const description = String(this.data.description || '').trim();

    if (!name) {
      wx.showToast({ title: '题库名称不能为空', icon: 'none' });
      return;
    }
    if (name.length < 2 || name.length > 50) {
      wx.showToast({ title: '题库名称需要 2-50 个字符', icon: 'none' });
      return;
    }
    if (description.length > 200) {
      wx.showToast({ title: '描述不能超过 200 个字符', icon: 'none' });
      return;
    }

    this.setData({ creating: true });
    try {
      const res: any = await api.createBank({ name, description });
      const id = Number(res?.id || 0);
      if (!Number.isFinite(id) || id <= 0) {
        wx.showToast({ title: '创建成功，但未返回题库ID', icon: 'none' });
        this.setData({ creating: false });
        return;
      }
      wx.showToast({ title: '创建成功', icon: 'success' });
      setTimeout(() => {
        wx.redirectTo({ url: `/pages/bank-detail/bank-detail?id=${id}` });
      }, 400);
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '创建失败', icon: 'none' });
      this.setData({ creating: false });
    }
  }
});
