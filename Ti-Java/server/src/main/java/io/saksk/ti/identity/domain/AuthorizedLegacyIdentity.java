package io.saksk.ti.identity.domain;

import java.util.Objects;

/**
 * Current PostgreSQL identity state authorized after a legacy credential has been verified.
 *
 * <p>The result deliberately contains neither the legacy credential nor a WeChat {@code openid}.
 * Its role flags and username are current database values, never values copied from a JWT or
 * Flask cookie.</p>
 */
public record AuthorizedLegacyIdentity(
        long id,
        String username,
        boolean administrator,
        boolean subjectAdministrator,
        boolean notificationAdministrator,
        int sessionVersion
) {

    public AuthorizedLegacyIdentity {
        if (id <= 0 || sessionVersion < 0) {
            throw new IllegalArgumentException("Invalid authorized legacy identity");
        }
        username = Objects.requireNonNull(username, "username");
        if (username.isBlank()) {
            throw new IllegalArgumentException("Authorized identity username must not be blank");
        }
    }

    @Override
    public String toString() {
        return "AuthorizedLegacyIdentity[redacted]";
    }
}
