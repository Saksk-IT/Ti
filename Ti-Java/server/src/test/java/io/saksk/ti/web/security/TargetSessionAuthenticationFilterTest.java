package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.api.LegacyAuthenticationResult;
import io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi;
import io.saksk.ti.identity.api.SessionAuthorityApi;
import io.saksk.ti.identity.api.SessionAuthorizationResult;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import jakarta.servlet.http.Cookie;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.session.web.http.CookieSerializer;
import tools.jackson.databind.ObjectMapper;

class TargetSessionAuthenticationFilterTest {

    private static final IdentitySummary CURRENT =
            new IdentitySummary(42, "database-user", true, true, false, 7);
    private static final IdentitySummary BEARER_IDENTITY =
            new IdentitySummary(99, "bearer-user", false, false, true, 3);

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void targetSessionIsReauthorizedAndRolesComeOnlyFromCurrentDatabaseState() throws Exception {
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.authorized(CURRENT),
                emptyLegacyProvider());
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession session = targetSession();
        session.setAttribute("is_admin", false);
        request.setSession(session);
        AtomicReference<Authentication> observed = new AtomicReference<>();

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) ->
                observed.set(SecurityContextHolder.getContext().getAuthentication()));

        assertThat(observed.get().getPrincipal()).isEqualTo(
                new TargetAuthenticatedPrincipal(42, "database-user"));
        assertThat(observed.get().getAuthorities())
                .extracting(Object::toString)
                .containsExactly("ROLE_USER", "ROLE_ADMIN", "ROLE_SUBJECT_ADMIN");
        assertThat(session.getAttribute("is_admin")).isEqualTo(false);
    }

    @Test
    void explicitValidBearerWinsOverCookieButNeverCreatesOrExtendsASession() throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.authorized(CURRENT),
                provider(legacyReturning(BEARER_IDENTITY, false)),
                allowingExchangeGuard(),
                registry);
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession existing = targetSession();
        request.setSession(existing);
        request.addHeader("Authorization", "Bearer valid-jwt");
        AtomicReference<Authentication> observed = new AtomicReference<>();

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) ->
                observed.set(SecurityContextHolder.getContext().getAuthentication()));

        assertThat(((TargetAuthenticatedPrincipal) observed.get().getPrincipal()).identityId())
                .isEqualTo(99);
        assertThat(existing.isInvalid()).isFalse();
        assertThat(request.getAttribute(
                TargetSessionAuthenticationFilter.LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE))
                .isEqualTo(true);

        MockHttpServletRequest stateless = new MockHttpServletRequest();
        stateless.addHeader("Authorization", "Bearer valid-jwt");
        filter.doFilter(stateless, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });
        assertThat(stateless.getSession(false)).isNull();
        verifyNoInteractions(registry);
    }

    @Test
    void explicitAuthorizationMarksTheStoredTargetForOuterCleanupWithoutExtendingIt()
            throws Exception {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(42, "evicted-session")).thenReturn(false);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> repository = mock(SessionRepository.class);
        Session stored = mock(Session.class);
        when(stored.getAttribute(TargetSessionAttributes.IDENTITY_ID)).thenReturn(42L);
        when(stored.getAttribute(TargetSessionAttributes.SESSION_VERSION)).thenReturn(7);
        when(repository.findById("evicted-session")).thenReturn(stored);
        CookieSerializer cookies = mock(CookieSerializer.class);
        MockHttpServletRequest request = new MockHttpServletRequest();
        when(cookies.readCookieValues(request)).thenReturn(List.of("evicted-session"));
        request.addHeader("Authorization", "Bearer invalid");
        TargetSessionProperties properties =
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false);
        TargetSessionAuthenticationFilter authentication = new TargetSessionAuthenticationFilter(
                mock(SessionAuthorityApi.class),
                provider(legacyReturning(null, false)),
                properties,
                allowingExchangeGuard(),
                registry,
                mock(TargetSessionIssuer.class),
                repository,
                cookies,
                targetRequest -> targetRequest.getRemoteAddr(),
                new SafeSecurityErrorWriter(new ObjectMapper()),
                Clock.fixed(Instant.parse("2026-07-16T00:00:00Z"), ZoneOffset.UTC));
        TargetSessionReconciliationFilter outer =
                new TargetSessionReconciliationFilter(
                        registry, repository, mock(TargetSessionCsrfRevoker.class));

        outer.doFilter(request, new MockHttpServletResponse(), (outerRequest, outerResponse) ->
                authentication.doFilter(outerRequest, outerResponse, (ignoredRequest, ignoredResponse) -> {
                }));

        verify(repository).findById("evicted-session");
        verify(repository).deleteById("evicted-session");
        verify(stored, never()).setLastAccessedTime(org.mockito.ArgumentMatchers.any());
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        assertThat(request.getSession(false)).isNull();
    }

    @Test
    void duplicateExplicitAuthorizationSessionCookiesNeverFanOutRepositoryReads()
            throws Exception {
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> repository = mock(SessionRepository.class);
        CookieSerializer cookies = mock(CookieSerializer.class);
        MockHttpServletRequest request = new MockHttpServletRequest();
        when(cookies.readCookieValues(request)).thenReturn(java.util.stream.IntStream.range(0, 200)
                .mapToObj(index -> "duplicate-session-" + index)
                .toList());
        request.addHeader("Authorization", "Bearer invalid");
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        TargetSessionProperties properties =
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false);
        TargetSessionAuthenticationFilter authentication = new TargetSessionAuthenticationFilter(
                mock(SessionAuthorityApi.class),
                provider(legacyReturning(null, false)),
                properties,
                allowingExchangeGuard(),
                registry,
                mock(TargetSessionIssuer.class),
                repository,
                cookies,
                targetRequest -> targetRequest.getRemoteAddr(),
                new SafeSecurityErrorWriter(new ObjectMapper()),
                Clock.fixed(Instant.parse("2026-07-16T00:00:00Z"), ZoneOffset.UTC));

        authentication.doFilter(
                request,
                new MockHttpServletResponse(),
                (ignoredRequest, ignoredResponse) -> {
                });

        verifyNoInteractions(repository, registry);
        assertThat(request.getAttribute(
                org.springframework.session.web.http.SessionRepositoryFilter
                        .INVALID_SESSION_ID_ATTR))
                .isEqualTo("true");
    }

    @Test
    void invalidOrDuplicateExplicitBearerDoesNotFallBackToAValidTargetOrFlaskSession()
            throws Exception {
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.authorized(CURRENT),
                provider(legacyReturning(null, false)));
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession target = targetSession();
        request.setSession(target);
        request.addHeader("Authorization", "Bearer invalid");
        request.setCookies(new Cookie("session", "valid-flask-cookie"));

        filter.doFilter(request, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        assertThat(target.isInvalid()).isFalse();

        MockHttpServletRequest duplicate = new MockHttpServletRequest();
        duplicate.addHeader("Authorization", "Bearer one");
        duplicate.addHeader("Authorization", "Bearer two");
        duplicate.setCookies(new Cookie("session", "valid-flask-cookie"));
        filter.doFilter(duplicate, new MockHttpServletResponse(), (ignoredRequest, ignoredResponse) -> {
        });
        assertThat(duplicate.getSession(false)).isNull();
    }

    @Test
    void flaskCookieRotatesAnAnonymousCsrfSessionAndPreservesRememberSemantics() throws Exception {
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.rejected(),
                provider(legacyReturning(CURRENT, true)));
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpSession anonymous = new MockHttpSession();
        anonymous.setAttribute(SessionBoundCsrfTokens.SESSION_ATTRIBUTE, "x".repeat(43));
        request.setSession(anonymous);
        request.setCookies(new Cookie("session", "signed-legacy-cookie"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, (ignoredRequest, ignoredResponse) -> {
        });

        assertThat(anonymous.isInvalid()).isTrue();
        assertThat(request.getSession(false).getId()).isNotEqualTo(anonymous.getId());
        assertThat(request.getSession(false).getAttribute(TargetSessionAttributes.IDENTITY_ID))
                .isEqualTo(42L);
        assertThat(request.getSession(false).getAttribute(TargetSessionAttributes.REMEMBER))
                .isEqualTo(true);
        assertThat(response.getHeaders("Set-Cookie"))
                .anySatisfy(value -> assertThat(value)
                        .contains("session=", "Max-Age=0", "HttpOnly"));
    }

    @Test
    void authoritativeRejectionInvalidatesButDatabaseOutageReturns503AndPreservesSession()
            throws Exception {
        MockHttpSession rejected = targetSession();
        MockHttpServletRequest rejectedRequest = new MockHttpServletRequest();
        rejectedRequest.setSession(rejected);
        filter((id, version) -> SessionAuthorizationResult.rejected(), emptyLegacyProvider())
                .doFilter(rejectedRequest, new MockHttpServletResponse(), (request, response) -> {
                });
        assertThat(rejected.isInvalid()).isTrue();

        MockHttpSession unavailable = targetSession();
        MockHttpServletRequest unavailableRequest = new MockHttpServletRequest();
        unavailableRequest.setSession(unavailable);
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chainCalled = new AtomicBoolean();
        filter((id, version) -> SessionAuthorizationResult.unavailable(), emptyLegacyProvider())
                .doFilter(unavailableRequest, response, (request, ignoredResponse) ->
                        chainCalled.set(true));

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentAsString()).contains("SERVICE_UNAVAILABLE");
        assertThat(unavailable.isInvalid()).isFalse();
        assertThat(chainCalled).isFalse();
    }

    @Test
    void registryEvictionInvalidatesBeforeDatabaseAndRegistryOutageFailsClosed() throws Exception {
        SessionAuthorityApi authority = mock(SessionAuthorityApi.class);
        TargetSessionRegistry evicted = mock(TargetSessionRegistry.class);
        when(evicted.isActive(42, "evicted-session")).thenReturn(false);
        MockHttpSession evictedSession = new MockHttpSession(null, "evicted-session");
        evictedSession.setAttribute(TargetSessionAttributes.IDENTITY_ID, 42L);
        evictedSession.setAttribute(TargetSessionAttributes.SESSION_VERSION, 7);
        MockHttpServletRequest evictedRequest = new MockHttpServletRequest();
        evictedRequest.setSession(evictedSession);

        filter(authority, emptyLegacyProvider(), allowingExchangeGuard(), evicted)
                .doFilter(evictedRequest, new MockHttpServletResponse(), (request, response) -> {
                });

        assertThat(evictedSession.isInvalid()).isTrue();
        verifyNoInteractions(authority);

        TargetSessionRegistry unavailable = mock(TargetSessionRegistry.class);
        when(unavailable.isActive(42, "preserved-session"))
                .thenThrow(new IllegalStateException("redis down"));
        MockHttpSession preserved = new MockHttpSession(null, "preserved-session");
        preserved.setAttribute(TargetSessionAttributes.IDENTITY_ID, 42L);
        preserved.setAttribute(TargetSessionAttributes.SESSION_VERSION, 7);
        MockHttpServletRequest unavailableRequest = new MockHttpServletRequest();
        unavailableRequest.setSession(preserved);
        MockHttpServletResponse unavailableResponse = new MockHttpServletResponse();

        filter(authority, emptyLegacyProvider(), allowingExchangeGuard(), unavailable)
                .doFilter(unavailableRequest, unavailableResponse, (request, response) -> {
                });

        assertThat(unavailableResponse.getStatus()).isEqualTo(503);
        assertThat(preserved.isInvalid()).isFalse();
    }

    @Test
    void authoritativeRememberSessionRefreshesCookieForSevenDays() throws Exception {
        TargetSessionRegistry registry = allowingRegistry();
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.authorized(CURRENT),
                emptyLegacyProvider(),
                allowingExchangeGuard(),
                registry);
        MockHttpSession session = targetSession();
        session.setAttribute(TargetSessionAttributes.REMEMBER, true);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setSession(session);
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, (ignoredRequest, ignoredResponse) -> {
        });

        assertThat(response.getHeaders("Set-Cookie"))
                .anySatisfy(value -> assertThat(value)
                        .contains("ti_dev_session=", "Max-Age=604800", "HttpOnly", "SameSite=Lax"));
    }

    @Test
    void legacyCookieReplayCannotCreateAnotherTargetSession() throws Exception {
        LegacySessionExchangeGuard guard = mock(LegacySessionExchangeGuard.class);
        when(guard.beginAttempt("127.0.0.1"))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        true,
                        10,
                        8,
                        60));
        when(guard.acquireCredential(
                        org.mockito.ArgumentMatchers.eq("replayed-cookie"),
                        org.mockito.ArgumentMatchers.eq(42L),
                        org.mockito.ArgumentMatchers.eq(7),
                        org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(new LegacySessionExchangeGuard.CredentialDecision(
                        LegacySessionExchangeGuard.CredentialStatus.REPLAY,
                        null,
                        60));
        TargetSessionAuthenticationFilter filter = filter(
                (id, version) -> SessionAuthorizationResult.rejected(),
                provider(legacyReturning(CURRENT, true)),
                guard);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
        request.setCookies(new Cookie("session", "replayed-cookie"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, (ignoredRequest, ignoredResponse) -> {
        });

        assertThat(request.getSession(false)).isNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        assertThat(response.getHeaders("Set-Cookie"))
                .anySatisfy(value -> assertThat(value)
                        .contains("session=", "Max-Age=0", "HttpOnly"));
    }

    @Test
    void failedLegacyExchangeReleasesItsReplayReservationBeforeReturning503()
            throws Exception {
        LegacySessionExchangeGuard guard = allowingExchangeGuard();
        TargetSessionRegistry failingRegistry = mock(TargetSessionRegistry.class);
        when(failingRegistry.registerAndSelectEvictions(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyString()))
                .thenThrow(new IllegalStateException("redis write failed"));
        TargetSessionProperties properties =
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false);
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> repository = mock(SessionRepository.class);
        Clock clock = Clock.fixed(Instant.parse("2026-07-16T00:00:00Z"), ZoneOffset.UTC);
        TargetSessionIssuer issuer = new TargetSessionIssuer(
                failingRegistry,
                repository,
                mock(CsrfTokenRepository.class),
                clock);
        TargetSessionAuthenticationFilter filter = new TargetSessionAuthenticationFilter(
                (id, version) -> SessionAuthorizationResult.rejected(),
                provider(legacyReturning(CURRENT, true)),
                properties,
                guard,
                failingRegistry,
                issuer,
                repository,
                new TargetSessionConfiguration().targetSessionCookieSerializer(properties),
                request -> request.getRemoteAddr(),
                new SafeSecurityErrorWriter(new ObjectMapper()),
                clock);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
        request.setCookies(new Cookie("session", "reserved-cookie"));
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chainCalled = new AtomicBoolean();

        filter.doFilter(request, response, (ignoredRequest, ignoredResponse) ->
                chainCalled.set(true));

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(chainCalled).isFalse();
        verify(guard).releaseCredential(
                org.mockito.ArgumentMatchers.eq("reserved-cookie"),
                org.mockito.ArgumentMatchers.eq(42L),
                org.mockito.ArgumentMatchers.eq(7),
                org.mockito.ArgumentMatchers.matches("[A-Za-z0-9_-]{43}"));
        assertThat(response.getHeaders("Set-Cookie"))
                .noneSatisfy(value -> assertThat(value).contains("session=;"));
    }

    @Test
    void legacyExchangeGuardFailureAndRateLimitStopBeforeSessionCreation() throws Exception {
        LegacySessionExchangeGuard unavailable = mock(LegacySessionExchangeGuard.class);
        when(unavailable.beginAttempt("127.0.0.1"))
                .thenThrow(new IllegalStateException("redis down"));
        MockHttpServletRequest unavailableRequest = new MockHttpServletRequest();
        unavailableRequest.setRemoteAddr("127.0.0.1");
        unavailableRequest.setCookies(new Cookie("session", "valid-cookie"));
        MockHttpServletResponse unavailableResponse = new MockHttpServletResponse();
        AtomicBoolean unavailableChain = new AtomicBoolean();

        filter(
                        (id, version) -> SessionAuthorizationResult.rejected(),
                        provider(legacyReturning(CURRENT, true)),
                        unavailable)
                .doFilter(unavailableRequest, unavailableResponse, (request, response) ->
                        unavailableChain.set(true));

        assertThat(unavailableResponse.getStatus()).isEqualTo(503);
        assertThat(unavailableRequest.getSession(false)).isNull();
        assertThat(unavailableChain).isFalse();

        LegacySessionExchangeGuard limited = mock(LegacySessionExchangeGuard.class);
        when(limited.beginAttempt("127.0.0.1"))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        false,
                        10,
                        0,
                        25));
        MockHttpServletRequest limitedRequest = new MockHttpServletRequest();
        limitedRequest.setRemoteAddr("127.0.0.1");
        limitedRequest.setCookies(new Cookie("session", "valid-cookie"));
        MockHttpServletResponse limitedResponse = new MockHttpServletResponse();

        filter(
                        (id, version) -> SessionAuthorizationResult.rejected(),
                        provider(legacyReturning(CURRENT, true)),
                        limited)
                .doFilter(limitedRequest, limitedResponse, (request, response) -> {
                });

        assertThat(limitedResponse.getStatus()).isEqualTo(429);
        assertThat(limitedResponse.getHeader("Retry-After")).isEqualTo("25");
        assertThat(limitedRequest.getSession(false)).isNull();
    }

    @Test
    void invalidCookiesNeverCreateLongLivedMarkersAndRateLimitRunsBeforeLegacyAuthority()
            throws Exception {
        LegacyCredentialAuthenticationApi legacy = mock(LegacyCredentialAuthenticationApi.class);
        when(legacy.authenticateFlaskSession("invalid-cookie")).thenReturn(Optional.empty());
        LegacySessionExchangeGuard guard = mock(LegacySessionExchangeGuard.class);
        when(guard.beginAttempt("127.0.0.1"))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        true,
                        10,
                        9,
                        60));
        MockHttpServletRequest invalid = new MockHttpServletRequest();
        invalid.setRemoteAddr("127.0.0.1");
        invalid.setCookies(new Cookie("session", "invalid-cookie"));

        filter(
                        (id, version) -> SessionAuthorizationResult.rejected(),
                        provider(legacy),
                        guard)
                .doFilter(invalid, new MockHttpServletResponse(), (request, response) -> {
                });

        org.mockito.Mockito.verify(legacy).authenticateFlaskSession("invalid-cookie");
        org.mockito.Mockito.verify(guard, org.mockito.Mockito.never())
                .acquireCredential(
                        org.mockito.ArgumentMatchers.anyString(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyInt(),
                        org.mockito.ArgumentMatchers.any(Instant.class));

        when(guard.beginAttempt("127.0.0.1"))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        false,
                        10,
                        0,
                        60));
        MockHttpServletRequest limited = new MockHttpServletRequest();
        limited.setRemoteAddr("127.0.0.1");
        limited.setCookies(new Cookie("session", "invalid-cookie"));

        filter(
                        (id, version) -> SessionAuthorizationResult.rejected(),
                        provider(legacy),
                        guard)
                .doFilter(limited, new MockHttpServletResponse(), (request, response) -> {
                });

        org.mockito.Mockito.verify(legacy, org.mockito.Mockito.times(1))
                .authenticateFlaskSession("invalid-cookie");
    }

    private static TargetSessionAuthenticationFilter filter(
            SessionAuthorityApi sessions,
            ObjectProvider<LegacyCredentialAuthenticationApi> legacy
    ) {
        return filter(sessions, legacy, allowingExchangeGuard());
    }

    private static TargetSessionAuthenticationFilter filter(
            SessionAuthorityApi sessions,
            ObjectProvider<LegacyCredentialAuthenticationApi> legacy,
            LegacySessionExchangeGuard exchangeGuard
    ) {
        return filter(sessions, legacy, exchangeGuard, allowingRegistry());
    }

    private static TargetSessionAuthenticationFilter filter(
            SessionAuthorityApi sessions,
            ObjectProvider<LegacyCredentialAuthenticationApi> legacy,
            LegacySessionExchangeGuard exchangeGuard,
            TargetSessionRegistry registry
    ) {
        TargetSessionProperties properties =
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false);
        CsrfTokenRepository csrf = new SessionBoundCsrfTokens(
                properties,
                new CsrfIssuanceRateLimitProperties(
                        "ti-java:identity:csrf-issuance-rate",
                        30,
                        1000,
                        java.time.Duration.ofMinutes(10)));
        when(registry.registerAndSelectEvictions(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyString()))
                .thenReturn(List.of());
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessionRepository = mock(SessionRepository.class);
        Clock clock = Clock.fixed(Instant.parse("2026-07-16T00:00:00Z"), ZoneOffset.UTC);
        TargetSessionIssuer issuer = new TargetSessionIssuer(
                registry,
                sessionRepository,
                csrf,
                clock);
        CookieSerializer cookies =
                new TargetSessionConfiguration().targetSessionCookieSerializer(properties);
        return new TargetSessionAuthenticationFilter(
                sessions,
                legacy,
                properties,
                exchangeGuard,
                registry,
                issuer,
                sessionRepository,
                cookies,
                request -> request.getRemoteAddr(),
                new SafeSecurityErrorWriter(new ObjectMapper()),
                clock);
    }

    private static MockHttpSession targetSession() {
        MockHttpSession session = new MockHttpSession();
        session.setAttribute(TargetSessionAttributes.IDENTITY_ID, 42L);
        session.setAttribute(TargetSessionAttributes.SESSION_VERSION, 7);
        return session;
    }

    private static LegacyCredentialAuthenticationApi legacyReturning(
            IdentitySummary identity,
            boolean remember
    ) {
        return new LegacyCredentialAuthenticationApi() {
            @Override
            public Optional<LegacyAuthenticationResult> authenticateJwt(String token) {
                return result();
            }

            @Override
            public Optional<LegacyAuthenticationResult> authenticateFlaskSession(String cookie) {
                return result();
            }

            private Optional<LegacyAuthenticationResult> result() {
                return identity == null
                        ? Optional.empty()
                        : Optional.of(new LegacyAuthenticationResult(
                                identity,
                                remember,
                                Optional.of(Instant.parse("2026-07-17T00:00:00Z"))));
            }
        };
    }

    private static ObjectProvider<LegacyCredentialAuthenticationApi> emptyLegacyProvider() {
        return new StaticListableBeanFactory().getBeanProvider(LegacyCredentialAuthenticationApi.class);
    }

    private static ObjectProvider<LegacyCredentialAuthenticationApi> provider(
            LegacyCredentialAuthenticationApi legacy
    ) {
        return new StaticListableBeanFactory(Map.of("legacy", legacy))
                .getBeanProvider(LegacyCredentialAuthenticationApi.class);
    }

    private static LegacySessionExchangeGuard allowingExchangeGuard() {
        LegacySessionExchangeGuard guard = mock(LegacySessionExchangeGuard.class);
        when(guard.beginAttempt(org.mockito.ArgumentMatchers.anyString()))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        true,
                        10,
                        9,
                        60));
        when(guard.acquireCredential(
                        org.mockito.ArgumentMatchers.anyString(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyInt(),
                        org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(new LegacySessionExchangeGuard.CredentialDecision(
                        LegacySessionExchangeGuard.CredentialStatus.ACQUIRED,
                        "r".repeat(43),
                        0));
        return guard;
    }

    private static TargetSessionRegistry allowingRegistry() {
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.isActive(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyString()))
                .thenReturn(true);
        return registry;
    }
}
