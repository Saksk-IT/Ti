package io.saksk.ti.web.security;

import java.time.Instant;

public interface LegacySessionExchangeGuard {

    AttemptDecision beginAttempt(String remoteAddress);

    CredentialDecision acquireCredential(
            String signedCookie,
            long identityId,
            int sessionVersion,
            Instant credentialExpiresAt);

    void releaseCredential(
            String signedCookie,
            long identityId,
            int sessionVersion,
            String reservationToken);

    enum CredentialStatus {
        ACQUIRED,
        REPLAY,
        IDENTITY_LIMITED,
        GLOBAL_LIMITED,
        EXPIRED
    }

    record CredentialDecision(
            CredentialStatus status,
            String reservationToken,
            long retryAfterSeconds
    ) {
        public CredentialDecision {
            if (status == null) {
                throw new IllegalArgumentException("Credential status is required");
            }
            if (status == CredentialStatus.ACQUIRED) {
                if (reservationToken == null
                        || !reservationToken.matches("[A-Za-z0-9_-]{43}")
                        || retryAfterSeconds != 0) {
                    throw new IllegalArgumentException(
                            "An acquired credential requires one opaque reservation token");
                }
            } else if (reservationToken != null
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 604_800) {
                throw new IllegalArgumentException(
                        "A rejected credential requires a bounded retry delay");
            }
        }
    }

    record AttemptDecision(boolean allowed, int limit, int remaining, long retryAfterSeconds) {
        public AttemptDecision {
            if (limit < 1
                    || remaining < 0
                    || remaining > limit
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 60) {
                throw new IllegalArgumentException("Invalid legacy Session exchange attempt decision");
            }
        }
    }
}
