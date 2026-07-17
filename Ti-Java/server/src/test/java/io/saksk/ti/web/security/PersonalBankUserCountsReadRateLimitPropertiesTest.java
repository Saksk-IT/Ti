package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

import java.time.Clock;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;

class PersonalBankUserCountsReadRateLimitPropertiesTest {

    private static final String KEY_SECRET = "test-only-user-counts-rate-secret-0001";

    @Test
    void appliesTheProductionMultiplierWithoutChangingTheConfiguredBaseLimits() {
        PersonalBankUserCountsReadRateLimitProperties properties = properties(100);

        assertThat(properties.namespace())
                .isEqualTo("ti-java:learning:personal-bank-user-counts-read-rate");
        assertThat(properties.requestsPerSecond()).isEqualTo(1_000);
        assertThat(properties.requestsPerHour()).isEqualTo(50_000);
        assertThat(properties.requestsPerDay()).isEqualTo(500_000);
        assertThat(properties.multiplier()).isEqualTo(100);
        assertThat(properties.toString())
                .contains("multiplier=100", "keySecret=<redacted>")
                .doesNotContain(KEY_SECRET);
    }

    @Test
    void rejectsUnsafeNamespacesInvalidBudgetsAndMultiplierOverflow() {
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "Unsafe Namespace", 10, 500, 5_000, 1, KEY_SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsafe");
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe:", 10, 500, 5_000, 1, KEY_SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsafe");
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe", 10, 9, 5_000, 1, KEY_SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("base rate limits");
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe", 10, 500, 5_000, 0, KEY_SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("1..1000");
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe", Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE,
                2, KEY_SECRET))
                .isInstanceOf(ArithmeticException.class);
    }

    @Test
    void requiresAnIndependentSecretOfAtLeastThirtyTwoUtf8Bytes() {
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe", 10, 500, 5_000, 1, null))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("keySecret");
        assertThatThrownBy(() -> new PersonalBankUserCountsReadRateLimitProperties(
                "safe", 10, 500, 5_000, 1, "short-secret"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("at least 32 bytes");

        String multibyteSecret = "密".repeat(11);
        PersonalBankUserCountsReadRateLimitProperties accepted =
                new PersonalBankUserCountsReadRateLimitProperties(
                        "safe", 10, 500, 5_000, 1, multibyteSecret);
        assertThat(accepted.keySecretBytes()).hasSize(33);
    }

    @Test
    void wiringRejectsLoginKeyReuseAndPublicBankNamespaceReuse() {
        LoginRateLimitConfiguration configuration = new LoginRateLimitConfiguration();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        LoginRateLimitProperties login = new LoginRateLimitProperties(
                "ti-java:identity:login-rate",
                5,
                KEY_SECRET);
        PublicBankReadRateLimitProperties publicBank =
                new PublicBankReadRateLimitProperties(
                        "ti-java:catalog:public-bank-read-rate",
                        10,
                        500,
                        5_000,
                        1);

        assertThatThrownBy(() -> configuration.personalBankUserCountsReadRateLimiter(
                redis,
                properties(1),
                publicBank,
                login,
                Clock.systemUTC()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("independent key material")
                .hasMessageNotContaining(KEY_SECRET);

        PersonalBankUserCountsReadRateLimitProperties independent =
                new PersonalBankUserCountsReadRateLimitProperties(
                        publicBank.namespace(),
                        10,
                        500,
                        5_000,
                        1,
                        "independent-user-counts-secret-0001");
        assertThatThrownBy(() -> configuration.personalBankUserCountsReadRateLimiter(
                redis,
                independent,
                publicBank,
                login,
                Clock.systemUTC()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("independent namespaces");
    }

    private static PersonalBankUserCountsReadRateLimitProperties properties(int multiplier) {
        return new PersonalBankUserCountsReadRateLimitProperties(
                "ti-java:learning:personal-bank-user-counts-read-rate",
                10,
                500,
                5_000,
                multiplier,
                KEY_SECRET);
    }
}
