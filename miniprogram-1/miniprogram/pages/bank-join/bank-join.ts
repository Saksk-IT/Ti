import { api } from '../../utils/api';
import { resolveUploadUrl } from '../../utils/api-endpoints';
import { checkLogin, wechatLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';

type JoinMode = 'public' | 'token' | 'code';
type PublicSourceType = 'system' | 'user';

type PublicBankCardView = {
  id: number;
  sourceType: PublicSourceType;
  name: string;
  description: string;
  coverUrl: string;
  hasCover: boolean;
  sourceLabel: string;
  ownerLabel: string;
  boardLabel: string;
  questionCount: number;
  participantsTotal: number;
  activeUsers7d: number;
  publishedAt: string;
  lastActivityAt: string;
  joinMode: string;
  joinModeLabel: string;
  joinNote: string;
  allowCopy: boolean;
  isOwner: boolean;
  isJoined: boolean;
};

const PENDING_MINI_REDIRECT_KEY = 'pendingMiniRedirect';

function setPendingMiniRedirect(url: string): void {
  try {
    const s = String(url || '').trim();
    if (!s) return;
    wx.setStorageSync(PENDING_MINI_REDIRECT_KEY, s);
  } catch (e) {}
}

function clearPendingMiniRedirect(): void {
  try {
    wx.removeStorageSync(PENDING_MINI_REDIRECT_KEY);
  } catch (e) {}
}

function normalizeTokenFromShareLink(input: any): string {
  const s = String(input || '').trim();
  if (!s) return '';
  if (/^[a-z0-9]{16,}$/i.test(s) && !s.includes('://') && !s.includes('?')) return s;

  const tokenMatch = s.match(/[?&]token=([^&#]+)/i);
  if (tokenMatch && tokenMatch[1]) {
    try {
      return decodeURIComponent(tokenMatch[1]);
    } catch {
      return tokenMatch[1];
    }
  }
  return '';
}

function normalizeSourceType(input: any): PublicSourceType {
  return String(input || '').trim() === 'system' ? 'system' : 'user';
}

function joinedBankDetailUrl(bankId: number, source: 'public' | 'shared'): string {
  const id = encodeURIComponent(String(bankId));
  return `/pages/bank-detail/bank-detail?id=${id}&source_type=user&source=${source}&relation=${source}`;
}

function joinLabel(mode: any): string {
  const value = String(mode || 'free').trim().toLowerCase();
  if (value === 'member') return '会员加入';
  if (value === 'paid') return '付费加入';
  if (value === 'approval') return '申请加入';
  return '免费加入';
}

function formatText(input: any, fallback = '-'): string {
  const raw = String(input || '').trim();
  return raw || fallback;
}

function buildPublicBankCard(raw: any, sourceType: PublicSourceType): PublicBankCardView {
  const coverUrl = resolveUploadUrl(raw?.cover_image);
  const joinMode = String(raw?.join_mode || 'free').trim().toLowerCase() || 'free';
  const isJoined = !!raw?.relation?.is_joined;
  return {
    id: Number(raw?.id || 0) || 0,
    sourceType,
    name: formatText(raw?.name, '未命名题库'),
    description: formatText(raw?.description, '暂无题库简介'),
    coverUrl,
    hasCover: !!coverUrl,
    sourceLabel: formatText(raw?.source_label, sourceType === 'system' ? '系统题库' : '用户公开'),
    ownerLabel: formatText(raw?.owner_label, sourceType === 'system' ? '系统题库' : '匿名用户'),
    boardLabel: formatText(raw?.board?.name, '未分板块'),
    questionCount: Number(raw?.question_count || 0) || 0,
    participantsTotal: Number(raw?.participants_total || 0) || 0,
    activeUsers7d: Number(raw?.answer_users_7d || 0) || 0,
    publishedAt: formatText(raw?.published_at),
    lastActivityAt: formatText(raw?.last_activity_at),
    joinMode,
    joinModeLabel: joinLabel(joinMode),
    joinNote: formatText(
      raw?.join_note,
      joinMode === 'free' ? '确认加入后，该题库会进入“我的题库”。' : '当前加入方式暂未在小程序开放。'
    ),
    allowCopy: !!raw?.allow_copy,
    isOwner: !!raw?.is_owner,
    isJoined
  };
}

Page({
  data: {
    mode: 'code' as JoinMode,
    token: '',
    shareCode: '',
    sourceType: 'user' as PublicSourceType,
    bankId: 0,
    card: null as PublicBankCardView | null,
    loading: false,
    joining: false,
    errorMsg: ''
  },

  async onLoad(options: any) {
    const sourceType = normalizeSourceType(options?.source_type || options?.sourceType || options?.type);
    const bankId = Number(options?.bank_id || options?.bankId || options?.id || 0);
    if (Number.isFinite(bankId) && bankId > 0) {
      this.setData({ mode: 'public', sourceType, bankId });
      await this.loadPublicCard(sourceType, bankId);
      return;
    }

    const rawToken = options?.token || options?.share_token || '';
    let token = normalizeTokenFromShareLink(rawToken);
    // 兼容：扫码/二维码场景可能走 scene 参数
    if (!token) {
      const scene = String(options?.scene || '').trim();
      if (scene) {
        try {
          token = normalizeTokenFromShareLink(decodeURIComponent(scene)) || normalizeTokenFromShareLink(scene);
        } catch {
          token = normalizeTokenFromShareLink(scene);
        }
      }
    }
    const shareCode = String(options?.share_code || options?.code || '').trim().toUpperCase();

    const mode: JoinMode = token ? 'token' : 'code';
    this.setData({ mode, token, shareCode });

    // 打开分享即加入：token / share_code 都直接尝试加入，不再走“预览/确认”
    if (token) {
      await this.autoJoinByToken(token);
      return;
    }
    if (shareCode && shareCode.length === 6) {
      await this.joinByCode(shareCode);
    }
  },

  async loadPublicCard(sourceType: PublicSourceType, bankId: number) {
    if (this.data.loading) return;
    this.setData({ loading: true, errorMsg: '' });
    try {
      const raw: any = await api.getPublicBankCard(sourceType, bankId);
      const card = buildPublicBankCard(raw, sourceType);
      if (!card.id) throw new Error('题库信息异常');
      this.setData({ card, sourceType, bankId: card.id });
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加载失败';
      this.setData({ errorMsg: msg, card: null });
    } finally {
      this.setData({ loading: false });
    }
  },

  onShareCodeInput(e: any) {
    const v = String(e?.detail?.value || '').trim().toUpperCase();
    this.setData({ shareCode: v, errorMsg: '' });
  },

  async ensureLoggedIn(nextUrl: string): Promise<boolean> {
    if (checkLogin()) return true;
    setPendingMiniRedirect(nextUrl);
    try {
      const result = await wechatLogin();
      if (result === 'success') return true;
      if (result === 'need_bind') {
        wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
        return false;
      }
    } catch (e) {
      wx.redirectTo({ url: '/pages/login/login' });
      return false;
    }
    wx.redirectTo({ url: '/pages/login/login' });
    return false;
  },

  async onConfirmPublicJoin() {
    if (this.data.joining) return;
    const sourceType = normalizeSourceType(this.data.sourceType);
    const bankId = Number(this.data.bankId || 0);
    const card = this.data.card;
    if (!bankId || !card) return;

    if (card.isOwner || card.isJoined) {
      this.goPublicPractice();
      return;
    }

    if (card.joinMode !== 'free') {
      wx.showToast({ title: `${card.joinModeLabel}暂未开放`, icon: 'none' });
      return;
    }

    const nextUrl = `/pages/bank-join/bank-join?source_type=${encodeURIComponent(sourceType)}&bank_id=${encodeURIComponent(String(bankId))}`;
    const ok = await this.ensureLoggedIn(nextUrl);
    if (!ok) return;

    this.setData({ joining: true, errorMsg: '' });
    wx.showLoading({ title: '加入中...' });
    try {
      await api.joinPublicBank(sourceType, bankId);
      wx.showToast({ title: '已加入', icon: 'success' });
      await this.loadPublicCard(sourceType, bankId);
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加入失败';
      this.setData({ errorMsg: msg });
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      wx.hideLoading();
      this.setData({ joining: false });
    }
  },

  goPublicPractice() {
    const sourceType = normalizeSourceType(this.data.sourceType);
    const bankId = Number(this.data.bankId || 0);
    const card = this.data.card;
    if (!bankId) return;
    if (sourceType === 'system') {
      const params = [`id=${encodeURIComponent(String(bankId))}`];
      if (card?.name) params.push(`subject=${encodeURIComponent(card.name)}`);
      safeNavigate(`/pages/subject-detail-v2/subject-detail-v2?${params.join('&')}`, 'redirectTo');
      return;
    }
    safeNavigate(joinedBankDetailUrl(bankId, 'public'), 'redirectTo');
  },

  onPublicRetry() {
    const sourceType = normalizeSourceType(this.data.sourceType);
    const bankId = Number(this.data.bankId || 0);
    if (!bankId) return;
    this.loadPublicCard(sourceType, bankId);
  },

  async autoJoinByToken(token: string) {
    const t = String(token || '').trim();
    if (!t) return;
    if (this.data.loading) return;

    const nextUrl = `/pages/bank-join/bank-join?token=${encodeURIComponent(t)}`;
    const ok = await this.ensureLoggedIn(nextUrl);
    if (!ok) return;

    this.setData({ loading: true, errorMsg: '' });
    wx.showLoading({ title: '加入中...' });
    try {
      const res: any = await api.joinBankByToken(t);
      const bankId = Number(res?.bank_id || 0);
      const bankName = String(res?.bank_name || '').trim();
      wx.showToast({ title: bankName ? `已加入「${bankName}」` : '已加入', icon: 'success' });
      clearPendingMiniRedirect();
      if (bankId > 0) {
        safeNavigate(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
      } else {
        safeNavigate('/pages/my-banks-v2/my-banks-v2', 'switchTab');
      }
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加入失败';
      this.setData({ errorMsg: msg });
    } finally {
      wx.hideLoading();
      this.setData({ loading: false });
    }
  },

  async joinByCode(code: string) {
    const c = String(code || '').trim().toUpperCase();
    if (!c || c.length !== 6) {
      wx.showToast({ title: '请输入6位分享码', icon: 'none' });
      return;
    }
    if (this.data.loading) return;

    const nextUrl = `/pages/bank-join/bank-join?share_code=${encodeURIComponent(c)}`;
    const ok = await this.ensureLoggedIn(nextUrl);
    if (!ok) return;

    this.setData({ loading: true, errorMsg: '' });
    wx.showLoading({ title: '加入中...' });
    try {
      const res: any = await api.joinBankByCode(c);
      const bankId = Number(res?.bank_id || 0);
      const bankName = String(res?.bank_name || '').trim();
      wx.showToast({ title: bankName ? `已加入「${bankName}」` : '已加入', icon: 'success' });
      clearPendingMiniRedirect();
      if (bankId > 0) {
        safeNavigate(joinedBankDetailUrl(bankId, 'shared'), 'redirectTo');
      } else {
        safeNavigate('/pages/my-banks-v2/my-banks-v2', 'switchTab');
      }
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '加入失败';
      this.setData({ errorMsg: msg });
    } finally {
      wx.hideLoading();
      this.setData({ loading: false });
    }
  },

  onJoinByCodeTap() {
    const code = String(this.data.shareCode || '').trim().toUpperCase();
    this.joinByCode(code);
  },

  onRetry() {
    if (this.data.mode === 'public') {
      this.onPublicRetry();
      return;
    }
    if (this.data.mode === 'token') {
      this.autoJoinByToken(String(this.data.token || ''));
      return;
    }
    this.joinByCode(String(this.data.shareCode || ''));
  },

  onSwitchToCode() {
    this.setData({ mode: 'code', token: '', errorMsg: '' });
  },

  onCancel() {
    // 分享打开的页面通常是页面栈第一个，无法 navigateBack，直接跳首页
    const pages = getCurrentPages();
    if (pages.length <= 1) {
      safeNavigate('/pages/hub-v2/hub-v2', 'switchTab');
      return;
    }
    wx.navigateBack({
      delta: 1,
      fail: () => {
        safeNavigate('/pages/hub-v2/hub-v2', 'switchTab');
      }
    });
  }
});
