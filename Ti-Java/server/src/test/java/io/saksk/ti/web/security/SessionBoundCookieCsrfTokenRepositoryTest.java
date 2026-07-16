package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class SessionBoundCookieCsrfTokenRepositoryTest {

    @Test
    void cookieIsOnlyAMirrorAndTheServerSessionRemainsAuthoritative() {
        var repository = new SessionBoundCsrfTokens(
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false),
                csrfIssuanceProperties());
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        var token = repository.generateToken(request);

        repository.saveToken(token, request, response);

        assertThat(repository.loadToken(request).getToken()).isEqualTo(token.getToken());
        assertThat(request.getSession(false).getMaxInactiveInterval()).isEqualTo(600);
        assertThat(request.getSession(false).getAttribute(
                TargetSessionAttributes.ANONYMOUS_EXPIRES_AT))
                .isInstanceOf(Long.class);
        assertThat(request.getSession(false).getAttribute(
                SessionBoundCsrfTokens.SESSION_ATTRIBUTE))
                .isEqualTo(token.getToken())
                .isInstanceOf(String.class);
        assertThat(response.getHeader("Set-Cookie"))
                .contains("ti_dev_csrf=" + token.getToken(), "Path=/", "SameSite=Lax")
                .doesNotContain("HttpOnly", "Secure");

        MockHttpServletRequest copiedCookieOnly = new MockHttpServletRequest();
        copiedCookieOnly.setCookies(new jakarta.servlet.http.Cookie("ti_dev_csrf", token.getToken()));
        assertThat(repository.loadToken(copiedCookieOnly)).isNull();
    }

    @Test
    void anonymousSessionTtlCanOnlyShrinkAndAbsoluteExpiryInvalidatesIt() {
        Instant now = Instant.parse("2026-07-16T00:00:00Z");
        var repository = new SessionBoundCsrfTokens(
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false),
                csrfIssuanceProperties(),
                Clock.fixed(now, ZoneOffset.UTC));
        MockHttpServletRequest request = new MockHttpServletRequest();
        repository.saveToken(
                repository.generateToken(request),
                request,
                new MockHttpServletResponse());
        var session = (org.springframework.mock.web.MockHttpSession) request.getSession(false);

        session.setAttribute(
                TargetSessionAttributes.ANONYMOUS_EXPIRES_AT,
                now.getEpochSecond() + 30);
        assertThat(repository.loadToken(request)).isNotNull();
        assertThat(session.getMaxInactiveInterval()).isEqualTo(30);

        session.setAttribute(
                TargetSessionAttributes.ANONYMOUS_EXPIRES_AT,
                now.getEpochSecond() - 1);
        assertThat(repository.loadToken(request)).isNull();
        assertThat(session.isInvalid()).isTrue();
    }

    @Test
    void clearingAfterSessionRotationRemovesAuthorityAndExpiresTheMirrorCookie() {
        var repository = new SessionBoundCsrfTokens(
                new TargetSessionProperties("__Host-ti_session", "__Host-ti_csrf", true),
                csrfIssuanceProperties());
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        repository.saveToken(repository.generateToken(request), request, response);
        response = new MockHttpServletResponse();

        repository.saveToken(null, request, response);

        assertThat(repository.loadToken(request)).isNull();
        assertThat(response.getHeader("Set-Cookie"))
                .contains("__Host-ti_csrf=", "Max-Age=0", "Secure", "SameSite=Lax");
    }

    private static CsrfIssuanceRateLimitProperties csrfIssuanceProperties() {
        return new CsrfIssuanceRateLimitProperties(
                "ti-java:identity:csrf-issuance-rate",
                30,
                1000,
                java.time.Duration.ofMinutes(10));
    }
}
