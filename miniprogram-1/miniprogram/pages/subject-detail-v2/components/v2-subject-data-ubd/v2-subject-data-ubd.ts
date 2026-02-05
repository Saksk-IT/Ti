import { themeManager } from '../../../../utils/theme';
import * as echarts from '../ec-canvas/echarts';
import * as ubdv2Echarts from '../../../../utils/ubdv2-echarts';

type DataSubTab = 'global' | 'mistakes' | 'favorites';

type TrendView = {
  day: string;
  label: string;
  answered: number;
  correct: number;
  wrong: number;
  answeredPct: number;
  correctPctInAnswered: number;
};

type TypeBreakdownView = {
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

type DifficultyBreakdownView = {
  label: string;
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  accuracyText: string;
  completionText: string;
  completionWidth: number;
};

type StatsOverviewView = {
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

type AdviceItem = { title?: string; content?: string };

type KpiItem = { key: string; label: string; value: string; meta: string };

type CalendarCell = { key: string; level: number; dayText: string };

type StatsQuestionItem = {
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

type FavoritesTrend = {
  total_added?: number;
  trend?: Array<{ day?: string; added?: number }>;
  [key: string]: any;
};

type MistakeMatrixDot = { id: number; x: number; y: number; level: number };
type TopItemView = { id: number; title: string; meta: string; count: number; bar: number };
type AddedBarView = { day: string; label: string; added: number; h: number; showLabel: boolean };
type TypeDistRowView = { q_type: string; total: number; bar: number; meta: string };
type ListRowView = {
  id: number;
  content: string;
  q_type: string;
  difficultyText: string;
  col1: string;
  col2: string;
  col3: string;
  resultText: string;
  resultClass: string;
};

type TypeChartRow = {
  q_type: string;
  correctWidth: number;
  wrongWidth: number;
  completionText: string;
};

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function toNum(input: any): number {
  const n = Number(input || 0);
  return Number.isFinite(n) ? n : 0;
}

function fmtCount(n: any): string {
  const v = Math.max(0, Math.floor(toNum(n)));
  try {
    return v.toLocaleString('zh-CN');
  } catch {
    return String(v);
  }
}

function fmtPercent(n: any): string {
  const v = clamp(toNum(n), 0, 100);
  return `${v.toFixed(1)}%`;
}

function parseDateTime(raw: any): Date | null {
  const s = String(raw || '').trim();
  if (!s) return null;
  try {
    const iso = s.includes('T') ? s : s.replace(' ', 'T');
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

function daysSince(raw: any): number | null {
  const d = parseDateTime(raw);
  if (!d) return null;
  const diff = Date.now() - d.getTime();
  if (!Number.isFinite(diff)) return null;
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}

function fmtMDHM(raw: any): string {
  const d = parseDateTime(raw);
  if (!d) return '—';
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${m}-${day} ${hh}:${mm}`;
}

function fmtMD(raw: any): string {
  const d = parseDateTime(raw);
  if (!d) return '—';
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${m}-${day}`;
}

function weekdayFromIsoDate(isoDate: string): number {
  const s = String(isoDate || '').trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(s)) return 0;
  try {
    const d = new Date(`${s.slice(0, 10)}T00:00:00`);
    if (Number.isNaN(d.getTime())) return 0;
    return d.getDay(); // 0 Sunday .. 6 Saturday
  } catch {
    return 0;
  }
}

function buildCalendarCells(trend: TrendView[], statsDays: number): CalendarCell[] {
  const list = Array.isArray(trend) ? trend : [];
  if (!list.length) return [];

  const maxAnswered = list.reduce((m, it) => Math.max(m, toNum((it as any)?.answered)), 0) || 0;
  const padStart = weekdayFromIsoDate(list[0].day);
  const cells: CalendarCell[] = [];

  for (let i = 0; i < padStart; i++) {
    cells.push({ key: `pad_s_${i}`, level: 0, dayText: '' });
  }

  for (const it of list) {
    const day = String((it as any)?.day || '');
    const answered = toNum((it as any)?.answered);
    const pct = maxAnswered > 0 ? answered / maxAnswered : 0;
    const level = pct >= 0.75 ? 3 : pct >= 0.5 ? 2 : pct > 0 ? 1 : 0;
    const dayText = /^\d{4}-\d{2}-\d{2}/.test(day) ? day.slice(8, 10) : '';
    cells.push({ key: day || `d_${cells.length}`, level, dayText });
  }

  const remainder = cells.length % 7;
  if (remainder) {
    const padEnd = 7 - remainder;
    for (let i = 0; i < padEnd; i++) {
      cells.push({ key: `pad_e_${i}`, level: 0, dayText: '' });
    }
  }

  const cap = clamp(toNum(statsDays) + 16, 14, 110);
  if (cells.length > cap) return cells.slice(cells.length - cap);
  return cells;
}

function calcActiveDays(trend: TrendView[]): number {
  return (trend || []).filter((d) => toNum((d as any)?.answered) > 0).length;
}

function calcRecentAnswered(trend: TrendView[], days: number): number {
  const list = Array.isArray(trend) ? trend : [];
  if (!list.length) return 0;
  const slice = list.slice(Math.max(0, list.length - Math.max(1, Math.floor(days))));
  return slice.reduce((sum, it) => sum + toNum((it as any)?.answered), 0);
}

function buildHeadline(subtab: DataSubTab, overview: StatsOverviewView, trend: TrendView[], statsDays: number): string {
  const activeDays = calcActiveDays(trend);
  const accuracy = toNum((overview as any)?.accuracy);
  const completion = toNum((overview as any)?.completion);
  const total = toNum((overview as any)?.total);
  const answered = toNum((overview as any)?.answered);
  const mistakesTimes = toNum((overview as any)?.mistakeTimes);

  if (subtab === 'mistakes') {
    return `错题池 ${fmtCount(total)} 题 · 错题次数 ${fmtCount(mistakesTimes)} · 近${statsDays}天活跃${fmtCount(activeDays)}天`;
  }
  if (subtab === 'favorites') {
    const todo = Math.max(0, total - answered);
    return `收藏池 ${fmtCount(total)} 题 · 未做 ${fmtCount(todo)} 题 · 近${statsDays}天活跃${fmtCount(activeDays)}天`;
  }
  return `全局：覆盖率 ${fmtPercent(completion)} · 正确率 ${fmtPercent(accuracy)} · 近${statsDays}天活跃${fmtCount(activeDays)}天`;
}

function computeKpis(
  subtab: DataSubTab,
  overview: StatsOverviewView,
  trend: TrendView[],
  statsDays: number,
  extras?: { bankTotal?: number; questions?: StatsQuestionItem[]; favoritesTrend?: FavoritesTrend }
): KpiItem[] {
  const total = toNum((overview as any)?.total);
  const answered = toNum((overview as any)?.answered);
  const correct = toNum((overview as any)?.correct);
  const wrong = toNum((overview as any)?.wrong);
  const favorites = toNum((overview as any)?.favorites);
  const mistakes = toNum((overview as any)?.mistakes);
  const mistakeTimes = toNum((overview as any)?.mistakeTimes);
  const accuracy = toNum((overview as any)?.accuracy);
  const completion = toNum((overview as any)?.completion);
  const streakDays = toNum((overview as any)?.streakDays);

  const recentAnswered = calcRecentAnswered(trend, Math.min(7, Math.max(1, Math.floor(statsDays || 7))));
  const mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;

  if (subtab === 'mistakes') {
    const bankTotal = toNum(extras?.bankTotal);
    const ratio = bankTotal > 0 ? (total * 100) / bankTotal : 0;
    const avgTimes = total > 0 ? mistakeTimes / total : 0;

    let highRisk = 0;
    let aging = 0;
    (extras?.questions || []).forEach((q) => {
      const wc = toNum((q as any)?.mistake_wrong_count) || 1;
      if (wc >= 3) highRisk += 1;
      const ds = daysSince((q as any)?.mistake_updated_at || (q as any)?.mistake_created_at);
      if (ds != null && ds >= 14) aging += 1;
    });

    return [
      { key: 'mis_total', label: '错题池', value: fmtCount(total), meta: bankTotal > 0 ? `占题库 ${fmtPercent(ratio)}` : '—' },
      { key: 'mis_times', label: '累计次数', value: fmtCount(mistakeTimes), meta: `平均 ${avgTimes.toFixed(1)} 次/题` },
      { key: 'mis_high', label: '高危错题', value: fmtCount(highRisk), meta: 'wrong_count ≥ 3' },
      { key: 'mis_aging', label: '冷却错题', value: fmtCount(aging), meta: '14天未再错' },
      { key: 'mis_accuracy', label: '复习正确率', value: fmtPercent(accuracy), meta: `近7天复习 ${fmtCount(recentAnswered)} 题` },
      { key: 'mis_completion', label: '复习覆盖率', value: fmtPercent(completion), meta: '（错题集内）' },
      { key: 'mis_recent', label: '近7天复习', value: fmtCount(recentAnswered), meta: '基于“最后一次作答”' },
    ];
  }

  if (subtab === 'favorites') {
    const todo = Math.max(0, total - answered);
    const added = toNum((extras?.favoritesTrend || {})?.total_added);
    return [
      { key: 'fav_total', label: '收藏池', value: fmtCount(total), meta: '当前收藏题数' },
      { key: 'fav_answered', label: '已做', value: fmtCount(answered), meta: `未做 ${fmtCount(todo)} 题` },
      { key: 'fav_accuracy', label: '正确率', value: fmtPercent(accuracy), meta: `正确 ${fmtCount(correct)} / 已做 ${fmtCount(answered)}` },
      { key: 'fav_completion', label: '覆盖率', value: fmtPercent(completion), meta: `未覆盖 ${fmtPercent(100 - completion)}` },
      { key: 'fav_todo', label: '未做收藏', value: fmtCount(todo), meta: '建议优先补齐覆盖' },
      { key: 'fav_recent', label: '近7天复习', value: fmtCount(recentAnswered), meta: '基于“最后一次作答”' },
      { key: 'fav_added', label: '最近新增', value: fmtCount(added), meta: '按收藏时间统计' },
    ];
  }

  return [
    { key: 'total', label: '题库总题', value: fmtCount(total), meta: '题库规模基座' },
    { key: 'answered', label: '已做', value: fmtCount(answered), meta: `近7天作答 ${fmtCount(recentAnswered)} 题` },
    { key: 'accuracy', label: '正确率', value: fmtPercent(accuracy), meta: `正确 ${fmtCount(correct)} / 已做 ${fmtCount(answered)}` },
    { key: 'completion', label: '覆盖率', value: fmtPercent(completion), meta: `未覆盖 ${fmtPercent(100 - completion)}` },
    { key: 'mistakeTimes', label: '错题次数', value: fmtCount(mistakeTimes), meta: `错题率 ${fmtPercent(mistakeRate)} · 错题池 ${fmtCount(mistakes)} 题` },
    { key: 'favorites', label: '收藏', value: fmtCount(favorites), meta: '收藏池题数' },
    { key: 'mistakes', label: '错题池', value: fmtCount(mistakes), meta: '当前错题池' },
    { key: 'streak', label: '连刷', value: fmtCount(streakDays), meta: '近似连续活跃' },
  ];
}

function computeGauge(subtab: DataSubTab, overview: StatsOverviewView, trend: TrendView[], statsDays: number) {
  const accuracy = toNum((overview as any)?.accuracy);
  const completion = toNum((overview as any)?.completion);
  const answered = toNum((overview as any)?.answered);
  const wrong = toNum((overview as any)?.wrong);
  const activeDays = calcActiveDays(trend);
  const recentAnswered = calcRecentAnswered(trend, Math.min(7, Math.max(1, Math.floor(statsDays || 7))));

  const mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;
  let score = accuracy * 0.6 + completion * 0.4;
  if (subtab === 'mistakes') score = 100 - mistakeRate;

  const label = subtab === 'mistakes' ? '纠错指数' : subtab === 'favorites' ? '收藏掌握度' : '掌握指数';
  const avgPerActiveDay = activeDays > 0 ? recentAnswered / activeDays : 0;
  const pacePercent = clamp((avgPerActiveDay / 20) * 100, 0, 100);
  return {
    gaugeValue: String(Math.round(clamp(score, 0, 100))),
    gaugePercent: clamp(score, 0, 100),
    gaugeLabel: label,
    metricStability: clamp(accuracy, 0, 100),
    metricStabilityText: fmtPercent(accuracy),
    metricPace: clamp(pacePercent, 0, 100),
    metricPaceText: `${avgPerActiveDay.toFixed(1)}/天`
  };
}

function computeTypeChartRows(byType: TypeBreakdownView[]): TypeChartRow[] {
  const list = Array.isArray(byType) ? byType.slice() : [];
  if (!list.length) return [];

  const top = list
    .slice()
    .sort((a, b) => toNum((b as any)?.answered) - toNum((a as any)?.answered))
    .slice(0, 8);
  const maxAnswered = top.reduce((m, it) => Math.max(m, toNum((it as any)?.answered)), 0) || 0;

  return top.map((it) => {
    const correct = toNum((it as any)?.correct);
    const wrong = toNum((it as any)?.wrong);
    const correctWidth = maxAnswered > 0 ? clamp((correct / maxAnswered) * 100, 0, 100) : 0;
    const wrongWidth = maxAnswered > 0 ? clamp((wrong / maxAnswered) * 100, 0, 100) : 0;
    return {
      q_type: String((it as any)?.q_type || '未知'),
      correctWidth,
      wrongWidth,
      completionText: String((it as any)?.completionText || '0.0%')
    };
  });
}

function normalizeDifficultyText(raw: any): string {
  const n = toNum(raw);
  if (!Number.isFinite(n) || n <= 0) return '—';
  return String(Math.max(1, Math.floor(n)));
}

function normalizeResult(raw: any): { text: string; cls: string } {
  if (raw === true || raw === 1) return { text: '正确', cls: 'ok' };
  if (raw === false || raw === 0) return { text: '错误', cls: 'bad' };
  return { text: '—', cls: 'muted' };
}

function buildMistakeMatrixDots(items: StatsQuestionItem[]): MistakeMatrixDot[] {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return [];

  const sample = list.slice(0, 80);
  const maxWrong = sample.reduce((m, it) => Math.max(m, Math.max(1, toNum((it as any)?.mistake_wrong_count) || 1)), 1);
  const capWrong = clamp(maxWrong, 3, 8);
  const capDays = 30;

  const out: MistakeMatrixDot[] = [];
  sample.forEach((it) => {
    const id = Math.floor(toNum((it as any)?.id));
    if (!id) return;
    const wc = Math.max(1, toNum((it as any)?.mistake_wrong_count) || 1);
    const ds = daysSince((it as any)?.mistake_updated_at || (it as any)?.mistake_created_at);
    if (ds == null) return;

    const x = capWrong > 1 ? clamp(((Math.min(wc, capWrong) - 1) / (capWrong - 1)) * 100, 0, 100) : 0;
    const yVal = clamp((Math.min(ds, capDays) / capDays) * 100, 0, 100);
    const y = 100 - yVal;
    const level = wc >= 3 ? 3 : wc === 2 ? 2 : 1;
    out.push({ id, x, y, level });
  });

  return out;
}

function buildTopMistakes(items: StatsQuestionItem[]): TopItemView[] {
  const list = Array.isArray(items) ? items.slice() : [];
  if (!list.length) return [];

  const sorted = list
    .slice()
    .sort((a, b) => (toNum((b as any)?.mistake_wrong_count) || 1) - (toNum((a as any)?.mistake_wrong_count) || 1))
    .slice(0, 8);
  const max = sorted.reduce((m, it) => Math.max(m, toNum((it as any)?.mistake_wrong_count) || 1), 1) || 1;

  return sorted.map((it) => {
    const id = Math.floor(toNum((it as any)?.id));
    const wc = Math.max(1, toNum((it as any)?.mistake_wrong_count) || 1);
    const title = String((it as any)?.content_preview || '').trim() || `题目 #${id}`;
    const qt = String((it as any)?.q_type || '').trim() || '—';
    const lw = fmtMD((it as any)?.mistake_updated_at || (it as any)?.mistake_created_at);
    const meta = `${qt} · 最近错题 ${lw}`;
    const bar = clamp((wc / max) * 100, 0, 100);
    return { id, title, meta, count: wc, bar };
  });
}

function buildAddedBars(favTrend: FavoritesTrend): AddedBarView[] {
  const raw = Array.isArray((favTrend as any)?.trend) ? ((favTrend as any).trend as any[]) : [];
  const list = raw
    .map((it) => ({
      day: String(it?.day || ''),
      added: toNum(it?.added),
    }))
    .filter((it) => !!it.day);
  if (!list.length) return [];

  const maxAdded = list.reduce((m, it) => Math.max(m, toNum(it.added)), 0) || 0;
  const n = list.length;
  return list.map((it, idx) => {
    const label = it.day ? it.day.slice(5) : '';
    const h = maxAdded > 0 ? clamp((toNum(it.added) / maxAdded) * 100, 0, 100) : 0;
    const showLabel = idx === 0 || idx === n - 1 || (n >= 9 && idx === Math.floor(n / 2));
    return { day: it.day, label, added: toNum(it.added), h, showLabel };
  });
}

function buildMistakeRows(items: StatsQuestionItem[], limit = 50): ListRowView[] {
  const list = Array.isArray(items) ? items.slice(0, Math.max(0, limit)) : [];
  return list.map((q) => {
    const id = Math.floor(toNum((q as any)?.id));
    const content = String((q as any)?.content_preview || '').trim() || `题目 #${id}`;
    const q_type = String((q as any)?.q_type || '').trim() || '—';
    const difficultyText = normalizeDifficultyText((q as any)?.difficulty);
    const wc = Math.max(1, toNum((q as any)?.mistake_wrong_count) || 1);
    const lastWrong = fmtMDHM((q as any)?.mistake_updated_at || (q as any)?.mistake_created_at);
    const lastAnswer = fmtMDHM((q as any)?.last_answered_at);
    const res = normalizeResult((q as any)?.last_is_correct);
    return {
      id,
      content,
      q_type,
      difficultyText,
      col1: fmtCount(wc),
      col2: lastWrong,
      col3: lastAnswer,
      resultText: res.text,
      resultClass: res.cls
    };
  });
}

function buildFavoriteRows(items: StatsQuestionItem[], limit = 50): ListRowView[] {
  const list = Array.isArray(items) ? items.slice(0, Math.max(0, limit)) : [];
  return list.map((q) => {
    const id = Math.floor(toNum((q as any)?.id));
    const content = String((q as any)?.content_preview || '').trim() || `题目 #${id}`;
    const q_type = String((q as any)?.q_type || '').trim() || '—';
    const difficultyText = normalizeDifficultyText((q as any)?.difficulty);
    const favAt = fmtMDHM((q as any)?.favorite_created_at);
    const lastAnswer = fmtMDHM((q as any)?.last_answered_at);
    const res = normalizeResult((q as any)?.last_is_correct);
    return {
      id,
      content,
      q_type,
      difficultyText,
      col1: favAt,
      col2: lastAnswer,
      col3: '',
      resultText: res.text,
      resultClass: res.cls
    };
  });
}

function buildTypeDistRows(byType: TypeBreakdownView[]): TypeDistRowView[] {
  const list = Array.isArray(byType) ? byType.slice() : [];
  if (!list.length) return [];

  const sum = list.reduce((m, it) => m + Math.max(0, toNum((it as any)?.total)), 0) || 0;
  const rows = list
    .slice()
    .sort((a, b) => toNum((b as any)?.total) - toNum((a as any)?.total))
    .slice(0, 12);

  return rows.map((it) => {
    const total = Math.max(0, toNum((it as any)?.total));
    const answered = Math.max(0, toNum((it as any)?.answered));
    const accText = String((it as any)?.accuracyText || '');
    const bar = sum > 0 ? clamp((total / sum) * 100, 0, 100) : 0;
    const q_type = String((it as any)?.q_type || '未知');
    const meta = `共 ${fmtCount(total)} 题 · 已做 ${fmtCount(answered)} · 正确率 ${accText || '—'}`;
    return { q_type, total, bar, meta };
  });
}

function buildCompatByTypeStats(byType: TypeBreakdownView[]): any[] {
  const list = Array.isArray(byType) ? byType.slice() : [];
  return list.map((it) => {
    const total = Math.max(0, toNum((it as any)?.total));
    const answered = Math.max(0, toNum((it as any)?.answered));
    const correctRaw = Math.max(0, toNum((it as any)?.correct));
    const correct = Math.min(answered, correctRaw);
    const wrongRaw = toNum((it as any)?.wrong);
    const wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
    const accuracy = answered > 0 ? clamp((correct * 100) / answered, 0, 100) : 0;
    const completion = total > 0 ? clamp((answered * 100) / total, 0, 100) : 0;
    return {
      q_type: String((it as any)?.q_type || '未知'),
      total,
      answered,
      correct,
      wrong,
      favorites: Math.max(0, toNum((it as any)?.favorites)),
      mistakes: Math.max(0, toNum((it as any)?.mistakes)),
      accuracy,
      completion
    };
  });
}

function buildCompatByDifficultyStats(byDifficulty: DifficultyBreakdownView[]): any[] {
  const list = Array.isArray(byDifficulty) ? byDifficulty.slice() : [];
  return list.map((it) => {
    const label = String((it as any)?.label || (it as any)?.difficulty || '—');
    const total = Math.max(0, toNum((it as any)?.total));
    const answered = Math.max(0, toNum((it as any)?.answered));
    const correctRaw = Math.max(0, toNum((it as any)?.correct));
    const correct = Math.min(answered, correctRaw);
    const wrongRaw = toNum((it as any)?.wrong);
    const wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
    const accuracy = answered > 0 ? clamp((correct * 100) / answered, 0, 100) : 0;
    const completion = total > 0 ? clamp((answered * 100) / total, 0, 100) : 0;
    return { label, total, answered, correct, wrong, accuracy, completion };
  });
}

function buildCompatStatsPayload(
  overview: StatsOverviewView,
  trend: TrendView[],
  byType: TypeBreakdownView[],
  byDifficulty: DifficultyBreakdownView[]
) {
  const total = Math.max(0, toNum((overview as any)?.total));
  const answered = Math.max(0, toNum((overview as any)?.answered));
  const correctRaw = Math.max(0, toNum((overview as any)?.correct));
  const correct = Math.min(answered, correctRaw);
  const wrongRaw = toNum((overview as any)?.wrong);
  const wrong = Math.max(0, Number.isFinite(wrongRaw) && wrongRaw > 0 ? wrongRaw : answered - correct);
  return {
    total_count: total,
    answered,
    correct,
    wrong,
    favorites: Math.max(0, toNum((overview as any)?.favorites)),
    mistakes: Math.max(0, toNum((overview as any)?.mistakes)),
    mistakes_times: Math.max(0, toNum((overview as any)?.mistakeTimes)),
    accuracy: clamp(toNum((overview as any)?.accuracy), 0, 100),
    completion: clamp(toNum((overview as any)?.completion), 0, 100),
    streak_days: Math.max(0, toNum((overview as any)?.streakDays)),
    last_activity: String((overview as any)?.lastText || ''),
    trend: Array.isArray(trend) ? trend : [],
    by_type: buildCompatByTypeStats(byType),
    by_difficulty: buildCompatByDifficultyStats(byDifficulty),
  };
}

function resolveActiveChartIds(subtab: DataSubTab, hasDifficulty: boolean): string[] {
  if (subtab === 'mistakes') {
    return ['ubdMistakeMatrixChart', 'ubdMistakeTopChart', 'ubdMisTrendChart', 'ubdMisTypePieChart', 'ubdMisDiffChart'];
  }
  if (subtab === 'favorites') {
    return ['ubdFavAddedChart', 'ubdFavTypePieChart', 'ubdFavDiffChart', 'ubdFavReviewTrendChart'];
  }
  const ids = ['ubdCalendarChart', 'ubdGaugeChart', 'ubdTrendChart', 'ubdTypeChart', 'ubdFunnelChart', 'ubdRiskRadarChart'];
  if (hasDifficulty) ids.push('ubdDiffChart');
  return ids;
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    addGlobalClass: true
  },
  properties: {
    subjectName: { type: String, value: '' },
    totalCount: { type: Number, value: 0 },
    favCount: { type: Number, value: 0 },
    mistakeCount: { type: Number, value: 0 },

    dataSubTab: { type: String, value: 'global' },
    statsDays: { type: Number, value: 14 },
    stickyTop: { type: String, value: '0rpx' },

    statsLoading: { type: Boolean, value: false },
    statsError: { type: String, value: '' },
    statsOverview: { type: Object, value: {} },
    statsTrend: { type: Array, value: [] },
    statsByType: { type: Array, value: [] },
    statsByDifficulty: { type: Array, value: [] },
    statsHasDifficulty: { type: Boolean, value: false },
    statsAdvice: { type: Array, value: [] },

    // 错题/收藏列表与收藏新增趋势（与 Web 统计页对齐）
    statsQuestions: { type: Array, value: [] },
    favoritesTrend: { type: Object, value: {} },
  },
  data: {
    heroTotalText: '0',
    heroFavText: '0',
    heroMistakeText: '0',
    ecLazy: { lazyLoad: true },

    headlineText: '加载中…',
    updatedAtText: '—',
    kpiItems: [] as KpiItem[],

    quickStartLabel: '',

    calendarCells: [] as CalendarCell[],

    gaugeValue: '0',
    gaugePercent: 0,
    gaugeLabel: '掌握指数',
    metricStability: 0,
    metricStabilityText: '0.0%',
    metricPace: 0,
    metricPaceText: '0.0%',

    typeChartRows: [] as TypeChartRow[],
    typeTableRows: [] as TypeBreakdownView[],

    typeDistRows: [] as TypeDistRowView[],

    mistakeMatrixDots: [] as MistakeMatrixDot[],
    mistakeTopItems: [] as TopItemView[],
    mistakeRows: [] as ListRowView[],

    favoriteAddedBars: [] as AddedBarView[],
    favoriteRows: [] as ListRowView[],
  },
  observers: {
    'totalCount,favCount,mistakeCount': function (this: any) {
      this.setData({
        heroTotalText: fmtCount(this.data.totalCount),
        heroFavText: fmtCount(this.data.favCount),
        heroMistakeText: fmtCount(this.data.mistakeCount)
      });
    },
    'dataSubTab,statsDays,statsLoading,statsError,statsOverview,statsTrend,statsByType,totalCount,statsQuestions,favoritesTrend': function (this: any) {
      const rawSub = String(this.data.dataSubTab || 'global');
      const subtab: DataSubTab = rawSub === 'mistakes' || rawSub === 'favorites' ? rawSub : 'global';
      const days = Math.max(1, Math.floor(toNum(this.data.statsDays || 14)));

      const overview = (this.data.statsOverview || {}) as StatsOverviewView;
      const trend = (this.data.statsTrend || []) as TrendView[];
      const byType = (this.data.statsByType || []) as TypeBreakdownView[];
      const questions = (this.data.statsQuestions || []) as StatsQuestionItem[];
      const favTrend = (this.data.favoritesTrend || {}) as FavoritesTrend;
      const bankTotal = toNum(this.data.totalCount);

      const loading = !!this.data.statsLoading;
      const err = String(this.data.statsError || '').trim();

      let headlineText = '加载中…';
      let updatedAtText = '—';
      let kpiItems: KpiItem[] = [];
      let calendarCells: CalendarCell[] = [];
      let gauge = {
        gaugeValue: '0',
        gaugePercent: 0,
        gaugeLabel: '掌握指数',
        metricStability: 0,
        metricStabilityText: '0.0%',
        metricPace: 0,
        metricPaceText: '0.0%'
      };
      let typeChartRows: TypeChartRow[] = [];
      let typeTableRows: TypeBreakdownView[] = [];
      let typeDistRows: TypeDistRowView[] = [];
      let mistakeMatrixDots: MistakeMatrixDot[] = [];
      let mistakeTopItems: TopItemView[] = [];
      let mistakeRows: ListRowView[] = [];
      let favoriteAddedBars: AddedBarView[] = [];
      let favoriteRows: ListRowView[] = [];

      if (loading) {
        headlineText = '加载中…';
        updatedAtText = '—';
        kpiItems = computeKpis(subtab, {} as any, [], days, { bankTotal, questions, favoritesTrend: favTrend }).map((it) =>
          Object.assign({}, it, { value: '—', meta: '—' })
        );
      } else if (err) {
        headlineText = '数据加载失败，请稍后重试。';
        updatedAtText = '—';
        kpiItems = computeKpis(subtab, {} as any, [], days, { bankTotal, questions, favoritesTrend: favTrend }).map((it) =>
          Object.assign({}, it, { value: '—', meta: '—' })
        );
      } else {
        headlineText = buildHeadline(subtab, overview, trend, days);
        updatedAtText = `最近活跃：${String((overview as any)?.lastText || '—')}`;
        kpiItems = computeKpis(subtab, overview, trend, days, { bankTotal, questions, favoritesTrend: favTrend });

        if (subtab === 'global') {
          calendarCells = buildCalendarCells(trend, days);
          gauge = computeGauge(subtab, overview, trend, days);
          typeChartRows = computeTypeChartRows(byType);
          typeTableRows = Array.isArray(byType) ? byType : [];
        } else {
          typeDistRows = buildTypeDistRows(byType);
        }

        if (subtab === 'mistakes') {
          mistakeMatrixDots = buildMistakeMatrixDots(questions);
          mistakeTopItems = buildTopMistakes(questions);
          mistakeRows = buildMistakeRows(questions, 50);
        } else if (subtab === 'favorites') {
          favoriteAddedBars = buildAddedBars(favTrend);
          favoriteRows = buildFavoriteRows(questions, 50);
        }
      }

      this.setData(
        {
        headlineText,
        updatedAtText,
        kpiItems,
        calendarCells,
        typeChartRows,
        typeTableRows,
        typeDistRows,
        mistakeMatrixDots,
        mistakeTopItems,
        mistakeRows,
        favoriteAddedBars,
        favoriteRows,
        ...gauge
        },
        () => {
          try {
            this.scheduleRenderCharts(false);
          } catch (e) {}
        }
      );
    }
  },
  lifetimes: {
    ready(this: any) {
      const self: any = this as any;
      self.__charts = {};
      self.__renderTimer = null;
      self.__pendingForceInit = false;
      self.__pendingIsDark = undefined;

      self.__themeUnsub = themeManager.onThemeChange((isDark: boolean) => {
        try {
          this.scheduleRenderCharts(false, isDark);
        } catch (e) {}
      });

      this.scheduleRenderCharts(true);
    },
    detached(this: any) {
      const self: any = this as any;
      try {
        this.disposeCharts();
      } catch (e) {}

      if (typeof self.__themeUnsub === 'function') {
        try {
          self.__themeUnsub();
        } catch (e) {}
      }
      self.__themeUnsub = null;

      if (self.__renderTimer) {
        try {
          clearTimeout(self.__renderTimer);
        } catch (e) {}
        self.__renderTimer = null;
      }
    }
  },
  methods: {
    onQuickStartTap(this: any) {
      const raw = String(this.data.dataSubTab || 'global');
      const subtab: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
      if (subtab !== 'mistakes' && subtab !== 'favorites') return;
      this.triggerEvent('quickstart', { subtab });
    },
    disposeCharts(this: any) {
      const self: any = this as any;
      const charts = (self.__charts || {}) as Record<string, any>;
      Object.keys(charts).forEach((k) => {
        try {
          charts[k] && typeof charts[k].dispose === 'function' && charts[k].dispose();
        } catch (e) {}
      });
      self.__charts = {};
    },
    scheduleRenderCharts(this: any, forceInit = false, isDarkOverride?: boolean) {
      const self: any = this as any;
      if (forceInit) self.__pendingForceInit = true;
      if (typeof isDarkOverride === 'boolean') self.__pendingIsDark = isDarkOverride;
      if (self.__renderTimer) return;

      self.__renderTimer = setTimeout(() => {
        const pendingForce = !!self.__pendingForceInit;
        const pendingIsDark = typeof self.__pendingIsDark === 'boolean' ? (self.__pendingIsDark as boolean) : undefined;
        self.__pendingForceInit = false;
        self.__pendingIsDark = undefined;
        self.__renderTimer = null;
        wx.nextTick(() => {
          try {
            this.renderCharts(pendingForce, pendingIsDark);
          } catch (e) {}
        });
      }, 0);
    },
    renderCharts(this: any, forceInit = false, isDarkOverride?: boolean) {
      const raw = String(this.data.dataSubTab || 'global');
      const subtab: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
      const hasDifficulty = !!this.data.statsHasDifficulty;

      const isDark = typeof isDarkOverride === 'boolean' ? isDarkOverride : themeManager.isDarkMode();
      const style = themeManager.getStyle();
      const tokens = (ubdv2Echarts as any).getUbdv2ThemeTokens(isDark, style);

      const overview = (this.data.statsOverview || {}) as StatsOverviewView;
      const trend = (this.data.statsTrend || []) as TrendView[];
      const byType = (this.data.statsByType || []) as TypeBreakdownView[];
      const byDifficulty = (this.data.statsByDifficulty || []) as DifficultyBreakdownView[];

      const payload = {
        loading: !!this.data.statsLoading,
        error: String(this.data.statsError || '').trim(),
        stats: buildCompatStatsPayload(overview, trend, byType, byDifficulty),
        questions: (this.data.statsQuestions || []) as StatsQuestionItem[],
        favoritesTrend: (this.data.favoritesTrend || {}) as FavoritesTrend
      };

      const activeIds = resolveActiveChartIds(subtab, hasDifficulty);
      const self: any = this as any;
      const charts = (self.__charts || (self.__charts = {})) as Record<string, any>;

      Object.keys(charts).forEach((id) => {
        if (activeIds.indexOf(id) === -1) {
          try {
            charts[id] && typeof charts[id].dispose === 'function' && charts[id].dispose();
          } catch (e) {}
          delete charts[id];
        }
      });

      activeIds.forEach((id) => {
        const comp: any = this.selectComponent(`#${id}`);
        const existing = charts[id];
        if (!comp || typeof comp.init !== 'function') {
          if (existing) {
            try {
              existing.dispose && existing.dispose();
            } catch (e) {}
            delete charts[id];
          }
          return;
        }

        if (existing && !forceInit) {
          try {
            const opt = (ubdv2Echarts as any).buildUbdv2ChartOption(id, payload, tokens);
            if (opt) existing.setOption(opt, { notMerge: true, lazyUpdate: false });
            if (typeof existing.resize === 'function') existing.resize();
          } catch (e) {}
          return;
        }

        if (existing) {
          try {
            existing.dispose && existing.dispose();
          } catch (e) {}
          delete charts[id];
        }

        comp.init((canvas: any, width: number, height: number, dpr: number) => {
          const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
          canvas.setChart(chart);
          charts[id] = chart;
          try {
            const opt = (ubdv2Echarts as any).buildUbdv2ChartOption(id, payload, tokens);
            if (opt) chart.setOption(opt, { notMerge: true, lazyUpdate: false });
          } catch (e) {}
          return chart;
        });
      });
    },
    onSubTabTap(this: any, e: any) {
      const raw = String(e?.currentTarget?.dataset?.subtab || 'global');
      const subtab: DataSubTab = raw === 'mistakes' || raw === 'favorites' ? raw : 'global';
      this.triggerEvent('subtabchange', { subtab });
    },
    onDaysTap(this: any, e: any) {
      const days = Number(e?.currentTarget?.dataset?.days || 14);
      if (![7, 14, 30, 90].includes(days)) return;
      this.triggerEvent('dayschange', { days });
    },
    onQuestionTap(this: any, e: any) {
      const id = Number(e?.currentTarget?.dataset?.id || 0);
      if (!Number.isFinite(id) || id <= 0) return;
      this.triggerEvent('questiontap', { id });
    }
  }
});
