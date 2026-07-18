<script setup lang="ts">
import { RouterLink } from 'vue-router';

import type { PublicBankCard } from '@/api/generated/phase4aPublicBank/types.gen';
import HighlightedText from '@/components/HighlightedText.vue';
import DefaultBankCover from '@/features/public-bank/components/DefaultBankCover.vue';

defineProps<{
  bank: PublicBankCard;
  keyword?: string;
}>();

function formatCount(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function displayDate(value: string | null): string {
  return value || '—';
}
</script>

<template>
  <li>
    <RouterLink
      class="forum-post-card plaza-bank-card"
      :to="{
        name: 'public-bank-detail',
        params: {
          sourceType: bank.source_type === 'user_public' ? 'user' : 'system',
          bankId: String(bank.id),
        },
      }"
    >
      <div class="forum-post-header">
        <img v-if="bank.owner_avatar" class="forum-avatar" :src="bank.owner_avatar" alt="" loading="lazy" />
        <span v-else class="forum-avatar plaza-owner-avatar-fallback" aria-hidden="true">
          {{ (bank.owner_label || bank.source_label).slice(0, 1) }}
        </span>
        <div class="forum-post-meta">
          <span class="forum-user-link"><HighlightedText :text="bank.owner_label || '系统'" :query="keyword" /></span>
          <span class="forum-board-tag">{{ bank.board.name }}</span>
        </div>
      </div>

      <div class="forum-post-title">
        <span class="plaza-badge" :class="bank.source_type === 'system' ? 'system' : 'user'">
          {{ bank.source_label }}
        </span>
        <span v-if="bank.is_featured" class="forum-badge forum-badge-feat">精华</span>
        <span v-if="bank.relation.is_joined" class="plaza-badge joined">已加入</span>
        <span class="plaza-bank-title-text"><HighlightedText :text="bank.name" :query="keyword" /></span>
      </div>

      <p class="forum-post-preview">
        <HighlightedText :text="bank.description || '暂无题库简介'" :query="keyword" />
      </p>

      <div class="forum-post-stats">
        <span><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 19.5h16M7 16V8m5 8V4m5 12v-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>{{ formatCount(bank.question_count) }} 题</span>
        <span><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm14 10v-2a4 4 0 0 0-3-3.87" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>{{ formatCount(bank.participants_total) }} 参与</span>
        <span><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 3v18h18M18 17V9m-5 8V5m-5 12v-3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>{{ formatCount(bank.answer_users_7d) }} 活跃</span>
      </div>

      <time class="plaza-bank-time">发布于 {{ displayDate(bank.published_at) }}</time>
      <div v-if="bank.cover_image" class="forum-post-cover-thumb">
        <img :src="bank.cover_image" alt="" loading="lazy" />
      </div>
      <DefaultBankCover v-else :name="bank.name" :board-name="bank.board.name" />
    </RouterLink>
  </li>
</template>
