package io.saksk.ti.web.contract;

import java.util.List;
import java.util.regex.Pattern;

public record ApiError(String code, String message, List<ApiErrorDetail> details) {

    private static final Pattern STABLE_ERROR_CODE = Pattern.compile("[A-Z][A-Z0-9_]*");

    public ApiError {
        if (code == null || !STABLE_ERROR_CODE.matcher(code).matches()
                || message == null || message.isBlank()) {
            throw new IllegalArgumentException("error code and message must satisfy the API contract");
        }
        details = details == null ? List.of() : List.copyOf(details);
    }
}
