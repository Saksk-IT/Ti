package io.saksk.ti.web.contract;

public record ApiSuccess<T>(boolean success, T data, ApiMeta meta) {

    public ApiSuccess {
        if (!success) {
            throw new IllegalArgumentException("success envelope must have success=true");
        }
        if (data == null) {
            throw new IllegalArgumentException("success envelope data must not be null; use HTTP 204 for no content");
        }
        if (meta == null) {
            throw new IllegalArgumentException("success envelope meta must not be null");
        }
    }

    public static <T> ApiSuccess<T> of(T data, String requestId) {
        return new ApiSuccess<>(true, data, ApiMeta.requestOnly(requestId));
    }

    public static <T> ApiSuccess<T> of(T data, String requestId, PaginationMeta pagination) {
        if (pagination == null) {
            throw new IllegalArgumentException("paginated success envelope requires pagination metadata");
        }
        return new ApiSuccess<>(true, data, new ApiMeta(requestId, pagination));
    }
}
