export const REQUEST_ID_HEADER = 'X-Request-ID';

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
}

function nonEmptyString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

export function createRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  const randomPart = Math.random().toString(36).slice(2, 12);
  return `ti-web-${Date.now().toString(36)}-${randomPart}`;
}

export function requestIdFromPayload(payload: unknown): string | undefined {
  if (!isRecord(payload)) {
    return undefined;
  }

  const direct = nonEmptyString(payload.request_id);
  if (direct) {
    return direct;
  }

  if (isRecord(payload.meta)) {
    return nonEmptyString(payload.meta.request_id);
  }

  return undefined;
}

export function extractRequestId(
  response: Response | undefined,
  payload?: unknown,
): string | undefined {
  return (
    nonEmptyString(response?.headers.get(REQUEST_ID_HEADER)) ??
    requestIdFromPayload(payload)
  );
}
