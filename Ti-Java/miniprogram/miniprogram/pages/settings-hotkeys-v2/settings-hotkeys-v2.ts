import { checkLogin } from '../../utils/auth';
import { buildLastPracticeUrl } from '../../utils/last-practice';
import { syncUserSettingsToServer } from '../../utils/user-settings';
import { themeManager, ThemeMode } from '../../utils/theme';

type SettingsNavKey = 'account' | 'theme' | 'hotkeys' | 'about';

type HotkeyDef = { key: string; label: string; desc: string };
type HotkeyRow = HotkeyDef & { display: string };

const QUIZ_HOTKEYS_KEY = 'quiz_hotkeys_v1';

const DEFAULT_QUIZ_HOTKEYS: Record<string, string> = {
  prev_question: 'ArrowLeft',
  next_question: 'ArrowRight',
  toggle_favorite: 'KeyF',
  choose_option_1: 'Digit1',
  choose_option_2: 'Digit2',
  choose_option_3: 'Digit3',
  choose_option_4: 'Digit4',
  blank_prev: 'ArrowUp',
  blank_next: 'ArrowDown',
  submit_or_next: 'Enter'
};

const HOTKEY_DEFS: HotkeyDef[] = [
  { key: 'prev_question', label: '上一题', desc: '切换到上一题' },
  { key: 'next_question', label: '下一题', desc: '切换到下一题' },
  { key: 'toggle_favorite', label: '收藏/取消收藏', desc: '切换题目收藏状态' },
  { key: 'choose_option_1', label: '选择选项 1', desc: '选择题/判断题：选第 1 个选项（A/对）' },
  { key: 'choose_option_2', label: '选择选项 2', desc: '选择题：选第 2 个选项（B/错）' },
  { key: 'choose_option_3', label: '选择选项 3', desc: '选择题：选第 3 个选项（C）' },
  { key: 'choose_option_4', label: '选择选项 4', desc: '选择题：选第 4 个选项（D）' },
  { key: 'blank_prev', label: '填空上一个挖空', desc: '填空题输入框：聚焦时切到上一个空' },
  { key: 'blank_next', label: '填空下一个挖空', desc: '填空题输入框：聚焦时切到下一个空' },
  { key: 'submit_or_next', label: '提交/查看结果/下一题', desc: '等同 Enter 行为（避免与输入换行冲突）' }
];

function navTo(key: SettingsNavKey): string {
  if (key === 'account') return '/pages/settings-account-profile-v2/settings-account-profile-v2';
  if (key === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  if (key === 'about') return '/pages/settings-about-v2/settings-about-v2';
  return '/pages/settings-hotkeys-v2/settings-hotkeys-v2';
}

function safeParseStorage(raw: any): any | null {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  const s = String(raw || '').trim();
  if (!s) return null;
  if (s.startsWith('{') || s.startsWith('[')) {
    try {
      return JSON.parse(s);
    } catch (e) {
      return null;
    }
  }
  return null;
}

function readHotkeys(): Record<string, string> {
  try {
    const raw: any = wx.getStorageSync(QUIZ_HOTKEYS_KEY);
    const js = safeParseStorage(raw);
    if (!js || typeof js !== 'object' || Array.isArray(js)) return { ...DEFAULT_QUIZ_HOTKEYS };
    const out: Record<string, string> = { ...DEFAULT_QUIZ_HOTKEYS };
    Object.keys(DEFAULT_QUIZ_HOTKEYS).forEach((k) => {
      if (typeof (js as Record<string, unknown>)[k] !== 'undefined') out[k] = String((js as Record<string, unknown>)[k] || '').trim();
    });
    return out;
  } catch (e) {
    return { ...DEFAULT_QUIZ_HOTKEYS };
  }
}

function writeHotkeys(hk: Record<string, string>): void {
  try {
    wx.setStorageSync(QUIZ_HOTKEYS_KEY, hk);
  } catch (e) {}
}

function partToDisplay(part: string): string {
  const p = String(part || '').trim();
  if (!p) return '';
  if (p === 'Ctrl' || p === 'Alt' || p === 'Shift' || p === 'Meta') return p;
  if (p === 'ArrowLeft') return '←';
  if (p === 'ArrowRight') return '→';
  if (p === 'ArrowUp') return '↑';
  if (p === 'ArrowDown') return '↓';
  if (p === 'Enter') return 'Enter';
  if (p === 'Space') return '空格';
  if (p.startsWith('Key') && p.length === 4) return p.slice(3);
  if (p.startsWith('Digit') && p.length === 6) return p.slice(5);
  return p;
}

function hotkeyToDisplay(code: any): string {
  const raw = String(code || '').trim();
  if (!raw) return '—';
  const parts = raw.split('+').map((x) => partToDisplay(x)).filter(Boolean);
  return parts.length ? parts.join(' + ') : raw;
}

function buildRows(): HotkeyRow[] {
  const hk = readHotkeys();
  return HOTKEY_DEFS.map((def) => ({
    ...def,
    display: hotkeyToDisplay(hk[def.key])
  }));
}

Page({
  data: {
    navKey: 'hotkeys' as SettingsNavKey,
    msg: '',
    hotkeyRows: [] as HotkeyRow[]
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}
    this.refreshRows();
  },

  refreshRows() {
    this.setData({ hotkeyRows: buildRows() });
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
    if (url === '/pages/settings-hotkeys-v2/settings-hotkeys-v2') return;
    wx.redirectTo({ url });
  },

  async onResetDefault() {
    writeHotkeys({ ...DEFAULT_QUIZ_HOTKEYS });
    this.refreshRows();
    this.setData({ msg: '已恢复默认，并尝试同步到云端' });
    await syncUserSettingsToServer();
  },

  async onSyncNow() {
    await syncUserSettingsToServer();
    this.setData({ msg: '已尝试同步到云端' });
  }
});
