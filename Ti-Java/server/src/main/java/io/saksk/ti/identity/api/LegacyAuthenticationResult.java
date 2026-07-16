package io.saksk.ti.identity.api;

import java.time.Instant;
import java.util.Objects;
import java.util.Optional;

public record LegacyAuthenticationResult(
        IdentitySummary identity,
        boolean remember,
        Optional<Instant> credentialExpiresAt
) {

    public LegacyAuthenticationResult {
        identity = Objects.requireNonNull(identity, "identity");
        credentialExpiresAt = Objects.requireNonNull(
                credentialExpiresAt,
                "credentialExpiresAt");
    }

    @Override
    public String toString() {
        return "LegacyAuthenticationResult[redacted]";
    }
}
