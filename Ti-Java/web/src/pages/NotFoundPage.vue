<script setup lang="ts">
import { RouterLink } from 'vue-router';
</script>

<template>
  <div class="app-container not-found-page">
    <section class="app-card not-found-card">
      <p class="boundary-kicker">404</p>
      <h1>页面不存在</h1>
      <p>当前地址不属于已开放的公共题库只读页面。</p>
      <RouterLink class="bank-card-action-btn primary" :to="{ name: 'public-bank-list' }">
        返回题库广场
      </RouterLink>
    </section>
  </div>
</template>
