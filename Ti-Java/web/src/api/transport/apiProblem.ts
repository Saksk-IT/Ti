import { extractRequestId } from './requestId';

export type ApiProblemKind =
  | 'bad-request'
  | 'not-found'
  | 'rate-limited'
  | 'unavailable'
  | 'server-error'
  | 'network-error'
  | 'invalid-response';

export interface ApiProblemOptions {
  kind: ApiProblemKind;
  message: string;
  requestId?: string;
  status?: number;
  retryable: boolean;
  cause?: unknown;
}

export class ApiProblem extends Error {
  readonly kind: ApiProblemKind;
  readonly requestId: string | undefined;
  readonly retryable: boolean;
  readonly status: number | undefined;

  constructor(options: ApiProblemOptions) {
    super(options.message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = 'ApiProblem';
    this.kind = options.kind;
    this.requestId = options.requestId;
    this.retryable = options.retryable;
    this.status = options.status;
  }
}

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
}

function asMessage(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function messageFromEnvelope(error: unknown): string | undefined {
  if (!isRecord(error)) {
    return error instanceof Error ? asMessage(error.message) : asMessage(error);
  }

  const direct = asMessage(error.message);
  if (direct) {
    return direct;
  }

  if (isRecord(error.error)) {
    return asMessage(error.error.message);
  }

  return undefined;
}

function statusFromEnvelope(error: unknown): number | undefined {
  if (!isRecord(error)) {
    return undefined;
  }

  return typeof error.status_code === 'number' ? error.status_code : undefined;
}

function kindForStatus(status: number | undefined): ApiProblemKind {
  if (status === 400) return 'bad-request';
  if (status === 404) return 'not-found';
  if (status === 429) return 'rate-limited';
  if (status === 503) return 'unavailable';
  if (status !== undefined && status >= 500) return 'server-error';
  return 'network-error';
}

function fallbackMessage(kind: ApiProblemKind): string {
  switch (kind) {
    case 'bad-request':
      return '请求参数无法处理，请调整后重试。';
    case 'not-found':
      return '题库不存在或尚未公开。';
    case 'rate-limited':
      return '请求过于频繁，请稍后再试。';
    case 'unavailable':
      return '服务暂时不可用，请稍后再试。';
    case 'server-error':
      return '服务处理失败，请稍后再试。';
    case 'invalid-response':
      return '服务返回了无法识别的数据。';
    case 'network-error':
      return '暂时无法连接服务，请检查网络后重试。';
  }
}

export function normalizeApiProblem(
  error: unknown,
  response?: Response,
): ApiProblem {
  if (error instanceof ApiProblem) {
    return error;
  }

  const status = response?.status ?? statusFromEnvelope(error);
  const kind = kindForStatus(status);
  return new ApiProblem({
    kind,
    message: messageFromEnvelope(error) ?? fallbackMessage(kind),
    requestId: extractRequestId(response, error),
    status,
    retryable:
      kind === 'network-error' || kind === 'unavailable' || kind === 'server-error',
    cause: error,
  });
}

export function invalidResponseProblem(
  response: Response | undefined,
  payload: unknown,
): ApiProblem {
  return new ApiProblem({
    kind: 'invalid-response',
    message: fallbackMessage('invalid-response'),
    requestId: extractRequestId(response, payload),
    status: response?.status,
    retryable: false,
    cause: payload,
  });
}
