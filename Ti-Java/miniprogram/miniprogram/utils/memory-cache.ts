type CacheItem<T = any> = {
  value: T;
  expiresAt: number;
};

class MemoryCache {
  private store = new Map<string, CacheItem>();

  get<T = any>(key: string): T | null {
    const item = this.store.get(key);
    if (!item) return null;
    if (item.expiresAt > 0 && item.expiresAt <= Date.now()) {
      this.store.delete(key);
      return null;
    }
    return item.value as T;
  }

  set<T = any>(key: string, value: T, ttlMs: number = 0): void {
    const ttl = Number(ttlMs) || 0;
    const expiresAt = ttl > 0 ? Date.now() + ttl : 0;
    this.store.set(key, { value, expiresAt });
  }

  del(key: string): void {
    this.store.delete(key);
  }

  clear(prefix?: string): void {
    if (!prefix) {
      this.store.clear();
      return;
    }
    const p = String(prefix);
    Array.from(this.store.keys()).forEach((k) => {
      if (k.startsWith(p)) this.store.delete(k);
    });
  }

  async remember<T = any>(key: string, ttlMs: number, loader: () => Promise<T>): Promise<T> {
    const hit = this.get<T>(key);
    if (hit !== null) return hit;
    const value = await loader();
    this.set(key, value, ttlMs);
    return value;
  }
}

export const memoryCache = new MemoryCache();
