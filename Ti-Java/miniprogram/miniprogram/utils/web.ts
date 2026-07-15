import { safeNavigate, NavType } from './nav';

export function normalizeWebNextPath(next: any, fallback: string = '/hub'): string {
  const raw = String(next || '').trim();
  const base = raw || String(fallback || '/hub').trim() || '/hub';
  return base.startsWith('/') ? base : `/${base}`;
}

export function buildWebFrontendUrl(next: any): string {
  const path = normalizeWebNextPath(next, '/hub');
  return `/pages/web-frontend/web-frontend?next=${encodeURIComponent(path)}`;
}

export function openWebFrontend(next: any, navType: NavType = 'navigateTo'): void {
  safeNavigate(buildWebFrontendUrl(next), navType);
}

export type OpenWebModalOptions = {
  title?: string;
  content: string;
  next: any;
  confirmText?: string;
  cancelText?: string;
  navType?: NavType;
};

export function showOpenWebModal(options: OpenWebModalOptions): Promise<boolean> {
  const title = String(options?.title || '请前往网页端').trim() || '请前往网页端';
  const content = String(options?.content || '').trim();
  const next = normalizeWebNextPath(options?.next, '/hub');
  const confirmText = String(options?.confirmText || '打开网页端').trim() || '打开网页端';
  const cancelText = String(options?.cancelText || '取消').trim() || '取消';
  const navType = (options?.navType || 'navigateTo') as NavType;

  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmText,
      cancelText,
      success: (res) => {
        if (res.confirm) {
          openWebFrontend(next, navType);
          resolve(true);
          return;
        }
        resolve(false);
      },
      fail: () => resolve(false)
    });
  });
}

