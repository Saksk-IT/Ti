package io.saksk.ti.web.compat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Writes the route-specific compatibility failures for the two user-counts aliases. */
@Component
public final class LegacyPersonalBankUserCountsSecurityErrorWriter {

    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private static final String LEGACY_ERROR_JSON_CONTENT_TYPE = "application/json";
    private static final String LEGACY_HTML_CONTENT_TYPE = "text/html; charset=utf-8";
    private static final String LOGIN_REDIRECT_BODY = "<!doctype html>\n"
            + "<html lang=en>\n"
            + "<title>Redirecting...</title>\n"
            + "<h1>Redirecting...</h1>\n"
            + "<p>You should be redirected automatically to the target URL: "
            + "<a href=\"/login\">/login</a>. If not, click the link.\n";
    private static final String LEGACY_NOT_FOUND_MESSAGE =
            "The requested URL was not found on the server. "
                    + "If you entered the URL manually please check your spelling and try again.";
    private static final String LEGACY_NOT_FOUND_HTML =
            "<h1>404 - 页面未找到</h1><p>" + LEGACY_NOT_FOUND_MESSAGE + "</p>";
    private static final String SAFE_INTERNAL_MESSAGE =
            "An unexpected server error occurred.";
    private static final String SAFE_INTERNAL_HTML =
            "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>";
    private static final String SAFE_UNAVAILABLE_MESSAGE = "服务暂时不可用";
    private static final String SAFE_UNAVAILABLE_HTML =
            "<h1>503 - 服务不可用</h1><p>服务暂时不可用，请稍后再试。</p>";
    private static final String AUTHENTICATION_RATE_LIMITED_MESSAGE = "请求过于频繁";

    private final ObjectMapper objectMapper;

    public LegacyPersonalBankUserCountsSecurityErrorWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void writeAuthenticationRequired(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        if (alias == Alias.WEB) {
            writeLoginRedirect(request, response);
            return;
        }
        ObjectNode body = objectMapper.createObjectNode()
                .put("status", "unauthorized")
                .put("message", "请先登录")
                .put("status_code", HttpStatus.UNAUTHORIZED.value())
                .put("request_id", RequestId.from(request));
        writeJson(
                request,
                response,
                alias,
                HttpStatus.UNAUTHORIZED,
                LEGACY_JSON_CONTENT_TYPE,
                body);
    }

    public void writeLoginRedirect(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        response.setStatus(HttpStatus.FOUND.value());
        response.setHeader(HttpHeaders.LOCATION, "/login");
        mergeVary(response, Alias.WEB);
        writeBody(request, response, LEGACY_HTML_CONTENT_TYPE, LOGIN_REDIRECT_BODY);
    }

    public void writeDenied(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        ObjectNode body = objectMapper.createObjectNode()
                .put("status", "error")
                .put("code", HttpStatus.FORBIDDEN.value())
                .put("message", "无权访问此题库")
                .put("status_code", HttpStatus.FORBIDDEN.value())
                .put("request_id", RequestId.from(request));
        writeJson(
                request,
                response,
                alias,
                HttpStatus.FORBIDDEN,
                LEGACY_JSON_CONTENT_TYPE,
                body);
    }

    public void writeNotFound(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        if (prefersHtml(request, alias)) {
            writeHtml(
                    request,
                    response,
                    alias,
                    HttpStatus.NOT_FOUND,
                    LEGACY_NOT_FOUND_HTML);
            return;
        }
        ObjectNode body = legacySafeError(
                request,
                LEGACY_NOT_FOUND_MESSAGE,
                HttpStatus.NOT_FOUND);
        writeJson(
                request,
                response,
                alias,
                HttpStatus.NOT_FOUND,
                LEGACY_ERROR_JSON_CONTENT_TYPE,
                body);
    }

    public void writeInternalFailure(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        if (prefersHtml(request, alias)) {
            writeHtml(
                    request,
                    response,
                    alias,
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    SAFE_INTERNAL_HTML);
            return;
        }
        ObjectNode body = legacySafeError(
                request,
                SAFE_INTERNAL_MESSAGE,
                HttpStatus.INTERNAL_SERVER_ERROR);
        writeJson(
                request,
                response,
                alias,
                HttpStatus.INTERNAL_SERVER_ERROR,
                LEGACY_ERROR_JSON_CONTENT_TYPE,
                body);
    }

    public void writeRateLimitHeaders(
            HttpServletResponse response,
            PersonalBankUserCountsReadRateLimiter.Decision decision
    ) {
        response.setHeader("X-RateLimit-Limit", Integer.toString(decision.limit()));
        response.setHeader("X-RateLimit-Remaining", Integer.toString(decision.remaining()));
        response.setHeader(
                "X-RateLimit-Reset",
                Long.toString(decision.resetAtEpochSecond()));
        response.setHeader(
                HttpHeaders.RETRY_AFTER,
                Long.toString(decision.retryAfterSeconds()));
    }

    public void writeRateLimited(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias,
            PersonalBankUserCountsReadRateLimiter.Decision decision
    ) throws IOException {
        String message = decision.legacyLimitDescription();
        if (prefersHtml(request, alias)) {
            writeHtml(
                    request,
                    response,
                    alias,
                    HttpStatus.TOO_MANY_REQUESTS,
                    "<h1>429 - Too Many Requests</h1><p>" + message + "</p>");
            return;
        }
        ObjectNode body = legacySafeError(
                request,
                message,
                HttpStatus.TOO_MANY_REQUESTS);
        writeJson(
                request,
                response,
                alias,
                HttpStatus.TOO_MANY_REQUESTS,
                LEGACY_ERROR_JSON_CONTENT_TYPE,
                body);
    }

    /**
     * Writes the distinct pre-route Flask-Session exchange throttle.  That guard has a separate
     * quota model from the user-counts read limiter, so this method intentionally preserves only
     * the headers the authentication guard actually supplied instead of inventing route quota
     * values.
     */
    public void writeAuthenticationRateLimited(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        if (prefersHtml(request, alias)) {
            writeHtml(
                    request,
                    response,
                    alias,
                    HttpStatus.TOO_MANY_REQUESTS,
                    "<h1>429 - Too Many Requests</h1><p>请求过于频繁，请稍后再试。</p>");
            return;
        }
        writeJson(
                request,
                response,
                alias,
                HttpStatus.TOO_MANY_REQUESTS,
                LEGACY_ERROR_JSON_CONTENT_TYPE,
                legacySafeError(
                        request,
                        AUTHENTICATION_RATE_LIMITED_MESSAGE,
                        HttpStatus.TOO_MANY_REQUESTS));
    }

    public void writeServiceUnavailable(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias
    ) throws IOException {
        if (prefersHtml(request, alias)) {
            writeHtml(
                    request,
                    response,
                    alias,
                    HttpStatus.SERVICE_UNAVAILABLE,
                    SAFE_UNAVAILABLE_HTML);
            return;
        }
        ObjectNode body = objectMapper.createObjectNode()
                .put("status", "error")
                .put("message", SAFE_UNAVAILABLE_MESSAGE)
                .put("status_code", HttpStatus.SERVICE_UNAVAILABLE.value())
                .put("request_id", RequestId.from(request));
        writeJson(
                request,
                response,
                alias,
                HttpStatus.SERVICE_UNAVAILABLE,
                LEGACY_ERROR_JSON_CONTENT_TYPE,
                body);
    }

    public static void mergeVary(HttpServletResponse response, Alias alias) {
        if (alias == Alias.API) {
            mergeVaryTokens(response, "Origin", "Cookie");
        } else {
            mergeVaryTokens(response, "Cookie");
        }
    }

    public static void mergeVaryTokens(
            HttpServletResponse response,
            String... requiredTokens
    ) {
        Map<String, String> tokens = new LinkedHashMap<>();
        Collection<String> existing = response.getHeaders(HttpHeaders.VARY);
        for (String header : existing) {
            for (String rawToken : header.split(",")) {
                String token = rawToken.strip();
                if (!token.isEmpty()) {
                    tokens.putIfAbsent(token.toLowerCase(Locale.ROOT), token);
                }
            }
        }
        for (String requiredToken : requiredTokens) {
            if (requiredToken != null && !requiredToken.isBlank()) {
                tokens.putIfAbsent(
                        requiredToken.toLowerCase(Locale.ROOT),
                        requiredToken);
            }
        }
        response.setHeader(HttpHeaders.VARY, String.join(", ", tokens.values()));
    }

    private ObjectNode legacySafeError(
            HttpServletRequest request,
            String message,
            HttpStatus status
    ) {
        return objectMapper.createObjectNode()
                .put("status", "error")
                .put("message", message)
                .putNull("payload")
                .put("status_code", status.value())
                .put("request_id", RequestId.from(request));
    }

    private void writeJson(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias,
            HttpStatus status,
            String contentType,
            ObjectNode body
    ) throws IOException {
        response.setStatus(status.value());
        mergeVary(response, alias);
        response.setHeader(HttpHeaders.CONTENT_TYPE, contentType);
        if (!isHead(request)) {
            objectMapper.writeValue(response.getOutputStream(), body);
        }
    }

    private static void writeHtml(
            HttpServletRequest request,
            HttpServletResponse response,
            Alias alias,
            HttpStatus status,
            String body
    ) throws IOException {
        response.setStatus(status.value());
        mergeVary(response, alias);
        writeBody(request, response, LEGACY_HTML_CONTENT_TYPE, body);
    }

    private static void writeBody(
            HttpServletRequest request,
            HttpServletResponse response,
            String contentType,
            String body
    ) throws IOException {
        response.setHeader(HttpHeaders.CONTENT_TYPE, contentType);
        if (!isHead(request)) {
            response.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static boolean prefersHtml(HttpServletRequest request, Alias alias) {
        if (alias == Alias.API) {
            return false;
        }
        String rawAccept = request.getHeader(HttpHeaders.ACCEPT);
        return rawAccept == null || !rawAccept.startsWith("application/json");
    }

    private static boolean isHead(HttpServletRequest request) {
        return HttpMethod.HEAD.matches(request.getMethod());
    }
}
