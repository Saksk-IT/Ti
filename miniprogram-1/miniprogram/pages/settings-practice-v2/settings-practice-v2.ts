import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { themeManager, ThemeMode, ThemeStyle } from '../../utils/theme';

type SettingsNavKey = 'account' | 'practice' | 'theme' | 'about';
type QuizLayoutTheme = 'traditional' | 'card';
type ModalRow = { name: string; checked: boolean };

const HOME_VISIBLE_SUBJECTS_KEY = 'home_visible_subjects';
const QUIZ_FAB_ENABLED_KEY = 'quiz_fab_enabled_v1';
const QUIZ_LAYOUT_THEME_KEY = 'quiz_layout_theme_v1';

function navTo(key: SettingsNavKey): string {
  if (key === 'account') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-practice-v2/settings-practice-v2';
}

function uniq(arr: string[]): string[] {
  const s = new Set<string>();
  const out: string[] = [];
  (arr || []).forEach((x) => {
    const v = String(x || '').trim();
    if (!v || s.has(v)) return;
    s.add(v);
    out.push(v);
  });
  return out;
}

function readVisibleSubjects(): string[] {
  try {
    const raw: any = wx.getStorageSync(HOME_VISIBLE_SUBJECTS_KEY);
    if (Array.isArray(raw)) return uniq(raw.map((x) => String(x || '').trim()).filter(Boolean));
    if (typeof raw === 'string' && raw.trim().startsWith('[')) {
      const js = JSON.parse(raw);
      if (Array.isArray(js)) return uniq(js.map((x) => String(x || '').trim()).filter(Boolean));
    }
  } catch (e) {}
  return [];
}

function writeVisibleSubjects(names: string[]): void {
  try {
    wx.setStorageSync(HOME_VISIBLE_SUBJECTS_KEY, uniq(names));
  } catch (e) {}
}

function isQuizFabEnabled(): boolean {
  try {
    const raw = wx.getStorageSync(QUIZ_FAB_ENABLED_KEY);
    if (raw === '' || raw == null) return true;
    const s = String(raw).trim();
    if (s === '0' || s === 'false' || s === 'off' || s === 'no') return false;
    return true;
  } catch (e) {
    return true;
  }
}

function setQuizFabEnabled(on: boolean): void {
  try {
    wx.setStorageSync(QUIZ_FAB_ENABLED_KEY, on ? '1' : '0');
  } catch (e) {}
}

function getQuizLayoutTheme(): QuizLayoutTheme {
  try {
    const raw = wx.getStorageSync(QUIZ_LAYOUT_THEME_KEY);
    const s = String(raw || '').trim().toLowerCase();
    return s === 'card' ? 'card' : 'traditional';
  } catch (e) {
    return 'traditional';
  }
}

function setQuizLayoutTheme(theme: QuizLayoutTheme): void {
  const t = theme === 'card' ? 'card' : 'traditional';
  try {
    wx.setStorageSync(QUIZ_LAYOUT_THEME_KEY, t);
  } catch (e) {}
}

function buildSubjectSummary(visible: string[], all: string[]): string {
  const v = uniq(visible);
  const a = uniq(all);

  if (!v.length) return '全部科目';

  // 若等于全部，也视为“全部”
  if (a.length && v.length >= a.length) {
    const setV = new Set(v);
    const isAll = a.every((x) => setV.has(x));
    if (isAll) return '全部科目';
  }

  if (v.length <= 4) return v.join('、');
  return `${v.slice(0, 3).join('、')} 等 ${v.length} 门`;
}

Page({
  data: {
    drawerOpen: false,
    navKey: 'practice' as SettingsNavKey,
    msg: '',

    subjectSummary: '全部科目',
    subjectsAll: [] as string[],
    subjectsLoading: false,

    quizFabEnabled: true,
    quizLayoutTheme: 'traditional' as QuizLayoutTheme,

    subjectModalOpen: false,
    modalRows: [] as ModalRow[]
  },

  onLoad() {
    wx.redirectTo({ url: '/pages/settings-center-v2/settings-center-v2?navKey=practice' });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    const subjectsAll = this.data.subjectsAll || [];
    const visible = readVisibleSubjects();
    this.setData({
      quizFabEnabled: isQuizFabEnabled(),
      quizLayoutTheme: getQuizLayoutTheme(),
      subjectSummary: buildSubjectSummary(visible, subjectsAll)
    });

    // 背景拉取一次科目列表，用于“全部科目”判断与弹层
    this.ensureSubjects(false);
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

  onContinueLast() {
    const url = buildLastPracticeUrl();
    if (!url) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }
    wx.navigateTo({ url });
  },

  onSettingsNavTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.key || '') as SettingsNavKey;
    if (!key) return;
    const url = navTo(key);
    if (url === '/pages/settings-practice-v2/settings-practice-v2') return;
    wx.redirectTo({ url });
  },

  async ensureSubjects(force = false) {
    if (this.data.subjectsLoading) return;
    if (!force && Array.isArray(this.data.subjectsAll) && this.data.subjectsAll.length) return;

    this.setData({ subjectsLoading: true });
    try {
      const res: any = await api.getSubjects();
      const listRaw = Array.isArray(res?.subjects) ? res.subjects : Array.isArray(res) ? res : [];
      const subjectsAll = uniq(listRaw.map((x: any) => String(x || '').trim()).filter(Boolean));
      this.setData({ subjectsAll });
      this.setData({ subjectSummary: buildSubjectSummary(readVisibleSubjects(), subjectsAll) });
    } catch (e) {
      // 忽略网络异常：弹层会显示“暂无可用科目/正在加载”
    } finally {
      this.setData({ subjectsLoading: false });
    }
  },

  async onOpenSubjectModal() {
    await this.ensureSubjects(true);
    const all = uniq(this.data.subjectsAll || []);
    const visible = uniq(readVisibleSubjects());
    const setV = new Set(visible);
    const treatAll = !visible.length || (all.length && all.every((x) => setV.has(x)));
    const selected = treatAll ? all : all.filter((x) => setV.has(x));
    const setSel = new Set(selected);
    const modalRows: ModalRow[] = all.map((name) => ({ name, checked: setSel.has(name) }));
    this.setData({ subjectModalOpen: true, modalRows });
  },

  onCloseSubjectModal() {
    this.setData({ subjectModalOpen: false });
  },

  stopTap() {},

  onSelectAllSubjects() {
    const modalRows = (this.data.modalRows || []).map((r) => ({ ...r, checked: true }));
    this.setData({ modalRows });
  },

  onClearAllSubjects() {
    const modalRows = (this.data.modalRows || []).map((r) => ({ ...r, checked: false }));
    this.setData({ modalRows });
  },

  onModalSubjectToggle(e: any) {
    const name = String(e?.currentTarget?.dataset?.name || '').trim();
    const checked = !!(e && e.detail && e.detail.value);
    if (!name) return;
    const modalRows = (this.data.modalRows || []).map((r) => (r.name === name ? { ...r, checked } : r));
    this.setData({ modalRows });
  },

  onCancelSubjectSelection() {
    this.setData({ subjectModalOpen: false });
  },

  async onApplySubjectSelection() {
    const all = uniq(this.data.subjectsAll || []);
    const checked = uniq((this.data.modalRows || []).filter((r) => r.checked).map((r) => r.name));
    const next = all.length && checked.length >= all.length ? [] : checked;

    writeVisibleSubjects(next);
    this.setData({
      subjectModalOpen: false,
      subjectSummary: buildSubjectSummary(next, all),
      msg: '已应用'
    });

    await syncUserSettingsToServer();
  },

  async onClearSubjectFilter() {
    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '显示全部',
        content: '确定要显示全部科目吗？',
        confirmText: '确定',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    writeVisibleSubjects([]);
    this.setData({
      subjectSummary: buildSubjectSummary([], this.data.subjectsAll || []),
      msg: '已设置为显示全部'
    });
    await syncUserSettingsToServer();
  },

  async onQuizFabChange(e: any) {
    const on = !!(e && e.detail && e.detail.value);
    setQuizFabEnabled(on);
    this.setData({ quizFabEnabled: on, msg: on ? '已开启悬浮球' : '已关闭悬浮球' });
    await syncUserSettingsToServer();
  },

  async onLayoutTap(e: any) {
    const key = String(e?.currentTarget?.dataset?.layout || 'traditional');
    const next: QuizLayoutTheme = key === 'card' ? 'card' : 'traditional';
    setQuizLayoutTheme(next);
    this.setData({ quizLayoutTheme: next, msg: next === 'card' ? '已切换到卡片布局' : '已切换到传统布局' });
    await syncUserSettingsToServer();
  },

  async onResetPractice() {
    const ok = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '恢复默认',
        content: '确定要恢复通用设置的默认值吗？',
        confirmText: '确定',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
    if (!ok) return;

    writeVisibleSubjects([]);
    setQuizFabEnabled(true);
    setQuizLayoutTheme('traditional');

    const all = this.data.subjectsAll || [];
    this.setData({
      quizFabEnabled: true,
      quizLayoutTheme: 'traditional',
      subjectSummary: buildSubjectSummary([], all),
      msg: '已恢复默认'
    });
    await syncUserSettingsToServer();
  }
});
