package io.saksk.ti.web.compat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

/** Writes the observed Flask auth-required envelope for the protected subject reads only. */
@Component
public final class LegacySubjectSecurityErrorWriter {

    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private static final String LEGACY_LIMIT_ERROR_CONTENT_TYPE = "application/json";

    private final ObjectMapper objectMapper;

    public LegacySubjectSecurityErrorWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void writeAuthenticationRequired(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setHeader(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE);
        response.setHeader(HttpHeaders.VARY, "Origin, Cookie");
        objectMapper.writeValue(response.getOutputStream(), new LegacySubjectAuthenticationError(
                "unauthorized",
                "请先登录",
                HttpStatus.UNAUTHORIZED.value(),
                RequestId.from(request)));
    }

    public void writeRateLimitHeaders(
            HttpServletResponse response,
            SubjectReadRateLimiter.Decision decision
    ) {
        response.setHeader("X-RateLimit-Limit", Integer.toString(decision.limit()));
        response.setHeader("X-RateLimit-Remaining", Integer.toString(decision.remaining()));
        response.setHeader("X-RateLimit-Reset", Long.toString(decision.resetAtEpochSecond()));
        response.setHeader(HttpHeaders.RETRY_AFTER, Long.toString(decision.retryAfterSeconds()));
    }

    public void writeRateLimited(
            HttpServletRequest request,
            HttpServletResponse response,
            SubjectReadRateLimiter.Decision decision
    ) throws IOException {
        writeError(
                request,
                response,
                HttpStatus.TOO_MANY_REQUESTS,
                decision.legacyLimitDescription(),
                true);
    }

    public void writeServiceUnavailable(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        writeError(
                request,
                response,
                HttpStatus.SERVICE_UNAVAILABLE,
                "服务暂时不可用",
                false);
    }

    private void writeError(
            HttpServletRequest request,
            HttpServletResponse response,
            HttpStatus status,
            String message,
            boolean includeNullPayload
    ) throws IOException {
        response.setStatus(status.value());
        response.setHeader(HttpHeaders.CONTENT_TYPE, LEGACY_LIMIT_ERROR_CONTENT_TYPE);
        response.setHeader(HttpHeaders.VARY, "Origin, Cookie");
        var body = objectMapper.createObjectNode()
                .put("status", "error")
                .put("message", message);
        if (includeNullPayload) {
            body.putNull("payload");
        }
        body.put("status_code", status.value())
                .put("request_id", RequestId.from(request));
        objectMapper.writeValue(response.getOutputStream(), body);
    }

    private record LegacySubjectAuthenticationError(
            String status,
            String message,
            int statusCode,
            String requestId
    ) {
    }
}
