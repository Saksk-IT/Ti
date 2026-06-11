import { resolveUploadUrl } from '../../../utils/api';

export const AI_EXPLAIN_CACHE_KEY_PREFIX = 'saksk_ai_explain_v1_';

export function getAIExplainCacheKey(qid: number): string {
  return `${AI_EXPLAIN_CACHE_KEY_PREFIX}${qid}`;
}

export function readAIExplainCache(qid: number): string {
  if (!qid) return '';
  try {
    const cached: any = wx.getStorageSync(getAIExplainCacheKey(qid));
    if (!cached) return '';
    if (typeof cached === 'string') return cached;
    if (typeof cached === 'object' && typeof cached.explain === 'string') return cached.explain;
  } catch (e) {
    // ignore
  }
  return '';
}

export function writeAIExplainCache(qid: number, explain: string) {
  if (!qid) return;
  const text = (explain || '').toString().trim();
  if (!text) return;
  try {
    wx.setStorageSync(getAIExplainCacheKey(qid), { v: 1, explain: text, updatedAt: Date.now() });
  } catch (e) {
    // ignore
  }
}

export type OptionItem = {
  key: string;
  value: string;
  answerValue: string;
};

export type DisplayOption = OptionItem & {
  isSelected: boolean;
  isCorrect: boolean;
  isWrong: boolean;
  className: string;
};

export type QuestionType = '选择题' | '多选题' | '判断题' | '填空题' | '简答题' | '计算题' | string;

const OPTION_ALPHA_SEED = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const OPTION_DIGIT_SEED = '123456789';

function parseExplicitOptionPrefix(text: string): { key: string; value: string } | null {
  const match = text.match(/^([A-Za-z]|\d{1,2})\s*([、.．:：])\s*(.+)$/);
  if (!match) return null;

  const rawKey = match[1].trim();
  const delimiter = match[2];
  const value = match[3].trim();
  if (!rawKey || !value) return null;

  if (/^\d+$/.test(rawKey) && (delimiter === '.' || delimiter === '．') && /^\d/.test(value)) {
    return null;
  }

  return { key: rawKey.slice(0, 1).toUpperCase(), value };
}

function compactAlphaKey(text: string): string {
  const first = text.slice(0, 1).toUpperCase();
  const second = text.slice(1, 2);
  if (!first || OPTION_ALPHA_SEED.indexOf(first) < 0 || !second) return '';
  if (/^[A-Za-z0-9]$/.test(second)) return '';
  return first;
}

function compactDigitKey(text: string): string {
  const first = text.slice(0, 1);
  const second = text.slice(1, 2);
  if (!/^\d$/.test(first) || !second) return '';
  if (!/[\u3400-\u9fff]/.test(second)) return '';
  return first;
}

function isSequential(keys: string[], seed: string): boolean {
  if (!keys.length) return false;
  return keys.every((key, index) => key === seed.slice(index, index + 1));
}

function getCompactOptionKeys(texts: string[]): Record<number, string> {
  const keyed = texts
    .map((text, index) => ({ text, index }))
    .filter((item) => !!item.text);
  if (!keyed.length) return {};

  const alphaKeys = keyed.map((item) => compactAlphaKey(item.text));
  if (alphaKeys.every(Boolean) && isSequential(alphaKeys, OPTION_ALPHA_SEED)) {
    return keyed.reduce((acc, item, index) => {
      acc[item.index] = alphaKeys[index];
      return acc;
    }, {} as Record<number, string>);
  }

  const digitKeys = keyed.map((item) => compactDigitKey(item.text));
  if (digitKeys.every(Boolean) && isSequential(digitKeys, OPTION_DIGIT_SEED)) {
    return keyed.reduce((acc, item, index) => {
      acc[item.index] = digitKeys[index];
      return acc;
    }, {} as Record<number, string>);
  }

  return {};
}

export function normalizeOptionItems(rawOptions: any, valueFormatter: (input: any) => string = stripHtmlToText): OptionItem[] {
  let optList: any = rawOptions;

  if (typeof optList === 'string') {
    const s = optList.trim();
    if (!s) {
      optList = [];
    } else {
      try {
        optList = JSON.parse(s);
      } catch (e) {
        optList = [s];
      }
    }
  }

  if (!Array.isArray(optList)) {
    optList = [];
  }

  const texts = optList.map((item: any) => (item && typeof item === 'object' ? '' : valueFormatter(item)));
  const compactKeys = getCompactOptionKeys(texts);
  const options: OptionItem[] = [];

  optList.forEach((item: any, index: number) => {
    if (item && typeof item === 'object') {
      const rawKey = (item as Record<string, unknown>).key;
      const rawValue = (item as Record<string, unknown>).value;
      const key = String(rawKey == null ? '' : rawKey).trim();
      const value = valueFormatter(rawValue);
      if (key || value) {
        options.push({ key, value, answerValue: key || value });
      }
      return;
    }

    const s = texts[index] || '';
    if (!s) return;

    const explicit = parseExplicitOptionPrefix(s);
    if (explicit) {
      options.push({ key: explicit.key, value: explicit.value, answerValue: explicit.key });
      return;
    }

    const compactKey = compactKeys[index];
    if (compactKey) {
      const value = s.slice(1).replace(/^[\s:：,，.．、\)\]]+/, '').trim();
      options.push({ key: compactKey, value, answerValue: compactKey });
      return;
    }

    options.push({ key: '', value: s, answerValue: s });
  });

  if (options.length > 0 && options.every((x) => !(x.key || '').trim())) {
    options.forEach((x, i) => {
      x.key = OPTION_ALPHA_SEED.slice(i, i + 1) || String(i + 1);
      x.answerValue = x.key;
    });
  }

  return options;
}

export function parseIdList(raw: any, maxLen: number = 200): number[] {
  if (raw == null) return [];

  let s = String(raw || '').trim();
  try {
    if (/%[0-9A-Fa-f]{2}/.test(s)) {
      s = decodeURIComponent(s);
    }
  } catch (e) {
    // 忽略解码失败
  }
  s = s.replace(/，/g, ',').trim();
  if (!s) return [];

  const parts = s.split(',').map((x) => String(x || '').trim()).filter(Boolean);
  const out: number[] = [];
  const seen = new Set<number>();

  for (const p of parts) {
    if (out.length >= maxLen) break;
    const n = Number(p);
    if (!Number.isFinite(n) || n <= 0) continue;
    const id = Math.floor(n);
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }

  return out;
}

export function safeFromCodePoint(n: number): string {
  if (!Number.isFinite(n) || n <= 0 || n > 0x10ffff) return '';
  try {
    return String.fromCodePoint(n);
  } catch (e) {
    return '';
  }
}

export function decodeHtmlEntities(input: any): string {
  const s = String(input || '');
  if (!s) return '';
  if (!s.includes('&') && !s.includes('&#')) return s;

  return s
    .replace(/&nbsp;/g, ' ')
    .replace(/&emsp;/g, '  ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => safeFromCodePoint(parseInt(hex, 16)))
    .replace(/&#([0-9]+);/g, (_, num) => safeFromCodePoint(parseInt(num, 10)));
}

export function stripHtmlToText(input: any): string {
  const raw = String(input || '');
  if (!raw) return '';

  const s0 = raw.replace(/\r\n/g, '\n');
  const looksLikeHtml = /<\/?[a-z][\s>]/i.test(s0);
  let out = s0;

  if (looksLikeHtml) {
    out = out
      .replace(/<\s*(script|style)\b[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
      .replace(/<\s*br\s*\/?\s*>/gi, '\n')
      .replace(/<\/\s*(p|div|pre|code|blockquote|h[1-6])\s*>/gi, '\n')
      .replace(/<\/\s*li\s*>/gi, '\n')
      .replace(/<\s*li\b[^>]*>/gi, '\n- ')
      .replace(/<\s*img\b[^>]*>/gi, '')
      .replace(/<[^>]+>/g, '');
  }

  out = decodeHtmlEntities(out);
  out = out
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return out;
}

export function uniqUrls(urls: string[]): string[] {
  const set = new Set<string>();
  const out: string[] = [];
  (urls || []).forEach((u) => {
    const v = String(u || '').trim();
    if (!v || set.has(v)) return;
    set.add(v);
    out.push(v);
  });
  return out;
}

export function resolveInlineUrl(src: string): string {
  const raw = String(src || '').trim();
  if (!raw) return '';
  if (raw.startsWith('data:') || raw.startsWith('blob:')) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith('//')) return `https:${raw}`;
  return resolveUploadUrl(raw);
}

export function extractInlineImageUrls(content: any): string[] {
  const raw = String(content || '');
  if (!raw) return [];

  const out: string[] = [];

  // HTML <img src="...">
  const imgRe = /<\s*img\b[^>]*\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))/gi;
  let m: RegExpExecArray | null = null;
  while ((m = imgRe.exec(raw))) {
    const src = decodeHtmlEntities((m[1] || m[2] || m[3] || '').trim());
    const url = resolveInlineUrl(src);
    if (url) out.push(url);
  }

  // Markdown ![alt](url)
  const mdRe = /!\[[^\]]*]\(([^)\s]+)(?:\s+[^)]*)?\)/g;
  while ((m = mdRe.exec(raw))) {
    const src = decodeHtmlEntities(String(m[1] || '').trim().replace(/^['"]|['"]$/g, ''));
    const url = resolveInlineUrl(src);
    if (url) out.push(url);
  }

  return uniqUrls(out);
}
