package io.saksk.ti.identity.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class LegacyAuthenticationAuthorityTest {

    @Test
    void authorizesOnlyCurrentUnlockedStateAndReturnsDatabaseIdentityAndRoles() {
        FakeStore store = new FakeStore(state(
                "current-database-name",
                " db-openid ",
                false,
                false,
                7,
                true,
                false));
        var authority = new LegacyAuthenticationAuthority(store);

        var result = authority.authorizeJwt(4242, 7, "db-openid").orElseThrow();

        assertThat(result.id()).isEqualTo(4242);
        assertThat(result.username()).isEqualTo("current-database-name");
        assertThat(result.administrator()).isFalse();
        assertThat(result.subjectAdministrator()).isTrue();
        assertThat(result.notificationAdministrator()).isFalse();
        assertThat(result.sessionVersion()).isEqualTo(7);
        assertThat(store.lastIdentityId).isEqualTo(4242);
    }

    @Test
    void rejectsMissingLockedVersionChangedAndWrongRows() {
        assertThat(new LegacyAuthenticationAuthority(new FakeStore(null))
                        .authorizeFlaskSession(4242, 7))
                .isEmpty();
        assertThat(new LegacyAuthenticationAuthority(new FakeStore(state(
                        "locked", null, true, true, 7, true, true)))
                        .authorizeFlaskSession(4242, 7))
                .isEmpty();
        assertThat(new LegacyAuthenticationAuthority(new FakeStore(state(
                        "changed", null, false, false, 8, false, false)))
                        .authorizeFlaskSession(4242, 7))
                .isEmpty();

        FakeStore wrongRow = new FakeStore(new AuthoritativeIdentityState(
                4243, "wrong-row", null, false, false, 7, false, false));
        assertThat(new LegacyAuthenticationAuthority(wrongRow)
                        .authorizeFlaskSession(4242, 7))
                .isEmpty();
    }

    @Test
    void appliesTheObservedNullEmptyAndNonEmptyOpenidRules() {
        var boundAuthority = new LegacyAuthenticationAuthority(new FakeStore(state(
                "bound", "openid-current", false, false, 7, false, false)));
        assertThat(boundAuthority.authorizeJwt(4242, 7, " openid-current ")).isPresent();
        assertThat(boundAuthority.authorizeJwt(4242, 7, "openid-rebound")).isEmpty();
        assertThat(boundAuthority.authorizeJwt(4242, 7, "")).isPresent();
        assertThat(boundAuthority.authorizeJwt(4242, 7, " \u00a0 ")).isPresent();
        assertThat(boundAuthority.authorizeJwt(4242, 7, null)).isEmpty();

        var unboundAuthority = new LegacyAuthenticationAuthority(new FakeStore(state(
                "unbound", null, false, false, 7, false, false)));
        assertThat(unboundAuthority.authorizeJwt(4242, 7, "openid-before-unbind"))
                .isEmpty();
        assertThat(unboundAuthority.authorizeJwt(4242, 7, "")).isPresent();
    }

    @Test
    void invalidParametersAndDatabaseFailuresFailClosed() {
        FakeStore untouched = new FakeStore(state(
                "current", null, false, false, 0, false, false));
        var authority = new LegacyAuthenticationAuthority(untouched);
        assertThat(authority.authorizeJwt(0, 0, "")).isEmpty();
        assertThat(authority.authorizeJwt(4242, -1, "")).isEmpty();
        assertThat(authority.authorizeFlaskSession(-1, 0)).isEmpty();
        assertThat(untouched.calls).isZero();

        FakeStore failing = new FakeStore(null);
        failing.failure = new IllegalStateException("database unavailable with secret detail");
        var failingAuthority = new LegacyAuthenticationAuthority(failing);
        assertThat(failingAuthority.authorizeJwt(4242, 7, "sensitive-openid")).isEmpty();
        assertThat(failingAuthority.authorizeFlaskSession(4242, 7)).isEmpty();
        assertThat(failingAuthority.toString()).isEqualTo("LegacyAuthenticationAuthority[redacted]");
    }

    @Test
    void stateAndResultStringRepresentationsAreRedacted() {
        AuthoritativeIdentityState state = state(
                "sensitive-name",
                "sensitive-openid",
                true,
                false,
                7,
                true,
                true);
        var result = state.authorize();

        assertThat(state.toString())
                .isEqualTo("AuthoritativeIdentityState[redacted]")
                .doesNotContain("sensitive-name", "sensitive-openid", "4242");
        assertThat(result.toString())
                .isEqualTo("AuthorizedLegacyIdentity[redacted]")
                .doesNotContain("sensitive-name", "sensitive-openid", "4242");
    }

    private static AuthoritativeIdentityState state(
            String username,
            String openid,
            boolean administrator,
            boolean locked,
            int sessionVersion,
            boolean subjectAdministrator,
            boolean notificationAdministrator
    ) {
        return new AuthoritativeIdentityState(
                4242,
                username,
                openid,
                administrator,
                locked,
                sessionVersion,
                subjectAdministrator,
                notificationAdministrator);
    }

    private static final class FakeStore implements AuthoritativeIdentityStateStore {
        private final AuthoritativeIdentityState state;
        private RuntimeException failure;
        private int calls;
        private long lastIdentityId;

        private FakeStore(AuthoritativeIdentityState state) {
            this.state = state;
        }

        @Override
        public Optional<AuthoritativeIdentityState> findById(long identityId) {
            calls++;
            lastIdentityId = identityId;
            if (failure != null) {
                throw failure;
            }
            return Optional.ofNullable(state);
        }
    }
}
