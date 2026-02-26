import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type TabKey = 'public' | 'bank';
type SubjectMeta = { id: number; name: string; question_count: number };

type BankCard = {
  id: number;
  name: string;
  question_count: number;
  sort_key?: string;
};

const KEY_TAB = 'favorites_bank_tab';
const KEY_KW = 'favorites_bank_kw';

function normalizeTab(input: any): TabKey {
  const s = String(input || '').trim().toLowerCase();
  return s === 'bank' ? 'bank' : 'public';
}

function getStoredString(key: string, fallback: string): string {
  try {
    const raw = wx.getStorageSync(key);
    const s = String(raw || '').trim();
    return s ? s : fallback;
  } catch (e) {
    return fallback;
  }
}

function setStoredString(key: string, value: string): void {
  try {
    wx.setStorageSync(key, String(value || ''));
  } catch (e) {}
}

function normalizeSubject(raw: any): SubjectMeta | null {
  const id = Number(raw?.id || 0);
  const name = String(raw?.name || '').trim();
  if (!Number.isFinite(id) || id <= 0 || !name) return null;
  return { id, name, question_count: Number(raw?.question_count || 0) || 0 };
}

function normalizeBank(raw: any): BankCard | null {
  const isShared = raw && raw.bank_id != null;
  const id = Number(isShared ? raw.bank_id : raw?.id || 0);
  const name = String(isShared ? raw.bank_name : raw?.name || '').trim();
  if (!Number.isFinite(id) || id <= 0 || !name) return null;
  const question_count = Number(raw?.question_count || 0) || 0;
  const sort_key = String(isShared ? raw?.last_access_at : raw?.updated_at || '').trim();
  return { id, name, question_count, sort_key };
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,

    tab: 'public' as TabKey,
    keyword: '',

    subjects: [] as SubjectMeta[],
    filteredSubjects: [] as SubjectMeta[],

    banks: [] as BankCard[],
    filteredBanks: [] as BankCard[],

    publicTotal: 0,
    bankTotal: 0,
    currentTotal: 0,
    shownTotal: 0
  },

  onLoad(options: any) {
    const storedTab = normalizeTab(getStoredString(KEY_TAB, 'public'));
    const storedKw = getStoredString(KEY_KW, '');
    const tab = normalizeTab(options?.tab || storedTab);
    const keyword = options?.keyword ? String(options.keyword) : storedKw;
    this.setData({ tab, keyword: keyword || '' });
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
      this.bootstrap();
      return;
    }

    this.applyFilter();
  },

  async bootstrap() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const [meta, myBanksRes, sharedBanksRes] = await Promise.all([
        api.getSubjectsMeta().catch(() => ({ subjects: [], quiz_count: 0 })),
        api.getMyBanks().catch(() => ({ banks: [] })),
        api.getSharedBanks().catch(() => ({ banks: [] }))
      ]);

      const metaObj = (meta && typeof meta === 'object' ? meta : {}) as Record<string, unknown>;
      const subjectsRaw = Array.isArray(metaObj.subjects) ? metaObj.subjects : [];
      const subjects: SubjectMeta[] = subjectsRaw.map(normalizeSubject).filter(Boolean) as SubjectMeta[];
      subjects.sort((a, b) => a.id - b.id);

      const map = new Map<number, BankCard>();
      const myBanksObj = (myBanksRes && typeof myBanksRes === 'object' ? myBanksRes : {}) as Record<string, unknown>;
      const sharedBanksObj = (sharedBanksRes && typeof sharedBanksRes === 'object' ? sharedBanksRes : {}) as Record<string, unknown>;
      const myBanksRaw = Array.isArray(myBanksObj.banks) ? myBanksObj.banks : [];
      const sharedBanksRaw = Array.isArray(sharedBanksObj.banks) ? sharedBanksObj.banks : [];

      for (const b of myBanksRaw) {
        const item = normalizeBank(b);
        if (!item) continue;
        map.set(item.id, item);
      }

      for (const b of sharedBanksRaw) {
        const item = normalizeBank(b);
        if (!item) continue;
        if (!map.has(item.id)) map.set(item.id, item);
      }

      const banks = Array.from(map.values()).sort(
        (a, b) => String(b.sort_key || '').localeCompare(String(a.sort_key || '')) || (b.id - a.id)
      );

      this.setData(
        {
          inited: true,
          subjects,
          banks,
          publicTotal: subjects.length,
          bankTotal: banks.length
        },
        () => this.applyFilter()
      );
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
      try {
        wx.stopPullDownRefresh();
      } catch (e) {}
    }
  },

  onPullDownRefresh() {
    this.bootstrap();
  },

  onTabTap(e: any) {
    const tab = normalizeTab(e?.currentTarget?.dataset?.tab || 'public');
    if (tab === this.data.tab) return;
    this.setData({ tab }, () => this.applyFilter());
    setStoredString(KEY_TAB, tab);
  },

  onReviewTabTap(e: any) {
    const kind = String(e?.currentTarget?.dataset?.kind || '').trim();
    if (kind === 'mistakes') {
      safeNavigate('/pages/mistakes-v2/mistakes-v2', 'redirectTo');
      return;
    }
    if (kind === 'tags') {
      safeNavigate('/pages/tags-v2/tags-v2', 'redirectTo');
      return;
    }
    safeNavigate('/pages/favorites-v2/favorites-v2', 'redirectTo');
  },

  onKeywordInput(e: any) {
    const keyword = String(e?.detail?.value || '');
    this.setData({ keyword }, () => this.applyFilter());
    setStoredString(KEY_KW, keyword);
  },

  onClearKeyword() {
    this.setData({ keyword: '' }, () => this.applyFilter());
    setStoredString(KEY_KW, '');
  },

  applyFilter() {
    const kw = String(this.data.keyword || '').trim().toLowerCase();
    const subjects = Array.isArray(this.data.subjects) ? this.data.subjects : [];
    const banks = Array.isArray(this.data.banks) ? this.data.banks : [];

    let filteredSubjects = subjects.slice();
    let filteredBanks = banks.slice();

    if (kw) {
      filteredSubjects = filteredSubjects.filter((s) => String(s.name || '').toLowerCase().includes(kw));
      filteredBanks = filteredBanks.filter((b) => String(b.name || '').toLowerCase().includes(kw));
    }

    const currentTotal = this.data.tab === 'bank' ? banks.length : subjects.length;
    const shownTotal = this.data.tab === 'bank' ? filteredBanks.length : filteredSubjects.length;

    this.setData({ filteredSubjects, filteredBanks, currentTotal, shownTotal });
  },

  onPublicBankTap(e: any) {
    const name = String(e?.currentTarget?.dataset?.name || '').trim();
    if (!name) return;
    const url = `/pages/review-center-v2/review-center-v2?kind=favorites&subject=${encodeURIComponent(name)}`;
    safeNavigate(url, 'navigateTo');
  },

  onBankTap(e: any) {
    const id = Number(e?.currentTarget?.dataset?.id || 0);
    if (!Number.isFinite(id) || id <= 0) return;
    const url = `/pages/review-center-v2/review-center-v2?kind=favorites&bank_id=${encodeURIComponent(String(id))}`;
    safeNavigate(url, 'navigateTo');
  },

  onHamburgerTap() {
    this.setData({ drawerOpen: true });
  },

  onDrawerClose() {
    this.setData({ drawerOpen: false });
  },

  onDrawerNavigate(e: any) {
    const url = e?.detail?.url;
    const navType = e?.detail?.navType;
    this.setData({ drawerOpen: false });
    if (!url) return;
    safeNavigate(url, navType);
  },

  async onDrawerSelectStyle(e: any) {
    const style = (e?.detail?.style || 'default') as ThemeStyle;
    themeManager.setStyle(style);
    this.setData(themeManager.getPageData());
    this.setData({ drawerOpen: false });
    await syncUserSettingsToServer();
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  }
});
