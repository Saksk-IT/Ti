package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.util.Base64;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.security.web.csrf.DefaultCsrfToken;
import org.springframework.security.web.csrf.DeferredCsrfToken;

/**
 * Keeps CSRF authority in the server-side session while mirroring the token to a readable SPA
 * cookie. A copied cookie is insufficient without the matching Redis-backed session.
 */
public final class SessionBoundCsrfTokens implements CsrfTokenRepository {

    static final String SESSION_ATTRIBUTE = "csrf_token";
    static final String HEADER_NAME = "X-CSRF-TOKEN";
    static final String PARAMETER_NAME = "_csrf";

    private static final int TOKEN_BYTES = 32;

    private final SecureRandom random = new SecureRandom();
    private final String cookieName;
    private final boolean secureCookie;
    private final int anonymousSessionTimeoutSeconds;
    private final Clock clock;

    public SessionBoundCsrfTokens(
            TargetSessionProperties properties,
            CsrfIssuanceRateLimitProperties issuanceProperties
    ) {
        this(properties, issuanceProperties, Clock.systemUTC());
    }

    public SessionBoundCsrfTokens(
            TargetSessionProperties properties,
            CsrfIssuanceRateLimitProperties issuanceProperties,
            Clock clock
    ) {
        cookieName = properties.csrfCookieName();
        secureCookie = properties.secureCookie();
        anonymousSessionTimeoutSeconds = Math.toIntExact(
                issuanceProperties.anonymousSessionTimeout().toSeconds());
        this.clock = java.util.Objects.requireNonNull(clock, "clock");
    }

    @Override
    public CsrfToken generateToken(HttpServletRequest request) {
        byte[] entropy = new byte[TOKEN_BYTES];
        random.nextBytes(entropy);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
        java.util.Arrays.fill(entropy, (byte) 0);
        return new DefaultCsrfToken(HEADER_NAME, PARAMETER_NAME, token);
    }

    @Override
    public void saveToken(
            CsrfToken token,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        if (token == null) {
            HttpSession session = request.getSession(false);
            if (session != null) {
                session.removeAttribute(SESSION_ATTRIBUTE);
            }
            writeCookie(response, "", Duration.ZERO);
            return;
        }

        HttpSession session = request.getSession(true);
        if (session.getAttribute(TargetSessionAttributes.IDENTITY_ID) == null) {
            if (session.getAttribute(TargetSessionAttributes.ANONYMOUS_EXPIRES_AT) == null) {
                AnonymousSessionLifetime.initialize(
                        session,
                        clock,
                        anonymousSessionTimeoutSeconds);
            } else if (!AnonymousSessionLifetime.capRemainingOrInvalidate(session, clock)) {
                session = request.getSession(true);
                AnonymousSessionLifetime.initialize(
                        session,
                        clock,
                        anonymousSessionTimeoutSeconds);
            }
        }
        session.setAttribute(SESSION_ATTRIBUTE, token.getToken());
        writeCookie(response, token.getToken(), null);
    }

    @Override
    public CsrfToken loadToken(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return null;
        }
        if (session.getAttribute(TargetSessionAttributes.IDENTITY_ID) == null
                && !AnonymousSessionLifetime.capRemainingOrInvalidate(session, clock)) {
            return null;
        }
        Object stored = session.getAttribute(SESSION_ATTRIBUTE);
        if (!(stored instanceof String token)
                || token.length() != 43
                || !token.matches("[A-Za-z0-9_-]{43}")) {
            return null;
        }
        return new DefaultCsrfToken(HEADER_NAME, PARAMETER_NAME, token);
    }

    @Override
    public DeferredCsrfToken loadDeferredToken(
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        return new DeferredCsrfToken() {
            private CsrfToken token;
            private boolean generated;

            @Override
            public CsrfToken get() {
                if (token == null) {
                    token = loadToken(request);
                    generated = token == null;
                    if (generated) {
                        token = generateToken(request);
                    }
                    // Re-mirror existing server authority after browser restart/cookie loss.
                    saveToken(token, request, response);
                }
                return token;
            }

            @Override
            public boolean isGenerated() {
                get();
                return generated;
            }
        };
    }

    private void writeCookie(HttpServletResponse response, String value, Duration maxAge) {
        ResponseCookie.ResponseCookieBuilder cookie = ResponseCookie.from(cookieName, value)
                .path("/")
                .httpOnly(false)
                .secure(secureCookie)
                .sameSite("Lax");
        if (maxAge != null) {
            cookie.maxAge(maxAge);
        }
        response.addHeader(HttpHeaders.SET_COOKIE, cookie.build().toString());
    }
}
