const AVATAR_REV_KEY = 'avatar_rev_v1';

export function getAvatarRev(): string {
  try {
    const v = wx.getStorageSync(AVATAR_REV_KEY);
    return v == null ? '' : String(v);
  } catch (e) {
    return '';
  }
}

export function bumpAvatarRev(): string {
  const rev = String(Date.now());
  try {
    wx.setStorageSync(AVATAR_REV_KEY, rev);
  } catch (e) {}
  return rev;
}

export function decorateAvatarUrl(url: any): string {
  const raw = String(url || '').trim();
  if (!raw) return '';

  const rev = getAvatarRev().trim();
  if (!rev) return raw;

  const sep = raw.includes('?') ? '&' : '?';
  return `${raw}${sep}v=${encodeURIComponent(rev)}`;
}

