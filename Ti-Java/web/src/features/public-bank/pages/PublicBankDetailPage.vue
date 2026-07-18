<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query';
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import type {
  PublicBankDetailParams,
  PublicBankSource,
} from '@/api/facade/publicBankFacade';
import { ApiProblem, normalizeApiProblem } from '@/api/transport/apiProblem';
import AsyncState from '@/components/AsyncState.vue';
import RequestIdNote from '@/components/RequestIdNote.vue';
import DefaultBankCover from '@/features/public-bank/components/DefaultBankCover.vue';
import { publicBankDetailQuery } from '@/features/public-bank/queries';
import NotFoundPage from '@/pages/NotFoundPage.vue';

const route = useRoute();

function routeParam(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

const detailParams = computed<PublicBankDetailParams | undefined>(() => {
  const sourceType = routeParam(route.params.sourceType);
  const bankId = routeParam(route.params.bankId);
  if (
    (sourceType !== 'system' && sourceType !== 'user') ||
    !/^\p{Decimal_Number}+$/u.test(bankId)
  ) {
    return undefined;
  }
  return {
    sourceType: sourceType === 'user' ? 'user_public' : 'system',
    bankId,
  };
});

const safeParams = computed<PublicBankDetailParams>(() =>
  detailParams.value ?? { sourceType: 'system', bankId: '0' },
);
const detailQuery = useQuery(
  computed(() => publicBankDetailQuery(safeParams.value, detailParams.value !== undefined)),
);
const bank = computed(() => detailQuery.data.value?.bank);
const problem = computed(() => {
  if (!detailQuery.error.value) return undefined;
  return detailQuery.error.value instanceof ApiProblem
    ? detailQuery.error.value
    : normalizeApiProblem(detailQuery.error.value);
});

function formatCount(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function displayDate(value: string | null): string {
  return value || '—';
}

function sourceBadgeClass(sourceType: PublicBankSource): string {
  return sourceType === 'system' ? 'system' : 'user';
}

function joinLabel(mode: string | undefined): string {
  if (mode === 'member') return '会员加入';
  if (mode === 'paid') return '付费加入';
  if (mode === 'approval') return '申请加入';
  return '免费加入';
}
</script>

<template>
  <NotFoundPage v-if="!detailParams" />
  <div v-else class="app-container">
    <div id="public-bank-detail" class="bank-card-shell">
      <RouterLink class="back-link" :to="{ name: 'public-bank-list' }">← 返回题库广场</RouterLink>

      <AsyncState v-if="detailQuery.isPending.value" mode="loading" />
      <AsyncState
        v-else-if="detailQuery.isError.value"
        mode="error"
        :message="problem?.message"
        :request-id="problem?.requestId"
        @retry="detailQuery.refetch"
      />

      <template v-else-if="bank">
        <section class="app-card bank-card-hero">
          <div class="bank-card-cover">
            <img v-if="bank.cover_image" class="bank-card-cover__image" :src="bank.cover_image" alt="" />
            <DefaultBankCover v-else :name="bank.name" :board-name="bank.board.name" />
          </div>
          <div class="bank-card-main">
            <div class="bank-card-badges">
              <span class="plaza-badge" :class="sourceBadgeClass(bank.source_type)">
                {{ bank.source_label }}
              </span>
              <span v-if="bank.is_featured" class="plaza-badge featured">精华</span>
              <span v-if="bank.relation.is_joined" class="plaza-badge joined">已加入</span>
              <span v-if="bank.allow_copy" class="plaza-badge user">可复制</span>
            </div>
            <h1>{{ bank.name }}</h1>
            <p class="bank-card-sub">{{ bank.description || '暂无题库简介' }}</p>
            <div class="bank-card-meta">
              <span class="app-pill">创建者 {{ bank.owner_label || '系统题库' }}</span>
              <span class="app-pill">板块 {{ bank.board.name }}</span>
              <span class="app-pill">题量 {{ formatCount(bank.question_count) }}</span>
            </div>
          </div>
        </section>

        <section class="bank-card-layout">
          <div class="bank-card-content">
            <section class="app-card bank-card-panel">
              <h2>题库介绍</h2>
              <div class="bank-card-rich">
                {{ bank.description || '暂无更详细的名片介绍。' }}
              </div>
            </section>

            <section class="app-card bank-card-panel">
              <h2>加入方式</h2>
              <div class="bank-card-join-mode">{{ joinLabel(bank.join_mode) }}</div>
              <p id="blocked-action-help" class="bank-card-join-note">
                {{ bank.join_note || '确认加入后，该题库会进入“我的题库”。' }}
              </p>
              <p class="bank-card-boundary-note">
                当前只开放题库浏览；加入和练习功能正在迁移，因此暂不可操作。
              </p>
              <div class="bank-card-actions">
                <button class="bank-card-action-btn primary" type="button" disabled aria-describedby="blocked-action-help">
                  🔒 加入题库
                </button>
                <button class="bank-card-action-btn" type="button" disabled aria-describedby="blocked-action-help">
                  🔒 开始练习
                </button>
                <RouterLink class="bank-card-action-btn" :to="{ name: 'feature-boundaries' }">
                  了解功能边界
                </RouterLink>
              </div>
            </section>
          </div>

          <aside class="bank-card-side">
            <section class="app-card bank-card-panel">
              <h2>题库信息</h2>
              <div class="bank-card-info-list">
                <div class="bank-card-info-item">
                  <div class="k">发布时间</div><div class="v">{{ displayDate(bank.published_at) }}</div>
                </div>
                <div class="bank-card-info-item">
                  <div class="k">最近活跃</div><div class="v">{{ displayDate(bank.last_activity_at) }}</div>
                </div>
                <div class="bank-card-info-item">
                  <div class="k">总参与人数</div><div class="v">{{ formatCount(bank.participants_total) }}</div>
                </div>
                <div class="bank-card-info-item">
                  <div class="k">近 7 天活跃</div><div class="v">{{ formatCount(bank.answer_users_7d) }}</div>
                </div>
                <div class="bank-card-info-item">
                  <div class="k">加入方式</div><div class="v">{{ joinLabel(bank.join_mode) }}</div>
                </div>
              </div>
            </section>
          </aside>
        </section>

        <RequestIdNote :request-id="detailQuery.data.value?.requestId" />
      </template>
    </div>
  </div>
</template>
