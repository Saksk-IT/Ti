package io.saksk.ti.web.contract;

import java.util.regex.Pattern;

public record ApiErrorDetail(String field, String code, String message) {

    private static final Pattern STABLE_ERROR_CODE = Pattern.compile("[A-Z][A-Z0-9_]*");

    public ApiErrorDetail {
        if (code == null || !STABLE_ERROR_CODE.matcher(code).matches()
                || message == null || message.isBlank()) {
            throw new IllegalArgumentException("error detail code and message must satisfy the API contract");
        }
    }
}
