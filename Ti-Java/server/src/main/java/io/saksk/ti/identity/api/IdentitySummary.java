package io.saksk.ti.identity.api;

import java.util.Objects;

public record IdentitySummary(
        long id,
        String username,
        boolean administrator,
        boolean subjectAdministrator,
        boolean notificationAdministrator,
        int sessionVersion
) {

    public IdentitySummary {
        if (id <= 0 || sessionVersion < 0) {
            throw new IllegalArgumentException("Invalid identity summary");
        }
        username = Objects.requireNonNull(username, "username");
    }

    @Override
    public String toString() {
        return "IdentitySummary[redacted]";
    }
}
