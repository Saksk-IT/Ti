import { publicBankOperationIds } from '@/api/contracts/sourceManifest';
import {
  legacy8Cfb837021AfGet,
  legacyA473896Ff467Get,
  legacyB7E49E77A026Get,
  legacyDb1Ac691D6FbGet,
  legacyF3644C1474F3Get,
} from '@/api/generated/phase4aPublicBank/sdk.gen';
import type {
  BoardsResponse,
  DetailResponse,
  HotResponse,
  PlazaListResponse,
  PublicBankDetail,
  SummaryResponse,
} from '@/api/generated/phase4aPublicBank/types.gen';
import { configureGeneratedClients } from '@/api/transport/configureGeneratedClients';
import {
  invalidResponseProblem,
  normalizeApiProblem,
} from '@/api/transport/apiProblem';
import { extractRequestId } from '@/api/transport/requestId';

export type PublicBankTab = 'latest' | 'hot' | 'active' | 'featured';
export type PublicBankSource = 'system' | 'user_public';

export interface PublicBankListParams {
  boardId?: string;
  keyword?: string;
  page?: number;
  perPage?: number;
  tab?: PublicBankTab;
}

export interface PublicBankDetailParams {
  bankId: string;
  sourceType: PublicBankSource;
}

export interface PublicBankCatalogFilters {
  boardId?: string;
  keyword?: string;
}

export type PublicBankListResult = PlazaListResponse['data'] & {
  requestId: string | undefined;
};

export interface PublicBankDetailResult {
  bank: PublicBankDetail;
  requestId: string | undefined;
}

export type PublicBankBoardsResult = BoardsResponse['data'] & {
  requestId: string | undefined;
};

export type PublicBankHotResult = HotResponse['data'] & {
  requestId: string | undefined;
};

export type PublicBankSummaryResult = SummaryResponse['data'] & {
  requestId: string | undefined;
};

interface TransportSuccess<T> {
  data: T;
  response?: Response;
}

interface TransportFailure {
  error: unknown;
  response?: Response;
}

type TransportResult<T> = TransportSuccess<T> | TransportFailure;

export interface PublicBankTransport {
  boards(filters: Pick<PublicBankCatalogFilters, 'keyword'>, signal?: AbortSignal): Promise<TransportResult<BoardsResponse>>;
  detail(params: PublicBankDetailParams, signal?: AbortSignal): Promise<TransportResult<DetailResponse>>;
  hot(filters: PublicBankCatalogFilters, signal?: AbortSignal): Promise<TransportResult<HotResponse>>;
  list(params: PublicBankListParams, signal?: AbortSignal): Promise<TransportResult<PlazaListResponse>>;
  summary(filters: PublicBankCatalogFilters, signal?: AbortSignal): Promise<TransportResult<SummaryResponse>>;
}

const PUBLIC_READ_TIMEOUT_MS = 12_000;

async function withReadTimeout<T>(
  parentSignal: AbortSignal | undefined,
  request: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const controller = new AbortController();
  const relayAbort = () => controller.abort(parentSignal?.reason);
  if (parentSignal?.aborted) relayAbort();
  else parentSignal?.addEventListener('abort', relayAbort, { once: true });
  const timeout = setTimeout(() => {
    controller.abort(new DOMException('请求超时，请稍后重试。', 'TimeoutError'));
  }, PUBLIC_READ_TIMEOUT_MS);

  try {
    return await request(controller.signal);
  } finally {
    clearTimeout(timeout);
    parentSignal?.removeEventListener('abort', relayAbort);
  }
}

function optionalString(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

const generatedTransport: PublicBankTransport = {
  async boards(filters, parentSignal) {
    configureGeneratedClients();
    const query: { keyword?: string } = {};
    const keyword = optionalString(filters.keyword);
    if (keyword) query.keyword = keyword;
    const result = await withReadTimeout(parentSignal, (signal) =>
      legacyDb1Ac691D6FbGet({ query, signal }));
    if (result.data !== undefined) {
      return { data: result.data, response: result.response };
    }
    return { error: result.error, response: result.response };
  },
  async list(params, parentSignal) {
    configureGeneratedClients();
    const query: {
      board_id?: string;
      keyword?: string;
      page?: string;
      per_page?: string;
      tab?: string;
    } = {};
    if (params.tab) query.tab = params.tab;
    const boardId = optionalString(params.boardId);
    const keyword = optionalString(params.keyword);
    if (boardId) query.board_id = boardId;
    if (keyword) query.keyword = keyword;
    if (params.page !== undefined) query.page = String(params.page);
    if (params.perPage !== undefined) query.per_page = String(params.perPage);
    const result = await withReadTimeout(parentSignal, (signal) =>
      legacyB7E49E77A026Get({ query, signal }));
    if (result.data !== undefined) {
      return { data: result.data, response: result.response };
    }
    return { error: result.error, response: result.response };
  },
  async detail(params, parentSignal) {
    configureGeneratedClients();
    const result = await withReadTimeout(parentSignal, (signal) =>
      legacy8Cfb837021AfGet({
        path: {
          source_type: params.sourceType,
          bank_id: params.bankId,
        },
        signal,
      }));
    if (result.data !== undefined) {
      return { data: result.data, response: result.response };
    }
    return { error: result.error, response: result.response };
  },
  async hot(filters, parentSignal) {
    configureGeneratedClients();
    const query: { board_id?: string; keyword?: string; limit: string } = { limit: '5' };
    const boardId = optionalString(filters.boardId);
    const keyword = optionalString(filters.keyword);
    if (boardId) query.board_id = boardId;
    if (keyword) query.keyword = keyword;
    const result = await withReadTimeout(parentSignal, (signal) =>
      legacyA473896Ff467Get({ query, signal }));
    if (result.data !== undefined) {
      return { data: result.data, response: result.response };
    }
    return { error: result.error, response: result.response };
  },
  async summary(filters, parentSignal) {
    configureGeneratedClients();
    const query: { board_id?: string; keyword?: string } = {};
    const boardId = optionalString(filters.boardId);
    const keyword = optionalString(filters.keyword);
    if (boardId) query.board_id = boardId;
    if (keyword) query.keyword = keyword;
    const result = await withReadTimeout(parentSignal, (signal) =>
      legacyF3644C1474F3Get({ query, signal }));
    if (result.data !== undefined) {
      return { data: result.data, response: result.response };
    }
    return { error: result.error, response: result.response };
  },
};

export function createPublicBankFacade(transport: PublicBankTransport) {
  return {
    operationIds: publicBankOperationIds,
    async boards(
      filters: Pick<PublicBankCatalogFilters, 'keyword'> = {},
      signal?: AbortSignal,
    ): Promise<PublicBankBoardsResult> {
      const result = await transport.boards(filters, signal);
      if ('error' in result) throw normalizeApiProblem(result.error, result.response);
      if (result.data.status !== 'success' || result.data.code !== 0) {
        throw invalidResponseProblem(result.response, result.data);
      }
      return {
        ...result.data.data,
        requestId: extractRequestId(result.response, result.data),
      };
    },
    async list(params: PublicBankListParams = {}, signal?: AbortSignal): Promise<PublicBankListResult> {
      const result = await transport.list(params, signal);
      if ('error' in result) {
        throw normalizeApiProblem(result.error, result.response);
      }
      if (result.data.status !== 'success' || result.data.code !== 0) {
        throw invalidResponseProblem(result.response, result.data);
      }
      return {
        ...result.data.data,
        requestId: extractRequestId(result.response, result.data),
      };
    },
    async detail(params: PublicBankDetailParams, signal?: AbortSignal): Promise<PublicBankDetailResult> {
      const result = await transport.detail(params, signal);
      if ('error' in result) {
        throw normalizeApiProblem(result.error, result.response);
      }
      if (result.data.status !== 'success' || result.data.code !== 0) {
        throw invalidResponseProblem(result.response, result.data);
      }
      return {
        bank: result.data.data,
        requestId: extractRequestId(result.response, result.data),
      };
    },
    async hot(filters: PublicBankCatalogFilters = {}, signal?: AbortSignal): Promise<PublicBankHotResult> {
      const result = await transport.hot(filters, signal);
      if ('error' in result) throw normalizeApiProblem(result.error, result.response);
      if (result.data.status !== 'success' || result.data.code !== 0) {
        throw invalidResponseProblem(result.response, result.data);
      }
      return {
        ...result.data.data,
        requestId: extractRequestId(result.response, result.data),
      };
    },
    async summary(filters: PublicBankCatalogFilters = {}, signal?: AbortSignal): Promise<PublicBankSummaryResult> {
      const result = await transport.summary(filters, signal);
      if ('error' in result) throw normalizeApiProblem(result.error, result.response);
      if (result.data.status !== 'success' || result.data.code !== 0) {
        throw invalidResponseProblem(result.response, result.data);
      }
      return {
        ...result.data.data,
        requestId: extractRequestId(result.response, result.data),
      };
    },
  };
}

export const publicBankFacade = createPublicBankFacade(generatedTransport);
