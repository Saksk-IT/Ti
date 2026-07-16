package io.saksk.ti.web.security;

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

final class RedisSubjectReadRateLimiter implements SubjectReadRateLimiter {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String IDENTITY_KEY_DOMAIN =
            "ti-java:catalog:subject-read-rate:identity:v1\0";

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT_WINDOWS = new DefaultRedisScript<>("""
            local minute_count = redis.call('INCR', KEYS[1])
            if minute_count == 1 then
              redis.call('EXPIRE', KEYS[1], 120)
            end
            local hour_count = redis.call('INCR', KEYS[2])
            if hour_count == 1 then
              redis.call('EXPIRE', KEYS[2], 7200)
            end
            return {minute_count, hour_count}
            """, List.class);

    private final StringRedisTemplate redis;
    private final SubjectReadRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisSubjectReadRateLimiter(
            StringRedisTemplate redis,
            SubjectReadRateLimitProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.keySecret = Objects.requireNonNull(loginProperties, "loginProperties")
                .keySecretBytes();
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Override
    public Decision acquire(Route route, long identityId) {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
        long epochSecond = clock.instant().getEpochSecond();
        long minuteBucket = Math.floorDiv(epochSecond, 60);
        long hourBucket = Math.floorDiv(epochSecond, 3_600);
        String prefix = properties.namespace()
                + ":" + route.key()
                + ":identity:v1:" + pseudonymizeIdentity(identityId);

        Object raw = redis.execute(
                INCREMENT_WINDOWS,
                List.of(
                        prefix + ":minute:" + minuteBucket,
                        prefix + ":hour:" + hourBucket));
        if (!(raw instanceof List<?> counts)
                || counts.size() != 2
                || counts.stream().anyMatch(value -> !(value instanceof Long count) || count < 1)) {
            throw new IllegalStateException("Redis returned invalid subject-read counters");
        }
        long minuteCount = (Long) counts.get(0);
        long hourCount = (Long) counts.get(1);
        int minuteLimit = properties.requestsPerMinute();
        int hourLimit = properties.requestsPerHour();

        if (minuteCount > minuteLimit) {
            long retryAfter = 60 - Math.floorMod(epochSecond, 60);
            return new Decision(
                    false,
                    minuteLimit,
                    0,
                    retryAfter,
                    epochSecond + retryAfter + 1,
                    minuteLimit + " per 1 minute");
        }
        if (hourCount > hourLimit) {
            long retryAfter = 3_600 - Math.floorMod(epochSecond, 3_600);
            return new Decision(
                    false,
                    hourLimit,
                    0,
                    retryAfter,
                    epochSecond + retryAfter + 1,
                    hourLimit + " per 1 hour");
        }

        long minuteRemaining = minuteLimit - minuteCount;
        long hourRemaining = hourLimit - hourCount;
        if (hourRemaining < minuteRemaining) {
            long retryAfter = 3_600 - Math.floorMod(epochSecond, 3_600);
            return new Decision(
                    true,
                    hourLimit,
                    (int) hourRemaining,
                    retryAfter,
                    epochSecond + retryAfter + 1,
                    hourLimit + " per 1 hour");
        }

        long retryAfter = 60 - Math.floorMod(epochSecond, 60);
        return new Decision(
                true,
                minuteLimit,
                (int) minuteRemaining,
                retryAfter,
                epochSecond + retryAfter + 1,
                minuteLimit + " per 1 minute");
    }

    private String pseudonymizeIdentity(long identityId) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            byte[] input = (IDENTITY_KEY_DOMAIN + identityId).getBytes(StandardCharsets.UTF_8);
            return HexFormat.of().formatHex(mac.doFinal(input));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }
}
