package io.saksk.ti.web.security;

import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.api.LegacyAuthenticationResult;
import io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi;
import io.saksk.ti.identity.api.SessionAuthorityApi;
import io.saksk.ti.identity.api.SessionAuthorizationResult;
import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.io.IOException;
import java.time.Clock;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.session.web.http.CookieSerializer;
import org.springframework.session.web.http.SessionRepositoryFilter;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Rehydrates target sessions from PostgreSQL and temporarily accepts locally verified legacy
 * credentials. Bearer credentials authenticate only their current request; only a Flask cookie is
 * exchanged for a Redis-backed target session.
 */
@Component
public final class TargetSessionAuthenticationFilter extends OncePerRequestFilter {

    public static final String LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE =
            TargetSessionAuthenticationFilter.class.getName() + ".legacyBearerAuthenticated";

    private static final int MAXIMUM_AUTHORIZATION_HEADER_LENGTH = 8_192;

    private final SessionAuthorityApi sessions;
    private final ObjectProvider<LegacyCredentialAuthenticationApi> legacyCredentials;
    private final TargetSessionProperties sessionProperties;
    private final LegacySessionExchangeGuard legacySessionExchanges;
    private final TargetSessionRegistry targetSessionRegistry;
    private final TargetSessionIssuer targetSessionIssuer;
    private final SessionRepository<? extends Session> sessionRepository;
    private final CookieSerializer cookieSerializer;
    private final ClientAddressResolver clientAddresses;
    private final SafeSecurityErrorWriter errorWriter;
    private final Clock clock;

    public TargetSessionAuthenticationFilter(
            SessionAuthorityApi sessions,
            ObjectProvider<LegacyCredentialAuthenticationApi> legacyCredentials,
            TargetSessionProperties sessionProperties,
            LegacySessionExchangeGuard legacySessionExchanges,
            TargetSessionRegistry targetSessionRegistry,
            TargetSessionIssuer targetSessionIssuer,
            SessionRepository<? extends Session> sessionRepository,
            CookieSerializer cookieSerializer,
            ClientAddressResolver clientAddresses,
            SafeSecurityErrorWriter errorWriter,
            Clock clock
    ) {
        this.sessions = sessions;
        this.legacyCredentials = legacyCredentials;
        this.sessionProperties = sessionProperties;
        this.legacySessionExchanges = legacySessionExchanges;
        this.targetSessionRegistry = targetSessionRegistry;
        this.targetSessionIssuer = targetSessionIssuer;
        this.sessionRepository = sessionRepository;
        this.cookieSerializer = cookieSerializer;
        this.clientAddresses = clientAddresses;
        this.errorWriter = errorWriter;
        this.clock = clock;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String authorization = singleAuthorizationHeader(request);
        if (authorization != null) {
            markExplicitRequestTargetSessionForReconciliation(request);
            authenticateLegacyBearerForCurrentRequest(request, authorization)
                    .ifPresent(this::installCurrentRequestAuthentication);
            filterChain.doFilter(request, response);
            return;
        }

        SessionAuthorizationResult target = authorizeTargetSession(request, response);
        if (target.status() == SessionAuthorizationResult.Status.UNAVAILABLE) {
            errorWriter.write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
            return;
        }

        Optional<IdentitySummary> identity = target.identity();
        if (identity.isEmpty()) {
            LegacySessionConversion conversion = convertLegacyFlaskSession(request, response);
            if (conversion.stopRequest()) {
                return;
            }
            identity = conversion.identity();
        }
        identity.ifPresent(this::installCurrentRequestAuthentication);
        filterChain.doFilter(request, response);
    }

    private void markExplicitRequestTargetSessionForReconciliation(HttpServletRequest request) {
        List<String> sessionIds = cookieSerializer.readCookieValues(request);
        if (sessionIds.size() != 1 || !isSafeSessionId(sessionIds.getFirst())) {
            request.setAttribute(SessionRepositoryFilter.INVALID_SESSION_ID_ATTR, "true");
            return;
        }
        String sessionId = sessionIds.getFirst();
        Session stored;
        try {
            stored = sessionRepository.findById(sessionId);
        } catch (RuntimeException exception) {
            return;
        }
        if (stored == null) {
            return;
        }
        Object identityId = stored.getAttribute(TargetSessionAttributes.IDENTITY_ID);
        Object sessionVersion = stored.getAttribute(TargetSessionAttributes.SESSION_VERSION);
        if (identityId instanceof Long id
                && id > 0
                && sessionVersion instanceof Integer version
                && version >= 0) {
            TargetSessionReconciliationFilter.mark(request, id, sessionId);
            return;
        }
        if (identityId == null
                && sessionVersion == null
                && AnonymousSessionLifetime.capRemaining(stored, clock)) {
            return;
        }
        try {
            sessionRepository.deleteById(sessionId);
        } catch (RuntimeException ignored) {
            // Bearer authentication remains independent from target Session availability.
        }
    }

    private SessionAuthorizationResult authorizeTargetSession(
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return SessionAuthorizationResult.rejected();
        }
        Object identityId = session.getAttribute(TargetSessionAttributes.IDENTITY_ID);
        Object sessionVersion = session.getAttribute(TargetSessionAttributes.SESSION_VERSION);
        if (identityId == null && sessionVersion == null) {
            AnonymousSessionLifetime.capRemainingOrInvalidate(session, clock);
            return SessionAuthorizationResult.rejected();
        }
        if (!(identityId instanceof Long id) || !(sessionVersion instanceof Integer version)) {
            session.invalidate();
            return SessionAuthorizationResult.rejected();
        }

        try {
            if (!targetSessionRegistry.isActive(id, session.getId())) {
                session.invalidate();
                return SessionAuthorizationResult.rejected();
            }
        } catch (RuntimeException exception) {
            return SessionAuthorizationResult.unavailable();
        }

        SessionAuthorizationResult authorized = sessions.authorize(id, version);
        if (authorized.status() == SessionAuthorizationResult.Status.REJECTED) {
            unregisterQuietly(id, session.getId());
            session.invalidate();
        } else if (authorized.status() == SessionAuthorizationResult.Status.AUTHORIZED) {
            TargetSessionReconciliationFilter.mark(request, id, session.getId());
            if (Boolean.TRUE.equals(session.getAttribute(TargetSessionAttributes.REMEMBER))) {
                TargetSessionCookiePolicy.rememberForSevenDays(request);
                cookieSerializer.writeCookieValue(
                        new CookieSerializer.CookieValue(request, response, session.getId()));
            }
        }
        return authorized;
    }

    private Optional<IdentitySummary> authenticateLegacyBearerForCurrentRequest(
            HttpServletRequest request,
            String authorization
    ) {
        LegacyCredentialAuthenticationApi legacy = legacyCredentials.getIfAvailable();
        if (legacy == null
                || !authorization.startsWith("Bearer ")
                || authorization.length() <= "Bearer ".length()
                || authorization.length() > MAXIMUM_AUTHORIZATION_HEADER_LENGTH) {
            return Optional.empty();
        }
        Optional<LegacyAuthenticationResult> authenticated =
                legacy.authenticateJwt(authorization.substring("Bearer ".length()));
        if (authenticated.isPresent()) {
            request.setAttribute(LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE, true);
        }
        return authenticated.map(LegacyAuthenticationResult::identity);
    }

    private LegacySessionConversion convertLegacyFlaskSession(
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        LegacyCredentialAuthenticationApi legacy = legacyCredentials.getIfAvailable();
        if (legacy == null) {
            return LegacySessionConversion.none();
        }
        String legacyCookie = singleCookie(request, "session");
        if (legacyCookie == null) {
            return LegacySessionConversion.none();
        }

        LegacySessionExchangeGuard.AttemptDecision attempt;
        try {
            attempt = legacySessionExchanges.beginAttempt(clientAddresses.resolve(request));
        } catch (RuntimeException exception) {
            errorWriter.write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
            return LegacySessionConversion.stop();
        }
        if (!attempt.allowed()) {
            response.setHeader(HttpHeaders.RETRY_AFTER, Long.toString(attempt.retryAfterSeconds()));
            response.setHeader("X-RateLimit-Limit", Integer.toString(attempt.limit()));
            response.setHeader("X-RateLimit-Remaining", Integer.toString(attempt.remaining()));
            errorWriter.write(request, response, ErrorCode.RATE_LIMITED);
            return LegacySessionConversion.stop();
        }

        Optional<LegacyAuthenticationResult> authenticated =
                legacy.authenticateFlaskSession(legacyCookie);
        if (authenticated.isEmpty()) {
            return LegacySessionConversion.none();
        }

        LegacySessionExchangeGuard.CredentialDecision credentialDecision;
        LegacyAuthenticationResult result = authenticated.orElseThrow();
        java.time.Instant credentialExpiresAt = result.credentialExpiresAt().orElse(null);
        if (credentialExpiresAt == null) {
            expireFlaskCookie(response);
            return LegacySessionConversion.none();
        }
        try {
            credentialDecision = legacySessionExchanges.acquireCredential(
                    legacyCookie,
                    result.identity().id(),
                    result.identity().sessionVersion(),
                    credentialExpiresAt);
        } catch (RuntimeException exception) {
            errorWriter.write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
            return LegacySessionConversion.stop();
        }
        LegacySessionExchangeGuard.CredentialStatus credentialStatus = credentialDecision.status();
        if (credentialStatus == LegacySessionExchangeGuard.CredentialStatus.REPLAY) {
            expireFlaskCookie(response);
            return LegacySessionConversion.none();
        }
        if (credentialStatus == LegacySessionExchangeGuard.CredentialStatus.EXPIRED) {
            expireFlaskCookie(response);
            return LegacySessionConversion.none();
        }
        if (credentialStatus == LegacySessionExchangeGuard.CredentialStatus.IDENTITY_LIMITED) {
            expireFlaskCookie(response);
            response.setHeader(
                    HttpHeaders.RETRY_AFTER,
                    Long.toString(credentialDecision.retryAfterSeconds()));
            errorWriter.write(request, response, ErrorCode.RATE_LIMITED);
            return LegacySessionConversion.stop();
        }
        if (credentialStatus == LegacySessionExchangeGuard.CredentialStatus.GLOBAL_LIMITED) {
            response.setHeader(
                    HttpHeaders.RETRY_AFTER,
                    Long.toString(credentialDecision.retryAfterSeconds()));
            errorWriter.write(request, response, ErrorCode.RATE_LIMITED);
            return LegacySessionConversion.stop();
        }

        try {
            targetSessionIssuer.issue(request, response, result.identity(), result.remember());
        } catch (TargetSessionIssuer.TargetSessionIssuanceException exception) {
            try {
                legacySessionExchanges.releaseCredential(
                        legacyCookie,
                        result.identity().id(),
                        result.identity().sessionVersion(),
                        credentialDecision.reservationToken());
            } catch (RuntimeException releaseFailure) {
                expireFlaskCookie(response);
            }
            errorWriter.write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
            return LegacySessionConversion.stop();
        }
        expireFlaskCookie(response);
        return LegacySessionConversion.authenticated(result.identity());
    }

    private void unregisterQuietly(long identityId, String sessionId) {
        try {
            targetSessionRegistry.unregister(identityId, sessionId);
        } catch (RuntimeException ignored) {
            // PostgreSQL authority rejected the Session; invalidation remains fail closed.
        }
    }

    private void installCurrentRequestAuthentication(IdentitySummary identity) {
        Authentication authentication = UsernamePasswordAuthenticationToken.authenticated(
                new TargetAuthenticatedPrincipal(identity.id(), identity.username()),
                null,
                authorities(identity));
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(authentication);
        SecurityContextHolder.setContext(context);
    }

    private static List<SimpleGrantedAuthority> authorities(IdentitySummary identity) {
        List<SimpleGrantedAuthority> authorities = new ArrayList<>();
        authorities.add(new SimpleGrantedAuthority("ROLE_USER"));
        if (identity.administrator()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_ADMIN"));
        }
        if (identity.subjectAdministrator()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_SUBJECT_ADMIN"));
        }
        if (identity.notificationAdministrator()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_NOTIFICATION_ADMIN"));
        }
        return List.copyOf(authorities);
    }

    private static String singleAuthorizationHeader(HttpServletRequest request) {
        java.util.Enumeration<String> values = request.getHeaders(HttpHeaders.AUTHORIZATION);
        if (values == null || !values.hasMoreElements()) {
            return null;
        }
        String first = values.nextElement();
        return values.hasMoreElements() ? "" : first;
    }

    private static boolean isSafeSessionId(String value) {
        return value != null && value.matches("[A-Za-z0-9._-]{1,256}");
    }

    private static String singleCookie(HttpServletRequest request, String name) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        String value = null;
        for (Cookie cookie : cookies) {
            if (cookie.getName().equals(name)) {
                if (value != null) {
                    return null;
                }
                value = cookie.getValue();
            }
        }
        return value;
    }

    private void expireFlaskCookie(HttpServletResponse response) {
        ResponseCookie expired = ResponseCookie.from("session", "")
                .path("/")
                .httpOnly(true)
                .secure(sessionProperties.secureCookie())
                .sameSite("Lax")
                .maxAge(Duration.ZERO)
                .build();
        response.addHeader(HttpHeaders.SET_COOKIE, expired.toString());
    }

    private record LegacySessionConversion(
            Optional<IdentitySummary> identity,
            boolean stopRequest
    ) {
        private static LegacySessionConversion authenticated(IdentitySummary identity) {
            return new LegacySessionConversion(Optional.of(identity), false);
        }

        private static LegacySessionConversion none() {
            return new LegacySessionConversion(Optional.empty(), false);
        }

        private static LegacySessionConversion stop() {
            return new LegacySessionConversion(Optional.empty(), true);
        }
    }
}
