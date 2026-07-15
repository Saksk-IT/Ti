package io.saksk.ti.web.contract;

public record ApiErrorEnvelope(boolean success, ApiError error, ApiMeta meta) {

    public ApiErrorEnvelope {
        if (success) {
            throw new IllegalArgumentException("error envelope must have success=false");
        }
        if (error == null || meta == null) {
            throw new IllegalArgumentException("error envelope requires error and meta");
        }
    }
}
