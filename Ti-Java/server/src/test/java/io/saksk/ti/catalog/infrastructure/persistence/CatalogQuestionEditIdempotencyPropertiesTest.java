package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import org.junit.jupiter.api.Test;

class CatalogQuestionEditIdempotencyPropertiesTest {

    private static final String SECRET = "catalog-question-edit-idempotency-test-secret-0001";

    @Test
    void defaultsTtlCopiesSecretAndRedactsConfiguration() {
        CatalogQuestionEditIdempotencyProperties properties =
                new CatalogQuestionEditIdempotencyProperties(SECRET, null);
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
        assertThatThrownBy(() -> new CatalogQuestionEditIdempotencyProperties("short", null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditIdempotencyProperties(
                        "x".repeat(1025),
                        null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditIdempotencyProperties(
                        SECRET,
                        Duration.ofMinutes(4)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditIdempotencyProperties(
                        SECRET,
                        Duration.ofDays(31)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
