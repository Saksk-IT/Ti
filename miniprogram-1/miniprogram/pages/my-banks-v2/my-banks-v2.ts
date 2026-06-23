import { api } from '../../utils/api';
import { resolveUploadUrl } from '../../utils/api-endpoints';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeMode } from '../../utils/theme';

type BankMeta = {
  id: number;
  name: string;
  description?: string;
  question_count?: number;
  is_public?: boolean | number;
  created_at?: string;
  created_at_fmt?: string;
  updated_at?: string;
  updated_at_fmt?: string;
  popularity_count?: number;
  source: 'created' | 'shared';
  owner_name?: string;
  owner_label?: string;
  owner_avatar_url?: string;
  cover_url?: string;
  has_cover?: boolean;
};

function formatDate(dateStr: any): string {
  const raw = String(dateStr || '').trim();
  if (!raw) return '-';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '-';
  try {
    return d.toLocaleDateString('zh-CN');
  } catch (e) {
    return '-';
  }
}

Page({
  data: {
    loading: false,
    inited: false,

    keyword: '',
    sourceIndex: 0,
    sourceLabels: ['全部', '我加入的', '我创建的'],
    sourceValues: ['all', 'shared', 'created'],
    banks: [] as BankMeta[],
    filteredBanks: [] as BankMeta[],

    createOpen: false,
    createName: '',
    createDesc: '',
    createError: '',
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

    this.loadBanks();
  },

  async loadBanks() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const [myRes, sharedRes]: any[] = await Promise.all([
        api.getMyBanks().catch(() => ({ banks: [] })),
        api.getSharedBanks().catch(() => ({ banks: [] }))
      ]);

      const createdList = Array.isArray(myRes?.banks) ? myRes.banks : [];
      const sharedList = Array.isArray(sharedRes?.banks) ? sharedRes.banks : [];

      const createdBanks: BankMeta[] = createdList.map((b: any) => {
        const coverUrl = resolveUploadUrl(b?.cover_image);
        const ownerLabel = String(b?.owner_nickname || '我').trim();
        const ownerAvatarUrl = resolveUploadUrl(b?.owner_avatar) || '/images/default-avatar.png';
        return {
          id: Number(b?.id || 0),
          name: String(b?.name || '未命名题库'),
          description: b?.description ? String(b.description) : '',
          question_count: Number(b?.question_count || 0) || 0,
          is_public: b?.is_public,
          created_at: b?.created_at || b?.updated_at,
          created_at_fmt: formatDate(b?.created_at || b?.updated_at),
          updated_at: b?.updated_at,
          updated_at_fmt: formatDate(b?.updated_at),
          popularity_count: Number(b?.public_use_count || b?.share_count || b?.use_count || 0) || 0,
          source: 'created' as const,
          owner_name: ownerLabel,
          owner_label: ownerLabel,
          owner_avatar_url: ownerAvatarUrl,
          cover_url: coverUrl,
          has_cover: !!coverUrl
        };
      }).filter((b: BankMeta) => Number.isFinite(b.id) && b.id > 0);

      const sharedBanks: BankMeta[] = sharedList.map((b: any) => {
        const coverUrl = resolveUploadUrl(b?.cover_image);
        const ownerLabel = String(b?.owner_nickname || b?.owner_name || '匿名用户').trim();
        const ownerAvatarUrl = resolveUploadUrl(b?.owner_avatar) || '/images/default-avatar.png';
        return {
          id: Number(b?.bank_id || b?.id || 0),
          name: String(b?.bank_name || b?.name || '未命名题库'),
          description: b?.description ? String(b.description) : '',
          question_count: Number(b?.question_count || 0) || 0,
          is_public: false,
          created_at: b?.created_at || b?.last_access_at,
          created_at_fmt: formatDate(b?.created_at || b?.last_access_at),
          updated_at: b?.last_access_at || b?.created_at,
          updated_at_fmt: formatDate(b?.last_access_at || b?.created_at),
          popularity_count: Number(b?.access_count || b?.share_count || 0) || 0,
          source: 'shared' as const,
          owner_name: ownerLabel,
          owner_label: ownerLabel,
          owner_avatar_url: ownerAvatarUrl,
          cover_url: coverUrl,
          has_cover: !!coverUrl
        };
      }).filter((b: BankMeta) => Number.isFinite(b.id) && b.id > 0);

      const byId = new Map<number, BankMeta>();
      [...sharedBanks, ...createdBanks].forEach((b) => {
        byId.set(b.id, b);
      });
      const banks = Array.from(byId.values());
      this.setData({ banks, inited: true }, () => this.applyFilter());
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '加载失败', icon: 'none' });
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

  onSourceChange(e: any) {
    const idx = Number(e?.detail?.value ?? 0) || 0;
    const max = (this.data.sourceLabels || []).length - 1;
    const sourceIndex = Math.max(0, Math.min(idx, max));
    if (sourceIndex === this.data.sourceIndex) return;
    this.setData({ sourceIndex }, () => this.applyFilter());
  },

  applyFilter() {
    const kw = (this.data.keyword || '').trim().toLowerCase();
    let out = (this.data.banks || []).slice();
    const sourceValues = this.data.sourceValues || ['all', 'shared', 'created'];
    const source = sourceValues[this.data.sourceIndex] || 'all';

    if (source === 'shared' || source === 'created') {
      out = out.filter((b) => b.source === source);
    }

    if (kw) {
      out = out.filter((b) => {
        const name = String(b.name || '').toLowerCase();
        const desc = String(b.description || '').toLowerCase();
        const owner = String(b.owner_name || '').toLowerCase();
        return name.includes(kw) || desc.includes(kw) || owner.includes(kw);
      });
    }

    out.sort((a, b) => {
      return String(b.updated_at || '').localeCompare(String(a.updated_at || '')) || (b.id - a.id);
    });

    this.setData({ filteredBanks: out });
  },

  onBankTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    safeNavigate(`/pages/bank-detail/bank-detail?id=${id}`, 'navigateTo');
  },

  onGoPublicBank() {
    safeNavigate('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
  },

  onGoCreateBank() {
    if (this.data.createOpen) return;
    this.setData({
      createOpen: true,
      createName: '',
      createDesc: '',
      createError: '',
      creating: false
    });
  },

  onCreateClose() {
    if (this.data.creating) return;
    this.setData({ createOpen: false });
  },

  onCreateSheetTap() {},

  onCreateNameInput(e: any) {
    const value = String(e?.detail?.value || '');
    this.setData({ createName: value, createError: '' });
  },

  onCreateDescInput(e: any) {
    const value = String(e?.detail?.value || '');
    this.setData({ createDesc: value, createError: '' });
  },

  async onCreateSubmit() {
    if (this.data.creating) return;

    const name = String(this.data.createName || '').trim();
    const description = String(this.data.createDesc || '').trim();

    if (!name) {
      const msg = '题库名称不能为空';
      this.setData({ createError: msg });
      wx.showToast({ title: msg, icon: 'none' });
      return;
    }
    if (name.length < 2 || name.length > 50) {
      const msg = '题库名称需要 2-50 个字符';
      this.setData({ createError: msg });
      wx.showToast({ title: msg, icon: 'none' });
      return;
    }
    if (description.length > 200) {
      const msg = '描述不能超过 200 个字符';
      this.setData({ createError: msg });
      wx.showToast({ title: msg, icon: 'none' });
      return;
    }

    this.setData({ creating: true, createError: '' });
    try {
      await api.createBank({ name, description });
      wx.showToast({ title: '创建成功', icon: 'success' });
      this.setData({
        createOpen: false,
        createName: '',
        createDesc: '',
        createError: '',
        creating: false
      });
      this.loadBanks();
    } catch (e: any) {
      const msg = (e && e.message) ? String(e.message) : '创建失败';
      this.setData({ creating: false, createError: msg });
      wx.showToast({ title: msg, icon: 'none' });
    }
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  }
});
