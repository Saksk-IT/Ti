package io.saksk.ti.identity.infrastructure.security;

import java.time.Instant;

/**
 * Identity-shaped values extracted from a signature-valid legacy JWT.
 *
 * <p>These values are deliberately authorization-untrusted. Callers must load the current user,
 * lock state, binding and {@code session_version} from PostgreSQL before creating an authenticated
 * principal. No legacy role claim is represented here.</p>
 */
public record LegacyJwtIdentity(
        long userId,
        String openid,
        int sessionVersion,
        Instant expiresAt,
        Instant issuedAt,
        String jti) {
    @Override
    public String toString() {
        return "LegacyJwtIdentity[redacted]";
    }
}
