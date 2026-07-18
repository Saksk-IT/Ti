<script setup lang="ts">
import { RouterLink } from 'vue-router';

import type {
  PublicBankBoard,
  PublicBankCard,
  PublicBankSummary,
} from '@/api/generated/phase4aPublicBank/types.gen';
import HighlightedText from '@/components/HighlightedText.vue';

interface SidebarProblem {
  message: string;
  requestId?: string;
}

defineProps<{
  activeBoardId: string;
  boardsError?: SidebarProblem;
  boardsLoading?: boolean;
  boards: PublicBankBoard[];
  hotError?: SidebarProblem;
  hotLoading?: boolean;
  hotItems: PublicBankCard[];
  keyword?: string;
  summaryError?: SidebarProblem;
  summaryLoading?: boolean;
  summary?: PublicBankSummary;
}>();

const emit = defineEmits<{
  retryBoards: [];
  retryHot: [];
  retrySummary: [];
  selectBoard: [id: string];
}>();

function formatCount(value: number | undefined): string {
  return value === undefined ? '—' : new Intl.NumberFormat('zh-CN').format(value);
}
</script>

<template>
  <div class="sidebar-content" :aria-busy="boardsLoading || hotLoading || summaryLoading">
    <section class="sidebar-card">
      <h2 class="sidebar-card-title">题库板块</h2>
      <div v-if="boardsError" class="sidebar-slice-error" role="status">
        <p>{{ boardsError.message }}</p>
        <small v-if="boardsError.requestId">请求 ID：{{ boardsError.requestId }}</small>
        <button type="button" @click="emit('retryBoards')">重试</button>
      </div>
      <p v-else-if="boardsLoading" class="sidebar-placeholder">正在加载板块…</p>
      <ul v-else class="sidebar-board-list">
        <li>
          <button
            class="sidebar-board-item"
            :class="{ active: !activeBoardId }"
            type="button"
            @click="emit('selectBoard', '')"
          >
            <span>全部</span><span class="sidebar-board-count">{{ formatCount(summary?.total_banks) }}</span>
          </button>
        </li>
        <li v-for="board in boards" :key="board.id">
          <button
            class="sidebar-board-item"
            :class="{ active: activeBoardId === String(board.id) }"
            type="button"
            @click="emit('selectBoard', String(board.id))"
          >
            <span>{{ board.name }}</span><span class="sidebar-board-count">{{ formatCount(board.bank_count) }}</span>
          </button>
        </li>
      </ul>
    </section>

    <section class="sidebar-card">
      <h2 class="sidebar-card-title">热门题库</h2>
      <div v-if="hotError" class="sidebar-slice-error" role="status">
        <p>{{ hotError.message }}</p>
        <small v-if="hotError.requestId">请求 ID：{{ hotError.requestId }}</small>
        <button type="button" @click="emit('retryHot')">重试</button>
      </div>
      <p v-else-if="hotLoading" class="sidebar-placeholder">正在加载热门题库…</p>
      <div v-else-if="hotItems.length">
        <RouterLink
          v-for="bank in hotItems"
          :key="`${bank.source_type}-${bank.id}`"
          class="sidebar-hot-item plaza-hot-item"
          :to="{
            name: 'public-bank-detail',
            params: {
              sourceType: bank.source_type === 'user_public' ? 'user' : 'system',
              bankId: String(bank.id),
            },
          }"
        >
          <strong class="hot-title"><HighlightedText :text="bank.name" :query="keyword" /></strong>
          <span class="hot-stats">{{ formatCount(bank.question_count) }} 题 · {{ formatCount(bank.participants_total) }} 参与</span>
        </RouterLink>
      </div>
      <p v-else class="sidebar-placeholder">暂无热门题库</p>
    </section>

    <section class="sidebar-card">
      <h2 class="sidebar-card-title">题库统计</h2>
      <div v-if="summaryError" class="sidebar-slice-error" role="status">
        <p>{{ summaryError.message }}</p>
        <small v-if="summaryError.requestId">请求 ID：{{ summaryError.requestId }}</small>
        <button type="button" @click="emit('retrySummary')">重试</button>
      </div>
      <p v-else-if="summaryLoading" class="sidebar-placeholder">正在加载统计…</p>
      <div v-else class="sidebar-stats">
        <div class="stat-item"><strong>{{ formatCount(summary?.total_banks) }}</strong><span>题库</span></div>
        <div class="stat-item"><strong>{{ formatCount(summary?.total_questions) }}</strong><span>题量</span></div>
        <div class="stat-item"><strong>{{ formatCount(summary?.new_banks_7d) }}</strong><span>近 7 天新增</span></div>
        <div class="stat-item"><strong>{{ formatCount(summary?.active_users_7d) }}</strong><span>近 7 天活跃</span></div>
      </div>
    </section>
  </div>
</template>
