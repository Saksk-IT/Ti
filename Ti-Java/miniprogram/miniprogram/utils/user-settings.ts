import { api } from './api';
import { ThemeStyle, themeManager } from './theme';

const SETTINGS_SYNC_KEY = 'user_settings_v1';
const SETTINGS_UPDATED_AT_KEY = 'settings_updated_at';

// 与 Web localStorage 约定保持一致（跨端同步在 user_settings_v1 中完成）
const HOME_VISIBLE_SUBJECTS_KEY = 'home_visible_subjects';
const QUIZ_HOTKEYS_KEY = 'quiz_hotkeys_v1';
const QUIZ_FAB_ENABLED_KEY = 'quiz_fab_enabled_v1';
const QUIZ_LAYOUT_THEME_KEY = 'quiz_layout_theme_v1';

type QuizLayoutTheme = 'traditional' | 'card';

type UserSettingsV1 = {
  version?: number;
  updated_at?: number;
  app_theme_style_v1?: string;
  home_visible_subjects?: string[];
  quiz_hotkeys_v1?: Record<string, any>;
  quiz_fab_enabled_v1?: boolean;
  quiz_layout_theme_v1?: QuizLayoutTheme;
  [k: string]: any;
};

function getLocalUpdatedAt(): number {
  const raw = wx.getStorageSync(SETTINGS_UPDATED_AT_KEY);
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

function setLocalUpdatedAt(ts: number): void {
  const n = Number(ts);
  if (!Number.isFinite(n) || n <= 0) return;
  wx.setStorageSync(SETTINGS_UPDATED_AT_KEY, String(Math.floor(n)));
}

function normalizeThemeStyle(v: any): ThemeStyle | null {
  const s = String(v || '').trim();
  if (s === 'mist' || s === 'dune' || s === 'pine' || s === 'celadon' || s === 'default') return s;
  return null;
}

function normalizeStringArray(v: any): string[] {
  const arr = Array.isArray(v) ? v : [];
  return arr
    .map((x) => String(x || '').trim())
    .filter((x) => !!x);
}

function readStorageJson(key: string): any {
  try {
    const raw = wx.getStorageSync(key);
    if (raw == null || raw === '') return null;
    if (typeof raw === 'object') return raw;
    const s = String(raw);
    if (!s) return null;
    if (s.trim().startsWith('{') || s.trim().startsWith('[')) {
      return JSON.parse(s);
    }
    return s;
  } catch (e) {
    return null;
  }
}

function writeStorageJson(key: string, value: any): void {
  try {
    wx.setStorageSync(key, value);
  } catch (e) {}
}

function getHomeVisibleSubjects(): string[] {
  const v = readStorageJson(HOME_VISIBLE_SUBJECTS_KEY);
  return normalizeStringArray(v);
}

function setHomeVisibleSubjects(names: string[]): void {
  writeStorageJson(HOME_VISIBLE_SUBJECTS_KEY, normalizeStringArray(names));
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

function setQuizLayoutTheme(theme: any): void {
  const t = String(theme || '').trim().toLowerCase() === 'card' ? 'card' : 'traditional';
  try {
    wx.setStorageSync(QUIZ_LAYOUT_THEME_KEY, t);
  } catch (e) {}
}

function getQuizHotkeys(): Record<string, any> {
  const v = readStorageJson(QUIZ_HOTKEYS_KEY);
  if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>;
  return {};
}

function setQuizHotkeys(obj: any): void {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return;
  writeStorageJson(QUIZ_HOTKEYS_KEY, obj);
}

export async function syncUserSettingsFromServer(): Promise<void> {
  try {
    const remote = (await api.getProgress(SETTINGS_SYNC_KEY)) as UserSettingsV1 | null;
    if (!remote || typeof remote !== 'object') return;

    const remoteTs = Number(remote.updated_at || 0) || 0;
    const localTs = getLocalUpdatedAt();

    if (remoteTs > localTs) {
      const style = normalizeThemeStyle(remote.app_theme_style_v1);
      if (style) themeManager.setStyle(style);
      setHomeVisibleSubjects(remote.home_visible_subjects || []);
      if (typeof remote.quiz_fab_enabled_v1 !== 'undefined') setQuizFabEnabled(!!remote.quiz_fab_enabled_v1);
      if (typeof remote.quiz_layout_theme_v1 === 'string') setQuizLayoutTheme(remote.quiz_layout_theme_v1);
      if (remote.quiz_hotkeys_v1 && typeof remote.quiz_hotkeys_v1 === 'object') setQuizHotkeys(remote.quiz_hotkeys_v1);
      setLocalUpdatedAt(remoteTs);
      return;
    }

    if (localTs > remoteTs) {
      await syncUserSettingsToServer();
    }
  } catch (e) {
    // 忽略网络异常/未登录等情况
  }
}

export async function syncUserSettingsToServer(): Promise<void> {
  try {
    const payload: UserSettingsV1 = {
      version: 1,
      home_visible_subjects: getHomeVisibleSubjects(),
      quiz_hotkeys_v1: getQuizHotkeys(),
      quiz_fab_enabled_v1: isQuizFabEnabled(),
      quiz_layout_theme_v1: getQuizLayoutTheme(),
      app_theme_style_v1: themeManager.getStyle(),
      updated_at: Date.now()
    };
    setLocalUpdatedAt(payload.updated_at || 0);
    await api.saveProgress(SETTINGS_SYNC_KEY, payload);
  } catch (e) {
    // 忽略网络异常/未登录等情况
  }
}
