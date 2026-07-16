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
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.HexFormat;
import java.util.List;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisSubjectReadRateLimiterTest {

    private static final Clock CLOCK =
            Clock.fixed(Instant.parse("2026-07-16T00:00:30Z"), ZoneOffset.UTC);
    private static final String KEY_SECRET = "test-only-login-rate-secret-key-0001";
    private static final String IDENTITY_KEY_DOMAIN =
            "ti-java:catalog:subject-read-rate:identity:v1\0";

    @Test
    void incrementsSeparateRouteIdentityMinuteAndHourWindowsAtomically() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 10L));

        SubjectReadRateLimiter.Decision decision = limiter(redis).acquire(
                SubjectReadRateLimiter.Route.SUBJECTS_META,
                4101);

        assertThat(decision).isEqualTo(new SubjectReadRateLimiter.Decision(
                true,
                60,
                59,
                30,
                CLOCK.instant().getEpochSecond() + 31,
                "60 per 1 minute"));
        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        verify(redis).execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        List<String> capturedKeys = ((List<?>) keys.getValue()).stream()
                .map(String.class::cast)
                .toList();
        String identityPseudonym = hmacIdentity(4101);
        assertThat(capturedKeys)
                .containsExactly(
                        "ti-java:catalog:subject-read-rate:subjects-meta:identity:v1:"
                                + identityPseudonym + ":minute:"
                                + Math.floorDiv(CLOCK.instant().getEpochSecond(), 60),
                        "ti-java:catalog:subject-read-rate:subjects-meta:identity:v1:"
                                + identityPseudonym + ":hour:"
                                + Math.floorDiv(CLOCK.instant().getEpochSecond(), 3_600));
        assertThat(capturedKeys)
                .allMatch(key -> !key.contains("4101") && !key.contains(":uid:"));
    }

    @Test
    void rejectsTheFirstRequestAboveTheMinuteOrHourBudget() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(61L, 61L))
                .thenReturn(List.of(1L, 601L));

        assertThat(limiter(redis).acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .isEqualTo(new SubjectReadRateLimiter.Decision(
                        false,
                        60,
                        0,
                        30,
                        CLOCK.instant().getEpochSecond() + 31,
                        "60 per 1 minute"));
        assertThat(limiter(redis).acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .isEqualTo(new SubjectReadRateLimiter.Decision(
                        false,
                        600,
                        0,
                        3_570,
                        CLOCK.instant().getEpochSecond() + 3_571,
                        "600 per 1 hour"));
    }

    @Test
    void reportsAConsistentHourWindowWhenItBecomesTheGoverningBudget() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 599L));

        assertThat(limiter(redis).acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .isEqualTo(new SubjectReadRateLimiter.Decision(
                        true,
                        600,
                        1,
                        3_570,
                        CLOCK.instant().getEpochSecond() + 3_571,
                        "600 per 1 hour"));
    }

    @Test
    void failsClosedForInvalidRedisResultsAndInvalidIdentity() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(null);

        assertThatThrownBy(() -> limiter(redis).acquire(
                        SubjectReadRateLimiter.Route.SUBJECTS,
                        4101))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid subject-read counters");
        assertThatThrownBy(() -> limiter(redis).acquire(
                        SubjectReadRateLimiter.Route.SUBJECTS,
                        0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("positive");
    }

    @Test
    void propertiesApplyTheLegacyEnvironmentMultiplierAndRejectUnsafeValues() {
        SubjectReadRateLimitProperties production = new SubjectReadRateLimitProperties(
                "ti-java:catalog:subject-read-rate",
                60,
                600,
                100);
        assertThat(production.requestsPerMinute()).isEqualTo(6_000);
        assertThat(production.requestsPerHour()).isEqualTo(60_000);

        assertThatThrownBy(() -> new SubjectReadRateLimitProperties("Unsafe Namespace", 60, 600, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsafe");
        assertThatThrownBy(() -> new SubjectReadRateLimitProperties("safe", 0, 600, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Invalid");
        assertThatThrownBy(() -> new SubjectReadRateLimitProperties("safe", 60, 600, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("1..1000");
    }

    private static RedisSubjectReadRateLimiter limiter(StringRedisTemplate redis) {
        return new RedisSubjectReadRateLimiter(
                redis,
                new SubjectReadRateLimitProperties(
                        "ti-java:catalog:subject-read-rate",
                        60,
                        600,
                        1),
                new LoginRateLimitProperties(
                        "ti-java:identity:login-rate",
                        5,
                        KEY_SECRET),
                CLOCK);
    }

    private static String hmacIdentity(long identityId) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (IDENTITY_KEY_DOMAIN + identityId).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }
}
