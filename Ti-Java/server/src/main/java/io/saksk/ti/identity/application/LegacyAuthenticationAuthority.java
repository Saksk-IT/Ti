package io.saksk.ti.identity.application;

import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import io.saksk.ti.identity.domain.AuthorizedLegacyIdentity;
import java.util.Objects;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * Resolves signature-valid legacy identity-shaped data against current PostgreSQL state.
 *
 * <p>Every invalid parameter, missing row, lock, version mismatch, binding mismatch or persistence
 * failure returns an empty result. No role-like value from a legacy credential reaches this
 * boundary.</p>
 */
@Service
public final class LegacyAuthenticationAuthority {

    private final AuthoritativeIdentityStateStore identities;

    public LegacyAuthenticationAuthority(AuthoritativeIdentityStateStore identities) {
        this.identities = Objects.requireNonNull(identities, "identities");
    }

    public Optional<AuthorizedLegacyIdentity> authorizeJwt(
            long identityId,
            int claimedSessionVersion,
            String claimedOpenid
    ) {
        if (identityId <= 0 || claimedSessionVersion < 0 || claimedOpenid == null) {
            return Optional.empty();
        }
        return load(identityId)
                .filter(state -> isCurrentAndUnlocked(state, identityId, claimedSessionVersion))
                .filter(state -> state.acceptsLegacyJwtOpenid(claimedOpenid))
                .map(AuthoritativeIdentityState::authorize);
    }

    public Optional<AuthorizedLegacyIdentity> authorizeFlaskSession(
            long identityId,
            int claimedSessionVersion
    ) {
        return authorizeServerSession(identityId, claimedSessionVersion);
    }

    public Optional<AuthorizedLegacyIdentity> authorizeServerSession(
            long identityId,
            int claimedSessionVersion
    ) {
        if (identityId <= 0 || claimedSessionVersion < 0) {
            return Optional.empty();
        }
        return load(identityId)
                .filter(state -> isCurrentAndUnlocked(state, identityId, claimedSessionVersion))
                .map(AuthoritativeIdentityState::authorize);
    }

    private Optional<AuthoritativeIdentityState> load(long identityId) {
        try {
            Optional<AuthoritativeIdentityState> result = identities.findById(identityId);
            return result == null ? Optional.empty() : result;
        } catch (RuntimeException exception) {
            return Optional.empty();
        }
    }

    private static boolean isCurrentAndUnlocked(
            AuthoritativeIdentityState state,
            long expectedIdentityId,
            int claimedSessionVersion
    ) {
        return state != null
                && state.id() == expectedIdentityId
                && !state.locked()
                && state.sessionVersion() == claimedSessionVersion;
    }

    @Override
    public String toString() {
        return "LegacyAuthenticationAuthority[redacted]";
    }
}
