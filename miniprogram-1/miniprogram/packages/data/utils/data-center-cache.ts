type CacheEntry = { at: number; res: any };

const TTL_MS = 60 * 1000;
const cache: Record<string, CacheEntry> = Object.create(null);

function toKey(days: any): string {
  const n = Number(days || 0);
  if (!Number.isFinite(n) || n <= 0) return '';
  return String(Math.trunc(n));
}

export function getCachedDataCenter(days: any): any | null {
  const key = toKey(days);
  if (!key) return null;
  const entry = cache[key];
  if (!entry) return null;
  if (Date.now() - entry.at > TTL_MS) return null;
  return entry.res;
}

export function setCachedDataCenter(days: any, res: any): void {
  const key = toKey(days);
  if (!key) return;
  cache[key] = { at: Date.now(), res };
}

export function clearCachedDataCenter(days?: any): void {
  if (days == null) {
    Object.keys(cache).forEach((k) => delete cache[k]);
    return;
  }
  const key = toKey(days);
  if (!key) return;
  delete cache[key];
}

