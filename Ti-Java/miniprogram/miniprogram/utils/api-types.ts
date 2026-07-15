/**
 * api-types.ts
 * 通用 API 响应类型，消除 (res as any)?.data 用法
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T = unknown> extends ApiResponse<T[]> {
  total?: number;
  page?: number;
  limit?: number;
}

/**
 * 从 wx.request 的 result 中安全提取 data
 */
export function extractData<T = unknown>(
  res: WechatMiniprogram.RequestSuccessCallbackResult
): ApiResponse<T> {
  const d = res.data as Record<string, unknown> | undefined;
  if (!d) return { success: false, error: '空响应' };
  return {
    success: d.success === true || d.code === 0 || d.status === 'ok',
    data: (d.data ?? d.result ?? d) as T,
    error: (d.error ?? d.message ?? d.msg) as string | undefined,
    message: (d.message ?? d.msg) as string | undefined,
  };
}
