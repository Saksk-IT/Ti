import { api } from '../../utils/api';
import { resolveUploadUrl } from '../../utils/api-endpoints';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { restartTabPageTransition } from '../../utils/tab-transition';
import { themeManager, ThemeMode } from '../../utils/theme';

type BankMeta = {
  key: string;
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
  source: 'created' | 'public' | 'shared';
  relation?: 'created' | 'public' | 'shared' | 'both';
  source_type?: 'user' | 'system';
  source_label?: string;
  owner_name?: string;
  owner_label?: string;
  owner_avatar_url?: string;
  cover_url?: string;
  has_cover?: boolean;
  detail_path?: string;
};

function formatDate(dateStr: any): string {
  const raw = String(dateStr || '').trim();
  if (!raw) return '-';
  const normalized = raw.replace(/-/g, '/');
  const d = new Date(normalized);
  if (Number.isFinite(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }
  const m = normalized.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})/);
  if (m) return `${m[1]}-${m[2]}`;
  return raw;
}

async function fetchAllOverviewItems(): Promise<any[]> {
  const perPage = 50;
  let page = 1;
  let total = 0;
  let items: any[] = [];
  let keepGoing = true;

  while (keepGoing) {
    const res: any = await api.getMyBankOverview({ scope: 'all', page, per_page: perPage });
    const pageItems = Array.isArray(res?.items) ? res.items : [];
    total = Number(res?.total || pageItems.length || 0) || 0;
    items = [...items, ...pageItems];
    page += 1;
    keepGoing = pageItems.length > 0 && items.length < total;
  }

  return items;
}

function normalizeSource(item: any): 'created' | 'public' | 'shared' {
  if (String(item?.kind || '') === 'created') return 'created';
  const relation = String(item?.relation || '').toLowerCase();
  if (relation === 'shared') return 'shared';
  if (relation === 'both') return 'shared';
  return 'public';
}

function normalizeRelation(item: any): 'created' | 'public' | 'shared' | 'both' {
  if (String(item?.kind || '') === 'created') return 'created';
  const relation = String(item?.relation || '').toLowerCase();
  if (relation === 'shared' || relation === 'both') return relation;
  return 'public';
}

function sourceLabelFor(item: any, source: 'created' | 'public' | 'shared', relation: 'created' | 'public' | 'shared' | 'both'): string {
  if (source === 'created') {
    const visibility = String(item?.visibility_label || '').trim();
    return visibility || (item?.is_public ? '公开' : '私密');
  }
  if (relation === 'both') return '公开+分享';
  return source === 'shared' ? '分享加入' : '公开加入';
}

function detailPathFor(
  id: number,
  source: 'created' | 'public' | 'shared',
  relation: 'created' | 'public' | 'shared' | 'both',
  sourceType: 'user' | 'system'
): string {
  if (sourceType === 'system') {
    const params = [`id=${encodeURIComponent(String(id))}`];
    if (source !== 'created') {
      params.push(`source_type=${encodeURIComponent('system')}`);
      params.push(`source=${encodeURIComponent(source)}`);
      params.push(`relation=${encodeURIComponent(relation)}`);
    }
    return `/pages/subject-detail-v2/subject-detail-v2?${params.join('&')}`;
  }
  const params = [`id=${encodeURIComponent(String(id))}`];
  if (source !== 'created') {
    params.push(`source_type=${encodeURIComponent(sourceType)}`);
    params.push(`source=${encodeURIComponent(source)}`);
    params.push(`relation=${encodeURIComponent(relation)}`);
  }
  return `/pages/bank-detail/bank-detail?${params.join('&')}`;
}

function overviewItemToBank(item: any): BankMeta | null {
  const id = Number(item?.id || 0);
  if (!Number.isFinite(id) || id <= 0) return null;

  const source = normalizeSource(item);
  const relation = normalizeRelation(item);
  const sourceType = String(item?.source_type || 'user').toLowerCase() === 'system' ? 'system' : 'user';
  const coverUrl = resolveUploadUrl(item?.cover_image);
  const ownerLabel = String(item?.owner_label || (source === 'created' ? '我创建的题库' : '匿名用户')).trim();
  const ownerAvatarUrl = resolveUploadUrl(item?.owner_avatar) || '/images/default-avatar.png';
  const timeValue = item?.updated_at || item?.last_joined_at || item?.last_activity_at;
  const isPublic = source === 'created' && String(item?.visibility_label || '') === '公开';

  return {
    key: `${sourceType}-${source}-${id}`,
    id,
    name: String(item?.name || '未命名题库'),
    description: item?.description ? String(item.description) : '',
    question_count: Number(item?.question_count || 0) || 0,
    is_public: isPublic,
    created_at: timeValue,
    created_at_fmt: formatDate(timeValue),
    updated_at: timeValue,
    updated_at_fmt: formatDate(timeValue),
    popularity_count: Number(item?.participants_total || item?.answer_users_7d || 0) || 0,
    source,
    relation,
    source_type: sourceType,
    source_label: sourceLabelFor(item, source, relation),
    owner_name: ownerLabel,
    owner_label: ownerLabel,
    owner_avatar_url: ownerAvatarUrl,
    cover_url: coverUrl,
    has_cover: !!coverUrl,
    detail_path: detailPathFor(id, source, relation, sourceType)
  };
}

Page({
  data: {
    loading: false,
    inited: false,

    keyword: '',
    sourceIndex: 0,
    sourceLabels: ['全部', '我创建的', '公开加入', '分享加入'],
    sourceValues: ['all', 'created', 'public', 'shared'],
    banks: [] as BankMeta[],
    filteredBanks: [] as BankMeta[],

    createOpen: false,
    createName: '',
    createDesc: '',
    createError: '',
    creating: false,
    tabPageTransitionClass: ''
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    restartTabPageTransition(this);
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    this.loadBanks();
  },

  async loadBanks() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const overviewItems = await fetchAllOverviewItems();
      const banks = overviewItems
        .map((item: any) => overviewItemToBank(item))
        .filter((bank: BankMeta | null): bank is BankMeta => !!bank);
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
    const sourceValues = this.data.sourceValues || ['all', 'created', 'public', 'shared'];
    const source = sourceValues[this.data.sourceIndex] || 'all';

    if (source === 'created') {
      out = out.filter((b) => b.source === 'created');
    } else if (source === 'public') {
      out = out.filter((b) => b.source === 'public' || b.relation === 'both');
    } else if (source === 'shared') {
      out = out.filter((b) => b.source === 'shared' || b.relation === 'both');
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
    const key = String(e?.currentTarget?.dataset?.key || '');
    const bank = (this.data.banks || []).find((item) => (key && item.key === key) || item.id === id);
    if (!bank && (!Number.isFinite(id) || id <= 0)) return;
    safeNavigate(bank?.detail_path || `/pages/bank-detail/bank-detail?id=${id}`, 'navigateTo');
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
