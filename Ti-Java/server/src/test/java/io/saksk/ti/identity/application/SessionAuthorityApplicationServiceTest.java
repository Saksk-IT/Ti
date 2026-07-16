package io.saksk.ti.identity.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.api.SessionAuthorizationResult;
import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class SessionAuthorityApplicationServiceTest {

    @Test
    void currentUnlockedSessionReceivesOnlyCurrentDatabaseIdentityAndRoles() {
        var service = new SessionAuthorityApplicationService(storeReturning(state(false, 7)));

        var result = service.authorize(42, 7);

        assertThat(result.status()).isEqualTo(SessionAuthorizationResult.Status.AUTHORIZED);
        assertThat(result.identity().orElseThrow().username()).isEqualTo("current-database-user");
        assertThat(result.identity().orElseThrow().administrator()).isTrue();
    }

    @Test
    void missingLockedOrVersionChangedSessionsAreAuthoritativelyRejected() {
        assertThat(new SessionAuthorityApplicationService(storeReturning(null))
                        .authorize(42, 7).status())
                .isEqualTo(SessionAuthorizationResult.Status.REJECTED);
        assertThat(new SessionAuthorityApplicationService(storeReturning(state(true, 7)))
                        .authorize(42, 7).status())
                .isEqualTo(SessionAuthorizationResult.Status.REJECTED);
        assertThat(new SessionAuthorityApplicationService(storeReturning(state(false, 8)))
                        .authorize(42, 7).status())
                .isEqualTo(SessionAuthorizationResult.Status.REJECTED);
    }

    @Test
    void databaseFailureIsUnavailableRatherThanPermanentRevocation() {
        AuthoritativeIdentityStateStore failing = identityId -> {
            throw new IllegalStateException("database unavailable");
        };

        var result = new SessionAuthorityApplicationService(failing).authorize(42, 7);

        assertThat(result.status()).isEqualTo(SessionAuthorizationResult.Status.UNAVAILABLE);
        assertThat(result.identity()).isEmpty();
        assertThat(result.toString()).doesNotContain("database unavailable", "current-database-user");
    }

    private static AuthoritativeIdentityStateStore storeReturning(
            AuthoritativeIdentityState state
    ) {
        return identityId -> Optional.ofNullable(state);
    }

    private static AuthoritativeIdentityState state(boolean locked, int sessionVersion) {
        return new AuthoritativeIdentityState(
                42,
                "current-database-user",
                null,
                true,
                locked,
                sessionVersion,
                false,
                true);
    }
}
