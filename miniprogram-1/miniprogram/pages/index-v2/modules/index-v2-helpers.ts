export type TabKey = 'new' | 'templates' | 'records' | 'data' | 'settings';
export type ExamSource = 'public' | 'user_bank';

export type SystemTemplate = {
  id: string;
  title: string;
  total: number;
  duration: number;
  preferred: string[];
  tags: string[];
  note: string;
};

export const QUICK_PRESETS = [
  { duration: 15, total: 20, label: '15 分钟 · 20 题' },
  { duration: 30, total: 30, label: '30 分钟 · 30 题' },
  { duration: 60, total: 50, label: '60 分钟 · 50 题' }
];

export const SYSTEM_TEMPLATES: SystemTemplate[] = [
  {
    id: 'quick-15',
    title: '速测 15 分钟',
    total: 20,
    duration: 15,
    preferred: ['单选题', '判断题'],
    tags: ['碎片时间', '基础回顾'],
    note: '适合课后小测与快速复盘。'
  },
  {
    id: 'standard-45',
    title: '标准 45 分钟',
    total: 40,
    duration: 45,
    preferred: ['单选题', '多选题', '判断题'],
    tags: ['综合覆盖', '模拟节奏'],
    note: '覆盖主流题型，节奏接近模拟考试。'
  },
  {
    id: 'focus-60',
    title: '专项 60 分钟',
    total: 60,
    duration: 60,
    preferred: ['多选题', '综合题', '简答题'],
    tags: ['强化', '高权重'],
    note: '偏重综合与高分题型，适合冲刺阶段。'
  }
];

export const FALLBACK_PUBLIC_Q_TYPES = ['单选题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
export const DEFAULT_PICKED_TYPES = ['单选题', '多选题', '判断题'];

export type Option<T> = { value: T; label: string };

export type BankMeta = {
  id: number;
  name: string;
  question_count?: number;
};

export type ExamTypeRow = {
  name: string;
  enabled: boolean;
  available: number;
  count: number;
  score: number;
  subtotalText: string;
};

export type ExamScope = {
  source: ExamSource;
  subject: string;
  bank_id: number | null;
};

export type ExamConfig = {
  source: ExamSource;
  subject: string;
  bank_id: number | null;
  duration: number;
  targetTotal: number;
  types: Record<string, number>;
  scores: Record<string, number>;
  label?: string;
};

export type UserTemplate = {
  id: number;
  title: string;
  config: any;
  created_at?: string;
  updated_at?: string;
};

export type UserTemplateCard = {
  id: number;
  title: string;
  meta: string;
  tags: string[];
};

export let examPresetApplied = false;
export const qTypesCache = new Map<string, string[]>();

export function clampInt(v: any, fallback: number, minV: number, maxV: number): number {
  const n = Math.floor(Number(v));
  if (!Number.isFinite(n)) return fallback;
  return Math.max(minV, Math.min(maxV, n));
}

export function clampFloat(v: any, fallback: number, minV: number, maxV: number): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(minV, Math.min(maxV, n));
}

export function formatNum(n: any): string {
  const v = Number(n);
  if (!Number.isFinite(v)) return '0';
  if (Math.abs(v - Math.round(v)) < 1e-6) return String(Math.round(v));
  return String(v.toFixed(2)).replace(/\.?0+$/, '');
}

export function todayStamp(): string {
  const now = new Date();
  const y = String(now.getFullYear());
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function setDataAsync(ctx: any, patch: Record<string, any>): Promise<void> {
  return new Promise((resolve) => ctx.setData(patch, resolve));
}

export function uniqueBanks(list: any[]): BankMeta[] {
  const map = new Map<number, BankMeta>();
  (list || []).forEach((b: any) => {
    const id = Number(b && b.id);
    if (!Number.isFinite(id) || id <= 0) return;
    const name = String(b.name || '').trim();
    if (!name) return;
    const question_count = Number(b.question_count || 0) || 0;
    map.set(id, { id, name, question_count });
  });
  return Array.from(map.values());
}

export function buildSubjectOptions(subjects: string[]): Option<string>[] {
  const rest = (subjects || [])
    .filter((s) => typeof s === 'string' && s.trim())
    .map((s) => String(s).trim());
  return [{ value: 'all', label: '全部科目' }, ...rest.map((s) => ({ value: s, label: s }))];
}

export function buildBankOptions(banks: BankMeta[]): Option<number>[] {
  return (banks || []).map((b) => ({
    value: b.id,
    label: b.question_count ? `${b.name}（${b.question_count}题）` : b.name
  }));
}

export function findOptionLabel<T>(options: Option<T>[], value: T, fallback: string): string {
  const hit = (options || []).find((o) => o && o.value === value);
  return hit ? hit.label : fallback;
}

export function normalizeTemplateConfig(raw: any): ExamConfig | null {
  if (!raw || typeof raw !== 'object') return null;
  const source: ExamSource = String(raw.source || 'public').toLowerCase() === 'user_bank' ? 'user_bank' : 'public';
  const subject = String(raw.subject || 'all').trim() || 'all';
  const bank_id = raw.bank_id != null && raw.bank_id !== '' ? Number(raw.bank_id) : null;
  const duration = clampInt(raw.duration, 60, 1, 1440);

  const typesRaw = raw.types && typeof raw.types === 'object' ? raw.types : {};
  const scoresRaw = raw.scores && typeof raw.scores === 'object' ? raw.scores : {};

  const types: Record<string, number> = {};
  const scores: Record<string, number> = {};

  Object.keys(typesRaw || {}).forEach((k) => {
    const name = String(k || '').trim();
    if (!name) return;
    const c = clampInt((typesRaw as Record<string, unknown>)[k], 0, 0, 500);
    if (c <= 0) return;
    types[name] = c;
    scores[name] = clampFloat((scoresRaw as Record<string, unknown>)[k], 1, 0, 1000);
  });

  let targetTotal = raw.targetTotal ?? raw.total ?? raw.target_total;
  targetTotal = clampInt(targetTotal, 0, 0, 300);
  if (!targetTotal) {
    targetTotal = Object.values(types).reduce((sum, v) => sum + (Number(v) || 0), 0);
    targetTotal = clampInt(targetTotal, 0, 0, 300);
  }

  return {
    source,
    subject,
    bank_id: source === 'user_bank' ? (Number.isFinite(bank_id as number) ? (bank_id as number) : null) : null,
    duration,
    targetTotal,
    types,
    scores
  };
}

export function buildTemplateScopeLabel(cfg: ExamConfig, bankLabel: string): string {
  if (cfg.source === 'user_bank') return bankLabel ? `个人题库 · ${bankLabel}` : '个人题库';
  return `公共题库 · ${cfg.subject === 'all' ? '全部科目' : cfg.subject}`;
}

export function distributeCounts(targetTotal: number, enabledTypes: Array<{ name: string; available: number }>): Record<string, number> {
  const cfg: Record<string, number> = {};
  const n = enabledTypes.length;
  if (n <= 0) return cfg;

  const target = clampInt(targetTotal, 30, 1, 300);
  const base = Math.floor(target / n);
  let rem = target % n;

  enabledTypes.forEach((t) => {
    const want = base + (rem > 0 ? 1 : 0);
    if (rem > 0) rem -= 1;
    cfg[t.name] = Math.min(want, Math.max(0, t.available));
  });

  let assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
  let remaining = target - assignedTotal;
  let safety = 5000;
  while (remaining > 0 && safety-- > 0) {
    let progressed = false;
    for (const t of enabledTypes) {
      if (remaining <= 0) break;
      const cap = Math.max(0, t.available) - (cfg[t.name] || 0);
      if (cap > 0) {
        cfg[t.name] = (cfg[t.name] || 0) + 1;
        remaining -= 1;
        progressed = true;
      }
    }
    if (!progressed) break;
  }

  assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
  if (assignedTotal <= 0) {
    enabledTypes.forEach((t) => {
      cfg[t.name] = Math.min(1, Math.max(0, t.available));
    });
  }
  return cfg;
}


