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


