package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

class RedisTargetSessionCsrfRevokerTest {

    @Test
    @SuppressWarnings("unchecked")
    void deletesOnlyTheBoundedCsrfFieldFromTheExactSessionHash() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(
                        any(RedisScript.class),
                        eq(List.of(
                                "ti-java:identity:sessions:sessions:bounded-session")),
                        eq("sessionAttr:csrf_token")))
                .thenReturn(1L);
        RedisTargetSessionCsrfRevoker revoker =
                new RedisTargetSessionCsrfRevoker(redis, "ti-java:identity:sessions");

        revoker.revoke("bounded-session");

        org.mockito.Mockito.verify(redis).execute(
                any(RedisScript.class),
                eq(List.of("ti-java:identity:sessions:sessions:bounded-session")),
                eq("sessionAttr:csrf_token"));
    }

    @Test
    void rejectsUnsafeStorageCoordinatesBeforeRedis() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);

        assertThatThrownBy(() -> new RedisTargetSessionCsrfRevoker(redis, "unsafe namespace"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("namespace");

        RedisTargetSessionCsrfRevoker revoker =
                new RedisTargetSessionCsrfRevoker(redis, "ti-java:test");
        assertThatThrownBy(() -> revoker.revoke("../unsafe"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("identifier");
        verifyNoInteractions(redis);
    }

    @ParameterizedTest
    @ValueSource(longs = {-2L, -1L, 2L})
    @SuppressWarnings("unchecked")
    void failsClosedOnAnInvalidRedisResult(long result) {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), any(List.class), any()))
                .thenReturn(result);
        RedisTargetSessionCsrfRevoker revoker =
                new RedisTargetSessionCsrfRevoker(redis, "ti-java:test");

        assertThatThrownBy(() -> revoker.revoke("bounded-session"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid target Session CSRF state")
                .hasMessageNotContaining("bounded-session");
    }

    @Test
    @SuppressWarnings("unchecked")
    void acceptsAnExistingHashWhoseCsrfFieldWasAlreadyAbsentButRejectsNull() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), any(List.class), any()))
                .thenReturn(0L)
                .thenReturn(null);
        RedisTargetSessionCsrfRevoker revoker =
                new RedisTargetSessionCsrfRevoker(redis, "ti-java:test");

        revoker.revoke("bounded-session");

        assertThatThrownBy(() -> revoker.revoke("bounded-session"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid target Session CSRF state");
    }
}
