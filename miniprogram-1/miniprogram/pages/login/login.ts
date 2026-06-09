// 登录页面
import { wechatLogin } from '../../utils/auth';
import { api } from '../../utils/api';
import { config } from '../../utils/config';
import { safeNavigate, consumePendingMiniRedirect } from '../../utils/nav';

const HOME_URL = '/pages/hub-v2/hub-v2';
type LoginMode = 'wechat' | 'password' | 'email';

type AuthLoginMethods = {
  phone_login_enabled?: boolean;
  wechat_login_enabled?: boolean;
  default_mode?: 'phone' | 'qr' | 'password' | 'code';
};

function navigateAfterLogin(): void {
  const next = consumePendingMiniRedirect();
  if (next) {
    safeNavigate(next, 'redirectTo');
    return;
  }
  safeNavigate(HOME_URL, 'switchTab');
}

function isConnectionRefusedMessage(message: string): boolean {
  const msg = String(message || '');
  return (
    msg.includes('ERR_CONNECTION_REFUSED') ||
    msg.includes('errcode:-102') ||
    msg.includes('cronet_error_code:-102') ||
    msg.toLowerCase().includes('connection refused')
  );
}

function isDevEnv(): boolean {
  try {
    return wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
  } catch (e) {
    return false;
  }
}

function defaultMiniMode(methods: AuthLoginMethods): LoginMode {
  if (methods.wechat_login_enabled) return 'wechat';
  return 'password';
}

Page({
  data: {
    mode: 'wechat' as LoginMode,
    loading: false,
    username: '',
    password: '',
    email: '',
    code: '',
    codeSending: false,
    countdown: 20,
    showDevTools: false,
    apiUrl: '',
    wechatLoginEnabled: true,
    loginHeroSub: '支持微信 / 邮箱或手机号密码 / 邮箱验证码登录',
  },

  async onLoad() {
    this.refreshApiInfo();
    await this.loadAuthLoginMethods();
    // 避免“旧 token 已失效，但仍在 storage 导致一直跳首页又被 401 踢回”的循环：先轻量校验 token
    const token = wx.getStorageSync('token');
    if (!token) return;

    try {
      await api.getSubjects();
      navigateAfterLogin();
    } catch (err: any) {
      // 401：token 无效，清理后留在登录页
      if (err && err.statusCode === 401) {
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        return;
      }

      // 网络错误：留在登录页，避免跳转后不断触发请求
      const msg = (err && err.message) || '';
      if (isConnectionRefusedMessage(msg)) {
        wx.showModal({
          title: '无法连接后端',
          content:
            `当前 API 地址为：${config.getApiUrl()}\n\n` +
            '请到「开发设置」切换到“自定义”，填写电脑局域网 IP（如 192.168.1.100）或粘贴完整 URL，并点击“保存并启用自定义”。\n\n' +
            '同时确保后端已启动（python run.py）。',
          confirmText: '去设置',
          cancelText: '知道了',
          success: (res) => {
            if (!res.confirm) return;
            wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
          }
        });
        return;
      }

      // 其它错误：不阻塞用户（可能是网络波动），仍按“已登录”处理
      navigateAfterLogin();
    }
  },

  onShow() {
    this.refreshApiInfo();
  },

  refreshApiInfo() {
    this.setData({
      showDevTools: isDevEnv(),
      apiUrl: config.getApiUrl()
    });
  },

  async loadAuthLoginMethods() {
    try {
      const methods = await api.getAuthLoginMethods();
      const phoneEnabled = methods.phone_login_enabled !== false;
      const wechatEnabled = methods.wechat_login_enabled !== false;
      const nextMode = this.isModeAvailable(this.data.mode, wechatEnabled)
        ? this.data.mode
        : defaultMiniMode({ wechat_login_enabled: wechatEnabled });

      this.setData({
        mode: nextMode,
        wechatLoginEnabled: wechatEnabled,
        loginHeroSub: this.buildLoginHeroSub(phoneEnabled, wechatEnabled),
      });
    } catch (e) {
      this.setData({
        loginHeroSub: this.buildLoginHeroSub(true, true)
      });
    }
  },

  buildLoginHeroSub(phoneEnabled: boolean, wechatEnabled: boolean): string {
    const parts: string[] = [];
    if (wechatEnabled) parts.push('微信');
    parts.push('邮箱或手机号密码');
    parts.push('邮箱验证码');
    return `支持${parts.join(' / ')}登录`;
  },

  isModeAvailable(mode: LoginMode, wechatEnabled?: boolean): boolean {
    const canUseWechat = wechatEnabled === undefined ? !!this.data.wechatLoginEnabled : !!wechatEnabled;
    if (mode === 'wechat') return canUseWechat;
    return mode === 'password' || mode === 'email';
  },

  onOpenDevSettingsTap() {
    wx.navigateTo({ url: '/pages/dev-settings/dev-settings' });
  },

  onCopyApiTap() {
    const data = String(this.data.apiUrl || '').trim();
    if (!data) return;
    wx.setClipboardData({
      data,
      success: () => wx.showToast({ title: '已复制', icon: 'success' }),
      fail: () => wx.showToast({ title: '复制失败', icon: 'none' })
    });
  },

  async promptBindWechatIfNeeded(loginData: any) {
    if (!this.data.wechatLoginEnabled) return;

    const userInfo = (loginData && loginData.user_info) || wx.getStorageSync('userInfo') || null;
    const wechatBound = !!(userInfo && (userInfo.wechat_bound || userInfo.wechatBound));
    if (wechatBound) return;

    const modalRes: any = await new Promise((resolve) => {
      wx.showModal({
        title: '绑定微信',
        content: '绑定后可使用微信快捷登录',
        confirmText: '绑定',
        cancelText: '稍后',
        success: resolve
      });
    });

    if (!modalRes || !modalRes.confirm) return;

    try {
      const code: string = await new Promise((resolve, reject) => {
        wx.login({
          success: (res) => {
            if (res.code) resolve(res.code);
            else reject(new Error('获取微信登录code失败'));
          },
          fail: (err) => reject(err)
        });
      });

      const bindRes: any = await api.miniWechatBind(code);
      if (bindRes && bindRes.token) wx.setStorageSync('token', bindRes.token);
      if (bindRes && bindRes.user_info) wx.setStorageSync('userInfo', bindRes.user_info);
      wx.showToast({ title: '微信已绑定', icon: 'success' });
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '绑定失败';
      wx.showToast({ title: msg, icon: 'none' });
    }
  },

  // 微信登录
  async handleLogin() {
    if (this.data.loading) return;
    if (!this.data.wechatLoginEnabled) {
      wx.showToast({ title: '微信登录已关闭', icon: 'none' });
      return;
    }
    
    this.setData({ loading: true });
    try {
      const result = await wechatLogin();
      if (result === 'need_bind') {
        wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
        return;
      }

      wx.showToast({ title: '登录成功', icon: 'success' });

      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }

      // 跳转到首页，使用reLaunch确保页面重新加载
      setTimeout(() => {
        navigateAfterLogin();
      }, 600);
    } catch (err: any) {
      console.error('登录失败:', err);
      const errorMsg = (err && (err.message || err.errMsg)) || '登录失败，请稍后重试';
      wx.showToast({ 
        title: errorMsg, 
        icon: 'none',
        duration: 3000
      });
      this.setData({ loading: false });
    }
  },

  // 手动登录按钮
  onLoginTap() {
    this.handleLogin();
  },

  onSwitchMode(e: any) {
    const mode = e.currentTarget.dataset.mode;
    if (mode !== 'wechat' && mode !== 'password' && mode !== 'email') return;
    if (!this.isModeAvailable(mode)) {
      wx.showToast({ title: '该登录方式已关闭', icon: 'none' });
      return;
    }
    this.setData({ mode });
  },

  onUsernameInput(e: any) {
    this.setData({ username: e.detail.value || '' });
  },

  onPasswordInput(e: any) {
    this.setData({ password: e.detail.value || '' });
  },

  onForgotPasswordTap() {
    wx.navigateTo({ url: '/pages/forgot-password/forgot-password' });
  },

  onEmailInput(e: any) {
    this.setData({ email: e.detail.value || '' });
  },

  onCodeInput(e: any) {
    this.setData({ code: e.detail.value || '' });
  },

  async onPasswordLoginTap() {
    if (this.data.loading) return;
    const username = (this.data.username || '').trim();
    const password = this.data.password || '';
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(username);
    const isPhone = /^1[3-9]\d{9}$/.test(username);
    if (!username || !password) {
      wx.showToast({ title: '请输入邮箱/手机号和密码', icon: 'none' });
      return;
    }
    if (!isEmail && !isPhone) {
      wx.showToast({ title: '仅支持邮箱或手机号登录', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const data: any = await api.miniPasswordLogin(username, password);
      if (!data || !data.token) throw new Error('登录返回异常');
      wx.setStorageSync('token', data.token);
      if (data.user_info) wx.setStorageSync('userInfo', data.user_info);

      await this.promptBindWechatIfNeeded(data);
      wx.showToast({ title: '登录成功', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }
      setTimeout(() => navigateAfterLogin(), 600);
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '登录失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async onSendCodeTap() {
    if (this.data.codeSending || this.data.loading) return;
    const email = (this.data.email || '').trim();
    if (!email) {
      wx.showToast({ title: '请输入邮箱', icon: 'none' });
      return;
    }
    try {
      await api.miniSendEmailLoginCode(email);
      wx.showToast({ title: '已发送', icon: 'success' });
      this.startCountdown();
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '发送失败', icon: 'none' });
    }
  },

  startCountdown() {
    this.setData({ codeSending: true, countdown: 20 });
    const timer = setInterval(() => {
      const next = (this.data.countdown || 0) - 1;
      if (next <= 0) {
        clearInterval(timer);
        this.setData({ codeSending: false, countdown: 20 });
        return;
      }
      this.setData({ countdown: next });
    }, 1000);
  },

  async onEmailLoginTap() {
    if (this.data.loading) return;
    const email = (this.data.email || '').trim();
    const code = (this.data.code || '').trim();
    if (!email || !code) {
      wx.showToast({ title: '请输入邮箱和验证码', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const data: any = await api.miniEmailLogin(email, code);
      if (!data || !data.token) throw new Error('登录返回异常');
      wx.setStorageSync('token', data.token);
      if (data.user_info) wx.setStorageSync('userInfo', data.user_info);

      await this.promptBindWechatIfNeeded(data);
      wx.showToast({ title: '登录成功', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }
      setTimeout(() => navigateAfterLogin(), 600);
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '登录失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 返回首页（游客模式）
  onBackHomeTap() {
    wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
  }
});
