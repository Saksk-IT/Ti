package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNoException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.security.SecureRandom;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

class TransitionalPasswordHashAdapterTest {

    private static final String ROLLBACK_PASSWORD =
            "PUBLIC-TEST-ONLY-Java-Rollback-密码";
    private static final String ROLLBACK_HASH =
            "scrypt:32768:8:1$JavaRollback0001$"
                    + "852cfabaed211c8db8f333be1d3e83869dc1791e39853b1f00c4a5aa1c267abc"
                    + "c1c5d81267cc4859e215e6dd9935731ec91472b603b35f94b510f61da3d41e7a";

    @Test
    void createsTheExactWerkzeugScryptFormatRequiredForFlaskRollback() {
        PasswordKdfBudget budget = new PasswordKdfBudget(new Semaphore(1));
        var hashes = new TransitionalPasswordHashAdapter(budget, new SecureRandom());
        var werkzeug = new WerkzeugPasswordVerifier(budget);
        char[] password = "PUBLIC-TEST-ONLY-target-password-密码".toCharArray();
        char[] wrong = "PUBLIC-TEST-ONLY-wrong".toCharArray();
        try {
            String encoded = hashes.encodeTarget(password);

            assertThat(encoded)
                    .startsWith(TransitionalPasswordHashAdapter.TARGET_PREFIX)
                    .matches("scrypt:32768:8:1\\$[A-Za-z0-9]{16}\\$[0-9a-f]{128}")
                    .doesNotContain("target-password", "密码", "{scrypt@");
            assertThat(hashes.isTargetHash(encoded)).isTrue();
            assertThat(hashes.matches(password, encoded)).isTrue();
            assertThat(hashes.matches(wrong, encoded)).isFalse();
            assertThat(werkzeug.verify(password, encoded)).isTrue();
            assertThat(budget.availablePermits()).isEqualTo(1);
        } finally {
            Arrays.fill(password, '\0');
            Arrays.fill(wrong, '\0');
        }
    }

    @Test
    void deterministicJavaEncodingMatchesThePublicFlaskRollbackVectorExactly() {
        var hashes = new TransitionalPasswordHashAdapter(
                new PasswordKdfBudget(new Semaphore(1)),
                new FixedSaltSecureRandom("JavaRollback0001"));
        char[] password = ROLLBACK_PASSWORD.toCharArray();
        try {
            assertThat(hashes.encodeTarget(password)).isEqualTo(ROLLBACK_HASH);
            assertThat(hashes.matches(password, ROLLBACK_HASH)).isTrue();
        } finally {
            Arrays.fill(password, '\0');
        }
    }

    @Test
    void currentWerkzeugScryptIsAlreadyTargetWhilePbkdf2NeedsCompatibleUpgrade() {
        var hashes = new TransitionalPasswordHashAdapter();
        String scrypt = LegacyAuthVectors.root().path("passwords").get(0).path("hash").asString();
        String pbkdf2 = LegacyAuthVectors.root().path("passwords").get(1).path("hash").asString();

        assertThat(hashes.isTargetHash(scrypt)).isTrue();
        assertThat(hashes.isTargetHash(pbkdf2)).isFalse();
        assertThat(hashes.isTargetHash(scrypt.replace("scrypt:32768:8:1", "scrypt:65536:8:1")))
                .isFalse();
    }

    @Test
    void publicSyntheticDummyUsesTheSameRollbackCompatibleGrammar() {
        PasswordKdfBudget budget = new PasswordKdfBudget(new Semaphore(1));
        var hashes = new TransitionalPasswordHashAdapter(budget, new SecureRandom());
        char[] publicDummyPassword = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        try {
            assertThat(hashes.isTargetHash(
                    TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH)).isTrue();
            assertThat(new WerkzeugPasswordVerifier(budget).verify(
                    publicDummyPassword,
                    TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH)).isTrue();
            assertThat(hashes.matches(publicDummyPassword, "unknown$format")).isFalse();
            assertThatNoException().isThrownBy(() ->
                    hashes.performDummyVerification(publicDummyPassword));
            assertThat(budget.availablePermits()).isEqualTo(1);
        } finally {
            Arrays.fill(publicDummyPassword, '\0');
        }
    }

    @Test
    void malformedTargetGrammarFailsClosed() {
        var hashes = new TransitionalPasswordHashAdapter();
        String valid = TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH;
        char[] password = "PUBLIC-TEST-ONLY-any-password".toCharArray();
        try {
            for (String malformed : List.of(
                    TransitionalPasswordHashAdapter.TARGET_PREFIX,
                    valid.replace("scrypt:32768:8:1", "scrypt:16384:8:1"),
                    valid.replace("PublicSalt123456", "bad-salt"),
                    valid.substring(0, valid.length() - 1),
                    valid + "0",
                    valid.substring(0, valid.length() - 2) + "AA")) {
                assertThat(hashes.isTargetHash(malformed)).isFalse();
                assertThat(hashes.matches(password, malformed)).isFalse();
            }
        } finally {
            Arrays.fill(password, '\0');
        }
    }

    @Test
    void nullMalformedAndOversizedPasswordsFailClosedWithoutLeakingInputs() {
        var hashes = new TransitionalPasswordHashAdapter();
        String valid = TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH;
        char[] oversized = new char[PasswordInputLimits.MAXIMUM_CHARACTERS + 1];
        char[] malformed = new char[] {'\ud800'};
        try {
            assertThat(hashes.matches(null, valid)).isFalse();
            assertThat(hashes.matches(oversized, valid)).isFalse();
            assertThat(hashes.matches(malformed, valid)).isFalse();
            assertThatNoException().isThrownBy(() -> hashes.performDummyVerification(null));
            assertThatNoException().isThrownBy(() -> hashes.performDummyVerification(oversized));
            assertThatThrownBy(() -> hashes.encodeTarget(null))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessage("password input is invalid");
            assertThatThrownBy(() -> hashes.encodeTarget(malformed))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessage("password input is invalid");
        } finally {
            Arrays.fill(oversized, '\0');
            Arrays.fill(malformed, '\0');
        }
    }

    @Test
    void everyExpensivePathSharesTheSameNonBlockingCapacityBudget() {
        PasswordKdfBudget saturated = new PasswordKdfBudget(new Semaphore(0));
        var hashes = new TransitionalPasswordHashAdapter(saturated, new SecureRandom());
        char[] password = "PUBLIC-TEST-ONLY-password".toCharArray();
        String target = TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH;
        String pbkdf2 = LegacyAuthVectors.root().path("passwords").get(1).path("hash").asString();
        try {
            assertThatThrownBy(() -> hashes.matches(password, target))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
            assertThatThrownBy(() -> hashes.matches(password, pbkdf2))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
            assertThatThrownBy(() -> hashes.matches(password, "unknown$format"))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
            assertThatThrownBy(() -> hashes.performDummyVerification(password))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
            assertThatThrownBy(() -> hashes.encodeTarget(password))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
            assertThat(saturated.availablePermits()).isZero();
        } finally {
            Arrays.fill(password, '\0');
        }
    }

    @Test
    @Timeout(value = 30)
    void twoRealScryptMatchesExhaustTheFairBudgetThenReleaseEveryPermit()
            throws Exception {
        GatedFairSemaphore semaphore = new GatedFairSemaphore(
                PasswordKdfBudget.MAXIMUM_CONCURRENT_KDFS);
        PasswordKdfBudget budget = new PasswordKdfBudget(semaphore);
        var hashes = new TransitionalPasswordHashAdapter(budget, new SecureRandom());
        String target = TransitionalPasswordHashAdapter.PUBLIC_TEST_ONLY_DUMMY_HASH;
        char[] firstPassword = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        char[] secondPassword = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        char[] rejectedPassword = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        char[] recoveredPassword = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        ExecutorService workers = Executors.newFixedThreadPool(
                PasswordKdfBudget.MAXIMUM_CONCURRENT_KDFS);
        try {
            Future<Boolean> firstMatch = workers.submit(() -> hashes.matches(firstPassword, target));
            Future<Boolean> secondMatch = workers.submit(() -> hashes.matches(secondPassword, target));

            assertThat(semaphore.awaitInitialAcquisitions(5, TimeUnit.SECONDS)).isTrue();
            assertThat(semaphore.isFair()).isTrue();
            assertThat(budget.availablePermits()).isZero();
            assertThatThrownBy(() -> hashes.matches(rejectedPassword, target))
                    .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class)
                    .hasMessage("password KDF capacity is exhausted");

            semaphore.allowKdfsToProceed();
            assertThat(firstMatch.get(20, TimeUnit.SECONDS)).isTrue();
            assertThat(secondMatch.get(20, TimeUnit.SECONDS)).isTrue();
            assertThat(budget.availablePermits())
                    .isEqualTo(PasswordKdfBudget.MAXIMUM_CONCURRENT_KDFS);
            assertThat(hashes.matches(recoveredPassword, target)).isTrue();
            assertThat(budget.availablePermits())
                    .isEqualTo(PasswordKdfBudget.MAXIMUM_CONCURRENT_KDFS);
        } finally {
            semaphore.allowKdfsToProceed();
            workers.shutdownNow();
            workers.awaitTermination(20, TimeUnit.SECONDS);
            Arrays.fill(firstPassword, '\0');
            Arrays.fill(secondPassword, '\0');
            Arrays.fill(rejectedPassword, '\0');
            Arrays.fill(recoveredPassword, '\0');
        }
    }

    /** Holds the first successful acquisitions before their real KDFs begin. */
    private static final class GatedFairSemaphore extends Semaphore {
        private final CountDownLatch initialAcquisitions;
        private final CountDownLatch kdfStartGate = new CountDownLatch(1);
        private final AtomicInteger successfulAcquisitions = new AtomicInteger();

        private GatedFairSemaphore(int permits) {
            super(permits, true);
            initialAcquisitions = new CountDownLatch(permits);
        }

        @Override
        public boolean tryAcquire() {
            boolean acquired = super.tryAcquire();
            if (!acquired) {
                return false;
            }
            if (successfulAcquisitions.getAndIncrement()
                    < PasswordKdfBudget.MAXIMUM_CONCURRENT_KDFS) {
                initialAcquisitions.countDown();
                try {
                    kdfStartGate.await();
                } catch (InterruptedException exception) {
                    release();
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException("test KDF start gate interrupted", exception);
                }
            }
            return true;
        }

        private boolean awaitInitialAcquisitions(long timeout, TimeUnit unit)
                throws InterruptedException {
            return initialAcquisitions.await(timeout, unit);
        }

        private void allowKdfsToProceed() {
            kdfStartGate.countDown();
        }
    }

    private static final class FixedSaltSecureRandom extends SecureRandom {
        private static final String ALPHABET =
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

        private final String salt;
        private int index;

        private FixedSaltSecureRandom(String salt) {
            this.salt = salt;
        }

        @Override
        public int nextInt(int bound) {
            assertThat(bound).isEqualTo(ALPHABET.length());
            return ALPHABET.indexOf(salt.charAt(index++));
        }
    }
}
