package io.saksk.ti.identity.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.api.AuthenticateCommand;
import io.saksk.ti.identity.api.AuthenticationOutcome;
import io.saksk.ti.identity.application.port.IdentityCredentialStore;
import io.saksk.ti.identity.application.port.PasswordHashPort;
import io.saksk.ti.identity.domain.IdentityCredential;
import io.saksk.ti.identity.domain.LoginIdentifier;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class PasswordLoginApplicationServiceTest {

    private static final char[] PASSWORD = "phase3-password".toCharArray();

    @Test
    void authenticatesAndAtomicallyUpgradesALegacyCredential() {
        FakeStore store = new FakeStore(List.of(credential("legacy-hash", false, false)));
        FakeHashes hashes = new FakeHashes(true, false);
        var service = new PasswordLoginApplicationService(store, hashes);

        try (var command = new AuthenticateCommand(" user@example.test ", PASSWORD)) {
            var result = service.authenticate(command);

            assertThat(result.outcome()).isEqualTo(AuthenticationOutcome.AUTHENTICATED);
            assertThat(result.passwordUpgraded()).isTrue();
            assertThat(result.authenticatedIdentity().orElseThrow().id()).isEqualTo(7L);
            assertThat(store.updatedTarget).isEqualTo("target-hash");
            assertThat(store.updatedObserved).isEqualTo("legacy-hash");
            assertThat(store.updatedSessionVersion).isEqualTo(3);
            assertThat(store.lastIdentifier.value()).isEqualTo("user@example.test");
        }
        assertThat(hashes.lastPasswordReference).containsOnly('\0');
    }

    @Test
    void marksAnExistingTargetCredentialWithoutRehashing() {
        FakeStore store = new FakeStore(List.of(credential("target-hash", false, false)));
        FakeHashes hashes = new FakeHashes(true, true);
        var service = new PasswordLoginApplicationService(store, hashes);

        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            var result = service.authenticate(command);
            assertThat(result.passwordUpgraded()).isFalse();
            assertThat(store.updatedTarget).isEqualTo("target-hash");
            assertThat(hashes.encodeCalls).isZero();
        }
    }

    @Test
    void invalidDuplicateAndLockedAccountsNeverWrite() {
        FakeHashes hashes = new FakeHashes(false, false);
        FakeStore wrong = new FakeStore(List.of(credential("legacy-hash", false, true)));
        var wrongService = new PasswordLoginApplicationService(wrong, hashes);
        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(wrongService.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
        assertThat(wrong.updatedTarget).isNull();

        FakeStore duplicate = new FakeStore(List.of(
                credential("one", false, true),
                credential("two", false, true)));
        var duplicateService = new PasswordLoginApplicationService(duplicate, new FakeHashes(true, false));
        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(duplicateService.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
        assertThat(duplicate.updatedTarget).isNull();

        FakeStore locked = new FakeStore(List.of(credential("legacy-hash", true, true)));
        var lockedService = new PasswordLoginApplicationService(locked, new FakeHashes(true, false));
        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(lockedService.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.ACCOUNT_LOCKED);
        }
        assertThat(locked.updatedTarget).isNull();
    }

    @Test
    void missingOrUnsupportedIdentifiersPayTheDummyHashCost() {
        FakeStore store = new FakeStore(List.of());
        FakeHashes hashes = new FakeHashes(false, false);
        var service = new PasswordLoginApplicationService(store, hashes);

        try (var command = new AuthenticateCommand("plain-username", PASSWORD)) {
            assertThat(service.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
        assertThat(hashes.dummyCalls).isOne();
        assertThat(store.findCalls).isZero();

        try (var command = new AuthenticateCommand("missing@example.test", PASSWORD)) {
            assertThat(service.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
        assertThat(hashes.dummyCalls).isEqualTo(2);
    }

    @Test
    void aFailedCompareAndSetFailsClosed() {
        FakeStore store = new FakeStore(List.of(credential("legacy-hash", false, false)));
        store.updateSucceeds = false;
        store.refreshed = Optional.empty();
        var service = new PasswordLoginApplicationService(store, new FakeHashes(true, false));

        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(service.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
    }

    @Test
    void concurrentLegacyUpgradeRevalidatesTheWinningTargetHashInsteadOfReturning503() {
        FakeStore store = new FakeStore(List.of(credential("legacy-hash", false, false)));
        store.updateSucceeds = false;
        store.refreshed = Optional.of(credential("target-hash", false, true));
        FakeHashes hashes = new FakeHashes(true, false);
        hashes.targetHashValue = "target-hash";
        var service = new PasswordLoginApplicationService(store, hashes);

        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            var result = service.authenticate(command);
            assertThat(result.outcome()).isEqualTo(AuthenticationOutcome.AUTHENTICATED);
            assertThat(result.authenticatedIdentity()).contains(credential(
                    "target-hash", false, true).summary());
        }
        assertThat(store.refreshCalls).isOne();
        assertThat(hashes.matchCalls).isEqualTo(2);
    }

    @Test
    void lockOrPasswordChangeDuringKdfCannotProduceASession() {
        FakeStore locked = new FakeStore(List.of(credential("legacy-hash", false, false)));
        locked.updateSucceeds = false;
        locked.refreshed = Optional.of(credential("legacy-hash", true, false));
        var lockedService = new PasswordLoginApplicationService(locked, new FakeHashes(true, false));
        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(lockedService.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.ACCOUNT_LOCKED);
        }

        FakeStore reset = new FakeStore(List.of(credential("legacy-hash", false, false)));
        reset.updateSucceeds = false;
        reset.refreshed = Optional.of(credential("reset-hash", false, true));
        FakeHashes changed = new FakeHashes(true, false);
        changed.rejectHash = "reset-hash";
        var resetService = new PasswordLoginApplicationService(reset, changed);
        try (var command = new AuthenticateCommand("user@example.test", PASSWORD)) {
            assertThat(resetService.authenticate(command).outcome())
                    .isEqualTo(AuthenticationOutcome.INVALID_CREDENTIALS);
        }
    }

    private static IdentityCredential credential(String hash, boolean locked, boolean passwordSet) {
        return new IdentityCredential(7, "phase3-user", hash, true, locked, 3, true, false, passwordSet);
    }

    private static final class FakeStore implements IdentityCredentialStore {
        private final List<IdentityCredential> candidates;
        private int findCalls;
        private LoginIdentifier lastIdentifier;
        private String updatedObserved;
        private String updatedTarget;
        private int updatedSessionVersion;
        private boolean updateSucceeds = true;
        private Optional<IdentityCredential> refreshed;
        private int refreshCalls;

        private FakeStore(List<IdentityCredential> candidates) {
            this.candidates = candidates;
            this.refreshed = candidates.size() == 1
                    ? Optional.of(candidates.getFirst())
                    : Optional.empty();
        }

        @Override
        public List<IdentityCredential> findForAuthentication(LoginIdentifier identifier) {
            findCalls++;
            lastIdentifier = identifier;
            return candidates;
        }

        @Override
        public Optional<IdentityCredential> findByIdForAuthentication(long id) {
            refreshCalls++;
            return refreshed;
        }

        @Override
        public boolean replacePasswordHashAndMarkSet(
                long id,
                String observedHash,
                int observedSessionVersion,
                String targetHash
        ) {
            updatedObserved = observedHash;
            updatedTarget = targetHash;
            updatedSessionVersion = observedSessionVersion;
            return updateSucceeds;
        }

        @Override
        public Optional<io.saksk.ti.identity.api.IdentitySummary> confirmSuccessfulAuthentication(
                long identityId,
                String observedHash,
                int observedSessionVersion
        ) {
            return refreshed
                    .filter(value -> !value.locked())
                    .filter(value -> value.summary().sessionVersion() == observedSessionVersion)
                    .map(IdentityCredential::summary);
        }
    }

    private static final class FakeHashes implements PasswordHashPort {
        private final boolean matches;
        private final boolean target;
        private int dummyCalls;
        private int encodeCalls;
        private int matchCalls;
        private char[] lastPasswordReference;
        private String targetHashValue = "target-hash";
        private String rejectHash;

        private FakeHashes(boolean matches, boolean target) {
            this.matches = matches;
            this.target = target;
        }

        @Override
        public boolean matches(char[] password, String storedHash) {
            lastPasswordReference = password;
            matchCalls++;
            return matches && !storedHash.equals(rejectHash);
        }

        @Override
        public boolean isTargetHash(String storedHash) {
            return target || storedHash.equals(targetHashValue);
        }

        @Override
        public String encodeTarget(char[] password) {
            encodeCalls++;
            return "target-hash";
        }

        @Override
        public void performDummyVerification(char[] password) {
            dummyCalls++;
            lastPasswordReference = password;
        }
    }
}
