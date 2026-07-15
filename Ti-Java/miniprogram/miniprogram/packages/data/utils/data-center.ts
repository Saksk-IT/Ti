export type TrendBar = {
  day: string;
  total: number;
  correct: number;
  accuracy: number;
  barPct: number;
  fillPct: number;
};

export type HeatmapRow = { dayIndex: number; cells: Array<{ level: number; value: number }> };

export function normalizeDays(input: any): 7 | 30 | 90 {
  const n = Number(input || 30);
  if (n === 7 || n === 30 || n === 90) return n;
  return 30;
}

export function toInt(v: any): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

export function pct1(v: any): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.round(n * 10) / 10;
}

export function buildTrendBars(dailyRaw: any[], dailyMax: number): TrendBar[] {
  const max = Math.max(toInt(dailyMax), 1);
  const rows = Array.isArray(dailyRaw) ? dailyRaw : [];
  return rows.map((d: any) => {
    const total = toInt(d?.total);
    const correct = toInt(d?.correct);
    const acc = pct1(d?.accuracy);
    const barPct = max > 0 ? pct1((total * 100) / max) : 0;
    const fillPct = total > 0 ? pct1((correct * 100) / total) : 0;
    return {
      day: String(d?.day || ''),
      total,
      correct,
      accuracy: acc,
      barPct,
      fillPct
    };
  });
}

export function buildHeatmapGrid(all: any, maxValue?: number): HeatmapRow[] {
  const max = Math.max(toInt(maxValue), 1);
  const grid: number[][] = Array.from({ length: 7 }, () => Array.from({ length: 24 }, () => 0));
  const rows = Array.isArray(all) ? all : [];
  rows.forEach((item: any) => {
    if (!item || item.length < 3) return;
    const day = toInt(item[0]);
    const hour = toInt(item[1]);
    const val = toInt(item[2]);
    if (day < 0 || day > 6) return;
    if (hour < 0 || hour > 23) return;
    grid[day][hour] = val;
  });

  return grid.map((row, dayIndex) => ({
    dayIndex,
    cells: row.map((val) => {
      const level = val <= 0 ? 0 : Math.min(4, Math.ceil((val / max) * 4));
      return { level, value: val };
    })
  }));
}

export function buildTopMix(subjects: any[], banks: any[], limit: number = 8) {
  const items: Array<{ name: string; answered: number; accuracy: number }> = [];
  (Array.isArray(subjects) ? subjects : []).forEach((s: any) => {
    const name = s?.subject ? String(s.subject) : '公共题库';
    items.push({ name: `公·${name}`, answered: toInt(s?.answered), accuracy: pct1(s?.accuracy) });
  });
  (Array.isArray(banks) ? banks : []).forEach((b: any) => {
    const name = b?.name ? String(b.name) : '个人题库';
    items.push({ name: `个·${name}`, answered: toInt(b?.answered), accuracy: pct1(b?.accuracy) });
  });
  return items.sort((a, b) => b.answered - a.answered).slice(0, limit);
}

