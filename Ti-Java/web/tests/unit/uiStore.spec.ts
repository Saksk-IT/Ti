import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUiStore } from '@/stores/ui';

function installMatchMedia(matches = false): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

describe('UI preferences', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    installMatchMedia();
  });

  it('沿用旧应用的三个 localStorage 键并恢复外观', () => {
    window.localStorage.setItem('theme', 'dark');
    window.localStorage.setItem('app_theme_style_v1', 'pine');
    window.localStorage.setItem('sidebar_collapsed', '1');

    const store = useUiStore();
    store.initializeUiPreferences();

    expect(store.themeMode).toBe('dark');
    expect(store.themeStyle).toBe('pine');
    expect(store.sidebarCollapsed).toBe(true);
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.documentElement.dataset.themeStyle).toBe('pine');
    expect(document.documentElement.classList.contains('sidebar-collapsed')).toBe(true);
  });

  it('只持久化 UI 偏好，不在 Pinia 中承载服务端题库数据', () => {
    const store = useUiStore();
    store.initializeUiPreferences();
    store.setThemeMode('light');
    store.setThemeStyle('celadon');
    store.toggleSidebarCollapsed();

    expect(window.localStorage.getItem('theme')).toBe('light');
    expect(window.localStorage.getItem('app_theme_style_v1')).toBe('celadon');
    expect(window.localStorage.getItem('sidebar_collapsed')).toBe('1');
    expect(Object.keys(store)).not.toContain('banks');
    expect(Object.keys(store)).not.toContain('userCounts');
  });
});
