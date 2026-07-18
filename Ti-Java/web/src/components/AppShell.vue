<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { watch } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import AppSidebar from '@/components/AppSidebar.vue';
import AppTopbar from '@/components/AppTopbar.vue';
import { useUiStore } from '@/stores/ui';

const route = useRoute();
const uiStore = useUiStore();
const { appSidebarOpen, sidebarCollapsed } = storeToRefs(uiStore);

uiStore.initializeUiPreferences();
watch(
  () => route.fullPath,
  () => uiStore.closeMobileNavigation(),
);
</script>

<template>
  <a class="app-skip-link" href="#main">跳到主要内容</a>
  <div
    class="app-shell"
    :class="{
      'sidebar-collapsed': sidebarCollapsed,
      'sidebar-open': appSidebarOpen,
    }"
  >
    <AppSidebar />
    <div class="app-body">
      <AppTopbar />
      <main id="main" class="app-main" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
  <button
    class="app-overlay"
    :class="{ open: appSidebarOpen }"
    type="button"
    aria-label="关闭侧边栏"
    @click="uiStore.closeAppSidebar"
  ></button>
</template>
