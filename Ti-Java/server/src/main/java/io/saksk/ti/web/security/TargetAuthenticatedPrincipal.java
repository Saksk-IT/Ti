package io.saksk.ti.web.security;

import java.security.Principal;

public record TargetAuthenticatedPrincipal(long identityId, String username) implements Principal {

    @Override
    public String getName() {
        return username;
    }

    @Override
    public String toString() {
        return "TargetAuthenticatedPrincipal[identityId=" + identityId + ", username=<redacted>]";
    }
}
