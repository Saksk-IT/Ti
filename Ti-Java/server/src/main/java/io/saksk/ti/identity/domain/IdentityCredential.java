package io.saksk.ti.identity.domain;

import io.saksk.ti.identity.api.IdentitySummary;
import java.util.Objects;

public final class IdentityCredential {

    private final long id;
    private final String username;
    private final String passwordHash;
    private final boolean administrator;
    private final boolean locked;
    private final int sessionVersion;
    private final boolean subjectAdministrator;
    private final boolean notificationAdministrator;
    private final boolean passwordSet;

    public IdentityCredential(
            long id,
            String username,
            String passwordHash,
            boolean administrator,
            boolean locked,
            int sessionVersion,
            boolean subjectAdministrator,
            boolean notificationAdministrator,
            boolean passwordSet
    ) {
        if (id <= 0 || sessionVersion < 0) {
            throw new IllegalArgumentException("Invalid identity credential");
        }
        this.id = id;
        this.username = Objects.requireNonNull(username, "username");
        this.passwordHash = Objects.requireNonNull(passwordHash, "passwordHash");
        this.administrator = administrator;
        this.locked = locked;
        this.sessionVersion = sessionVersion;
        this.subjectAdministrator = subjectAdministrator;
        this.notificationAdministrator = notificationAdministrator;
        this.passwordSet = passwordSet;
    }

    public long id() {
        return id;
    }

    public String passwordHash() {
        return passwordHash;
    }

    public boolean locked() {
        return locked;
    }

    public boolean passwordSet() {
        return passwordSet;
    }

    public IdentitySummary summary() {
        return new IdentitySummary(
                id,
                username,
                administrator,
                subjectAdministrator,
                notificationAdministrator,
                sessionVersion);
    }

    @Override
    public String toString() {
        return "IdentityCredential[id=" + id + ", credential=<redacted>]";
    }
}
