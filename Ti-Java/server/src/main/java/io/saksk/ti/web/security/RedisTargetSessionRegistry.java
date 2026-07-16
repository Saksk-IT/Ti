package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

final class RedisTargetSessionRegistry implements TargetSessionRegistry {

    private static final String HMAC_ALGORITHM = "HmacSHA256";

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> REGISTER_AND_EVICT = new DefaultRedisScript<>("""
            if redis.call('ZSCORE', KEYS[1], ARGV[1]) ~= false then
              redis.call('EXPIRE', KEYS[1], ARGV[2])
              redis.call('EXPIRE', KEYS[2], ARGV[2])
              redis.call('EXPIRE', KEYS[3], ARGV[2])
              redis.call('EXPIRE', KEYS[4], ARGV[2])
              redis.call('EXPIRE', KEYS[5], ARGV[2])
              return {}
            end
            local identity_sequence = tonumber(redis.call('GET', KEYS[2]) or '0')
            if identity_sequence == 0 then
              local latest = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')
              if #latest == 2 then
                identity_sequence = tonumber(latest[2]) or 0
              end
            end
            local global_sequence = tonumber(redis.call('GET', KEYS[4]) or '0')
            if global_sequence == 0 then
              local latest = redis.call('ZREVRANGE', KEYS[3], 0, 0, 'WITHSCORES')
              if #latest == 2 then
                global_sequence = tonumber(latest[2]) or 0
              end
            end
            identity_sequence = identity_sequence + 1
            global_sequence = global_sequence + 1
            redis.call('SET', KEYS[2], tostring(identity_sequence), 'EX', ARGV[2])
            redis.call('SET', KEYS[4], tostring(global_sequence), 'EX', ARGV[2])
            redis.call('ZADD', KEYS[1], identity_sequence, ARGV[1])
            redis.call('ZADD', KEYS[3], global_sequence, ARGV[1])
            redis.call('HSET', KEYS[5], ARGV[1], ARGV[5])
            redis.call('EXPIRE', KEYS[1], ARGV[2])
            redis.call('EXPIRE', KEYS[3], ARGV[2])
            redis.call('EXPIRE', KEYS[5], ARGV[2])

            local evicted = {}
            local seen = {}
            local function record_eviction(session_id)
              if not seen[session_id] then
                seen[session_id] = true
                table.insert(evicted, session_id)
              end
            end

            local identity_excess = redis.call('ZCARD', KEYS[1]) - tonumber(ARGV[3])
            if identity_excess > 0 then
              local popped = redis.call('ZPOPMIN', KEYS[1], identity_excess)
              for index = 1, #popped, 2 do
                local victim = popped[index]
                redis.call('ZREM', KEYS[3], victim)
                redis.call('HDEL', KEYS[5], victim)
                record_eviction(victim)
              end
            end

            local global_excess = redis.call('ZCARD', KEYS[3]) - tonumber(ARGV[4])
            if global_excess > 0 then
              local popped = redis.call('ZPOPMIN', KEYS[3], global_excess)
              for index = 1, #popped, 2 do
                local victim = popped[index]
                local owner = redis.call('HGET', KEYS[5], victim)
                redis.call('HDEL', KEYS[5], victim)
                if owner then
                  local prefix = ARGV[6] .. ':{' .. owner .. '}'
                  local owner_sessions = prefix .. ':sessions'
                  local owner_sequence = prefix .. ':sequence'
                  redis.call('ZREM', owner_sessions, victim)
                  if redis.call('ZCARD', owner_sessions) == 0 then
                    redis.call('DEL', owner_sessions)
                    redis.call('DEL', owner_sequence)
                  end
                end
                record_eviction(victim)
              end
            end
            return evicted
            """, List.class);

    private static final DefaultRedisScript<Long> IS_ACTIVE = new DefaultRedisScript<>("""
            if redis.call('ZSCORE', KEYS[1], ARGV[1]) == false
                or redis.call('ZSCORE', KEYS[3], ARGV[1]) == false
                or redis.call('HGET', KEYS[5], ARGV[1]) ~= ARGV[3] then
              return 0
            end
            redis.call('EXPIRE', KEYS[1], ARGV[2])
            redis.call('EXPIRE', KEYS[2], ARGV[2])
            redis.call('EXPIRE', KEYS[3], ARGV[2])
            redis.call('EXPIRE', KEYS[4], ARGV[2])
            redis.call('EXPIRE', KEYS[5], ARGV[2])
            return 1
            """, Long.class);

    private static final DefaultRedisScript<Long> UNREGISTER = new DefaultRedisScript<>("""
            local identity_removed = redis.call('ZREM', KEYS[1], ARGV[1])
            local global_removed = redis.call('ZREM', KEYS[3], ARGV[1])
            redis.call('HDEL', KEYS[5], ARGV[1])
            if redis.call('ZCARD', KEYS[1]) == 0 then
              redis.call('DEL', KEYS[1])
              redis.call('DEL', KEYS[2])
            end
            if redis.call('ZCARD', KEYS[3]) == 0 then
              redis.call('DEL', KEYS[3])
              redis.call('DEL', KEYS[4])
              redis.call('DEL', KEYS[5])
            end
            if identity_removed == 1 or global_removed == 1 then
              return 1
            end
            return 0
            """, Long.class);

    private final StringRedisTemplate redis;
    private final TargetSessionLimitProperties properties;
    private final byte[] keySecret;

    RedisTargetSessionRegistry(
            StringRedisTemplate redis,
            TargetSessionLimitProperties properties,
            LoginRateLimitProperties loginProperties
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.keySecret = Objects.requireNonNull(loginProperties, "loginProperties").keySecretBytes();
    }

    @Override
    public List<String> registerAndSelectEvictions(long identityId, String sessionId) {
        Keys keys = keys(identityId);
        String boundedSessionId = requireSessionId(sessionId);
        Object raw = redis.execute(
                REGISTER_AND_EVICT,
                keys.all(),
                boundedSessionId,
                Long.toString(properties.registryTtl().toSeconds()),
                Integer.toString(properties.maxSessionsPerIdentity()),
                Integer.toString(properties.maxTotalSessions()),
                keys.identityDigest(),
                properties.namespace());
        if (!(raw instanceof List<?> values)
                || values.stream().anyMatch(value -> !(value instanceof String))) {
            throw new IllegalStateException("Redis returned invalid target Session evictions");
        }
        List<String> evicted = values.stream().map(String.class::cast).toList();
        if (evicted.contains(boundedSessionId)) {
            throw new IllegalStateException("Redis evicted the newly issued target Session");
        }
        return evicted;
    }

    @Override
    public boolean isActive(long identityId, String sessionId) {
        Keys keys = keys(identityId);
        Long active = redis.execute(
                IS_ACTIVE,
                keys.all(),
                requireSessionId(sessionId),
                Long.toString(properties.registryTtl().toSeconds()),
                keys.identityDigest());
        if (active == null || (active != 0L && active != 1L)) {
            throw new IllegalStateException("Redis returned invalid target Session state");
        }
        return active == 1L;
    }

    @Override
    public void unregister(long identityId, String sessionId) {
        Keys keys = keys(identityId);
        Long removed = redis.execute(
                UNREGISTER,
                keys.all(),
                requireSessionId(sessionId));
        if (removed == null || (removed != 0L && removed != 1L)) {
            throw new IllegalStateException("Redis returned invalid target Session removal state");
        }
    }

    private Keys keys(long identityId) {
        if (identityId <= 0) {
            throw new IllegalArgumentException("Target Session identity must be positive");
        }
        String identity = pseudonymize("identity\0" + identityId);
        String prefix = properties.namespace() + ":{" + identity + "}";
        return new Keys(
                identity,
                prefix + ":sessions",
                prefix + ":sequence",
                properties.namespace() + ":global:sessions",
                properties.namespace() + ":global:sequence",
                properties.namespace() + ":global:owners");
    }

    private String pseudonymize(String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            return HexFormat.of().formatHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }

    private static String requireSessionId(String value) {
        if (value == null || !value.matches("[A-Za-z0-9._-]{1,256}")) {
            throw new IllegalArgumentException("Unsafe target Session identifier");
        }
        return value;
    }

    private record Keys(
            String identityDigest,
            String sessions,
            String sequence,
            String globalSessions,
            String globalSequence,
            String owners
    ) {
        private List<String> all() {
            return List.of(sessions, sequence, globalSessions, globalSequence, owners);
        }
    }
}
