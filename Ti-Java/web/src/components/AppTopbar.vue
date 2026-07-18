<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useUiStore } from '@/stores/ui';

const route = useRoute();
const uiStore = useUiStore();
const pageTitle = computed(() =>
  typeof route.meta.title === 'string' ? route.meta.title : 'SAK',
);
</script>

<template>
  <header class="app-topbar">
    <div class="app-topbar-left">
      <button
        class="app-icon-btn app-hamburger"
        type="button"
        aria-label="打开侧边栏"
        aria-controls="app-sidebar"
        @click="uiStore.toggleAppSidebar"
      >
        <svg class="app-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
      <div class="app-topbar-title">{{ pageTitle }}</div>
    </div>

    <div class="app-topbar-center">
      <div class="app-topbar-search" aria-label="全局搜索尚未迁移">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm10 2-4.3-4.3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input type="text" placeholder="全局搜索尚未迁移" disabled />
        <span aria-hidden="true">🔒</span>
      </div>
    </div>

    <div class="app-topbar-actions">
      <RouterLink
        class="app-top-practice"
        :to="{ name: 'blocked-journey', params: { journey: 'practice' } }"
      >
        🔒 练习功能尚未迁移
      </RouterLink>
      <button class="app-icon-btn" type="button" aria-label="切换浅色或深色主题" @click="uiStore.toggleTheme">
        <span aria-hidden="true">{{ uiStore.effectiveTheme === 'dark' ? '☀' : '☾' }}</span>
      </button>
    </div>
  </header>
</template>
