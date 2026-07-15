package io.saksk.ti.web.contract;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;
import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.request.RequestId;

public final class ApiResponses {

    private ApiResponses() {
    }

    public static <T> ApiSuccess<T> success(T data, HttpServletRequest request) {
        return ApiSuccess.of(data, RequestId.from(request));
    }

    public static <T> ApiSuccess<T> success(
            T data,
            PaginationMeta pagination,
            HttpServletRequest request
    ) {
        return ApiSuccess.of(data, RequestId.from(request), pagination);
    }

    public static ApiErrorEnvelope error(
            ErrorCode errorCode,
            List<ApiErrorDetail> details,
            HttpServletRequest request
    ) {
        return new ApiErrorEnvelope(
                false,
                new ApiError(errorCode.name(), errorCode.safeMessage(), details),
                ApiMeta.requestOnly(RequestId.from(request))
        );
    }
}
