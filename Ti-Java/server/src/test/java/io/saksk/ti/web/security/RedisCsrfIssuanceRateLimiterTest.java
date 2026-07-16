package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisCsrfIssuanceRateLimiterTest {

    private static final String SECRET = "test-only-login-rate-secret-key-0001";
    private static final Clock CLOCK =
            Clock.fixed(Instant.parse("2026-07-16T00:00:30Z"), ZoneOffset.UTC);

    @Test
    void usesGlobalAndHmacIpKeysWithoutLeakingTheAddress() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 1L));

        CsrfIssuanceRateLimiter.Decision decision = limiter(redis).acquire("203.0.113.9");

        assertThat(decision).isEqualTo(new CsrfIssuanceRateLimiter.Decision(true, 30, 29, 30));
        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<String>> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        assertThat(keys.getValue()).hasSize(2).allSatisfy(key -> assertThat(key)
                .endsWith(":" + Math.floorDiv(CLOCK.instant().getEpochSecond(), 60))
                .doesNotContain("203.0.113.9", SECRET));
        assertThat(keys.getValue())
                .anyMatch(key -> key.contains(":global:"))
                .anyMatch(key -> key.contains(":ip:"));
    }

    @Test
    void acceptsZeroIpCounterOnlyWhenTheGlobalGateRejectedBeforeKeyCreation() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1001L, 0L));

        assertThat(limiter(redis).acquire("203.0.113.9"))
                .isEqualTo(new CsrfIssuanceRateLimiter.Decision(false, 30, 0, 30));
    }

    @Test
    void failsClosedOnMalformedRedisCountersAndInvalidConfiguration() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 0L));

        assertThatThrownBy(() -> limiter(redis).acquire("127.0.0.1"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid CSRF issuance");
        assertThatThrownBy(() -> new CsrfIssuanceRateLimitProperties(
                        "unsafe namespace",
                        30,
                        1000,
                        Duration.ofMinutes(10)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CsrfIssuanceRateLimitProperties(
                        "safe",
                        30,
                        29,
                        Duration.ofMinutes(10)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CsrfIssuanceRateLimitProperties(
                        "safe",
                        30,
                        1000,
                        Duration.ofDays(1)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static RedisCsrfIssuanceRateLimiter limiter(StringRedisTemplate redis) {
        return new RedisCsrfIssuanceRateLimiter(
                redis,
                new CsrfIssuanceRateLimitProperties(
                        "ti-java:identity:csrf-issuance-rate",
                        30,
                        1000,
                        Duration.ofMinutes(10)),
                new LoginRateLimitProperties(
                        "ti-java:identity:login-rate",
                        5,
                        SECRET),
                CLOCK);
    }
}
