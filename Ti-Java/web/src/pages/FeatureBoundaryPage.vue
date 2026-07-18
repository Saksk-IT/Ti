<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

const route = useRoute();

const journeys = {
  join: {
    title: '加入题库',
    description: '加入功能正在迁移，当前可先浏览题库内容，暂不能建立或取消加入关系。',
  },
  practice: {
    title: '练习',
    description: '练习与答题功能正在迁移，当前暂不能开始或继续练习。',
  },
  'personal-banks': {
    title: '个人题库',
    description: '个人题库的查看、编辑和管理功能正在迁移，当前暂不可用。',
  },
  'user-counts': {
    title: '用户计数',
    description: '用户统计功能尚未开放，当前页面不会展示不完整或未经确认的数据。',
  },
  write: {
    title: '写入操作',
    description: '创建、编辑、复制和分享等操作正在迁移，当前全部保持禁用。',
  },
} as const;

type JourneyKey = keyof typeof journeys;
const selectedJourney = computed(() => {
  const key = typeof route.params.journey === 'string' ? route.params.journey : '';
  return key in journeys ? journeys[key as JourneyKey] : undefined;
});
</script>

<template>
  <div class="app-container boundary-page">
    <header class="app-card boundary-hero">
      <p class="boundary-kicker">功能迁移中</p>
      <h1>{{ selectedJourney?.title ?? '当前功能边界' }}</h1>
      <p>
        {{ selectedJourney?.description ?? '当前生产范围只有已迁移公共题库的列表与详情只读浏览。' }}
      </p>
    </header>

    <section class="boundary-grid" aria-label="尚未迁移的用户旅程">
      <article v-for="journey in journeys" :key="journey.title" class="app-card boundary-card">
        <span class="boundary-card__lock" aria-hidden="true">🔒</span>
        <div>
          <h2>{{ journey.title }}</h2>
          <p>{{ journey.description }}</p>
        </div>
      </article>
    </section>

    <aside class="app-card no-fallback-notice">
      <strong>当前操作暂不可用</strong>
      <p>页面会留在当前应用中，不会跳转到功能不完整的旧入口。</p>
    </aside>

    <RouterLink class="bank-card-action-btn" :to="{ name: 'public-bank-list' }">
      返回题库广场
    </RouterLink>
  </div>
</template>
