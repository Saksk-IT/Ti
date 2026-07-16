package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.identity.api.IdentitySummary;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;

class TargetSessionIssuerTest {

    private static final Instant NOW = Instant.parse("2026-07-16T00:00:00Z");
    private static final IdentitySummary IDENTITY =
            new IdentitySummary(42, "wang", false, false, false, 7);

    @Test
    void rotatesPreviousSessionRegistersNewAndDeletesEveryEviction() {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.registerAndSelectEvictions(anyLong(), anyString()))
                .thenReturn(List.of("oldest-one", "oldest-two"));
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> repository = mock(SessionRepository.class);
        CsrfTokenRepository csrf = mock(CsrfTokenRepository.class);
        TargetSessionIssuer issuer = issuer(registry, repository, csrf);
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession previous = new MockHttpSession();
        previous.setAttribute(TargetSessionAttributes.IDENTITY_ID, 42L);
        request.setSession(previous);
        MockHttpServletResponse response = new MockHttpServletResponse();

        var issued = issuer.issue(request, response, IDENTITY, true);

        assertThat(previous.isInvalid()).isTrue();
        assertThat(issued.getId()).isNotEqualTo(previous.getId());
        assertThat(issued.getMaxInactiveInterval()).isEqualTo(604_800);
        assertThat(issued.getAttribute(TargetSessionAttributes.IDENTITY_ID)).isEqualTo(42L);
        assertThat(issued.getAttribute(TargetSessionAttributes.SESSION_VERSION)).isEqualTo(7);
        assertThat(issued.getAttribute(TargetSessionAttributes.AUTHENTICATED_AT))
                .isEqualTo(NOW.getEpochSecond());
        assertThat(issued.getAttribute(TargetSessionAttributes.REMEMBER)).isEqualTo(true);
        verify(registry).unregister(42, previous.getId());
        verify(repository).deleteById("oldest-one");
        verify(repository).deleteById("oldest-two");
        verify(csrf).saveToken(null, request, response);
    }

    @Test
    void redisFailureBeforeRotationIsWrappedAndPreservesExistingSession() {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        doThrow(new IllegalStateException("redis down"))
                .when(registry).unregister(42, "existing-session");
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> repository = mock(SessionRepository.class);
        TargetSessionIssuer issuer = issuer(
                registry,
                repository,
                mock(CsrfTokenRepository.class));
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession previous = new MockHttpSession(null, "existing-session");
        previous.setAttribute(TargetSessionAttributes.IDENTITY_ID, 42L);
        request.setSession(previous);

        assertThatThrownBy(() -> issuer.issue(
                        request,
                        new MockHttpServletResponse(),
                        IDENTITY,
                        false))
                .isInstanceOf(TargetSessionIssuer.TargetSessionIssuanceException.class)
                .hasCauseInstanceOf(IllegalStateException.class);
        assertThat(previous.isInvalid()).isFalse();
        assertThat(request.getSession(false)).isSameAs(previous);
    }

    private static TargetSessionIssuer issuer(
            TargetSessionRegistry registry,
            SessionRepository<? extends Session> repository,
            CsrfTokenRepository csrf
    ) {
        return new TargetSessionIssuer(
                registry,
                repository,
                csrf,
                Clock.fixed(NOW, ZoneOffset.UTC));
    }
}
