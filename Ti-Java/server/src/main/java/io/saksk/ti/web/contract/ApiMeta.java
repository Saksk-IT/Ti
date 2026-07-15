package io.saksk.ti.web.contract;

public record ApiMeta(String requestId, PaginationMeta pagination) {

    public ApiMeta {
        if (requestId == null || requestId.isBlank()) {
            throw new IllegalArgumentException("requestId must not be blank");
        }
    }

    public static ApiMeta requestOnly(String requestId) {
        return new ApiMeta(requestId, null);
    }
}
