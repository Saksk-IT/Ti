package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpSession;
import java.time.Clock;
import java.time.Duration;
import org.springframework.session.Session;

final class AnonymousSessionLifetime {

    private AnonymousSessionLifetime() {
    }

    static void initialize(HttpSession session, Clock clock, int lifetimeSeconds) {
        session.setAttribute(
                TargetSessionAttributes.ANONYMOUS_EXPIRES_AT,
                Math.addExact(clock.instant().getEpochSecond(), lifetimeSeconds));
        session.setMaxInactiveInterval(lifetimeSeconds);
    }

    static boolean capRemainingOrInvalidate(HttpSession session, Clock clock) {
        Object raw = session.getAttribute(TargetSessionAttributes.ANONYMOUS_EXPIRES_AT);
        long remaining = remainingSeconds(raw, clock);
        if (remaining <= 0) {
            session.invalidate();
            return false;
        }
        session.setMaxInactiveInterval(Math.toIntExact(remaining));
        return true;
    }

    static boolean capRemaining(Session session, Clock clock) {
        Object raw = session.getAttribute(TargetSessionAttributes.ANONYMOUS_EXPIRES_AT);
        long remaining = remainingSeconds(raw, clock);
        if (remaining <= 0) {
            return false;
        }
        session.setMaxInactiveInterval(Duration.ofSeconds(remaining));
        return true;
    }

    private static long remainingSeconds(Object raw, Clock clock) {
        if (!(raw instanceof Long expiresAt) || expiresAt <= 0) {
            return 0;
        }
        return Math.max(0, expiresAt - clock.instant().getEpochSecond());
    }
}
