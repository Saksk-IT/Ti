import { infiniteQueryOptions, queryOptions } from '@tanstack/vue-query';

import {
  publicBankFacade,
  type PublicBankCatalogFilters,
  type PublicBankDetailParams,
  type PublicBankListParams,
} from '@/api/facade/publicBankFacade';

export const publicBankKeys = {
  all: ['phase4aPublicBank', 'publicBanks'] as const,
  lists: () => [...publicBankKeys.all, 'list'] as const,
  list: (params: PublicBankListParams) => [...publicBankKeys.lists(), params] as const,
  infiniteList: (params: Omit<PublicBankListParams, 'page'>) =>
    [...publicBankKeys.lists(), 'infinite', params] as const,
  boards: (keyword: string) => [...publicBankKeys.all, 'boards', keyword] as const,
  hot: (filters: PublicBankCatalogFilters) => [...publicBankKeys.all, 'hot', filters] as const,
  summary: (filters: PublicBankCatalogFilters) =>
    [...publicBankKeys.all, 'summary', filters] as const,
  details: () => [...publicBankKeys.all, 'detail'] as const,
  detail: (params: PublicBankDetailParams) =>
    [...publicBankKeys.details(), params.sourceType, params.bankId] as const,
};

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 1) {
    return false;
  }

  return (
    typeof error === 'object' &&
    error !== null &&
    'retryable' in error &&
    error.retryable === true
  );
}

export function publicBankListQuery(params: PublicBankListParams) {
  return queryOptions({
    queryKey: publicBankKeys.list(params),
    queryFn: ({ signal }) => publicBankFacade.list(params, signal),
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function publicBankInfiniteListQuery(params: Omit<PublicBankListParams, 'page'>) {
  return infiniteQueryOptions({
    queryKey: publicBankKeys.infiniteList(params),
    queryFn: ({ pageParam, signal }) => publicBankFacade.list({ ...params, page: pageParam }, signal),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page * lastPage.per_page < lastPage.total
        ? lastPage.page + 1
        : undefined,
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function publicBankBoardsQuery(keyword = '') {
  return queryOptions({
    queryKey: publicBankKeys.boards(keyword),
    queryFn: ({ signal }) => publicBankFacade.boards(keyword ? { keyword } : {}, signal),
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function publicBankHotQuery(filters: PublicBankCatalogFilters) {
  return queryOptions({
    queryKey: publicBankKeys.hot(filters),
    queryFn: ({ signal }) => publicBankFacade.hot(filters, signal),
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function publicBankSummaryQuery(filters: PublicBankCatalogFilters) {
  return queryOptions({
    queryKey: publicBankKeys.summary(filters),
    queryFn: ({ signal }) => publicBankFacade.summary(filters, signal),
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function publicBankDetailQuery(params: PublicBankDetailParams, enabled = true) {
  return queryOptions({
    queryKey: publicBankKeys.detail(params),
    queryFn: ({ signal }) => publicBankFacade.detail(params, signal),
    staleTime: 60_000,
    retry: shouldRetry,
    enabled,
  });
}
