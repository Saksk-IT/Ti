<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { RouterLink } from 'vue-router';

import ThemeMenu from '@/components/ThemeMenu.vue';
import { useAuthStore } from '@/stores/auth';
import { useUiStore } from '@/stores/ui';

const authStore = useAuthStore();
const uiStore = useUiStore();
const { displayName } = storeToRefs(authStore);
const { sidebarCollapsed } = storeToRefs(uiStore);
</script>

<template>
  <aside id="app-sidebar" class="app-sidebar" aria-label="侧边栏导航">
    <div class="app-sidebar-head">
      <RouterLink class="app-brand" :to="{ name: 'public-bank-list' }" aria-label="SAK 题库广场">
        <span class="app-brand-dot" aria-hidden="true"></span>
        <span class="app-brand-text">SAK</span>
      </RouterLink>
      <button
        class="app-icon-btn app-sidebar-collapse"
        type="button"
        :aria-label="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
        @click="uiStore.toggleSidebarCollapsed"
      >
        <span aria-hidden="true">‹</span>
      </button>
    </div>

    <section class="app-cta" aria-label="练习功能状态">
      <div class="app-cta-title">练习功能尚未迁移</div>
      <p class="app-cta-meta">公共题库当前仅支持只读浏览。</p>
      <RouterLink
        class="app-btn app-btn-primary app-cta-primary"
        :to="{ name: 'blocked-journey', params: { journey: 'practice' } }"
      >
        <span aria-hidden="true">🔒</span><span class="app-btn-text">查看功能边界</span>
      </RouterLink>
    </section>

    <nav class="app-nav" aria-label="主导航">
      <section class="app-nav-section">
        <div class="app-nav-title">浏览</div>
        <RouterLink class="app-nav-item" :to="{ name: 'public-bank-list' }">
          <svg class="app-nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 6.5 12 3l8 3.5-8 3.5-8-3.5Zm0 5L12 15l8-3.5M4 16.5 12 20l8-3.5" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          <span class="app-nav-label">题库广场</span>
        </RouterLink>
      </section>

      <section class="app-nav-section">
        <div class="app-nav-title">学习</div>
        <RouterLink class="app-nav-item" :to="{ name: 'blocked-journey', params: { journey: 'practice' } }">
          <svg class="app-nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m4 20 4.4-1 10-10-3.4-3.4-10 10L4 20Zm9.5-12.9 3.4 3.4" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          <span class="app-nav-label">练习</span><span class="app-nav-lock" aria-label="未迁移">🔒</span>
        </RouterLink>
      </section>

      <section class="app-nav-section">
        <div class="app-nav-title">我的</div>
        <RouterLink class="app-nav-item" :to="{ name: 'blocked-journey', params: { journey: 'personal-banks' } }">
          <svg class="app-nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 0v9m8-4.5-8 4.5-8-4.5" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          <span class="app-nav-label">个人题库</span><span class="app-nav-lock" aria-label="未迁移">🔒</span>
        </RouterLink>
      </section>

      <section class="app-nav-section">
        <div class="app-nav-title">数据与写入</div>
        <RouterLink class="app-nav-item" :to="{ name: 'blocked-journey', params: { journey: 'user-counts' } }">
          <svg class="app-nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 19V9m6 10V4m6 15v-7m4 7H2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <span class="app-nav-label">用户计数</span><span class="app-nav-lock" aria-label="未迁移">🔒</span>
        </RouterLink>
        <RouterLink class="app-nav-item" :to="{ name: 'blocked-journey', params: { journey: 'write' } }">
          <svg class="app-nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v13m0-13 4 4m-4-4L8 7M5 21h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <span class="app-nav-label">题库写入</span><span class="app-nav-lock" aria-label="未迁移">🔒</span>
        </RouterLink>
      </section>
    </nav>

    <ThemeMenu />
    <div class="app-user" aria-label="当前身份">
      <span class="app-user-avatar" aria-hidden="true">{{ displayName.slice(0, 1) }}</span>
      <span class="app-user-text"><strong>{{ displayName }}</strong><small>只读访问</small></span>
    </div>
  </aside>
</template>
