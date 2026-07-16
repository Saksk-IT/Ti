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

final class RedisCsrfIssuanceRateLimiter implements CsrfIssuanceRateLimiter {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final int COUNTER_TTL_SECONDS = 120;

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT_BOUNDED = new DefaultRedisScript<>("""
            local function increment(key)
              local count = redis.call('INCR', key)
              if count == 1 then
                redis.call('EXPIRE', key, ARGV[1])
              end
              return count
            end

            local global_count = increment(KEYS[1])
            if global_count > tonumber(ARGV[2]) then
              return {global_count, 0}
            end

            local ip_count = increment(KEYS[2])
            return {global_count, ip_count}
            """, List.class);

    private final StringRedisTemplate redis;
    private final CsrfIssuanceRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisCsrfIssuanceRateLimiter(
            StringRedisTemplate redis,
            CsrfIssuanceRateLimitProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.keySecret = Objects.requireNonNull(loginProperties, "loginProperties").keySecretBytes();
    }

    @Override
    public Decision acquire(String remoteAddress) {
        long epochSecond = clock.instant().getEpochSecond();
        long minuteBucket = Math.floorDiv(epochSecond, 60);
        String suffix = ":" + minuteBucket;
        List<String> keys = List.of(
                properties.namespace() + ":global" + suffix,
                properties.namespace() + ":ip:"
                        + pseudonymize(normalize(remoteAddress)) + suffix);

        Object raw = redis.execute(
                INCREMENT_BOUNDED,
                keys,
                Integer.toString(COUNTER_TTL_SECONDS),
                Integer.toString(properties.globalRequestsPerMinute()));
        if (!(raw instanceof List<?> counts)
                || counts.size() != 2
                || counts.stream().anyMatch(value -> !(value instanceof Long count) || count < 0)
                || (Long) counts.get(0) < 1) {
            throw new IllegalStateException("Redis returned invalid CSRF issuance rate-limit counters");
        }
        long globalCount = (Long) counts.get(0);
        long ipCount = (Long) counts.get(1);
        boolean allowed = globalCount <= properties.globalRequestsPerMinute()
                && ipCount >= 1
                && ipCount <= properties.requestsPerMinute();
        int remaining = allowed
                ? (int) Math.max(0, Math.min(
                        properties.globalRequestsPerMinute() - globalCount,
                        properties.requestsPerMinute() - ipCount))
                : 0;
        long retryAfter = 60 - Math.floorMod(epochSecond, 60);
        return new Decision(
                allowed,
                properties.requestsPerMinute(),
                remaining,
                retryAfter);
    }

    private String pseudonymize(String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            return HexFormat.of().formatHex(mac.doFinal(
                    ("csrf-ip\0" + value).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }

    private static String normalize(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        return normalized.length() <= 128 ? normalized : normalized.substring(0, 128);
    }
}
