package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.concurrent.Semaphore;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

class WerkzeugPasswordVerifierTest {
    private final WerkzeugPasswordVerifier verifier = new WerkzeugPasswordVerifier();

    @Test
    void verifiesWerkzeugScryptAndUnicodePbkdf2CrossLanguageVectors() {
        for (JsonNode vector : LegacyAuthVectors.root().path("passwords")) {
            char[] correct = vector.path("password").asString().toCharArray();
            char[] wrong = (vector.path("password").asString() + "-wrong").toCharArray();
            try {
                assertThat(verifier.verify(correct, vector.path("hash").asString()))
                        .as("valid public test-only %s vector", vector.path("method").asString())
                        .isTrue();
                assertThat(verifier.verify(wrong, vector.path("hash").asString()))
                        .as("wrong password for %s", vector.path("method").asString())
                        .isFalse();
            } finally {
                java.util.Arrays.fill(correct, '\0');
                java.util.Arrays.fill(wrong, '\0');
            }
        }
    }

    @Test
    void acceptsOnlyExactScryptParametersAndBoundedPbkdf2Sha256Grammar() {
        String scrypt = LegacyAuthVectors.root().path("passwords").get(0).path("hash").asString();
        String pbkdf2 = LegacyAuthVectors.root().path("passwords").get(1).path("hash").asString();
        char[] password = "PUBLIC-TEST-ONLY-Passw0rd!".toCharArray();
        try {
            for (String malformed : List.of(
                    scrypt.replace("scrypt:32768:8:1", "scrypt"),
                    scrypt.replace("scrypt:32768:8:1", "scrypt:16384:8:1"),
                    scrypt.replace("scrypt:32768:8:1", "scrypt:32768:4:1"),
                    scrypt.replace("scrypt:32768:8:1", "scrypt:32768:8:2"),
                    pbkdf2.replace("pbkdf2:sha256:600000", "pbkdf2:sha1:600000"),
                    pbkdf2.replace("pbkdf2:sha256:600000", "pbkdf2:sha256:49999"),
                    pbkdf2.replace("pbkdf2:sha256:600000", "pbkdf2:sha256:1000001"),
                    pbkdf2.replace("pbkdf2:sha256:600000", "pbkdf2:sha256:0600000"),
                    pbkdf2 + "$extra",
                    pbkdf2.replace("PublicSalt654321", "bad-salt"),
                    "plain$PublicSalt654321$" + "0".repeat(64))) {
                assertThat(verifier.verify(password, malformed))
                        .as("malformed hash grammar must fail closed")
                        .isFalse();
            }
        } finally {
            java.util.Arrays.fill(password, '\0');
        }
    }

    @Test
    void rejectsNonCanonicalDigestLengthsCaseAndInputLimitsBeforeExpensiveWork() {
        String pbkdf2 = LegacyAuthVectors.root().path("passwords").get(1).path("hash").asString();
        int hashSeparator = pbkdf2.lastIndexOf('$');
        String prefix = pbkdf2.substring(0, hashSeparator + 1);
        String digest = pbkdf2.substring(hashSeparator + 1);
        char[] password = "x".toCharArray();
        try {
            assertThat(verifier.verify(password, prefix + digest.toUpperCase())).isFalse();
            assertThat(verifier.verify(password, prefix + digest.substring(1))).isFalse();
            assertThat(verifier.verify(password, prefix + digest + "0")).isFalse();
            assertThat(verifier.verify(password, "x".repeat(
                            WerkzeugPasswordVerifier.MAXIMUM_STORED_HASH_CHARACTERS + 1)))
                    .isFalse();
            assertThat(verifier.verify(
                            new char[WerkzeugPasswordVerifier.MAXIMUM_PASSWORD_CHARACTERS + 1], pbkdf2))
                    .isFalse();
            assertThat(verifier.verify(new char[] {'\ud800'}, pbkdf2)).isFalse();
            assertThat(verifier.verify(null, pbkdf2)).isFalse();
            assertThat(verifier.verify(password, null)).isFalse();
        } finally {
            java.util.Arrays.fill(password, '\0');
        }
    }

    @Test
    void rejectsImmediatelyWhenTheProcessWideKdfBudgetIsSaturatedAndReleasesPermits() {
        JsonNode vector = LegacyAuthVectors.root().path("passwords").get(1);
        char[] password = vector.path("password").asString().toCharArray();
        try {
            assertThat(new WerkzeugPasswordVerifier(new PasswordKdfBudget(new Semaphore(0)))
                            .verify(password, vector.path("hash").asString()))
                    .isFalse();

            Semaphore singlePermit = new Semaphore(1);
            assertThat(new WerkzeugPasswordVerifier(new PasswordKdfBudget(singlePermit))
                            .verify(password, vector.path("hash").asString()))
                    .isTrue();
            assertThat(singlePermit.availablePermits()).isEqualTo(1);
        } finally {
            java.util.Arrays.fill(password, '\0');
        }
    }
}
