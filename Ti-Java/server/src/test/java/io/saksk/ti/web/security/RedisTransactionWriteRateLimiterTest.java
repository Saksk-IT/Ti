package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisTransactionWriteRateLimiterTest {

    private static final String SECRET =
            "test-only-transaction-write-rate-secret-0001";
    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-07-18T04:00:00Z"),
            ZoneOffset.UTC);

    @Test
    void routeAndActorDomainsAreIndependentAndNeverExposeRawActors() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 60_000L));
        RedisTransactionWriteRateLimiter limiter = limiter(redis);

        limiter.acquireForIdentity(Route.FAVORITE_WEB, 91_001L);
        limiter.acquireForIdentity(Route.FAVORITE_API, 91_001L);
        limiter.acquireForAddress(Route.FAVORITE_API, "198.51.100.88");

        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis, times(3)).execute(
                any(RedisScript.class),
                keys.capture(),
                any(Object[].class));
        assertThat(keys.getAllValues()).doesNotHaveDuplicates();
        assertThat(keys.getAllValues().toString())
                .contains("favorite-web-alias", "favorite-quiz-api")
                .doesNotContain("91001", "198.51.100.88", SECRET);
    }

    @Test
    void countAndTtlProduceTheExactAllowedAndRejectedLegacyDecisions() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 60_000L))
                .thenReturn(List.of(31L, 27_000L));
        RedisTransactionWriteRateLimiter limiter = limiter(redis);

        assertThat(limiter.acquireForIdentity(Route.FAVORITE_API, 91_001L))
                .isEqualTo(new TransactionWriteRateLimiter.Decision(
                        true,
                        30,
                        29,
                        61,
                        CLOCK.instant().getEpochSecond() + 61));
        assertThat(limiter.acquireForIdentity(Route.FAVORITE_API, 91_001L))
                .isEqualTo(new TransactionWriteRateLimiter.Decision(
                        false,
                        30,
                        0,
                        28,
                        CLOCK.instant().getEpochSecond() + 28));
    }

    @Test
    void invalidRedisStateAndActorsFailClosed() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(null)
                .thenReturn(List.of(1L))
                .thenReturn(List.of(0L, 1L))
                .thenReturn(List.of(1L, 0L));
        RedisTransactionWriteRateLimiter limiter = limiter(redis);

        for (int attempt = 0; attempt < 4; attempt++) {
            assertThatThrownBy(() ->
                    limiter.acquireForIdentity(Route.CHECKIN, 91_001L))
                    .isInstanceOf(IllegalStateException.class)
                    .hasMessageContaining("invalid transaction-write");
        }
        assertThatThrownBy(() -> limiter.acquireForIdentity(Route.CHECKIN, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> limiter.acquireForAddress(Route.CHECKIN, " "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static RedisTransactionWriteRateLimiter limiter(
            StringRedisTemplate redis
    ) {
        return new RedisTransactionWriteRateLimiter(
                redis,
                new TransactionWriteRateLimitProperties(
                        "ti-java:web:transaction-write-rate-test",
                        1,
                        SECRET),
                CLOCK);
    }
}
