export type Scope = 'all' | 'favorites' | 'mistakes';
export type DetailTab = 'practice' | 'reinforce' | 'exam' | 'search' | 'stats' | 'export' | 'share';
export type DataSubTab = 'global' | 'mistakes' | 'favorites';
export type SubjectMeta = { id: number; name: string; question_count: number };
export type TagItem = { name: string; count?: number };
export type SearchItem = {
  id: number;
  content?: string;
  content_preview?: string;
  q_type?: string;
  is_fav?: number | boolean;
  is_mistake?: number | boolean;
};
export type DetailOption = { key: string; value: string };
export type AdviceItem = { title?: string; content?: string };
export type TrendView = {
  day: string;
  label: string;
  answered: number;
  correct: number;
  wrong: number;
  answeredPct: number;
  correctPctInAnswered: number;
};
export type TypeBreakdownView = {
  q_type: string;
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  favorites: number;
  mistakes: number;
  accuracyText: string;
  completionText: string;
  completionWidth: number;
  metaText: string;
};
export type DifficultyBreakdownView = {
  label: string;
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  accuracyText: string;
  completionText: string;
  completionWidth: number;
};
export type StatsOverviewView = {
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  favorites: number;
  mistakes: number;
  mistakeTimes: number;
  accuracy: number;
  completion: number;
  accuracyText: string;
  completionText: string;
  streakDays: number;
  lastText: string;
};
export type StatsQuestionItem = {
  id: number;
  content_preview?: string;
  q_type?: string;
  difficulty?: number;
  mistake_wrong_count?: number;
  mistake_created_at?: string;
  mistake_updated_at?: string;
  favorite_created_at?: string;
  last_is_correct?: number | boolean | null;
  last_answered_at?: string;
  [key: string]: any;
};
export type FavoritesTrend = {
  total_added?: number;
  trend?: Array<{ day?: string; added?: number }>;
  [key: string]: any;
};

export const OPTION_TYPES = new Set(['选择题', '多选题']);
export const KEY_SHUFFLE_Q = 'shuffle_questions';
export const KEY_SHUFFLE_O = 'shuffle_options';

export type ReinforceSubTab = 'wrong' | 'similar';
export type ReinforceWrongTopItem = {
  question_id: number;
  wrong_count: number;
  q_type?: string;
  content_preview?: string;
};
export type ReinforceSimilarPairItem = {
  key?: string;
  a_id: number;
  b_id: number;
  a_type?: string;
  b_type?: string;
  a_preview?: string;
  b_preview?: string;
  stem_sim?: number;
  opt_sim?: number;
  sim_pct?: number;
  sim_pct_text?: string;
};
export type ReinforceWrongState = {
  loading: boolean;
  loaded: boolean;
  error: string;
  desc: string;
  listMeta: string;
  wrongTotal: number;
  recommendIds: number[];
  top: ReinforceWrongTopItem[];
};
export type ReinforceSimilarState = {
  loading: boolean;
  loaded: boolean;
  error: string;
  desc: string;
  listMeta: string;
  wrongTotal: number;
  similarMode: string;
  pairsCount: number;
  seedIds: number[];
  startIds: number[];
  pairs: ReinforceSimilarPairItem[];
};

export type DetailTabView = { key: DetailTab; label: string };

export const DEFAULT_DETAIL_TAB_ORDER: DetailTab[] = ['practice', 'reinforce', 'exam', 'search', 'stats', 'export', 'share'];
export const VALID_DETAIL_TABS = new Set(DEFAULT_DETAIL_TAB_ORDER);
export const DETAIL_TAB_LABELS: Record<DetailTab, string> = {
  practice: '练习',
  reinforce: '加强',
  exam: '考试',
  search: '搜索',
  stats: '数据',
  export: '导出',
  share: '分享'
};

export function normalizeDetailTabOrder(input: any, fallback: DetailTab[]): DetailTab[] {
  const base = Array.isArray(fallback) ? fallback : DEFAULT_DETAIL_TAB_ORDER;
  const out: DetailTab[] = [];
  const seen = new Set<string>();

  const push = (k: any) => {
    const key = String(k || '').trim().toLowerCase();
    if (!VALID_DETAIL_TABS.has(key as DetailTab)) return;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(key as DetailTab);
  };

  (Array.isArray(input) ? input : []).forEach(push);
  base.forEach(push);
  return out;
}

export function buildDetailTabViews(order: DetailTab[]): DetailTabView[] {
  const list = Array.isArray(order) ? order : DEFAULT_DETAIL_TAB_ORDER;
  return list.map((key) => ({ key, label: DETAIL_TAB_LABELS[key] || key }));
}

export function getSubjectDetailTabOrderKey(subjectId: number, subjectName: string): string {
  const id = Number(subjectId || 0);
  if (Number.isFinite(id) && id > 0) return `subject_${Math.floor(id)}_detail_tab_order_v1`;
  const name = String(subjectName || '').trim();
  return name ? `subject_${name}_detail_tab_order_v1` : '';
}

export function readSubjectDetailTabOrder(key: string, fallback: DetailTab[]): DetailTab[] {
  if (!key) return normalizeDetailTabOrder(null, fallback);
  try {
    const raw: any = wx.getStorageSync(key);
    if (Array.isArray(raw)) return normalizeDetailTabOrder(raw, fallback);
    if (typeof raw === 'string') {
      const s = raw.trim();
      if (!s) return normalizeDetailTabOrder(null, fallback);
      try {
        return normalizeDetailTabOrder(JSON.parse(s), fallback);
      } catch (e) {
        return normalizeDetailTabOrder(null, fallback);
      }
    }
    return normalizeDetailTabOrder(null, fallback);
  } catch (e) {
    return normalizeDetailTabOrder(null, fallback);
  }
}

export function persistSubjectDetailTabOrder(key: string, order: DetailTab[]): void {
  if (!key) return;
  try {
    wx.setStorageSync(key, Array.isArray(order) ? order : []);
  } catch (e) {}
}

export function scopeFromEntry(entry: string): Scope {
  if (entry === 'favorites') return 'favorites';
  if (entry === 'mistakes') return 'mistakes';
  return 'all';
}

export function shouldCountForTab(tab: DetailTab): boolean {
  return tab === 'practice' || tab === 'export';
}

export function normalizeTab(input: any): DetailTab {
  const s = String(input || '').trim().toLowerCase();
  if (s === 'data') return 'stats';
  if (s === 'exam') return 'exam';
  if (s === 'reinforce' || s === 'strengthen' || s === 'enhance') return 'reinforce';
  if (s === 'search') return 'search';
  if (s === 'stats') return 'stats';
  if (s === 'favorites' || s === 'mistakes') return 'practice';
  if (s === 'export') return 'export';
  if (s === 'share') return 'share';
  return 'practice';
}

export function normalizeReinforceSubTab(input: any): ReinforceSubTab {
  const s = String(input || '').trim().toLowerCase();
  return s === 'similar' ? 'similar' : 'wrong';
}

export function getStoredString(key: string, fallback: string): string {
  try {
    const raw = wx.getStorageSync(key);
    const s = String(raw || '').trim();
    return s ? s : fallback;
  } catch (e) {
    return fallback;
  }
}

export function setStoredString(key: string, value: string): void {
  try {
    wx.setStorageSync(key, String(value || ''));
  } catch (e) {}
}

export function normalizeTextLines(input: any): string[] {
  const text = String(input ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = text.split('\n').map((s) => String(s ?? '').replace(/[ \t]+$/g, ''));
  while (lines.length && !lines[lines.length - 1]) lines.pop();
  return lines;
}

export function normalizeSubjectDetailOptions(rawOptions: any, qType: string): DetailOption[] {
  const qt = String(qType || '').trim();
  const list = Array.isArray(rawOptions) ? rawOptions : [];
  if (!list.length && qt === '判断题') {
    return [
      { key: '正确', value: '正确' },
      { key: '错误', value: '错误' }
    ];
  }
  const out: DetailOption[] = [];
  list.forEach((opt, idx) => {
    if (opt && typeof opt === 'object') {
      const key = String((opt as Record<string, unknown>).key ?? '').trim();
      const value = String((opt as Record<string, unknown>).value ?? '').trim();
      if (key || value) out.push({ key: key || String(idx + 1), value });
    } else {
      const value = String(opt ?? '').trim();
      if (value) out.push({ key: String(idx + 1), value });
    }
  });
  return out;
}

export function getStoredBool(key: string, fallback = false): boolean {
  try {
    const raw: any = wx.getStorageSync(key);
    if (raw === true || raw === 1 || raw === '1') return true;
    if (raw === false || raw === 0 || raw === '0') return false;
    return fallback;
  } catch (e) {
    return fallback;
  }
}

export function setStoredBool(key: string, value: boolean): void {
  try {
    wx.setStorageSync(key, value ? '1' : '0');
  } catch (e) {}
}

export function clampPct(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(100, v));
}


