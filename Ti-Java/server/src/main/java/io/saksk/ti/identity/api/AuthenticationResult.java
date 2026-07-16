package io.saksk.ti.identity.api;

import java.util.Objects;
import java.util.Optional;

public record AuthenticationResult(
        AuthenticationOutcome outcome,
        IdentitySummary identity,
        boolean passwordUpgraded
) {

    public AuthenticationResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        if ((outcome == AuthenticationOutcome.AUTHENTICATED) != (identity != null)) {
            throw new IllegalArgumentException("Identity is present only for authenticated results");
        }
        if (passwordUpgraded && outcome != AuthenticationOutcome.AUTHENTICATED) {
            throw new IllegalArgumentException("Only authenticated results can upgrade a password");
        }
    }

    public static AuthenticationResult authenticated(IdentitySummary identity, boolean passwordUpgraded) {
        return new AuthenticationResult(AuthenticationOutcome.AUTHENTICATED, identity, passwordUpgraded);
    }

    public static AuthenticationResult invalidCredentials() {
        return new AuthenticationResult(AuthenticationOutcome.INVALID_CREDENTIALS, null, false);
    }

    public static AuthenticationResult accountLocked() {
        return new AuthenticationResult(AuthenticationOutcome.ACCOUNT_LOCKED, null, false);
    }

    public Optional<IdentitySummary> authenticatedIdentity() {
        return Optional.ofNullable(identity);
    }
}
