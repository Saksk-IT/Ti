package io.saksk.ti.web.compat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PublicBankReadRateLimiter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

/** Writes Flask-compatible limiter failures for the seven public-bank reads only. */
@Component
public final class LegacyPublicBankSecurityErrorWriter {

    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private static final String LEGACY_LIMIT_CONTENT_TYPE = "application/json";

    private final ObjectMapper objectMapper;

    public LegacyPublicBankSecurityErrorWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void writeRateLimitHeaders(
            HttpServletResponse response,
            PublicBankReadRateLimiter.Decision decision
    ) {
        response.setHeader("X-RateLimit-Limit", Integer.toString(decision.limit()));
        response.setHeader("X-RateLimit-Remaining", Integer.toString(decision.remaining()));
        response.setHeader("X-RateLimit-Reset", Long.toString(decision.resetAtEpochSecond()));
        response.setHeader(HttpHeaders.RETRY_AFTER, Long.toString(decision.retryAfterSeconds()));
    }

    public void writeRateLimited(
            HttpServletRequest request,
            HttpServletResponse response,
            PublicBankReadRateLimiter.Decision decision
    ) throws IOException {
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setHeader(HttpHeaders.CONTENT_TYPE, LEGACY_LIMIT_CONTENT_TYPE);
        response.setHeader(HttpHeaders.VARY, "Origin, Cookie");
        var body = objectMapper.createObjectNode()
                .put("status", "error")
                .put("message", decision.legacyLimitDescription())
                .putNull("payload")
                .put("status_code", HttpStatus.TOO_MANY_REQUESTS.value())
                .put("request_id", RequestId.from(request));
        objectMapper.writeValue(response.getOutputStream(), body);
    }

    public void writeServiceUnavailable(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        response.setStatus(HttpStatus.SERVICE_UNAVAILABLE.value());
        response.setHeader(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE);
        response.setHeader(HttpHeaders.VARY, "Origin, Cookie");
        var body = objectMapper.createObjectNode()
                .put("status", "error")
                .put("code", 1)
                .put("message", "服务暂时不可用")
                .put("status_code", HttpStatus.SERVICE_UNAVAILABLE.value())
                .put("request_id", RequestId.from(request));
        objectMapper.writeValue(response.getOutputStream(), body);
    }
}
