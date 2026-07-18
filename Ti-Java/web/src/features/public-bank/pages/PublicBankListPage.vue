<script setup lang="ts">
import { useInfiniteQuery, useQuery } from '@tanstack/vue-query';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import type {
  PublicBankCatalogFilters,
  PublicBankListParams,
  PublicBankTab,
} from '@/api/facade/publicBankFacade';
import { ApiProblem, normalizeApiProblem } from '@/api/transport/apiProblem';
import AsyncState from '@/components/AsyncState.vue';
import RequestIdNote from '@/components/RequestIdNote.vue';
import ScopeNotice from '@/components/ScopeNotice.vue';
import PlazaSidebar from '@/features/public-bank/components/PlazaSidebar.vue';
import PublicBankListItem from '@/features/public-bank/components/PublicBankListItem.vue';
import {
  publicBankBoardsQuery,
  publicBankHotQuery,
  publicBankInfiniteListQuery,
  publicBankSummaryQuery,
} from '@/features/public-bank/queries';
import { useUiStore } from '@/stores/ui';

const RECENT_SEARCH_KEY = 'public_bank_plaza_recent_v2';
const route = useRoute();
const router = useRouter();
const uiStore = useUiStore();
const tabs: Array<{ label: string; value: PublicBankTab }> = [
  { label: '最新', value: 'latest' },
  { label: '热门', value: 'hot' },
  { label: '活跃', value: 'active' },
  { label: '精华', value: 'featured' },
];

function queryString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function normalizeKeyword(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}

function readRecentSearches(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(RECENT_SEARCH_KEY) ?? '[]');
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string' && Boolean(item)).slice(0, 6)
      : [];
  } catch {
    return [];
  }
}

const activeTab = computed<PublicBankTab>(() => {
  const candidate = queryString(route.query.tab);
  return tabs.some((tab) => tab.value === candidate)
    ? (candidate as PublicBankTab)
    : 'latest';
});
const activeKeyword = computed(() => normalizeKeyword(queryString(route.query.keyword)));
const activeBoardId = computed(() => queryString(route.query.board_id).trim());
const keywordDraft = ref(activeKeyword.value);
const recentSearches = ref(readRecentSearches());
let keywordTimer: ReturnType<typeof setTimeout> | undefined;

watch(activeKeyword, (value) => {
  keywordDraft.value = value;
});

const catalogFilters = computed<PublicBankCatalogFilters>(() => {
  const filters: PublicBankCatalogFilters = {};
  if (activeKeyword.value) filters.keyword = activeKeyword.value;
  if (activeBoardId.value) filters.boardId = activeBoardId.value;
  return filters;
});
const listParams = computed<Omit<PublicBankListParams, 'page'>>(() => ({
  ...catalogFilters.value,
  perPage: 10,
  tab: activeTab.value,
}));

const listQuery = useInfiniteQuery(
  computed(() => publicBankInfiniteListQuery(listParams.value)),
);
const boardsQuery = useQuery(
  computed(() => publicBankBoardsQuery(activeKeyword.value)),
);
const hotQuery = useQuery(
  computed(() => publicBankHotQuery(catalogFilters.value)),
);
const summaryQuery = useQuery(
  computed(() => publicBankSummaryQuery(catalogFilters.value)),
);

const items = computed(() =>
  listQuery.data.value?.pages.flatMap((page) => page.items) ?? [],
);
const total = computed(() => listQuery.data.value?.pages[0]?.total ?? 0);
const requestId = computed(() => listQuery.data.value?.pages.at(-1)?.requestId);
const activeBoardName = computed(() =>
  boardsQuery.data.value?.items.find((board) => String(board.id) === activeBoardId.value)?.name ??
  (activeBoardId.value ? '当前板块' : ''),
);
const listProblem = computed(() => {
  if (!listQuery.error.value) return undefined;
  return listQuery.error.value instanceof ApiProblem
    ? listQuery.error.value
    : normalizeApiProblem(listQuery.error.value);
});

function sidebarProblem(error: unknown): { message: string; requestId?: string } | undefined {
  if (!error) return undefined;
  const problem = error instanceof ApiProblem ? error : normalizeApiProblem(error);
  return problem.requestId
    ? { message: problem.message, requestId: problem.requestId }
    : { message: problem.message };
}

const boardsProblem = computed(() => sidebarProblem(boardsQuery.error.value));
const hotProblem = computed(() => sidebarProblem(hotQuery.error.value));
const summaryProblem = computed(() => sidebarProblem(summaryQuery.error.value));

watch(
  () => [activeKeyword.value, total.value] as const,
  ([keyword, currentTotal]) => {
    if (keyword.length < 2 || currentTotal <= 0 || typeof window === 'undefined') return;
    const next = [keyword, ...recentSearches.value.filter((item) => item !== keyword)].slice(0, 6);
    recentSearches.value = next;
    window.localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(next));
  },
);

function updateQuery(changes: Record<string, string | undefined>): void {
  const nextQuery = { ...route.query };
  for (const [key, value] of Object.entries(changes)) {
    if (value) nextQuery[key] = value;
    else delete nextQuery[key];
  }
  void router.replace({ query: nextQuery });
}

function applyKeyword(): void {
  if (keywordTimer) clearTimeout(keywordTimer);
  keywordTimer = undefined;
  updateQuery({ keyword: normalizeKeyword(keywordDraft.value) || undefined });
}

function scheduleKeyword(): void {
  if (keywordTimer) clearTimeout(keywordTimer);
  keywordTimer = setTimeout(applyKeyword, 250);
}

function handleSearchKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    event.preventDefault();
    applyKeyword();
  } else if (event.key === 'Escape') {
    keywordDraft.value = '';
    applyKeyword();
  }
}

function selectTab(tab: PublicBankTab): void {
  updateQuery({ tab: tab === 'latest' ? undefined : tab });
}

function selectBoard(boardId: string): void {
  updateQuery({ board_id: boardId || undefined });
  uiStore.closePlazaDrawer();
}

function clearAll(): void {
  keywordDraft.value = '';
  updateQuery({ board_id: undefined, keyword: undefined, tab: undefined });
}

function clearKeyword(): void {
  keywordDraft.value = '';
  updateQuery({ keyword: undefined });
}

function clearBoard(): void {
  selectBoard('');
}

function resetTab(): void {
  selectTab('latest');
}

function useRecentSearch(keyword: string): void {
  keywordDraft.value = keyword;
  applyKeyword();
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function loadMore(): void {
  void listQuery.fetchNextPage();
}

function retryBoards(): void {
  void boardsQuery.refetch();
}

function retryHot(): void {
  void hotQuery.refetch();
}

function retrySummary(): void {
  void summaryQuery.refetch();
}

onBeforeUnmount(() => {
  if (keywordTimer) clearTimeout(keywordTimer);
});
</script>

<template>
  <div
    class="forum-drawer-overlay"
    :class="{ open: uiStore.plazaDrawerOpen }"
    aria-hidden="true"
    @click="uiStore.closePlazaDrawer"
  ></div>
  <aside class="forum-drawer" :class="{ open: uiStore.plazaDrawerOpen }" aria-label="题库侧栏抽屉">
    <div class="forum-drawer-close">
      <button type="button" aria-label="关闭题库侧栏" @click="uiStore.closePlazaDrawer">×</button>
    </div>
    <PlazaSidebar
      :active-board-id="activeBoardId"
      :boards-error="boardsProblem"
      :boards-loading="boardsQuery.isPending.value"
      :boards="boardsQuery.data.value?.items ?? []"
      :hot-error="hotProblem"
      :hot-loading="hotQuery.isPending.value"
      :hot-items="hotQuery.data.value?.items ?? []"
      :keyword="activeKeyword"
      :summary-error="summaryProblem"
      :summary-loading="summaryQuery.isPending.value"
      :summary="summaryQuery.data.value"
      @retry-boards="retryBoards"
      @retry-hot="retryHot"
      @retry-summary="retrySummary"
      @select-board="selectBoard"
    />
  </aside>

  <div class="forum-layout plaza-layout">
    <aside class="forum-sidebar plaza-sidebar" aria-label="题库筛选与概览">
      <PlazaSidebar
        :active-board-id="activeBoardId"
        :boards-error="boardsProblem"
        :boards-loading="boardsQuery.isPending.value"
        :boards="boardsQuery.data.value?.items ?? []"
        :hot-error="hotProblem"
        :hot-loading="hotQuery.isPending.value"
        :hot-items="hotQuery.data.value?.items ?? []"
        :keyword="activeKeyword"
        :summary-error="summaryProblem"
        :summary-loading="summaryQuery.isPending.value"
        :summary="summaryQuery.data.value"
        @retry-boards="retryBoards"
        @retry-hot="retryHot"
        @retry-summary="retrySummary"
        @select-board="selectBoard"
      />
    </aside>

    <section class="forum-main plaza-main">
      <div class="forum-topbar plaza-topbar">
        <button
          class="forum-drawer-toggle"
          type="button"
          aria-label="打开题库侧栏"
          @click="uiStore.togglePlazaDrawer"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>

      <div class="plaza-searchbar">
        <label class="sr-only" for="plaza-keyword">搜索题库</label>
        <input
          id="plaza-keyword"
          v-model="keywordDraft"
          class="plaza-search-input"
          type="search"
          placeholder="搜索题库名称、简介或创建者"
          autocomplete="off"
          @input="scheduleKeyword"
          @keydown="handleSearchKeydown"
        />
        <button
          class="plaza-search-clear"
          type="button"
          :disabled="!keywordDraft"
          @click="keywordDraft = ''; applyKeyword()"
        >
          清空
        </button>
      </div>

      <div class="plaza-search-meta" aria-live="polite">
        <div class="plaza-search-summary">
          <span v-if="activeKeyword">搜索 <strong>“{{ activeKeyword }}”</strong>，找到 <strong>{{ formatCount(total) }}</strong> 个题库</span>
          <span v-else-if="activeBoardId">当前板块 <strong>{{ activeBoardName }}</strong>，共 <strong>{{ formatCount(total) }}</strong> 个题库</span>
          <span v-else>当前共 <strong>{{ formatCount(total) }}</strong> 个题库</span>
        </div>
        <div class="plaza-search-actions">
          <button v-if="activeKeyword" class="plaza-search-link" type="button" @click="clearKeyword">清空关键词</button>
          <button v-if="activeBoardId" class="plaza-search-link" type="button" @click="clearBoard">清空板块</button>
          <button v-if="activeTab !== 'latest'" class="plaza-search-link" type="button" @click="resetTab">恢复默认排序</button>
        </div>
      </div>

      <div v-if="!activeKeyword && recentSearches.length" class="plaza-search-recent">
        <span class="plaza-search-recent-label">最近搜索</span>
        <button
          v-for="keyword in recentSearches"
          :key="keyword"
          class="plaza-search-chip"
          type="button"
          @click="useRecentSearch(keyword)"
        >
          {{ keyword }}
        </button>
      </div>

      <div class="forum-tabs" role="tablist" aria-label="题库排序">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="forum-tab"
          :class="{ active: activeTab === tab.value }"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.value"
          @click="selectTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div v-if="activeBoardId" class="forum-active-board-chip">
        {{ activeBoardName }}
        <button class="chip-close" type="button" aria-label="清除板块筛选" @click="selectBoard('')">×</button>
      </div>

      <ScopeNotice />

      <AsyncState v-if="listQuery.isPending.value" class="forum-state" mode="loading" />
      <AsyncState
        v-else-if="listQuery.isError.value"
        class="forum-state"
        mode="error"
        :message="listProblem?.message"
        :request-id="listProblem?.requestId"
        @retry="listQuery.refetch"
      />
      <template v-else-if="items.length === 0">
        <AsyncState class="forum-state" mode="empty" />
        <div class="plaza-empty-actions">
          <button v-if="activeKeyword" class="plaza-search-link" type="button" @click="clearKeyword">清空关键词</button>
          <button v-if="activeBoardId" class="plaza-search-link" type="button" @click="clearBoard">移除板块筛选</button>
          <button v-if="activeTab !== 'latest'" class="plaza-search-link" type="button" @click="resetTab">切回最新</button>
          <button v-if="!activeKeyword && !activeBoardId && activeTab === 'latest'" class="plaza-search-link" type="button" @click="clearAll">重新查看全部题库</button>
        </div>
      </template>

      <ul v-else id="public-bank-list" class="forum-posts plaza-posts">
        <PublicBankListItem
          v-for="bank in items"
          :key="`${bank.source_type}-${bank.id}`"
          :bank="bank"
          :keyword="activeKeyword"
        />
      </ul>

      <div v-if="listQuery.hasNextPage.value" class="forum-load-more">
        <button
          class="btn-load-more"
          type="button"
          :disabled="listQuery.isFetchingNextPage.value"
          @click="loadMore"
        >
          {{ listQuery.isFetchingNextPage.value ? '正在加载…' : '加载更多' }}
        </button>
      </div>

      <RequestIdNote :request-id="requestId" />
    </section>
  </div>
</template>
