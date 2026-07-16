package io.saksk.ti.web.security;

import io.saksk.ti.identity.api.IdentitySummary;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Objects;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.stereotype.Component;

/**
 * Single fail-closed issuance path shared by password login and legacy Flask Session exchange.
 */
@Component
public final class TargetSessionIssuer {

    private static final int SESSION_TTL_SECONDS =
            Math.toIntExact(Duration.ofDays(7).toSeconds());

    private final TargetSessionRegistry registry;
    private final SessionRepository<? extends Session> sessionRepository;
    private final CsrfTokenRepository csrfTokens;
    private final Clock clock;

    public TargetSessionIssuer(
            TargetSessionRegistry registry,
            SessionRepository<? extends Session> sessionRepository,
            CsrfTokenRepository csrfTokens,
            Clock clock
    ) {
        this.registry = Objects.requireNonNull(registry, "registry");
        this.sessionRepository = Objects.requireNonNull(sessionRepository, "sessionRepository");
        this.csrfTokens = Objects.requireNonNull(csrfTokens, "csrfTokens");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    public HttpSession issue(
            HttpServletRequest request,
            HttpServletResponse response,
            IdentitySummary identity,
            boolean remember
    ) {
        Objects.requireNonNull(request, "request");
        Objects.requireNonNull(response, "response");
        Objects.requireNonNull(identity, "identity");

        HttpSession target = null;
        String targetSessionId = null;
        try {
            removeAndInvalidatePrevious(request);
            if (remember) {
                TargetSessionCookiePolicy.rememberForSevenDays(request);
            }

            target = request.getSession(true);
            targetSessionId = target.getId();
            target.setMaxInactiveInterval(SESSION_TTL_SECONDS);
            target.setAttribute(TargetSessionAttributes.IDENTITY_ID, identity.id());
            target.setAttribute(
                    TargetSessionAttributes.SESSION_VERSION,
                    identity.sessionVersion());
            target.setAttribute(
                    TargetSessionAttributes.AUTHENTICATED_AT,
                    clock.instant().getEpochSecond());
            target.setAttribute(TargetSessionAttributes.REMEMBER, remember);

            List<String> evicted = registry.registerAndSelectEvictions(
                    identity.id(), targetSessionId);
            for (String evictedSessionId : evicted) {
                sessionRepository.deleteById(evictedSessionId);
            }
            csrfTokens.saveToken(null, request, response);
            TargetSessionReconciliationFilter.markIssued(
                    request, identity.id(), targetSessionId);
            return target;
        } catch (RuntimeException exception) {
            if (target != null) {
                invalidateQuietly(target, exception);
                unregisterQuietly(identity.id(), targetSessionId, exception);
            }
            throw new TargetSessionIssuanceException(exception);
        }
    }

    private void removeAndInvalidatePrevious(HttpServletRequest request) {
        HttpSession previous = request.getSession(false);
        if (previous == null) {
            return;
        }
        Object previousIdentity = previous.getAttribute(TargetSessionAttributes.IDENTITY_ID);
        if (previousIdentity instanceof Long identityId && identityId > 0) {
            registry.unregister(identityId, previous.getId());
        }
        previous.invalidate();
    }

    private void unregisterQuietly(long identityId, String sessionId, RuntimeException failure) {
        try {
            registry.unregister(identityId, sessionId);
        } catch (RuntimeException cleanupFailure) {
            failure.addSuppressed(cleanupFailure);
        }
    }

    private static void invalidateQuietly(HttpSession session, RuntimeException failure) {
        try {
            session.invalidate();
        } catch (RuntimeException cleanupFailure) {
            failure.addSuppressed(cleanupFailure);
        }
    }

    public static final class TargetSessionIssuanceException extends RuntimeException {

        private TargetSessionIssuanceException(RuntimeException cause) {
            super("Target Session issuance failed", cause);
        }
    }
}
