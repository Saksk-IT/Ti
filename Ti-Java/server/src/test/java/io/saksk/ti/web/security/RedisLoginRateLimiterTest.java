package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisLoginRateLimiterTest {

    private static final String SECRET = "test-only-login-rate-secret-key-0001";
    private static final Clock CLOCK =
            Clock.fixed(Instant.parse("2026-07-16T00:00:30Z"), ZoneOffset.UTC);

    @Test
    void usesOnlyAnHmacPseudonymAndMinuteBucketInTheRedisKey() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 1L, 1L));
        RedisLoginRateLimiter limiter = limiter(redis, 5);

        LoginRateLimiter.Decision decision = limiter.acquire(
                "203.0.113.9", "User@Example.Test");

        assertThat(decision).isEqualTo(new LoginRateLimiter.Decision(true, 5, 4, 30));
        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<String>> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        assertThat(keys.getValue()).hasSize(3).allSatisfy(key -> assertThat(key)
                .endsWith(":" + Math.floorDiv(CLOCK.instant().getEpochSecond(), 60))
                .doesNotContain("203.0.113.9", "user@example.test", SECRET));
        assertThat(keys.getValue())
                .anyMatch(key -> key.contains(":global:"))
                .anyMatch(key -> key.contains(":ip:"))
                .anyMatch(key -> key.contains(":account:"));
    }

    @Test
    void rejectsTheFirstCounterAboveTheConfiguredLimit() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(6L, 6L, 6L));

        assertThat(limiter(redis, 5).acquire("127.0.0.1", "user@example.test"))
                .isEqualTo(new LoginRateLimiter.Decision(false, 5, 0, 30));
    }

    @Test
    void globalAndAccountDimensionsStopDistributedKdfPressure() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(101L, 0L, 0L))
                .thenReturn(List.of(1L, 1L, 6L));

        assertThat(limiter(redis, 5).acquire("198.51.100.1", "missing-a@example.test").allowed())
                .isFalse();
        assertThat(limiter(redis, 5).acquire("198.51.100.2", "victim@example.test").allowed())
                .isFalse();
        assertThat(RedisLoginRateLimiter.globalLimit(5)).isEqualTo(100);
    }

    @Test
    void failsClosedWhenRedisDoesNotReturnAValidCounter() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class))).thenReturn(null);

        assertThatThrownBy(() -> limiter(redis, 5).acquire(
                        "127.0.0.1", "user@example.test"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid login rate-limit counters");
    }

    @Test
    void propertiesRejectWeakSecretsUnsafeNamespacesAndInvalidLimits() {
        assertThatThrownBy(() -> new LoginRateLimitProperties("safe", 5, "too-short"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("32 bytes");
        assertThatThrownBy(() -> new LoginRateLimitProperties("Unsafe Namespace", 5, SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsafe");
        assertThatThrownBy(() -> new LoginRateLimitProperties("safe", 0, SECRET))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("between");

        LoginRateLimitProperties properties = properties(5);
        assertThat(properties.toString())
                .contains("keySecret=<redacted>")
                .doesNotContain(SECRET);
    }

    private static RedisLoginRateLimiter limiter(StringRedisTemplate redis, int limit) {
        return new RedisLoginRateLimiter(redis, properties(limit), CLOCK);
    }

    private static LoginRateLimitProperties properties(int limit) {
        return new LoginRateLimitProperties("ti-java:identity:login-rate", limit, SECRET);
    }
}
