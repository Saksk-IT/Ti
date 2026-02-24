// URL 工具函数（从 api-endpoints.ts 提取）
import { config, getWxPlatform } from './config';

export function getApiBaseUrl(): string {
  return config.getApiUrl();
}

function getApiOriginFromBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/api\/?$/, '');
}

export function getApiOrigin(): string {
  return getApiOriginFromBaseUrl(getApiBaseUrl());
}

function isPrivateHostname(hostname: string): boolean {
  const h = String(hostname || '').trim().toLowerCase();
  if (!h) return true;
  if (h === 'localhost') return true;
  if (h.endsWith('.local')) return true;

  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const a = Number(m[1]);
  const b = Number(m[2]);
  const c = Number(m[3]);
  const d = Number(m[4]);
  if (![a, b, c, d].every((n) => Number.isFinite(n) && n >= 0 && n <= 255)) return false;

  if (a === 127) return true;
  if (a === 10) return true;
  if (a === 192 && b === 168) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 169 && b === 254) return true;
  return false;
}

export function maybeUpgradeToHttps(url: string): string {
  const raw = String(url || '').trim();
  if (!/^http:\/\//i.test(raw)) return raw;

  try {
    if (getWxPlatform() === 'devtools') return raw;
  } catch (e) {}

  const noScheme = raw.replace(/^http:\/\//i, '');
  const slashIdx = noScheme.indexOf('/');
  const hostPort = slashIdx === -1 ? noScheme : noScheme.slice(0, slashIdx);
  const rest = slashIdx === -1 ? '' : noScheme.slice(slashIdx);
  if (!hostPort) return raw;

  const parts = hostPort.split(':');
  const host = String(parts[0] || '').trim();
  const portRaw = parts.length > 1 ? String(parts[1] || '').trim() : '';
  const portNum = portRaw ? Number(portRaw) : NaN;
  const port =
    Number.isFinite(portNum) && portNum > 0 && portNum <= 65535 ? Math.floor(portNum) : undefined;

  if (!host) return raw;
  if (isPrivateHostname(host)) return raw;

  if (typeof port === 'number' && port !== 80) return raw;

  const finalHostPort = typeof port === 'number' && port === 80 ? host : hostPort;
  return `https://${finalHostPort}${rest}`;
}

// 将后端存储的相对路径转换为可访问的完整 URL
export function resolveUploadUrl(input: any): string {
  const API_ORIGIN = maybeUpgradeToHttps(getApiOrigin());
  if (input == null) return '';
  const raw = String(input).trim();
  if (!raw || raw === '[]') return '';
  if (/^https?:\/\//i.test(raw)) return maybeUpgradeToHttps(raw);

  if (raw.startsWith('/uploads/')) return `${API_ORIGIN}${raw}`;
  if (raw.startsWith('uploads/')) return `${API_ORIGIN}/${raw}`;
  if (raw.startsWith('/')) return `${API_ORIGIN}${raw}`;

  return `${API_ORIGIN}/uploads/${raw}`;
}

// 兼容 image_path 可能为：单路径字符串、JSON 数组字符串、数组
export function normalizeImageUrls(imagePath: any): string[] {
  if (imagePath == null) return [];

  if (Array.isArray(imagePath)) {
    return imagePath
      .map((p) => resolveUploadUrl(p))
      .filter((p) => typeof p === 'string' && p.length > 0);
  }

  const raw = String(imagePath).trim();
  if (!raw || raw === '[]') return [];

  if (raw.startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed
          .map((p) => resolveUploadUrl(p))
          .filter((p) => typeof p === 'string' && p.length > 0);
      }
      if (typeof parsed === 'string') {
        const url = resolveUploadUrl(parsed);
        return url ? [url] : [];
      }
    } catch (e) {
      // 忽略 JSON 解析失败，走单路径兜底
    }
  }

  const url = resolveUploadUrl(raw);
  return url ? [url] : [];
}
