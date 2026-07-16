package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

final class RedisLoginRateLimiter implements LoginRateLimiter {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final int COUNTER_TTL_SECONDS = 120;
    private static final int GLOBAL_LIMIT_MULTIPLIER = 20;
    private static final int MINIMUM_GLOBAL_LIMIT = 20;

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT_ALL = new DefaultRedisScript<>("""
            local function increment(key)
              local count = redis.call('INCR', key)
              if count == 1 then
                redis.call('EXPIRE', key, ARGV[1])
              end
              return count
            end

            local global_count = increment(KEYS[1])
            if global_count > tonumber(ARGV[2]) then
              return {global_count, 0, 0}
            end

            local ip_count = increment(KEYS[2])
            if ip_count > tonumber(ARGV[3]) then
              return {global_count, ip_count, 0}
            end

            local account_count = increment(KEYS[3])
            return {global_count, ip_count, account_count}
            """, List.class);

    private final StringRedisTemplate redis;
    private final LoginRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisLoginRateLimiter(
            StringRedisTemplate redis,
            LoginRateLimitProperties properties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.keySecret = properties.keySecretBytes();
    }

    @Override
    @SuppressWarnings("unchecked")
    public Decision acquire(String remoteAddress, String loginIdentifier) {
        long epochSecond = clock.instant().getEpochSecond();
        long minuteBucket = Math.floorDiv(epochSecond, 60);
        String suffix = ":" + minuteBucket;
        List<String> keys = List.of(
                properties.namespace() + ":global" + suffix,
                properties.namespace() + ":ip:"
                        + pseudonymize("ip\0" + normalize(remoteAddress, 128)) + suffix,
                properties.namespace() + ":account:"
                        + pseudonymize("account\0" + normalize(loginIdentifier, 1_024)) + suffix);

        Object raw = redis.execute(
                INCREMENT_ALL,
                keys,
                Integer.toString(COUNTER_TTL_SECONDS),
                Integer.toString(globalLimit(properties.requestsPerMinute())),
                Integer.toString(properties.requestsPerMinute()));
        if (!(raw instanceof List<?> counts)
                || counts.size() != 3
                || counts.stream().anyMatch(value -> !(value instanceof Long count) || count < 0)
                || (Long) counts.get(0) < 1) {
            throw new IllegalStateException("Redis returned invalid login rate-limit counters");
        }
        long globalCount = (Long) counts.get(0);
        long ipCount = (Long) counts.get(1);
        long accountCount = (Long) counts.get(2);

        int subjectLimit = properties.requestsPerMinute();
        int globalLimit = globalLimit(subjectLimit);
        boolean allowed = globalCount <= globalLimit
                && ipCount >= 1
                && ipCount <= subjectLimit
                && accountCount >= 1
                && accountCount <= subjectLimit;
        int remaining = allowed
                ? (int) Math.max(0, Math.min(
                        Math.min(subjectLimit - ipCount, subjectLimit - accountCount),
                        globalLimit - globalCount))
                : 0;
        long retryAfter = 60 - Math.floorMod(epochSecond, 60);
        return new Decision(allowed, subjectLimit, remaining, retryAfter);
    }

    static int globalLimit(int subjectLimit) {
        return (int) Math.min(
                100_000L,
                Math.max(MINIMUM_GLOBAL_LIMIT, (long) subjectLimit * GLOBAL_LIMIT_MULTIPLIER));
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

    private static String normalize(String value, int maximumLength) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        return normalized.length() <= maximumLength
                ? normalized
                : normalized.substring(0, maximumLength);
    }
}
