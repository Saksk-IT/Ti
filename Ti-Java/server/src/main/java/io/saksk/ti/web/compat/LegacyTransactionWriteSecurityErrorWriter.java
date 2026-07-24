package io.saksk.ti.web.compat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TransactionWriteRateLimiter;
import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Frozen compatibility envelopes emitted before the transaction-write controllers. */
@Component
public final class LegacyTransactionWriteSecurityErrorWriter {

    private final ObjectMapper objectMapper;

    public LegacyTransactionWriteSecurityErrorWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void writeAuthenticationRequired(
            HttpServletRequest request,
            HttpServletResponse response,
            Route route
    ) throws IOException {
        write(
                request,
                response,
                HttpStatus.UNAUTHORIZED,
                "unauthorized",
                route.authenticationMessage(),
                false);
    }

    public void writeMissingSafetyHeader(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        write(
                request,
                response,
                HttpStatus.FORBIDDEN,
                "error",
                "请求被拒绝（缺少安全标头）",
                false);
    }

    public void writeServiceUnavailable(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        write(
                request,
                response,
                HttpStatus.SERVICE_UNAVAILABLE,
                "error",
                "服务暂时不可用",
                true);
    }

    public void writeRateLimited(
            HttpServletRequest request,
            HttpServletResponse response,
            TransactionWriteRateLimiter.Decision decision
    ) throws IOException {
        write(
                request,
                response,
                HttpStatus.TOO_MANY_REQUESTS,
                "error",
                decision.legacyLimitDescription(),
                true);
    }

    public void writeAuthenticationRateLimited(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        write(
                request,
                response,
                HttpStatus.TOO_MANY_REQUESTS,
                "error",
                "请求过于频繁",
                true);
    }

    public void writeRateHeaders(
            HttpServletResponse response,
            TransactionWriteRateLimiter.Decision decision
    ) {
        response.setHeader("X-RateLimit-Limit", Integer.toString(decision.limit()));
        response.setHeader(
                "X-RateLimit-Remaining",
                Integer.toString(decision.remaining()));
        response.setHeader(
                "X-RateLimit-Reset",
                Long.toString(decision.resetAtEpochSecond()));
        response.setHeader(
                HttpHeaders.RETRY_AFTER,
                Long.toString(decision.retryAfterSeconds()));
    }

    public static void mergeVary(HttpServletResponse response) {
        Set<String> tokens = new LinkedHashSet<>();
        for (String existing : response.getHeaders(HttpHeaders.VARY)) {
            for (String raw : existing.split(",")) {
                if (!raw.isBlank()) {
                    tokens.add(raw.strip());
                }
            }
        }
        tokens.add("Origin");
        tokens.add("Cookie");
        response.setHeader(HttpHeaders.VARY, String.join(", ", tokens));
    }

    private void write(
            HttpServletRequest request,
            HttpServletResponse response,
            HttpStatus status,
            String legacyStatus,
            String message,
            boolean payload
    ) throws IOException {
        ObjectNode body = objectMapper.createObjectNode()
                .put("status", legacyStatus)
                .put("message", message)
                .put("status_code", status.value())
                .put("request_id", RequestId.from(request));
        if (payload) {
            body.putNull("payload");
        }
        response.setStatus(status.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json");
        mergeVary(response);
        objectMapper.writeValue(response.getOutputStream(), body);
    }
}
