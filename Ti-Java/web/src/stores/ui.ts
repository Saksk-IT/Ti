import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export type ThemeMode = 'system' | 'light' | 'dark';
export type ThemeStyle = 'default' | 'mist' | 'dune' | 'pine' | 'celadon';

const themeStyles: readonly ThemeStyle[] = ['default', 'mist', 'dune', 'pine', 'celadon'];

export const useUiStore = defineStore('ui', () => {
  const appSidebarOpen = ref(false);
  const plazaDrawerOpen = ref(false);
  const sidebarCollapsed = ref(false);
  const themeMode = ref<ThemeMode>('system');
  const themeStyle = ref<ThemeStyle>('default');
  const systemPrefersDark = ref(false);
  const effectiveTheme = computed<'light' | 'dark'>(() =>
    themeMode.value === 'system'
      ? systemPrefersDark.value
        ? 'dark'
        : 'light'
      : themeMode.value,
  );

  let initialized = false;

  function applyRootPreferences(): void {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.theme = effectiveTheme.value;
    document.documentElement.dataset.themeStyle = themeStyle.value;
    document.documentElement.classList.toggle('sidebar-collapsed', sidebarCollapsed.value);
  }

  function initializeUiPreferences(): void {
    if (initialized || typeof window === 'undefined') return;
    initialized = true;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    systemPrefersDark.value = media.matches;
    media.addEventListener('change', (event) => {
      systemPrefersDark.value = event.matches;
      applyRootPreferences();
    });

    const savedTheme = window.localStorage.getItem('theme');
    themeMode.value = savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system';
    const savedStyle = window.localStorage.getItem('app_theme_style_v1');
    themeStyle.value = themeStyles.includes(savedStyle as ThemeStyle)
      ? (savedStyle as ThemeStyle)
      : 'default';
    sidebarCollapsed.value = window.localStorage.getItem('sidebar_collapsed') === '1';
    applyRootPreferences();
  }

  function setThemeMode(mode: ThemeMode): void {
    themeMode.value = mode;
    if (typeof window !== 'undefined') {
      if (mode === 'system') window.localStorage.removeItem('theme');
      else window.localStorage.setItem('theme', mode);
    }
    applyRootPreferences();
  }

  function setThemeStyle(style: ThemeStyle): void {
    themeStyle.value = style;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('app_theme_style_v1', style);
    }
    applyRootPreferences();
  }

  function toggleTheme(): void {
    setThemeMode(effectiveTheme.value === 'dark' ? 'light' : 'dark');
  }

  function toggleSidebarCollapsed(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value ? '1' : '0');
    }
    applyRootPreferences();
  }

  function closeAppSidebar(): void {
    appSidebarOpen.value = false;
  }

  function toggleAppSidebar(): void {
    appSidebarOpen.value = !appSidebarOpen.value;
  }

  function closePlazaDrawer(): void {
    plazaDrawerOpen.value = false;
  }

  function togglePlazaDrawer(): void {
    plazaDrawerOpen.value = !plazaDrawerOpen.value;
  }

  function closeMobileNavigation(): void {
    closeAppSidebar();
    closePlazaDrawer();
  }

  return {
    appSidebarOpen,
    closeAppSidebar,
    closeMobileNavigation,
    closePlazaDrawer,
    effectiveTheme,
    initializeUiPreferences,
    plazaDrawerOpen,
    setThemeMode,
    setThemeStyle,
    sidebarCollapsed,
    themeMode,
    themeStyle,
    toggleAppSidebar,
    togglePlazaDrawer,
    toggleSidebarCollapsed,
    toggleTheme,
  };
});
