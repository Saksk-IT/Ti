import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type NotiRaw = {
  id: number;
  title: string;
  content: string;
  n_type?: string;
  priority?: number;
  created_at?: string;
  is_read?: number | boolean;
};

type NotiVM = {
  id: number;
  title: string;
  content: string;
  typeKey: string;
  typeLabel: string;
  priority: number;
  createdAt: string;
  timeText: string;
  timeValue: number;
  isRead: boolean;
  snippet: string;
};

type TypeFacetItem = { type: string; label: string; count: number; color: string };
type TypeFacets = { total: number; items: TypeFacetItem[] };
type ReadGroup = { type: string; label: string; count: number; items: Array<NotiVM & { expanded: boolean }> };

const TYPE_ORDER = ['announcement', 'reminder', 'warning', 'info'];
const TYPE_LABEL: Record<string, string> = {
  info: '信息',
  announcement: '公告',
  reminder: '提醒',
  warning: '警告'
};

function toInt(v: any): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

function normalizeType(t: any): string {
  const raw = (t || 'info').toString().trim().toLowerCase();
  return TYPE_LABEL[raw] ? raw : 'info';
}

function typeDotColor(type: string): string {
  const t = normalizeType(type);
  if (t === 'announcement') return 'var(--noti-announcement)';
  if (t === 'reminder') return 'var(--noti-reminder)';
  if (t === 'warning') return 'var(--noti-warning)';
  return 'var(--noti-info)';
}

function fmtTime(s: any): string {
  if (!s) return '';
  const raw = String(s).replace('T', ' ');
  if (raw.length >= 16) return raw.slice(0, 16);
  return raw;
}

function toTimeValue(s: any): number {
  if (!s) return 0;
  const raw = String(s);
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/);
  // 统一以北京时间为准：后端返回的 "YYYY-MM-DD HH:mm:ss" 视为本地（北京时间）时间
  if (m) return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)).getTime();
  try {
    const d = new Date(raw);
    const t = d.getTime();
    return Number.isFinite(t) ? t : 0;
  } catch (e) {
    return 0;
  }
}

function snippetText(s: any, maxLen: number): string {
  const t = (s || '').toString().replace(/\s+/g, ' ').trim();
  if (!t) return '';
  if (t.length <= maxLen) return t;
  return t.slice(0, maxLen) + '…';
}

function sortTypeKeys(keys: string[]): string[] {
  const arr = (keys || []).slice();
  arr.sort((a, b) => {
    const ia = TYPE_ORDER.indexOf(a);
    const ib = TYPE_ORDER.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
  return arr;
}

function getReadFacets(list: NotiVM[]): TypeFacets {
  const counts: Record<string, number> = {};
  (list || []).forEach((n) => {
    const key = normalizeType(n.typeKey);
    counts[key] = (counts[key] || 0) + 1;
  });
  const keys = sortTypeKeys(Object.keys(counts));
  const items: TypeFacetItem[] = keys.map((t) => ({
    type: t,
    label: TYPE_LABEL[t] || t,
    count: counts[t] || 0,
    color: typeDotColor(t)
  }));
  return { total: (list || []).length, items };
}

function sortReadItems(items: NotiVM[], sortKey: 'time' | 'priority'): NotiVM[] {
  const arr = (items || []).slice();
  arr.sort((a, b) => {
    const pa = toInt(a.priority);
    const pb = toInt(b.priority);
    const ta = toInt(a.timeValue);
    const tb = toInt(b.timeValue);
    if (sortKey === 'priority') {
      if (pb !== pa) return pb - pa;
      if (tb !== ta) return tb - ta;
    } else {
      if (tb !== ta) return tb - ta;
      if (pb !== pa) return pb - pa;
    }
    return toInt(b.id) - toInt(a.id);
  });
  return arr;
}

function groupByType(items: NotiVM[]): Array<{ type: string; items: NotiVM[] }> {
  const groups: Record<string, NotiVM[]> = {};
  (items || []).forEach((n) => {
    const k = normalizeType(n.typeKey);
    if (!groups[k]) groups[k] = [];
    groups[k].push(n);
  });
  const keys = sortTypeKeys(Object.keys(groups));
  return keys.map((k) => ({ type: k, items: groups[k] || [] }));
}

function resolvePresetTab(raw: any): 'read' | 'unread' | '' {
  const t = String(raw || '').trim().toLowerCase();
  if (t === 'read') return 'read';
  if (t === 'unread') return 'unread';
  return '';
}

Page({
  data: {
    drawerOpen: false,
    loading: false,
    inited: false,
    errorMsg: '',

    tab: 'unread' as 'unread' | 'read',

    list: [] as NotiVM[],
    unreadList: [] as NotiVM[],
    readAll: [] as NotiVM[],
    readGroups: [] as ReadGroup[],

    unreadCount: 0,
    readCount: 0,
    unreadSub: '优先处理',
    readSub: '按通知类型归档展示',

    markingId: 0,
    markAllLoading: false,

    readTypeFilter: 'all',
    readTypeFacets: { total: 0, items: [] as TypeFacetItem[] } as TypeFacets,
    readFilteredCount: 0
  },

  onLoad(options: any) {
    const preset = resolvePresetTab(options?.tab);
    (this as any).__presetTab = preset;
    if (preset) this.setData({ tab: preset });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    this.fetchList(false);
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
  },

  onTabTap(e: any) {
    const tab = String(e?.currentTarget?.dataset?.tab || '');
    const next = tab === 'read' ? 'read' : 'unread';
    if (next === this.data.tab) return;
    this.setData({ tab: next });
  },

  onRefreshTap() {
    this.fetchList(true);
  },

  onPullDownRefresh() {
    Promise.resolve()
      .then(async () => {
        await this.fetchList(true);
      })
      .finally(() => {
        wx.stopPullDownRefresh();
      });
  },

  onReadTypeTap(e: any) {
    const type = String(e?.currentTarget?.dataset?.type || 'all');
    if (type === this.data.readTypeFilter) return;
    this.setData({ readTypeFilter: type }, () => this.rebuildDerived());
  },

  onToggleReadExpand(e: any) {
    const id = toInt(e?.currentTarget?.dataset?.id);
    if (!id) return;
    const self = this;
    if (!self.__expandedReadIds) self.__expandedReadIds = new Set<number>();
    const s: Set<number> = self.__expandedReadIds as Set<number>;
    if (s.has(id)) s.delete(id);
    else s.add(id);
    this.rebuildDerived();
  },

  async onMarkRead(e: any) {
    const id = toInt(e?.currentTarget?.dataset?.id);
    if (!id) return;
    if (this.data.markingId) return;

    this.setData({ markingId: id, errorMsg: '' });
    try {
      await api.markNotificationRead(id);
      const list = (this.data.list || []).map((n) => (n.id === id ? { ...n, isRead: true } : n));
      this.setData({ list }, () => this.rebuildDerived());
    } catch (err: any) {
      wx.showToast({ title: err?.message || '操作失败', icon: 'none' });
    } finally {
      this.setData({ markingId: 0 });
    }
  },

  async onMarkAllRead() {
    if (this.data.loading || this.data.markAllLoading) return;
    const unread = (this.data.list || []).filter((n) => !n.isRead);
    if (unread.length === 0) return;

    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '批量标记',
        content: `将 ${unread.length} 条未读通知全部标记为已读？`,
        confirmText: '确定',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    this.setData({ markAllLoading: true, errorMsg: '' });
    try {
      for (const n of unread) {
        if (!n?.id) continue;
        await api.markNotificationRead(n.id);
        const list = (this.data.list || []).map((x) => (x.id === n.id ? { ...x, isRead: true } : x));
        this.setData({ list }, () => this.rebuildDerived());
      }
    } catch (err: any) {
      wx.showToast({ title: err?.message || '部分操作失败', icon: 'none' });
    } finally {
      this.setData({ markAllLoading: false });
      this.fetchList(true);
    }
  },

  rebuildDerived() {
    const list = Array.isArray(this.data.list) ? this.data.list : [];
    const unreadList = list.filter((n) => !n.isRead);
    const readAll = list.filter((n) => !!n.isRead);

    const unreadCount = unreadList.length;
    const readCount = readAll.length;
    const unreadSub = unreadCount > 0 ? '优先处理' : '已清空';

    const facets = getReadFacets(readAll);

    let readTypeFilter = (this.data.readTypeFilter || 'all').toString();
    if (readTypeFilter !== 'all' && facets.total > 0 && !facets.items.some((i) => i.type === readTypeFilter)) {
      readTypeFilter = 'all';
    }

    const readFiltered = readTypeFilter === 'all' ? readAll : readAll.filter((n) => n.typeKey === readTypeFilter);

    const readFilteredCount = readFiltered.length;

    const self = this;
    if (!self.__expandedReadIds) self.__expandedReadIds = new Set<number>();
    const expanded: Set<number> = self.__expandedReadIds as Set<number>;

    const groups: ReadGroup[] = groupByType(readFiltered).map((g) => {
      const sorted = sortReadItems(g.items, 'time');
      const items = sorted.map((n) => ({ ...n, expanded: expanded.has(n.id) }));
      return {
        type: g.type,
        label: TYPE_LABEL[g.type] || g.type,
        count: items.length,
        items
      };
    });

    const typeLabel = readTypeFilter === 'all' ? '全部' : (TYPE_LABEL[readTypeFilter] || readTypeFilter);

    let readSub = '按通知类型归档展示';
    if (readAll.length === 0) {
      readSub = '暂无已读通知';
    } else {
      readSub = `共 ${readFilteredCount}/${readAll.length} 条 · ${typeLabel}`;
    }

    this.setData({
      unreadList,
      readAll,
      unreadCount,
      readCount,
      unreadSub,
      readSub,
      readTypeFacets: facets,
      readTypeFilter,
      readGroups: groups,
      readFilteredCount
    });
  },

  async fetchList(force = false) {
    if (this.data.loading) return;

    const self = this;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    const isFirstLoad = !this.data.inited;
    if (!force && !isFirstLoad && now - lastAt < 12000) return;

    self.__lastLoadedAt = now;
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res = (await api.getNotifications({ include_dismissed: 1, limit: 200 })) as NotiRaw[];
      const rawList = Array.isArray(res) ? res : [];
      const list: NotiVM[] = rawList
        .map((n) => {
          const id = toInt(n?.id);
          if (!id) return null;
          const title = (n?.title || '通知').toString();
          const content = (n?.content || '').toString();
          const typeKey = normalizeType(n?.n_type);
          const priority = toInt(n?.priority);
          const createdAt = (n?.created_at || '').toString();
          const isRead = !!n?.is_read;
          return {
            id,
            title,
            content,
            typeKey,
            typeLabel: TYPE_LABEL[typeKey] || '信息',
            priority,
            createdAt,
            timeText: fmtTime(createdAt),
            timeValue: toTimeValue(createdAt),
            isRead,
            snippet: snippetText(content, 70)
          } as NotiVM;
        })
        .filter((x): x is NotiVM => !!x);

      // 首次进入：如果没指定 tab，则根据是否有未读自动选择
      let tab = this.data.tab;
      const preset = (self.__presetTab || '') as string;
      if (isFirstLoad) {
        if (preset === 'read' || preset === 'unread') tab = preset;
        else tab = list.some((n) => !n.isRead) ? 'unread' : 'read';
      }

      this.setData({ list, tab, inited: true }, () => this.rebuildDerived());
    } catch (err: any) {
      this.setData({ errorMsg: err?.message || '网络异常：无法加载通知' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
