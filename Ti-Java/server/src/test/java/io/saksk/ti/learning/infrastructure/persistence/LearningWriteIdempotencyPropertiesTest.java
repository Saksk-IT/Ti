package io.saksk.ti.learning.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import org.junit.jupiter.api.Test;

class LearningWriteIdempotencyPropertiesTest {

    private static final String SECRET = "learning-write-idempotency-test-secret-0001";

    @Test
    void defaultsTtlCopiesSecretAndRedactsConfiguration() {
        LearningWriteIdempotencyProperties properties =
                new LearningWriteIdempotencyProperties(SECRET, null);
        byte[] first = properties.keySecretBytes();
        first[0] = 0;

        assertThat(properties.keySecretBytes()).isNotEqualTo(first);
        assertThat(properties.receiptTtl()).isEqualTo(Duration.ofHours(24));
        assertThat(properties.toString())
                .contains("keySecret=<redacted>", "PT24H")
                .doesNotContain(SECRET);
    }

    @Test
    void rejectsShortOrOversizedSecretsAndUnsafeTtl() {
        assertThatThrownBy(() -> new LearningWriteIdempotencyProperties("short", null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteIdempotencyProperties(
                        "x".repeat(1025),
                        null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteIdempotencyProperties(
                        SECRET,
                        Duration.ofMinutes(4)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteIdempotencyProperties(
                        SECRET,
                        Duration.ofDays(31)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
