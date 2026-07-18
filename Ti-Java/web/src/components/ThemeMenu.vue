<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useUiStore, type ThemeMode, type ThemeStyle } from '@/stores/ui';

const uiStore = useUiStore();
const { effectiveTheme, themeStyle } = storeToRefs(uiStore);
const modes: Array<{ label: string; value: ThemeMode }> = [
  { label: '浅色', value: 'light' },
  { label: '深色', value: 'dark' },
];
const styles: Array<{ label: string; value: ThemeStyle }> = [
  { label: '默认', value: 'default' },
  { label: '薄雾', value: 'mist' },
  { label: '沙丘', value: 'dune' },
  { label: '松林', value: 'pine' },
  { label: '青瓷', value: 'celadon' },
];

function previewTheme(mode: ThemeMode): void {
  if (mode !== 'system') document.documentElement.dataset.theme = mode;
}

function previewStyle(style: ThemeStyle): void {
  document.documentElement.dataset.themeStyle = style;
}

function restorePreview(): void {
  document.documentElement.dataset.theme = effectiveTheme.value;
  document.documentElement.dataset.themeStyle = themeStyle.value;
}
</script>

<template>
  <details class="app-theme-menu">
    <summary class="app-theme-summary">
      <span aria-hidden="true">☼</span><span class="app-theme-summary__label">外观与风格</span>
    </summary>
    <div class="app-theme-panel" @mouseleave="restorePreview">
      <fieldset>
        <legend>外观</legend>
        <button
          v-for="mode in modes"
          :key="mode.value"
          type="button"
          :class="{ active: effectiveTheme === mode.value }"
          @mouseenter="previewTheme(mode.value)"
          @mouseleave="restorePreview"
          @click="uiStore.setThemeMode(mode.value)"
        >
          {{ mode.label }}
        </button>
      </fieldset>
      <fieldset>
        <legend>风格</legend>
        <button
          v-for="style in styles"
          :key="style.value"
          type="button"
          :class="{ active: themeStyle === style.value }"
          @mouseenter="previewStyle(style.value)"
          @mouseleave="restorePreview"
          @click="uiStore.setThemeStyle(style.value)"
        >
          <span class="theme-dot" :class="`theme-dot--${style.value}`" aria-hidden="true"></span>
          {{ style.label }}
        </button>
      </fieldset>
    </div>
  </details>
</template>
