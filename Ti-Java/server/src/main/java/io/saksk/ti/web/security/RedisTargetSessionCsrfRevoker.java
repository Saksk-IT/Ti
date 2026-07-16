package io.saksk.ti.web.security;

import java.util.List;
import java.util.Objects;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

/**
 * Physically removes the CSRF hash field after Spring Session has committed the login response.
 *
 * <p>{@code RedisSessionRepository.removeAttribute(...)} records a null delta and can persist an
 * empty hash value with a custom serializer. The login boundary requires the field to be absent,
 * so this cleanup uses the repository's documented Redis key layout and an atomic HDEL
 * postcondition check.</p>
 */
@Component
final class RedisTargetSessionCsrfRevoker implements TargetSessionCsrfRevoker {

    private static final String SESSION_KEY_SEGMENT = ":sessions:";
    private static final String CSRF_HASH_FIELD =
            "sessionAttr:" + SessionBoundCsrfTokens.SESSION_ATTRIBUTE;
    private static final DefaultRedisScript<Long> REVOKE = new DefaultRedisScript<>("""
            if redis.call('EXISTS', KEYS[1]) == 0 then
              return -2
            end
            local removed = redis.call('HDEL', KEYS[1], ARGV[1])
            if redis.call('HEXISTS', KEYS[1], ARGV[1]) ~= 0 then
              return -1
            end
            return removed
            """, Long.class);

    private final StringRedisTemplate redis;
    private final String sessionKeyPrefix;

    RedisTargetSessionCsrfRevoker(
            StringRedisTemplate redis,
            @Value("${spring.session.data.redis.namespace:ti-java:identity:sessions}")
            String namespace
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.sessionKeyPrefix = requireNamespace(namespace) + SESSION_KEY_SEGMENT;
    }

    @Override
    public void revoke(String sessionId) {
        String boundedSessionId = requireSessionId(sessionId);
        Long removed = redis.execute(
                REVOKE,
                List.of(sessionKeyPrefix + boundedSessionId),
                CSRF_HASH_FIELD);
        if (removed == null || removed < 0L || removed > 1L) {
            throw new IllegalStateException("Redis returned invalid target Session CSRF state");
        }
    }

    private static String requireNamespace(String value) {
        if (value == null
                || !value.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || value.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe target Session Redis namespace");
        }
        return value;
    }

    private static String requireSessionId(String value) {
        if (value == null || !value.matches("[A-Za-z0-9._-]{1,256}")) {
            throw new IllegalArgumentException("Unsafe target Session identifier");
        }
        return value;
    }
}
