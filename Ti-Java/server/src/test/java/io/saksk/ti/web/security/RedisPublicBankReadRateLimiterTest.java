package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

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
class RedisPublicBankReadRateLimiterTest {

    private static final Instant INTEGER_NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final Clock INTEGER_CLOCK = Clock.fixed(INTEGER_NOW, ZoneOffset.UTC);
    private static final Clock FRACTIONAL_CLOCK = Clock.fixed(
            INTEGER_NOW.plusMillis(250), ZoneOffset.UTC);
    private static final String KEY_SECRET = "test-only-public-bank-rate-secret-0001";
    private static final String IDENTITY_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:identity:v1\0";
    private static final String ADDRESS_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:ip:v1\0";

    @Test
    void allowedRequestUsesIndependentRouteAndDomainSeparatedHmacIdentityKeys() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 1L, 1_000L));

        PublicBankReadRateLimiter.Decision decision = limiter(redis, INTEGER_CLOCK)
                .acquireForIdentity(PublicBankReadRequestResolver.Route.SUMMARY, 4101);

        assertThat(decision).isEqualTo(new PublicBankReadRateLimiter.Decision(
                true,
                10,
                9,
                2,
                INTEGER_NOW.getEpochSecond() + 2,
                "10 per 1 second"));
        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        String pseudonym = hmac(IDENTITY_DOMAIN, "4101");
        assertThat(keys.getValue()).containsExactly(
                key("summary", "identity:v1", pseudonym, "second"),
                key("summary", "identity:v1", pseudonym, "hour"),
                key("summary", "identity:v1", pseudonym, "day"));
        assertThat(keys.getValue().toString()).doesNotContain("4101", ":uid:");
    }

    @Test
    void addressKeysUseADifferentHmacDomainAndRouteNamespace() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 1L, 1_000L));

        limiter(redis, INTEGER_CLOCK).acquireForAddress(
                PublicBankReadRequestResolver.Route.CARD_DETAIL,
                "198.51.100.41");

        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        String addressPseudonym = hmac(ADDRESS_DOMAIN, "198.51.100.41");
        assertThat(keys.getValue()).containsExactly(
                key("card-detail", "ip:v1", addressPseudonym, "second"),
                key("card-detail", "ip:v1", addressPseudonym, "hour"),
                key("card-detail", "ip:v1", addressPseudonym, "day"));
        assertThat(addressPseudonym).isNotEqualTo(hmac(IDENTITY_DOMAIN, "198.51.100.41"));
        assertThat(keys.getValue().toString()).doesNotContain("198.51.100.41");
    }

    @Test
    void reportsTheFirstBreachedWindowAndExactFractionalRetrySemantics() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 11L, 1_000L))
                .thenReturn(List.of(2L, 501L, 3_570_000L))
                .thenReturn(List.of(3L, 5_001L, 50_390_000L));
        RedisPublicBankReadRateLimiter limiter = limiter(redis, FRACTIONAL_CLOCK);

        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.1"))
                .isEqualTo(rejected(10, 1, 2, "10 per 1 second"));
        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.2"))
                .isEqualTo(rejected(500, 3_570, 3_571, "500 per 1 hour"));
        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.3"))
                .isEqualTo(rejected(5_000, 50_390, 50_391, "5000 per 1 day"));
    }

    @Test
    void millisecondExpiryKeepsResetStableAtIntegerFractionalAndNearExpiryTimes() {
        assertThat(allowedAt(INTEGER_NOW, 1_000))
                .extracting(
                        PublicBankReadRateLimiter.Decision::resetAtEpochSecond,
                        PublicBankReadRateLimiter.Decision::retryAfterSeconds)
                .containsExactly(INTEGER_NOW.getEpochSecond() + 2, 2L);
        assertThat(allowedAt(INTEGER_NOW.plusMillis(250), 1_000))
                .extracting(
                        PublicBankReadRateLimiter.Decision::resetAtEpochSecond,
                        PublicBankReadRateLimiter.Decision::retryAfterSeconds)
                .containsExactly(INTEGER_NOW.getEpochSecond() + 2, 1L);
        assertThat(allowedAt(INTEGER_NOW.plusMillis(900), 100))
                .extracting(
                        PublicBankReadRateLimiter.Decision::resetAtEpochSecond,
                        PublicBankReadRateLimiter.Decision::retryAfterSeconds)
                .containsExactly(INTEGER_NOW.getEpochSecond() + 2, 1L);
    }

    @Test
    void rejectsInvalidRedisStateAndInvalidActors() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(null)
                .thenReturn(List.of(4L, 1L, 1_000L))
                .thenReturn(List.of(0L, 11L, 1_000L));
        RedisPublicBankReadRateLimiter limiter = limiter(redis, INTEGER_CLOCK);

        assertThatThrownBy(() -> limiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.DETAIL, 4101))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid public-bank rate-limit state");
        assertThatThrownBy(() -> limiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.DETAIL, 4101))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid public-bank rate-limit state");
        assertThatThrownBy(() -> limiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.DETAIL, 4101))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid public-bank rate-limit state");
        assertThatThrownBy(() -> limiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.DETAIL, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("positive");
        assertThatThrownBy(() -> limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.DETAIL, " "))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("bounded");
    }

    @Test
    void propertiesApplyTheLegacyProductionMultiplierAndRejectUnsafeValues() {
        PublicBankReadRateLimitProperties production = new PublicBankReadRateLimitProperties(
                "ti-java:catalog:public-bank-read-rate", 10, 500, 5_000, 100);
        assertThat(production.requestsPerSecond()).isEqualTo(1_000);
        assertThat(production.requestsPerHour()).isEqualTo(50_000);
        assertThat(production.requestsPerDay()).isEqualTo(500_000);

        assertThatThrownBy(() -> new PublicBankReadRateLimitProperties(
                "Unsafe Namespace", 10, 500, 5_000, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsafe");
        assertThatThrownBy(() -> new PublicBankReadRateLimitProperties(
                "safe", 10, 9, 5_000, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Invalid");
        assertThatThrownBy(() -> new PublicBankReadRateLimitProperties(
                "safe", 10, 500, 5_000, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("1..1000");
    }

    private static PublicBankReadRateLimiter.Decision rejected(
            int limit,
            long retryAfter,
            long resetOffset,
            String description
    ) {
        return new PublicBankReadRateLimiter.Decision(
                false,
                limit,
                0,
                retryAfter,
                INTEGER_NOW.getEpochSecond() + resetOffset,
                description);
    }

    private static PublicBankReadRateLimiter.Decision allowedAt(Instant now, long pttlMillis) {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 1L, pttlMillis));
        return limiter(redis, Clock.fixed(now, ZoneOffset.UTC)).acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS,
                "198.51.100.99");
    }

    private static RedisPublicBankReadRateLimiter limiter(
            StringRedisTemplate redis,
            Clock clock
    ) {
        return new RedisPublicBankReadRateLimiter(
                redis,
                new PublicBankReadRateLimitProperties(
                        "ti-java:catalog:public-bank-read-rate", 10, 500, 5_000, 1),
                new LoginRateLimitProperties(
                        "ti-java:identity:login-rate", 5, KEY_SECRET),
                clock);
    }

    private static String key(String route, String actorType, String actor, String window) {
        return "ti-java:catalog:public-bank-read-rate:" + route + ":" + actorType + ":"
                + actor + ":" + window;
    }

    private static String hmac(String domain, String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (domain + value).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }
}
