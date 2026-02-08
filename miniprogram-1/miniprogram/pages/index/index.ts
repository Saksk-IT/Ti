// index.ts
import { api, resolveUploadUrl } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager } from '../../utils/theme';
import { decorateAvatarUrl } from '../../utils/avatar';

function parseQuery(raw: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!raw) return out;
  const parts = raw.split('&');
  for (const part of parts) {
    const kv = part.split('=');
    const k = kv[0];
    const v = kv[1];
    if (!k) continue;
    out[decodeURIComponent(k)] = decodeURIComponent(v || '');
  }
  return out;
}

function parseCompactBindScene(scene: string): { sid: string; nonce: string } | null {
  const s = (scene || '').trim();
  // B + sid(16 hex) + nonce(8 hex)
  if (!/^B[0-9a-fA-F]{24}$/.test(s)) return null;
  const sid = s.slice(1, 17);
  const nonce = s.slice(17, 25);
  return { sid, nonce };
}

Page({
  data: {
    stats: {
      total: 0,
      favorites: 0,
      mistakes: 0
    },
    lastSession: null as any,
    loading: false,
    userInfo: null as any,
    isLoggedIn: false, // 是否已登录
    // 主题相关
    isDarkMode: false,
    themeClass: 'theme-light',
    themeStyle: 'dune' as any,
    themeStyleClass: '',
    themeMode: 'light' as any,
    // 页面进入动画
    pageVisible: false
  },

  onLoad(options: Record<string, any>) {
    // 初始化主题
    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}

    // 页面进入动画：延迟触发，防止白屏
    setTimeout(() => {
      this.setData({ pageVisible: true });
    }, 50);

    // 兼容后端生成二维码使用 index 作为落地页（避免 41030 invalid page）
    let sid = (options && options.sid ? String(options.sid) : '').trim();
    let nonce = (options && (options.nonce || options.n) ? String(options.nonce || options.n) : '').trim();
    const scene = (options && options.scene ? String(options.scene) : '').trim();
    if ((!sid || !nonce) && scene) {
      const decoded = decodeURIComponent(scene);
      const compactBind = parseCompactBindScene(decoded);
      if (compactBind) {
        wx.navigateTo({
          url: `/pages/web-bind/web-bind?sid=${encodeURIComponent(compactBind.sid)}&nonce=${encodeURIComponent(compactBind.nonce)}`
        });
        return;
      }
      const q = parseQuery(decoded);
      sid = (q.sid || '').trim();
      nonce = (q.n || q.nonce || '').trim();
    }

    if (sid && nonce) {
      wx.setStorageSync('pendingWebLogin', { sid, nonce, ts: Date.now() });
      const token = wx.getStorageSync('token');
      if (token) {
        wx.navigateTo({ url: `/pages/web-login/web-login?sid=${encodeURIComponent(sid)}&nonce=${encodeURIComponent(nonce)}` });
      } else {
        wx.redirectTo({ url: '/pages/login/login' });
      }
      return;
    }
  },

  onShow() {
    // 更新主题
    try {
      this.setData(themeManager.getPageData() as any);
    } catch (e) {}
    
    // 统一走鉴权&加载，避免 onLoad/onShow 重复触发导致并发请求
    this.checkAuthAndLoad();
  },

  // 检查认证并加载数据
  async checkAuthAndLoad() {
    const isLoggedIn = checkLogin();
    if (isLoggedIn) {
      const userInfo = wx.getStorageSync('userInfo');
      // 将相对路径的 avatar 转为完整 URL，确保 <image> 能正常加载
      if (userInfo && (userInfo.avatar || userInfo.avatar_url)) {
        const rawAvatar = userInfo.avatar || userInfo.avatar_url;
        const fullUrl = decorateAvatarUrl(resolveUploadUrl(rawAvatar));
        userInfo.avatar = fullUrl;
        userInfo.avatar_url = fullUrl;
      }
      this.setData({ userInfo, isLoggedIn: true });
    } else {
      this.setData({ isLoggedIn: false, userInfo: null });
    }
    // 无论是否登录都加载首页数据
    this.loadHome();
  },

  // 加载首页数据（统计 + 上次练习）
  async loadHome() {
    this.setData({ loading: true });
    try {
      const isLoggedIn = checkLogin();

      // 总题目数（无需登录）
      const countData = await api.getQuestionsCount({ subject: 'all' });
      const total = (countData && (countData as any).count) ? (countData as any).count : 0;

      let favorites = 0;
      let mistakes = 0;
      let lastSession = null;

      // 用户相关数据（需要登录）
      if (isLoggedIn) {
        try {
          const userCounts = await api.getUserCounts({ subject: 'all' });
          favorites = (userCounts && (userCounts as any).favorites) ? (userCounts as any).favorites : 0;
          mistakes = (userCounts && (userCounts as any).mistakes) ? (userCounts as any).mistakes : 0;

          // 上次练习（云端优先，本地兜底）
          const remote = await this.safeGetProgress('last_practice_session');
          const local = this.safeParseStorage(wx.getStorageSync('last_practice_session'));
          const merged = this.pickLatestSession(local, remote);

          // 如果云端数据更新，同步到本地存储
          if (remote && merged === remote) {
            try {
              wx.setStorageSync('last_practice_session', remote);
            } catch (e) {
              console.error('同步云端数据到本地失败:', e);
            }
          }

          lastSession = this.normalizeSession(merged);
        } catch (err: any) {
          console.error('加载用户数据失败:', err);
          // 如果是401错误，清除登录状态但不跳转
          const errorMsg = (err && err.message) || '';
          if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期') || errorMsg.includes('unauthorized')) {
            wx.removeStorageSync('token');
            wx.removeStorageSync('userInfo');
            this.setData({ isLoggedIn: false, userInfo: null });
          }
        }
      }

      this.setData({
        stats: { total, favorites, mistakes },
        lastSession,
        loading: false
      });
    } catch (err: any) {
      console.error('加载数据失败:', err);
      const errorMsg = (err && err.message) || '加载失败';
      wx.showToast({ title: errorMsg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async safeGetProgress(key: string): Promise<any | null> {
    if (!key) return null;
    try {
      return await api.getProgress(key);
    } catch (e) {
      return null;
    }
  },

  safeParseStorage(val: any): any | null {
    if (!val) return null;
    if (typeof val === 'string') {
      try {
        return JSON.parse(val);
      } catch (e) {
        return null;
      }
    }
    if (typeof val === 'object') return val;
    return null;
  },

  pickLatestSession(a: any, b: any): any | null {
    if (!a && !b) return null;
    if (a && !b) return a;
    if (!a && b) return b;
    const ta = Number(a && a.timestamp) || 0;
    const tb = Number(b && b.timestamp) || 0;
    return tb >= ta ? b : a;
  },

  normalizeSession(raw: any): any | null {
    if (!raw || typeof raw !== 'object') return null;

    // 支持两种来源：公共题库(subject) 和 个人题库(bank_id)
    const subject = (raw.subject || '').toString().trim();
    const bankId = raw.bank_id ? Number(raw.bank_id) : null;
    const sourceType = (raw.source_type || '').toString().trim();
    const sourceId = raw.source_id;
    const displayName = (raw.display_name || '').toString().trim();

    // 必须有 subject 或 bank_id 或 source_id
    if (!subject && !bankId && !sourceId) return null;

    const mode = (raw.mode || 'quiz').toString();
    const type = (raw.type || 'all').toString();
    const source = (raw.source || 'all').toString();
    const shuffleQuestions = raw.shuffle_questions === 1 || raw.shuffle_questions === '1' || raw.shuffle_questions === true;
    const shuffleOptions = raw.shuffle_options === 1 || raw.shuffle_options === '1' || raw.shuffle_options === true;
    const timestamp = Number(raw.timestamp) || 0;

    const modeText = mode === 'memo' ? '背题' : '刷题';
    const sourceText = source === 'favorites' ? '收藏' : source === 'mistakes' ? '错题' : '全部';
    const typeText = type === 'all' ? '全部题型' : type;
    const metaText = `${modeText} · ${sourceText} · ${typeText}`;

    return {
      subject,
      bankId,
      sourceType,
      sourceId,
      displayName,
      mode,
      type,
      source,
      shuffleQuestions,
      shuffleOptions,
      timestamp,
      timeText: this.formatTimestamp(timestamp),
      metaText
    };
  },

  formatTimestamp(ts: number): string {
    const t = Number(ts) || 0;
    if (!t) return '';
    try {
      const d = new Date(t);
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const mi = String(d.getMinutes()).padStart(2, '0');
      return `${mm}-${dd} ${hh}:${mi}`;
    } catch (e) {
      return '';
    }
  },

  onContinueTap() {
    // 未登录时提示登录
    if (!this.data.isLoggedIn) {
      wx.showModal({
        title: '提示',
        content: '登录后可查看练习记录',
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

    const s = this.data.lastSession;
    if (!s) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }

    const params: string[] = [];

    // 判断来源类型：个人题库 or 公共题库
    if (s.bankId || s.sourceType === 'bank') {
      const bankId = s.bankId || s.sourceId;
      if (!bankId) {
        wx.showToast({ title: '题库信息无效', icon: 'none' });
        return;
      }
      params.push(`bank_id=${encodeURIComponent(bankId)}`);
    } else if (s.subject) {
      params.push(`subject=${encodeURIComponent(s.subject)}`);
    } else if (s.sourceId) {
      // 兼容 source_type = 'public' 的情况
      params.push(`subject=${encodeURIComponent(s.sourceId)}`);
    } else {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }

    params.push(`mode=${encodeURIComponent(s.mode || 'quiz')}`);
    if (s.type && s.type !== 'all') params.push(`type=${encodeURIComponent(s.type)}`);
    if (s.source && s.source !== 'all') params.push(`source=${s.source}`);
    if (s.shuffleQuestions) params.push('shuffle_questions=1');
    if (s.shuffleOptions) params.push('shuffle_options=1');

    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  },

  // 跳转到登录页
  onGoLoginTap() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  onGoSubjectsTap() {
    wx.switchTab({ url: '/pages/subjects/subjects' });
  },

  onToggleThemeTap() {
    themeManager.toggleDark();
    this.setData(themeManager.getPageData() as any);
    wx.showToast({ title: `主题：${themeManager.getModeName()}`, icon: 'none' });
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadHome().finally(() => wx.stopPullDownRefresh());
  }
});
