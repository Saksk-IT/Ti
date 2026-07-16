package io.saksk.ti.identity.api;

import java.util.Objects;
import java.util.Optional;

public record SessionAuthorizationResult(
        Status status,
        Optional<IdentitySummary> identity
) {

    public SessionAuthorizationResult {
        status = Objects.requireNonNull(status, "status");
        identity = Objects.requireNonNull(identity, "identity");
        if ((status == Status.AUTHORIZED) != identity.isPresent()) {
            throw new IllegalArgumentException("Only an authorized decision may contain an identity");
        }
    }

    public static SessionAuthorizationResult authorized(IdentitySummary identity) {
        return new SessionAuthorizationResult(Status.AUTHORIZED, Optional.of(identity));
    }

    public static SessionAuthorizationResult rejected() {
        return new SessionAuthorizationResult(Status.REJECTED, Optional.empty());
    }

    public static SessionAuthorizationResult unavailable() {
        return new SessionAuthorizationResult(Status.UNAVAILABLE, Optional.empty());
    }

    @Override
    public String toString() {
        return "SessionAuthorizationResult[status=" + status + ", identity=<redacted>]";
    }

    public enum Status {
        AUTHORIZED,
        REJECTED,
        UNAVAILABLE
    }
}
