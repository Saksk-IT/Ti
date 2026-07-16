package io.saksk.ti.identity.infrastructure.security;

import java.time.Instant;

/**
 * Identity-shaped values extracted from a signature-valid Flask cookie session.
 *
 * <p>The record intentionally has no role fields. Its contents remain authorization-untrusted
 * until the current PostgreSQL user state and {@code session_version} have been checked.</p>
 */
public record LegacySessionIdentity(
        long userId,
        String username,
        int sessionVersion,
        boolean remember,
        Instant signedAt,
        Instant expiresAt) {
    @Override
    public String toString() {
        return "LegacySessionIdentity[redacted]";
    }
}
