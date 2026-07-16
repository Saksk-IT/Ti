package io.saksk.ti.identity.infrastructure.security;

import io.saksk.ti.identity.application.LegacyAuthenticationAuthority;
import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.api.LegacyAuthenticationResult;
import io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi;
import io.saksk.ti.identity.domain.AuthorizedLegacyIdentity;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.Optional;

/**
 * Local-only compatibility facade: verify the legacy format, then require PostgreSQL authority.
 *
 * <p>It performs no Flask callback, introspection or network request. Construction is explicit so
 * the temporary legacy secrets can be wired only by the migration boundary and removed with that
 * boundary later.</p>
 */
public final class LegacyAuthenticationCompatibilityService
        implements LegacyCredentialAuthenticationApi {

    private final LegacyJwtVerifier jwtVerifier;
    private final LegacyFlaskSessionVerifier flaskSessionVerifier;
    private final LegacyAuthenticationAuthority authority;
    private final Clock clock;
    private final Instant acceptUntil;
    private final LegacyAuthenticationMetrics metrics;

    LegacyAuthenticationCompatibilityService(
            LegacyJwtVerifier jwtVerifier,
            LegacyFlaskSessionVerifier flaskSessionVerifier,
            LegacyAuthenticationAuthority authority,
            Clock clock,
            Instant acceptUntil,
            LegacyAuthenticationMetrics metrics
    ) {
        this.jwtVerifier = Objects.requireNonNull(jwtVerifier, "jwtVerifier");
        this.flaskSessionVerifier =
                Objects.requireNonNull(flaskSessionVerifier, "flaskSessionVerifier");
        this.authority = Objects.requireNonNull(authority, "authority");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.acceptUntil = Objects.requireNonNull(acceptUntil, "acceptUntil");
        this.metrics = metrics;
    }

    @Override
    public Optional<LegacyAuthenticationResult> authenticateJwt(String token) {
        Optional<AuthorizedLegacyIdentity> result = Optional.empty();
        try {
            if (compatibilityWindowIsOpen()) {
                result = jwtVerifier.verify(token).flatMap(identity -> authority.authorizeJwt(
                        identity.userId(), identity.sessionVersion(), identity.openid()));
            }
        } catch (RuntimeException exception) {
            result = Optional.empty();
        }
        recordJwt(result.isPresent());
        return result.map(identity -> new LegacyAuthenticationResult(
                toSummary(identity),
                false,
                Optional.empty()));
    }

    @Override
    public Optional<LegacyAuthenticationResult> authenticateFlaskSession(String cookie) {
        Optional<LegacyAuthenticationResult> result = Optional.empty();
        try {
            if (compatibilityWindowIsOpen()) {
                result = flaskSessionVerifier.verify(cookie).flatMap(legacyIdentity ->
                        authority.authorizeFlaskSession(
                                        legacyIdentity.userId(), legacyIdentity.sessionVersion())
                                .map(current -> new LegacyAuthenticationResult(
                                        toSummary(current),
                                        legacyIdentity.remember(),
                                        Optional.of(earlierOf(
                                                legacyIdentity.expiresAt(),
                                                acceptUntil)))));
            }
        } catch (RuntimeException exception) {
            result = Optional.empty();
        }
        recordFlaskSession(result.isPresent());
        return result;
    }

    private boolean compatibilityWindowIsOpen() {
        return clock.instant().isBefore(acceptUntil);
    }

    private static Instant earlierOf(Instant left, Instant right) {
        return left.isBefore(right) ? left : right;
    }

    private void recordJwt(boolean accepted) {
        if (metrics != null) {
            metrics.recordJwt(accepted);
        }
    }

    private void recordFlaskSession(boolean accepted) {
        if (metrics != null) {
            metrics.recordFlaskSession(accepted);
        }
    }

    private static IdentitySummary toSummary(AuthorizedLegacyIdentity identity) {
        return new IdentitySummary(
                identity.id(),
                identity.username(),
                identity.administrator(),
                identity.subjectAdministrator(),
                identity.notificationAdministrator(),
                identity.sessionVersion());
    }

    @Override
    public String toString() {
        return "LegacyAuthenticationCompatibilityService[redacted]";
    }
}
