package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.List;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisPersonalBankUserCountsReadRateLimiterTest {

    private static final Instant INTEGER_NOW = Instant.parse("2026-07-17T04:00:00Z");
    private static final Clock INTEGER_CLOCK = Clock.fixed(INTEGER_NOW, ZoneOffset.UTC);
    private static final Clock FRACTIONAL_CLOCK = Clock.fixed(
            INTEGER_NOW.plusMillis(250), ZoneOffset.UTC);
    private static final String KEY_SECRET = "test-only-user-counts-rate-secret-0001";
    private static final String NAMESPACE =
            "ti-java:learning:personal-bank-user-counts-read-rate";
    private static final String DOMAIN_PREFIX =
            "ti-java:learning:personal-bank-user-counts-read-rate:";

    @Test
    void identityKeysAreAliasScopedDomainSeparatedHmacValues() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 1L, 1_000L));

        Decision decision = limiter(redis, INTEGER_CLOCK).acquireForIdentity(Alias.API, 4101);

        assertThat(decision).isEqualTo(new Decision(
                true,
                Window.SECOND,
                10,
                9,
                2,
                INTEGER_NOW.getEpochSecond() + 2));
        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        String pseudonym = hmac("api", "identity:v1", "4101");
        assertThat(keys.getValue()).containsExactly(
                key("api", "identity:v1", pseudonym, "second"),
                key("api", "identity:v1", pseudonym, "hour"),
                key("api", "identity:v1", pseudonym, "day"));
        assertThat(keys.getValue().toString())
                .doesNotContain("4101", ":uid:", KEY_SECRET);
    }

    @Test
    void webAddressUsesADifferentAliasAndActorDomainWithoutRawAddress() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 1L, 1_000L));

        RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(redis, INTEGER_CLOCK);
        limiter.acquireForAddress(Alias.API, "198.51.100.41");
        limiter.acquireForAddress(Alias.WEB, "198.51.100.41");

        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis, times(2)).execute(
                any(RedisScript.class), keys.capture(), any(Object[].class));
        String apiPseudonym = hmac("api", "ip:v1", "198.51.100.41");
        String webPseudonym = hmac("web", "ip:v1", "198.51.100.41");
        assertThat(apiPseudonym).isNotEqualTo(webPseudonym);
        assertThat(keys.getAllValues().get(0).toString())
                .contains(":" + apiPseudonym + ":")
                .doesNotContain("198.51.100.41");
        assertThat(keys.getAllValues().get(1).toString())
                .contains(":" + webPseudonym + ":")
                .doesNotContain("198.51.100.41");
    }

    @Test
    void reportsTheFirstBreachedWindowWithExactFractionalRetrySemantics() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 11L, 1_000L))
                .thenReturn(List.of(2L, 501L, 3_570_000L))
                .thenReturn(List.of(3L, 5_001L, 50_390_000L));
        RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(redis, FRACTIONAL_CLOCK);

        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.1"))
                .isEqualTo(rejected(Window.SECOND, 10, 1, 2));
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.2"))
                .isEqualTo(rejected(Window.HOUR, 500, 3_570, 3_571));
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.3"))
                .isEqualTo(rejected(Window.DAY, 5_000, 50_390, 50_391));
    }

    @Test
    void rejectsInvalidRedisStateAndInvalidActors() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(null)
                .thenReturn(List.of(4L, 1L, 1_000L))
                .thenReturn(List.of(0L, 11L, 1_000L))
                .thenReturn(List.of(1L, 10L, 1_000L))
                .thenReturn(List.of(0L, 1L, 0L))
                .thenReturn(List.of(Long.MAX_VALUE, 1L, 1_000L));
        RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(redis, INTEGER_CLOCK);

        for (int attempt = 0; attempt < 6; attempt++) {
            assertThatThrownBy(() -> limiter.acquireForIdentity(Alias.API, 4101))
                    .isInstanceOf(IllegalStateException.class)
                    .hasMessageContaining("invalid user-counts rate-limit state");
        }
        assertThatThrownBy(() -> limiter.acquireForIdentity(Alias.API, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("positive");
        assertThatThrownBy(() -> limiter.acquireForAddress(Alias.WEB, " "))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("bounded");
        assertThatThrownBy(() -> limiter.acquireForAddress(null, "198.51.100.41"))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("alias");
    }

    @Test
    void decisionDerivesOnlyTheBoundedLegacyLimitDescription() {
        assertThat(new Decision(false, Window.SECOND, 10, 0, 1, 2)
                .legacyLimitDescription()).isEqualTo("10 per 1 second");
        assertThat(new Decision(false, Window.HOUR, 500, 0, 1, 2)
                .legacyLimitDescription()).isEqualTo("500 per 1 hour");
        assertThat(new Decision(false, Window.DAY, 5_000, 0, 1, 2)
                .legacyLimitDescription()).isEqualTo("5000 per 1 day");
        assertThatThrownBy(() -> new Decision(false, Window.DAY, 5_000, 1, 1, 2))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static Decision rejected(
            Window window,
            int limit,
            long retryAfter,
            long resetOffset
    ) {
        return new Decision(
                false,
                window,
                limit,
                0,
                retryAfter,
                INTEGER_NOW.getEpochSecond() + resetOffset);
    }

    private static RedisPersonalBankUserCountsReadRateLimiter limiter(
            StringRedisTemplate redis,
            Clock clock
    ) {
        return new RedisPersonalBankUserCountsReadRateLimiter(
                redis,
                new PersonalBankUserCountsReadRateLimitProperties(
                        NAMESPACE,
                        10,
                        500,
                        5_000,
                        1,
                        KEY_SECRET),
                clock);
    }

    private static String key(
            String alias,
            String actorType,
            String actor,
            String window
    ) {
        return NAMESPACE + ":" + alias + ":" + actorType + ":" + actor + ":" + window;
    }

    private static String hmac(String alias, String actorType, String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (DOMAIN_PREFIX + alias + ":" + actorType + "\0" + value)
                            .getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }
}
