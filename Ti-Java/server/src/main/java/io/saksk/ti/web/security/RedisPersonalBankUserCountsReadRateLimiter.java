package io.saksk.ti.web.security;

import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
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

final class RedisPersonalBankUserCountsReadRateLimiter
        implements PersonalBankUserCountsReadRateLimiter {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String KEY_DOMAIN_PREFIX =
            "ti-java:learning:personal-bank-user-counts-read-rate:";
    private static final long SECOND_WINDOW_MILLIS = 1_000;
    private static final long HOUR_WINDOW_MILLIS = 3_600_000;
    private static final long DAY_WINDOW_MILLIS = 86_400_000;

    /**
     * The first hit starts each window. Evaluation stops at the first breach, so rejecting a
     * shorter window never deducts a longer one. EVAL serializes all three decisions under
     * concurrency, and every touched key must retain its bounded expiry.
     */
    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> INCREMENT_WINDOWS = new DefaultRedisScript<>("""
            local function increment(key, expiry_millis)
              local count = redis.call('INCR', key)
              if count == 1 then
                local expiry_set = redis.call('PEXPIRE', key, expiry_millis)
                if expiry_set ~= 1 then
                  return redis.error_reply('user-counts rate-limit expiry was not set')
                end
              end
              local ttl_millis = redis.call('PTTL', key)
              if ttl_millis < 1 or ttl_millis > expiry_millis then
                return redis.error_reply('user-counts rate-limit key has invalid expiry')
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
    private final PersonalBankUserCountsReadRateLimitProperties properties;
    private final Clock clock;
    private final byte[] keySecret;

    RedisPersonalBankUserCountsReadRateLimiter(
            StringRedisTemplate redis,
            PersonalBankUserCountsReadRateLimitProperties properties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.keySecret = properties.keySecretBytes();
    }

    @Override
    public Decision acquireForIdentity(Alias alias, long identityId) {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
        return acquire(
                Objects.requireNonNull(alias, "alias"),
                "identity:v1",
                pseudonymize(alias, "identity:v1", Long.toString(identityId)));
    }

    @Override
    public Decision acquireForAddress(Alias alias, String clientAddress) {
        if (clientAddress == null || clientAddress.isBlank() || clientAddress.length() > 128) {
            throw new IllegalArgumentException("clientAddress must be a bounded non-blank value");
        }
        return acquire(
                Objects.requireNonNull(alias, "alias"),
                "ip:v1",
                pseudonymize(alias, "ip:v1", clientAddress));
    }

    private Decision acquire(Alias alias, String actorType, String actorPseudonym) {
        String prefix = properties.namespace()
                + ":" + aliasKey(alias)
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
            throw invalidRedisState();
        }

        long tier = (Long) result.get(0);
        long count = (Long) result.get(1);
        long ttlMillis = (Long) result.get(2);
        if (tier < 0 || tier > 3) {
            throw invalidRedisState();
        }
        WindowState state = windowState(tier);
        if (count < 1
                || ttlMillis < 1
                || ttlMillis > state.durationMillis()
                || tier == 0 && count > state.limit()
                || tier > 0 && count <= state.limit()) {
            throw invalidRedisState();
        }

        Instant now = clock.instant();
        long expiryMillis = Math.addExact(now.toEpochMilli(), ttlMillis);
        long resetAt = Math.addExact(Math.floorDiv(expiryMillis, 1_000), 1);
        long retryAfter = Math.max(
                1,
                resetAt - now.getEpochSecond() - (now.getNano() == 0 ? 0 : 1));
        boolean allowed = tier == 0;
        int remaining = allowed ? Math.toIntExact(state.limit() - count) : 0;
        return new Decision(
                allowed,
                state.window(),
                state.limit(),
                remaining,
                retryAfter,
                resetAt);
    }

    private WindowState windowState(long tier) {
        return switch (Math.toIntExact(tier)) {
            case 0, 1 -> new WindowState(
                    Window.SECOND,
                    properties.requestsPerSecond(),
                    SECOND_WINDOW_MILLIS);
            case 2 -> new WindowState(
                    Window.HOUR,
                    properties.requestsPerHour(),
                    HOUR_WINDOW_MILLIS);
            case 3 -> new WindowState(
                    Window.DAY,
                    properties.requestsPerDay(),
                    DAY_WINDOW_MILLIS);
            default -> throw invalidRedisState();
        };
    }

    static String aliasKey(Alias alias) {
        return switch (Objects.requireNonNull(alias, "alias")) {
            case API -> "api";
            case WEB -> "web";
        };
    }

    private String pseudonymize(Alias alias, String actorType, String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            String domain = KEY_DOMAIN_PREFIX + aliasKey(alias) + ":" + actorType + "\0";
            return HexFormat.of().formatHex(mac.doFinal(
                    (domain + value).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }

    private static IllegalStateException invalidRedisState() {
        return new IllegalStateException("Redis returned invalid user-counts rate-limit state");
    }

    private record WindowState(Window window, int limit, long durationMillis) {
    }
}
