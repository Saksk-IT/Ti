package io.saksk.ti.web.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Runs outside Spring Session and removes a hash that an already-running evicted request may have
 * written back while its filter chain unwound.
 */
@Component
public final class TargetSessionReconciliationFilter extends OncePerRequestFilter {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(TargetSessionReconciliationFilter.class);
    private static final String IDENTITY_ATTRIBUTE =
            TargetSessionReconciliationFilter.class.getName() + ".identity";
    private static final String SESSION_ATTRIBUTE =
            TargetSessionReconciliationFilter.class.getName() + ".session";
    private static final String CLEAR_CSRF_ATTRIBUTE =
            TargetSessionReconciliationFilter.class.getName() + ".clearCsrf";

    private final TargetSessionRegistry registry;
    private final SessionRepository<? extends Session> sessions;
    private final TargetSessionCsrfRevoker csrfRevoker;

    public TargetSessionReconciliationFilter(
            TargetSessionRegistry registry,
            SessionRepository<? extends Session> sessions,
            TargetSessionCsrfRevoker csrfRevoker
    ) {
        this.registry = Objects.requireNonNull(registry, "registry");
        this.sessions = Objects.requireNonNull(sessions, "sessions");
        this.csrfRevoker = Objects.requireNonNull(csrfRevoker, "csrfRevoker");
    }

    static void mark(HttpServletRequest request, long identityId, String sessionId) {
        request.setAttribute(IDENTITY_ATTRIBUTE, identityId);
        request.setAttribute(SESSION_ATTRIBUTE, sessionId);
    }

    static void markIssued(HttpServletRequest request, long identityId, String sessionId) {
        mark(request, identityId, sessionId);
        request.setAttribute(CLEAR_CSRF_ATTRIBUTE, Boolean.TRUE);
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        try {
            filterChain.doFilter(request, response);
        } finally {
            reconcile(request);
        }
    }

    private void reconcile(HttpServletRequest request) {
        Object identity = request.getAttribute(IDENTITY_ATTRIBUTE);
        Object session = request.getAttribute(SESSION_ATTRIBUTE);
        if (!(identity instanceof Long identityId)
                || identityId <= 0
                || !(session instanceof String sessionId)) {
            return;
        }
        try {
            if (!registry.isActive(identityId, sessionId)) {
                sessions.deleteById(sessionId);
                return;
            }
            if (Boolean.TRUE.equals(request.getAttribute(CLEAR_CSRF_ATTRIBUTE))) {
                csrfRevoker.revoke(sessionId);
            }
            if (sessions.findById(sessionId) == null) {
                registry.unregister(identityId, sessionId);
            }
        } catch (RuntimeException failure) {
            if (Boolean.TRUE.equals(request.getAttribute(CLEAR_CSRF_ATTRIBUTE))) {
                revokeIssuedSession(identityId, sessionId, failure);
                LOGGER.warn(
                        "A newly issued target Session failed reconciliation and was revoked");
            }
            // A late Redis failure cannot change an already-written response. Newly issued
            // sessions are deleted above so a response cookie cannot retain stale CSRF authority.
        }
    }

    private void revokeIssuedSession(
            long identityId,
            String sessionId,
            RuntimeException failure
    ) {
        boolean sessionRevoked = false;
        boolean registryRevoked = false;
        try {
            sessions.deleteById(sessionId);
            sessionRevoked = true;
        } catch (RuntimeException cleanupFailure) {
            failure.addSuppressed(cleanupFailure);
        }
        try {
            registry.unregister(identityId, sessionId);
            registryRevoked = true;
        } catch (RuntimeException cleanupFailure) {
            failure.addSuppressed(cleanupFailure);
        }
        if (!sessionRevoked && !registryRevoked) {
            throw failure;
        }
    }
}
