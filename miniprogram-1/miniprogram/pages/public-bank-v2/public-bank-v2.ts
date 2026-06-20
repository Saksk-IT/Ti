import { api } from '../../utils/api';
import { resolveUploadUrl } from '../../utils/api-endpoints';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeMode } from '../../utils/theme';

type BankType = 'system' | 'user';
type PlazaBank = {
  id: number;
  name: string;
  description?: string;
  question_count?: number;
  use_count?: number;
  allow_copy?: number;
  is_shared?: number | boolean;
  cover_image?: string | null;
  public_at?: string;
  created_at?: string;
  owner_nickname?: string;
  owner_avatar?: string;
  join_mode?: string;
  relation?: { is_joined?: boolean; joined_via?: string };
  bank_type: BankType;
};

type PlazaBankView = {
  key: string;
  id: number;
  name: string;
  description: string;
  question_count: number;
  use_count: number;
  allow_copy: boolean;
  cover_url: string;
  has_cover: boolean;
  owner_label: string;
  created_label: string;
  bank_type: BankType;
  type_label: string;
  is_shared: boolean;
  is_joined: boolean;
};

function formatDateLabel(input: any): string {
  const raw = String(input || '').trim();
  if (!raw) return '-';
  // iOS 对 YYYY-MM-DD HH:mm:ss 兼容较差，统一替换为 YYYY/MM/DD
  const normalized = raw.replace(/-/g, '/');
  const d = new Date(normalized);
  if (Number.isFinite(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
  const m = normalized.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  return raw;
}

Page({
  data: {
    loading: false,
    inited: false,

    banks: [] as PlazaBankView[],
    keyword: '',

    sortIndex: 0,
    sortLabels: ['最近', '最受欢迎', '题目最多'],
    sortValues: ['newest', 'popular', 'questions'],

    page: 1,
    perPage: 20,
    total: 0,
    shownTotal: 0,
    hasMore: true
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    if (!this.data.inited && !this.data.loading) {
      this.loadBanks(true);
    }
  },

  async loadBanks(reset = false) {
    // reset（筛选/搜索/排序）时允许并发请求：用序号丢弃旧响应，避免“闪烁/回跳”。
    if (this.data.loading && !reset) return;
    if (!reset && !this.data.hasMore) return;

    const that: any = this as any;
    that._bankReqSeq = Number(that._bankReqSeq || 0) + 1;
    const reqSeq = that._bankReqSeq;

    const nextPage = reset ? 1 : Number(this.data.page || 1) || 1;
    this.setData({ loading: true });
    try {
      const sortValues = this.data.sortValues || ['newest', 'popular', 'questions'];
      const sort = (sortValues[this.data.sortIndex] || 'newest') as string;

      const params: any = {
        page: nextPage,
        per_page: this.data.perPage || 20,
        sort
      };
      const keyword = String(this.data.keyword || '').trim();
      if (keyword) params.keyword = keyword;

      const res = await api.getPublicBanks(params);
      if (reqSeq !== that._bankReqSeq) return;
      const resObj = (res && typeof res === 'object' ? res : {}) as Record<string, unknown>;
      const rawBanks: PlazaBank[] = Array.isArray(resObj.banks) ? (resObj.banks as PlazaBank[]) : [];
      const total = Number(resObj.total || 0) || 0;

      const mapped: PlazaBankView[] = (rawBanks || [])
        .map((b: any) => {
          const bankType: BankType = b?.bank_type === 'system' ? 'system' : 'user';
          const id = Number(b?.id || 0) || 0;
          const name = String(b?.name || '').trim();
          const description = String(b?.description || '').trim();
          const questionCount = Number(b?.question_count || 0) || 0;
          const useCount = Number(b?.use_count || 0) || 0;
          const allowCopy = !!b?.allow_copy;
          const isShared = !!b?.is_shared;
          const coverUrl = resolveUploadUrl(b?.cover_image);
          const isJoined = !!b?.relation?.is_joined;
          const ownerLabel = String(b?.owner_nickname || (bankType === 'system' ? '系统管理员' : '匿名')).trim();
          const createdLabel = formatDateLabel(b?.created_at || b?.public_at);
          return {
            key: `${bankType}_${id}`,
            id,
            name,
            description,
            question_count: questionCount,
            use_count: useCount,
            allow_copy: allowCopy,
            cover_url: coverUrl,
            has_cover: !!coverUrl,
            owner_label: ownerLabel,
            created_label: createdLabel,
            bank_type: bankType,
            type_label: bankType === 'system' ? '系统题库' : '用户',
            is_shared: isShared,
            is_joined: isJoined
          };
        })
        .filter((b) => b.id > 0 && !!b.name);

      let merged: PlazaBankView[] = [];
      if (reset) {
        merged = mapped;
      } else {
        const existing = (this.data.banks || []) as PlazaBankView[];
        const seen = new Set(existing.map((x) => x.key));
        merged = existing.concat(mapped.filter((x) => !seen.has(x.key)));
      }

      const shownTotal = merged.length;
      const hasMore = shownTotal < total;

      this.setData({
        inited: true,
        banks: merged,
        total,
        shownTotal,
        hasMore,
        page: nextPage + 1
      });
    } catch (e: any) {
      if (reqSeq !== that._bankReqSeq) return;
      if (reset) {
        this.setData({ banks: [], total: 0, shownTotal: 0, hasMore: false, page: 1 });
      }
      wx.showToast({ title: (e && e.message) || '加载失败', icon: 'none' });
    } finally {
      if (reqSeq !== that._bankReqSeq) return;
      this.setData({ loading: false });
    }
  },

  scheduleReload() {
    const that: any = this as any;
    try {
      if (that._kwTimer) clearTimeout(that._kwTimer);
    } catch (e) {}
    that._kwTimer = setTimeout(() => {
      that._kwTimer = null;
      that.setData({ page: 1, hasMore: true }, () => that.loadBanks(true));
    }, 250);
  },

  onKeywordInput(e: any) {
    const keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
    this.setData({ keyword }, () => this.scheduleReload());
  },

  onClearKeyword() {
    this.setData({ keyword: '' }, () => this.loadBanks(true));
  },

  onSortTap(e: any) {
    const idx = Number(e?.currentTarget?.dataset?.index ?? 0) || 0;
    const max = (this.data.sortLabels || []).length - 1;
    const sortIndex = Math.max(0, Math.min(idx, max));
    if (sortIndex === this.data.sortIndex) return;
    this.setData({ sortIndex, page: 1, hasMore: true }, () => this.loadBanks(true));
  },

  onSortChange(e: any) {
    const idx = Number(e?.detail?.value ?? 0) || 0;
    const max = (this.data.sortLabels || []).length - 1;
    const sortIndex = Math.max(0, Math.min(idx, max));
    this.setData({ sortIndex, page: 1, hasMore: true }, () => this.loadBanks(true));
  },

  onScrollToLower() {
    if (this.data.loading) return;
    if (!this.data.hasMore) return;
    this.loadBanks(false);
  },

  onBankTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    const bankType = String(e?.currentTarget?.dataset?.bankType || '').trim();
    const name = e?.currentTarget?.dataset?.name;

    if (!Number.isFinite(id) || id <= 0) return;

    if (bankType === 'system') {
      const params: string[] = [];
      params.push(`id=${id}`);
      if (name) params.push(`subject=${encodeURIComponent(String(name))}`);
      safeNavigate(`/pages/subject-detail-v2/subject-detail-v2?${params.join('&')}`, 'navigateTo');
      return;
    }

    safeNavigate(`/pages/bank-join/bank-join?source_type=user&bank_id=${encodeURIComponent(String(id))}`, 'navigateTo');
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  }
});
