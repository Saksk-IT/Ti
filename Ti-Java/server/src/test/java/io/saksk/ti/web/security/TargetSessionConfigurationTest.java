package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import jakarta.servlet.http.Cookie;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.session.web.http.CookieSerializer;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.session.web.http.CookieHttpSessionIdResolver;
import org.springframework.session.web.http.SessionRepositoryFilter;

class TargetSessionConfigurationTest {

    private final CookieSerializer cookies =
            new TargetSessionConfiguration().targetSessionCookieSerializer(
                    new TargetSessionProperties("__Host-ti_session", "__Host-ti_csrf", true));

    @Test
    void writesAHostOnlySecureSessionCookieByDefault() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();

        cookies.writeCookieValue(new CookieSerializer.CookieValue(request, response, "opaque-id"));

        assertThat(response.getHeader("Set-Cookie"))
                .startsWith("__Host-ti_session=")
                .contains("Path=/")
                .contains("Secure")
                .contains("HttpOnly")
                .contains("SameSite=Lax")
                .doesNotContain("Domain=")
                .doesNotContain("Max-Age=");
    }

    @Test
    void rememberFlagAddsExactlyTheLegacySevenDayLifetime() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        TargetSessionCookiePolicy.rememberForSevenDays(request);

        cookies.writeCookieValue(new CookieSerializer.CookieValue(request, response, "opaque-id"));

        assertThat(response.getHeader("Set-Cookie"))
                .contains("Max-Age=604800")
                .contains("Expires=");
    }

    @Test
    void authenticationFilterIsOnlyRegisteredInsideTheSpringSecurityChain() {
        TargetSessionAuthenticationFilter filter = mock(TargetSessionAuthenticationFilter.class);
        var registration = new TargetSessionFilterRegistrationConfiguration()
                .targetSessionAuthenticationFilterRegistration(filter);

        assertThat(registration.isEnabled()).isFalse();
        assertThat(registration.getFilter()).isSameAs(filter);
    }

    @Test
    void reconciliationRunsOutsideSpringSessionSoItsFinallyExecutesAfterPersistence() {
        TargetSessionReconciliationFilter filter =
                mock(TargetSessionReconciliationFilter.class);
        var registration = new TargetSessionFilterRegistrationConfiguration()
                .targetSessionReconciliationFilterRegistration(filter);

        assertThat(registration.isEnabled()).isTrue();
        assertThat(registration.getOrder())
                .isEqualTo(SessionRepositoryFilter.DEFAULT_ORDER - 1);
        assertThat(registration.getFilter()).isSameAs(filter);
    }

    @Test
    void springSessionNeverFansOutReadsForDuplicateTargetCookies() throws Exception {
        @SuppressWarnings("unchecked")
        SessionRepository<Session> repository = mock(SessionRepository.class);
        SessionRepositoryFilter<Session> sessionFilter =
                new SessionRepositoryFilter<>(repository);
        CookieHttpSessionIdResolver resolver = new CookieHttpSessionIdResolver();
        resolver.setCookieSerializer(cookies);
        sessionFilter.setHttpSessionIdResolver(resolver);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setCookies(IntStream.range(0, 200)
                .mapToObj(index -> new Cookie("__Host-ti_session", "short" + index))
                .toArray(Cookie[]::new));

        sessionFilter.doFilter(
                request,
                new MockHttpServletResponse(),
                (wrapped, response) -> ((jakarta.servlet.http.HttpServletRequest) wrapped)
                        .getSession(false));

        verify(repository, never()).findById(anyString());
    }
}
