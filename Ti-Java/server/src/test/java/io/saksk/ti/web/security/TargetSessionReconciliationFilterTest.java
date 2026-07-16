package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;

class TargetSessionReconciliationFilterTest {

    @Test
    void removesDeferredCsrfOnlyFromANewlyIssuedSessionAfterPersistence() throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(42, "issued-session")).thenReturn(true);
        @SuppressWarnings("unchecked")
        SessionRepository<Session> sessions = mock(SessionRepository.class);
        TargetSessionCsrfRevoker csrfRevoker = mock(TargetSessionCsrfRevoker.class);
        TargetSessionReconciliationFilter filter =
                new TargetSessionReconciliationFilter(registry, sessions, csrfRevoker);
        MockHttpServletRequest request = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.markIssued(request, 42, "issued-session");

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });

        verify(csrfRevoker).revoke("issued-session");

        TargetSessionRegistry existingRegistry = mock(TargetSessionRegistry.class);
        when(existingRegistry.isActive(42, "existing-session")).thenReturn(true);
        @SuppressWarnings("unchecked")
        SessionRepository<Session> existingSessions = mock(SessionRepository.class);
        TargetSessionCsrfRevoker existingCsrfRevoker = mock(TargetSessionCsrfRevoker.class);
        TargetSessionReconciliationFilter existingFilter =
                new TargetSessionReconciliationFilter(
                        existingRegistry, existingSessions, existingCsrfRevoker);
        MockHttpServletRequest existingRequest = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.mark(existingRequest, 42, "existing-session");

        existingFilter.doFilter(
                existingRequest,
                new MockHttpServletResponse(),
                (ignoredRequest, ignoredResponse) -> {
                });

        verifyNoInteractions(existingCsrfRevoker);
    }

    @Test
    void deletesAnEvictedHashAfterTheDownstreamSessionWriteHasFinished() throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(42, "evicted-session")).thenReturn(false);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessions = mock(SessionRepository.class);
        TargetSessionReconciliationFilter filter =
                new TargetSessionReconciliationFilter(
                        registry, sessions, mock(TargetSessionCsrfRevoker.class));
        MockHttpServletRequest request = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.mark(request, 42, "evicted-session");
        boolean[] downstreamCompleted = {false};

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) ->
                downstreamCompleted[0] = true);

        verify(sessions).deleteById("evicted-session");
        org.assertj.core.api.Assertions.assertThat(downstreamCompleted[0]).isTrue();
    }

    @Test
    void removesAnIndexGhostWhenDownstreamInvalidatedAnOtherwiseActiveSession() throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(42, "logged-out-session")).thenReturn(true);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessions = mock(SessionRepository.class);
        when(sessions.findById("logged-out-session")).thenReturn(null);
        TargetSessionReconciliationFilter filter =
                new TargetSessionReconciliationFilter(
                        registry, sessions, mock(TargetSessionCsrfRevoker.class));
        MockHttpServletRequest request = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.mark(request, 42, "logged-out-session");

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });

        verify(registry).unregister(42, "logged-out-session");
    }

    @Test
    void unmarkedRequestsDoNotTouchRedisAndFinallyRunsOnDownstreamFailure() throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessions = mock(SessionRepository.class);
        TargetSessionCsrfRevoker csrfRevoker = mock(TargetSessionCsrfRevoker.class);
        TargetSessionReconciliationFilter filter =
                new TargetSessionReconciliationFilter(registry, sessions, csrfRevoker);

        filter.doFilter(
                new MockHttpServletRequest(),
                new MockHttpServletResponse(),
                (request, response) -> {
                });
        verifyNoInteractions(registry, sessions, csrfRevoker);

        MockHttpServletRequest marked = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.mark(marked, 42, "evicted-session");
        when(registry.isActive(42, "evicted-session")).thenReturn(false);
        assertThatThrownBy(() -> filter.doFilter(
                        marked,
                        new MockHttpServletResponse(),
                        (request, response) -> {
                            throw new IOException("downstream failed");
                        }))
                .isInstanceOf(IOException.class)
                .hasMessage("downstream failed");
        verify(sessions).deleteById("evicted-session");
    }

    @Test
    void revokerFailureAttemptsBothCleanupPathsAndEscalatesOnlyIfNeitherCanRevoke()
            throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(42, "issued-session")).thenReturn(true);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessions = mock(SessionRepository.class);
        TargetSessionCsrfRevoker csrfRevoker = mock(TargetSessionCsrfRevoker.class);
        doThrow(new IllegalStateException("opaque revoker failure"))
                .when(csrfRevoker).revoke("issued-session");
        TargetSessionReconciliationFilter filter =
                new TargetSessionReconciliationFilter(registry, sessions, csrfRevoker);
        MockHttpServletRequest request = new MockHttpServletRequest();
        TargetSessionReconciliationFilter.markIssued(request, 42, "issued-session");

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });

        verify(sessions).deleteById("issued-session");
        verify(registry).unregister(42, "issued-session");

        doThrow(new IllegalStateException("opaque session cleanup failure"))
                .when(sessions).deleteById("issued-session");
        doThrow(new IllegalStateException("opaque registry cleanup failure"))
                .when(registry).unregister(42, "issued-session");

        assertThatThrownBy(() -> filter.doFilter(
                        request,
                        new MockHttpServletResponse(),
                        (ignoredRequest, ignoredResponse) -> {
                        }))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("opaque revoker failure")
                .satisfies(failure -> org.assertj.core.api.Assertions
                        .assertThat(failure.getSuppressed())
                        .extracting(Throwable::getMessage)
                        .containsExactly(
                                "opaque session cleanup failure",
                                "opaque registry cleanup failure"));
    }
}
