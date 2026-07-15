package io.saksk.ti.web.error;

import java.util.List;

import io.saksk.ti.web.contract.ApiErrorDetail;

public class ApiException extends RuntimeException {

    private final ErrorCode errorCode;
    private final List<ApiErrorDetail> safeDetails;

    public ApiException(ErrorCode errorCode) {
        this(errorCode, List.of());
    }

    public ApiException(ErrorCode errorCode, List<ApiErrorDetail> safeDetails) {
        super(errorCode.name());
        this.errorCode = errorCode;
        this.safeDetails = safeDetails == null ? List.of() : List.copyOf(safeDetails);
    }

    public ErrorCode errorCode() {
        return errorCode;
    }

    public List<ApiErrorDetail> safeDetails() {
        return safeDetails;
    }
}
