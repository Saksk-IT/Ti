package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

final class RedisPublicBankReadRateLimiter implements PublicBankReadRateLimiter {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String IDENTITY_KEY_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:identity:v1\0";
    private static final String ADDRESS_KEY_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:ip:v1\0";
    private static final long SECOND_WINDOW_MILLIS = 1_000;
    private static final long HOUR_WINDOW_MILLIS = 3_600_000;
    private static final long DAY_WINDOW_MILLIS = 86_400_000;

    /**
     * Each window starts on its first hit, exactly like limits' fixed-window Redis storage.
     * Evaluation stops at the first breach, so a rejected shorter window never deducts a longer
     * one. One script makes both properties true under concurrency.
     */
    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT_WINDOWS = new DefaultRedisScript<>("""
            local function increment(key, expiry_millis)
              local count = redis.call('INCR', key)
              if count == 1 then
                local expiry_set = redis.call('PEXPIRE', key, expiry_millis)
                if expiry_set ~= 1 then
                  return redis.error_reply('public-bank rate-limit expiry was not set')
                end
              end
              local ttl_millis = redis.call('PTTL', key)
              if ttl_millis < 1 then
                return redis.error_reply('public-bank rate-limit key has no expiry')
              end
              return {count, ttl_millis}
            end

            local second = increment(KEYS[1], tonumber(ARGV[1]))
            if second[1] > tonumber(ARGV[4]) then
              return {1, second[1], second[2]}
            end

            local hour = increment(KEYS[2], tonumber(ARGV[2]))
            if hour[1] > tonumber(ARGV[5]) then
              return {2, hour[1], hour[2]}
            end

            local day = increment(KEYS[3], tonumber(ARGV[3]))
            if day[1] > tonumber(ARGV[6]) then
              return {3, day[1], day[2]}
            end

            return {0, second[1], second[2]}
            """, List.class);

    private final StringRedisTemplate redis;
    private final PublicBankReadRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisPublicBankReadRateLimiter(
            StringRedisTemplate redis,
            PublicBankReadRateLimitProperties properties,
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
    public Decision acquireForIdentity(
            PublicBankReadRequestResolver.Route route,
            long identityId
    ) {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
        return acquire(route, "identity:v1", pseudonymize(IDENTITY_KEY_DOMAIN, identityId));
    }

    @Override
    public Decision acquireForAddress(
            PublicBankReadRequestResolver.Route route,
            String clientAddress
    ) {
        if (clientAddress == null || clientAddress.isBlank() || clientAddress.length() > 128) {
            throw new IllegalArgumentException("clientAddress must be a bounded non-blank value");
        }
        return acquire(route, "ip:v1", pseudonymize(ADDRESS_KEY_DOMAIN, clientAddress));
    }

    private Decision acquire(
            PublicBankReadRequestResolver.Route route,
            String actorType,
            String actorPseudonym
    ) {
        String prefix = properties.namespace()
                + ":" + routeKey(Objects.requireNonNull(route, "route"))
                + ":" + actorType + ":" + actorPseudonym;
        Object raw = redis.execute(
                INCREMENT_WINDOWS,
                List.of(prefix + ":second", prefix + ":hour", prefix + ":day"),
                Long.toString(SECOND_WINDOW_MILLIS),
                Long.toString(HOUR_WINDOW_MILLIS),
                Long.toString(DAY_WINDOW_MILLIS),
                Integer.toString(properties.requestsPerSecond()),
                Integer.toString(properties.requestsPerHour()),
                Integer.toString(properties.requestsPerDay()));
        if (!(raw instanceof List<?> result)
                || result.size() != 3
                || result.stream().anyMatch(value -> !(value instanceof Long))) {
            throw new IllegalStateException("Redis returned invalid public-bank rate-limit state");
        }
        long tier = (Long) result.get(0);
        long count = (Long) result.get(1);
        long ttlMillis = (Long) result.get(2);
        Window window = window(tier);
        if (count < 1
                || ttlMillis < 1
                || ttlMillis > window.durationMillis()
                || tier == 0 && count > window.limit()
                || tier > 0 && count <= window.limit()) {
            throw new IllegalStateException("Redis returned invalid public-bank rate-limit state");
        }

        Instant now = clock.instant();
        long expiryMillis = Math.addExact(now.toEpochMilli(), ttlMillis);
        long resetAt = Math.addExact(Math.floorDiv(expiryMillis, 1_000), 1);
        long retryAfter = Math.max(
                1,
                resetAt - now.getEpochSecond() - (now.getNano() == 0 ? 0 : 1));
        boolean allowed = tier == 0;
        int remaining = allowed ? Math.toIntExact(window.limit() - count) : 0;
        return new Decision(
                allowed,
                window.limit(),
                remaining,
                retryAfter,
                resetAt,
                window.legacyDescription());
    }

    private Window window(long tier) {
        return switch (Math.toIntExact(tier)) {
            case 0 -> new Window(
                    properties.requestsPerSecond(),
                    SECOND_WINDOW_MILLIS,
                    properties.requestsPerSecond() + " per 1 second");
            case 1 -> new Window(
                    properties.requestsPerSecond(),
                    SECOND_WINDOW_MILLIS,
                    properties.requestsPerSecond() + " per 1 second");
            case 2 -> new Window(
                    properties.requestsPerHour(),
                    HOUR_WINDOW_MILLIS,
                    properties.requestsPerHour() + " per 1 hour");
            case 3 -> new Window(
                    properties.requestsPerDay(),
                    DAY_WINDOW_MILLIS,
                    properties.requestsPerDay() + " per 1 day");
            default -> throw new IllegalStateException(
                    "Redis returned invalid public-bank rate-limit state");
        };
    }

    static String routeKey(PublicBankReadRequestResolver.Route route) {
        return switch (route) {
            case LEGACY_LIST -> "legacy-list";
            case BOARDS -> "boards";
            case CARD_DETAIL -> "card-detail";
            case HOT -> "hot";
            case PLAZA_LIST -> "plaza-list";
            case SUMMARY -> "summary";
            case DETAIL -> "detail";
        };
    }

    private String pseudonymize(String domain, long value) {
        return pseudonymize(domain, Long.toString(value));
    }

    private String pseudonymize(String domain, String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            return HexFormat.of().formatHex(mac.doFinal(
                    (domain + value).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }

    private record Window(int limit, long durationMillis, String legacyDescription) {
    }
}
