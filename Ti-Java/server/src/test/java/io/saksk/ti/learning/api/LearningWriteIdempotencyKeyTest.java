package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class LearningWriteIdempotencyKeyTest {

    @Test
    void blankIsAbsentAndPresentValuesAreAlwaysRedacted() {
        assertThat(LearningWriteIdempotencyKey.fromNullable(null).isPresent()).isFalse();
        assertThat(LearningWriteIdempotencyKey.fromNullable(" \t").isPresent()).isFalse();

        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("private-idempotency-key");
        assertThat(key.value()).contains("private-idempotency-key");
        assertThat(key.toString())
                .contains("<redacted>")
                .doesNotContain("private-idempotency-key");
    }

    @Test
    void enforcesTheUtf8ByteBoundary() {
        assertThat(LearningWriteIdempotencyKey.of("a".repeat(255)).isPresent()).isTrue();
        assertThatThrownBy(() -> LearningWriteIdempotencyKey.of("a".repeat(256)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LearningWriteIdempotencyKey.of("界".repeat(86)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
