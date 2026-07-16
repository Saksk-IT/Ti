package io.saksk.ti.web.compat;

import io.saksk.ti.identity.api.AuthenticateCommand;
import io.saksk.ti.identity.api.AuthenticationOutcome;
import io.saksk.ti.identity.api.AuthenticationResult;
import io.saksk.ti.identity.api.IdentityApplicationApi;
import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.LoginRateLimiter;
import io.saksk.ti.web.security.TargetSessionIssuer;
import io.saksk.ti.web.security.TargetSessionProperties;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.time.Duration;
import java.util.Arrays;
import java.util.regex.Pattern;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

@RestController
class LegacyLoginController {

    private static final Pattern PHONE = Pattern.compile("1[3-9]\\d{9}");
    private static final MediaType LEGACY_JSON =
            MediaType.parseMediaType("application/json;charset=UTF-8");
    private final IdentityApplicationApi identity;
    private final LoginRateLimiter rateLimiter;
    private final ClientAddressResolver clientAddresses;
    private final TargetSessionIssuer targetSessions;
    private final TargetSessionProperties sessionProperties;
    private final LegacyLoginRequestParser parser = new LegacyLoginRequestParser();

    LegacyLoginController(
            IdentityApplicationApi identity,
            LoginRateLimiter rateLimiter,
            ClientAddressResolver clientAddresses,
            TargetSessionIssuer targetSessions,
            TargetSessionProperties sessionProperties
    ) {
        this.identity = identity;
        this.rateLimiter = rateLimiter;
        this.clientAddresses = clientAddresses;
        this.targetSessions = targetSessions;
        this.sessionProperties = sessionProperties;
    }

    @PostMapping(
            path = "/api/login",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = "application/json;charset=UTF-8")
    ResponseEntity<?> login(
            @RequestBody(required = false) JsonNode body,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        LegacyLoginInput parsed;
        try {
            parsed = parser.parse(body);
        } catch (LegacyLoginRequestParser.InvalidLegacyLoginRequest exception) {
            return error(HttpStatus.BAD_REQUEST, "请求数据格式不正确", request);
        }

        try (parsed) {
            if (parsed.identifier().isEmpty()) {
                return error(HttpStatus.BAD_REQUEST, "账号和密码不能为空", request);
            }
            if (!isEmailOrPhone(parsed.identifier())) {
                return error(
                        HttpStatus.BAD_REQUEST,
                        "暂不支持用户名登录，请使用邮箱或手机号",
                        request);
            }

            LoginRateLimiter.Decision rateLimit;
            try {
                rateLimit = rateLimiter.acquire(
                        clientAddresses.resolve(request),
                        parsed.identifier().toLowerCase(java.util.Locale.ROOT));
            } catch (RuntimeException exception) {
                return error(
                        HttpStatus.SERVICE_UNAVAILABLE,
                        "登录服务暂时不可用，请稍后重试",
                        request);
            }
            if (!rateLimit.allowed()) {
                return rateLimited(rateLimit, request);
            }

            AuthenticationResult result;
            char[] password = parsed.passwordCopy();
            try (var command = new AuthenticateCommand(parsed.identifier(), password)) {
                result = identity.authenticate(command);
            } catch (RuntimeException exception) {
                return error(
                        HttpStatus.SERVICE_UNAVAILABLE,
                        "登录服务暂时不可用，请稍后重试",
                        request);
            } finally {
                Arrays.fill(password, '\0');
            }

            if (result.outcome() == AuthenticationOutcome.INVALID_CREDENTIALS) {
                return error(HttpStatus.BAD_REQUEST, "账号或密码错误", request);
            }
            if (result.outcome() == AuthenticationOutcome.ACCOUNT_LOCKED) {
                return error(HttpStatus.FORBIDDEN, "账户已被锁定，请联系管理员", request);
            }

            IdentitySummary authenticated = result.authenticatedIdentity().orElseThrow();
            try {
                targetSessions.issue(request, response, authenticated, parsed.remember());
            } catch (TargetSessionIssuer.TargetSessionIssuanceException exception) {
                return error(
                        HttpStatus.SERVICE_UNAVAILABLE,
                        "登录服务暂时不可用，请稍后重试",
                        request);
            }
            clearLegacySessionCookie(response);

            LegacyLoginData data = new LegacyLoginData(
                    parsed.redirect(),
                    parsed.remember(),
                    false);
            return ResponseEntity.ok()
                    .contentType(LEGACY_JSON)
                    .body(new LegacyLoginSuccess(
                            "success",
                            parsed.redirect(),
                            parsed.remember(),
                            false,
                            "",
                            data,
                            RequestId.from(request)));
        }
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<LegacyLoginError> malformedJson(
            HttpMessageNotReadableException exception,
            HttpServletRequest request
    ) {
        return error(HttpStatus.BAD_REQUEST, "请求数据格式不正确", request);
    }

    private void clearLegacySessionCookie(HttpServletResponse response) {
        ResponseCookie expired = ResponseCookie.from("session", "")
                .path("/")
                .httpOnly(true)
                .secure(sessionProperties.secureCookie())
                .sameSite("Lax")
                .maxAge(Duration.ZERO)
                .build();
        response.addHeader(HttpHeaders.SET_COOKIE, expired.toString());
    }

    private static boolean isEmailOrPhone(String identifier) {
        return identifier.indexOf('@') >= 0 || PHONE.matcher(identifier).matches();
    }

    private static ResponseEntity<LegacyLoginError> error(
            HttpStatus status,
            String message,
            HttpServletRequest request
    ) {
        return ResponseEntity.status(status)
                .contentType(LEGACY_JSON)
                .body(new LegacyLoginError(
                        "error",
                        message,
                        status.value(),
                        RequestId.from(request)));
    }

    private static ResponseEntity<LegacyLoginError> rateLimited(
            LoginRateLimiter.Decision decision,
            HttpServletRequest request
    ) {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                .contentType(LEGACY_JSON)
                .header(HttpHeaders.RETRY_AFTER, Long.toString(decision.retryAfterSeconds()))
                .header("X-RateLimit-Limit", Integer.toString(decision.limit()))
                .header("X-RateLimit-Remaining", Integer.toString(decision.remaining()))
                .body(new LegacyLoginError(
                        "error",
                        "请求过于频繁，请稍后重试",
                        HttpStatus.TOO_MANY_REQUESTS.value(),
                        RequestId.from(request)));
    }

    record LegacyLoginSuccess(
            String status,
            String redirect,
            boolean remember,
            boolean needsPasswordSet,
            String message,
            LegacyLoginData data,
            String requestId
    ) {
    }

    record LegacyLoginData(String redirect, boolean remember, boolean needsPasswordSet) {
    }

    record LegacyLoginError(String status, String message, int statusCode, String requestId) {
    }
}
