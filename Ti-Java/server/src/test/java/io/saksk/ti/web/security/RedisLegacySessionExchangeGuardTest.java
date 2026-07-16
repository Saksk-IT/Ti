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
class RedisLegacySessionExchangeGuardTest {

    private static final String SECRET = "test-only-login-rate-secret-key-0001";
    private static final Clock CLOCK =
            Clock.fixed(Instant.parse("2026-07-16T00:00:30Z"), ZoneOffset.UTC);

    @Test
    void usesHmacMarkersAndVersionedIdentityQuotasWithoutLeakingInputs() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(1L, 1L))
                .thenReturn(List.of(0L, 0L))
                .thenReturn(List.of(0L, 0L))
                .thenReturn(1L);
        RedisLegacySessionExchangeGuard guard = guard(redis);

        LegacySessionExchangeGuard.AttemptDecision decision =
                guard.beginAttempt("203.0.113.9");
        LegacySessionExchangeGuard.CredentialDecision credential =
                guard.acquireCredential(
                        "signed.Cookie-Value",
                        42,
                        7,
                        CLOCK.instant().plus(Duration.ofDays(1)));
        LegacySessionExchangeGuard.CredentialDecision nextVersion =
                guard.acquireCredential(
                        "second-version-cookie",
                        42,
                        8,
                        CLOCK.instant().plus(Duration.ofDays(1)));
        guard.releaseCredential(
                "signed.Cookie-Value", 42, 7, credential.reservationToken());

        assertThat(decision).isEqualTo(new LegacySessionExchangeGuard.AttemptDecision(
                true,
                10,
                9,
                30));
        assertThat(credential.status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        assertThat(nextVersion.status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        assertThat(credential.reservationToken()).matches("[A-Za-z0-9_-]{43}");
        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<String>> keys = ArgumentCaptor.forClass(List.class);
        verify(redis, org.mockito.Mockito.times(4))
                .execute(any(RedisScript.class), keys.capture(), any(Object[].class));
        assertThat(keys.getAllValues()).extracting(List::size).containsExactly(2, 3, 3, 3);
        assertThat(keys.getAllValues().get(1).get(1))
                .as("identity quota keys must be isolated by authoritative Session version")
                .isNotEqualTo(keys.getAllValues().get(2).get(1));
        assertThat(keys.getAllValues().get(1).get(1))
                .as("release must address the same identity-version quota as acquire")
                .isEqualTo(keys.getAllValues().get(3).get(1));
        assertThat(keys.getAllValues().stream().flatMap(List::stream)).allSatisfy(key -> assertThat(key)
                .doesNotContain("203.0.113.9", "signed.Cookie-Value", SECRET));
        assertThat(keys.getAllValues().stream().flatMap(List::stream))
                .anyMatch(key -> key.contains(":global:"))
                .anyMatch(key -> key.contains(":ip:"))
                .anyMatch(key -> key.contains(":credential:"))
                .anyMatch(key -> key.contains(":identity:"));
    }

    @Test
    void reportsReplayAndRateLimitWithoutCreatingAnotherTargetSessionDecision() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(2L, 2L))
                .thenReturn(List.of(1L, 120L))
                .thenReturn(List.of(501L, 0L));
        RedisLegacySessionExchangeGuard guard = guard(redis);

        assertThat(guard.beginAttempt("203.0.113.9").allowed()).isTrue();
        assertThat(guard.acquireCredential(
                        "same-cookie",
                        42,
                        7,
                        CLOCK.instant().plus(Duration.ofDays(1))).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.REPLAY);
        assertThat(guard.beginAttempt("203.0.113.10"))
                .isEqualTo(new LegacySessionExchangeGuard.AttemptDecision(
                        false,
                        10,
                        0,
                        30));
    }

    @Test
    void malformedRedisResultAndUnsafePropertiesFailClosed() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(0L, 0L));

        assertThatThrownBy(() -> guard(redis).beginAttempt("127.0.0.1"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid legacy Session exchange counters");
        assertThatThrownBy(() -> new LegacySessionExchangeProperties(
                        "unsafe namespace",
                        10,
                        500,
                        3,
                        10_000,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LegacySessionExchangeProperties(
                        "safe",
                        10,
                        9,
                        3,
                        10_000,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LegacySessionExchangeProperties(
                        "safe",
                        10,
                        500,
                        3,
                        10_000,
                        Duration.ofDays(8)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LegacySessionExchangeProperties(
                        "safe",
                        10,
                        500,
                        3,
                        10_000,
                        Duration.ofMinutes(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LegacySessionExchangeProperties(
                        "safe",
                        10,
                        500,
                        3,
                        2,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void limitsDistinctCredentialsForOneAuthoritativeIdentity() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of(2L, 60L))
                .thenReturn(List.of(3L, 30L));

        assertThat(guard(redis).acquireCredential(
                        "another-cookie",
                        42,
                        7,
                        CLOCK.instant().plus(Duration.ofDays(1))).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.IDENTITY_LIMITED);
        LegacySessionExchangeGuard.CredentialDecision global =
                guard(redis).acquireCredential(
                        "global-cookie",
                        99,
                        1,
                        CLOCK.instant().plus(Duration.ofDays(1)));
        assertThat(global.status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.GLOBAL_LIMITED);
        assertThat(global.retryAfterSeconds()).isEqualTo(30);
    }

    private static RedisLegacySessionExchangeGuard guard(StringRedisTemplate redis) {
        return new RedisLegacySessionExchangeGuard(
                redis,
                new LegacySessionExchangeProperties(
                        "ti-java:identity:legacy-session-exchange",
                        10,
                        500,
                        3,
                        10_000,
                        Duration.ofDays(7)),
                new LoginRateLimitProperties(
                        "ti-java:identity:login-rate",
                        5,
                        SECRET),
                CLOCK);
    }
}
