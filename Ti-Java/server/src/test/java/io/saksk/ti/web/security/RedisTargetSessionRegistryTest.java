package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

@SuppressWarnings("unchecked")
class RedisTargetSessionRegistryTest {

    private static final String SECRET = "test-only-target-session-secret-0001";

    @Test
    void registersChecksAndRemovesOnlyHmacIdentityKeys() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of("old-session"))
                .thenReturn(1L)
                .thenReturn(1L);
        RedisTargetSessionRegistry registry = registry(redis);

        assertThat(registry.registerAndSelectEvictions(42, "new-session"))
                .containsExactly("old-session");
        assertThat(registry.isActive(42, "new-session")).isTrue();
        registry.unregister(42, "new-session");

        @SuppressWarnings("rawtypes")
        ArgumentCaptor<List> keys = ArgumentCaptor.forClass(List.class);
        ArgumentCaptor<Object[]> arguments = ArgumentCaptor.forClass(Object[].class);
        verify(redis, org.mockito.Mockito.times(3))
                .execute(any(RedisScript.class), keys.capture(), arguments.capture());
        assertThat(keys.getAllValues()).allSatisfy(value -> assertThat(value)
                .hasSize(5)
                .allSatisfy(key -> assertThat(key.toString())
                        .startsWith("ti-java:identity:target-session-index:")
                        .doesNotContain("42", SECRET)));
        assertThat(keys.getAllValues().get(0).get(0).toString())
                .endsWith(":sessions");
        assertThat(keys.getAllValues().get(0).get(1).toString())
                .endsWith(":sequence");
        Object[] registerArguments = arguments.getAllValues().getFirst();
        assertThat(registerArguments).hasSize(6);
        assertThat(registerArguments[3]).isEqualTo("10000");
    }

    @Test
    void malformedRedisStateAndUnsafeInputsFailClosed() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class)))
                .thenReturn(List.of("new-session"));

        assertThatThrownBy(() -> registry(redis)
                .registerAndSelectEvictions(42, "new-session"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("newly issued");
        assertThatThrownBy(() -> registry(redis).isActive(0, "safe-session"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> registry(redis).unregister(42, "unsafe/session"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TargetSessionLimitProperties(
                        "unsafe namespace",
                        3,
                        10_000,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TargetSessionLimitProperties(
                        "safe",
                        11,
                        10_000,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TargetSessionLimitProperties(
                        "safe",
                        3,
                        10_000,
                        Duration.ofDays(6)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TargetSessionLimitProperties(
                        "safe",
                        3,
                        2,
                        Duration.ofDays(7)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static RedisTargetSessionRegistry registry(StringRedisTemplate redis) {
        return new RedisTargetSessionRegistry(
                redis,
                new TargetSessionLimitProperties(
                        "ti-java:identity:target-session-index",
                        3,
                        10_000,
                        Duration.ofDays(7)),
                new LoginRateLimitProperties(
                        "ti-java:identity:login-rate",
                        5,
                        SECRET));
    }
}
