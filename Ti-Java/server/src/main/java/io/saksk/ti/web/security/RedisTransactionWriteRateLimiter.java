package io.saksk.ti.web.security;

import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

final class RedisTransactionWriteRateLimiter implements TransactionWriteRateLimiter {

    private static final long WINDOW_MILLIS = 60_000;
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String DOMAIN = "ti-java:web:transaction-write-rate:v1:";

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT = new DefaultRedisScript<>("""
            local count = redis.call('INCR', KEYS[1])
            if count == 1 then
              if redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[1])) ~= 1 then
                return redis.error_reply('transaction-write expiry was not set')
              end
            end
            local ttl = redis.call('PTTL', KEYS[1])
            if ttl < 1 or ttl > tonumber(ARGV[1]) then
              return redis.error_reply('transaction-write key has invalid expiry')
            end
            return {count, ttl}
            """, List.class);

    private final StringRedisTemplate redis;
    private final TransactionWriteRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisTransactionWriteRateLimiter(
            StringRedisTemplate redis,
            TransactionWriteRateLimitProperties properties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.keySecret = properties.keySecretBytes();
    }

    @Override
    public Decision acquireForIdentity(Route route, long identityId) {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
        return acquire(route, "identity", Long.toString(identityId));
    }

    @Override
    public Decision acquireForAddress(Route route, String clientAddress) {
        if (clientAddress == null || clientAddress.isBlank() || clientAddress.length() > 128) {
            throw new IllegalArgumentException("clientAddress must be bounded and non-blank");
        }
        return acquire(route, "ip", clientAddress);
    }

    private Decision acquire(Route route, String actorType, String actor) {
        route = Objects.requireNonNull(route, "route");
        int limit = properties.effectiveLimit(route.requestsPerMinute());
        String actorKey = pseudonymize(route, actorType, actor);
        String key = properties.namespace() + ":" + route.operationId()
                + ":" + actorType + ":v1:" + actorKey;
        Object raw = redis.execute(
                INCREMENT,
                List.of(key),
                Long.toString(WINDOW_MILLIS));
        if (!(raw instanceof List<?> values)
                || values.size() != 2
                || !(values.get(0) instanceof Long count)
                || !(values.get(1) instanceof Long ttl)
                || count < 1
                || ttl < 1
                || ttl > WINDOW_MILLIS) {
            throw new IllegalStateException(
                    "Redis returned invalid transaction-write rate-limit state");
        }
        long resetAt = Math.addExact(
                Math.floorDiv(Math.addExact(clock.millis(), ttl), 1_000),
                1);
        long retryAfter = Math.max(1, resetAt - clock.instant().getEpochSecond());
        boolean allowed = count <= limit;
        return new Decision(
                allowed,
                limit,
                allowed ? Math.toIntExact(limit - count) : 0,
                retryAfter,
                resetAt);
    }

    private String pseudonymize(Route route, String actorType, String actor) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            return HexFormat.of().formatHex(mac.doFinal(
                    (DOMAIN + route.operationId() + ":" + actorType + "\0" + actor)
                            .getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }
}
