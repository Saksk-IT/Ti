package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

final class RedisLegacySessionExchangeGuard implements LegacySessionExchangeGuard {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final int COUNTER_TTL_SECONDS = 120;

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> BEGIN_BOUNDED_ATTEMPT = new DefaultRedisScript<>("""
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

    @SuppressWarnings("rawtypes")
    private static final DefaultRedisScript<List> ACQUIRE_CREDENTIAL_ONCE =
            new DefaultRedisScript<>("""
                    if redis.call('EXISTS', KEYS[1]) == 1 then
                      local replay_ttl = redis.call('TTL', KEYS[1])
                      return {1, math.max(1, replay_ttl)}
                    end
                    local redis_time = redis.call('TIME')
                    local now = tonumber(redis_time[1])
                    local credential_ttl = tonumber(ARGV[6]) - now
                    if credential_ttl < 1 then
                      return {4, 1}
                    end
                    redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
                    redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', now)
                    if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[2]) then
                      local oldest = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
                      return {2, math.max(1, tonumber(oldest[2]) - now)}
                    end
                    if redis.call('ZCARD', KEYS[3]) >= tonumber(ARGV[3]) then
                      local oldest = redis.call('ZRANGE', KEYS[3], 0, 0, 'WITHSCORES')
                      return {3, math.max(1, tonumber(oldest[2]) - now)}
                    end
                    local marker_ttl = math.min(tonumber(ARGV[1]), credential_ttl)
                    local expires_at = now + marker_ttl
                    redis.call('SET', KEYS[1], ARGV[4], 'EX', marker_ttl)
                    redis.call('ZADD', KEYS[2], expires_at, ARGV[5])
                    redis.call('EXPIRE', KEYS[2], ARGV[1])
                    redis.call('ZADD', KEYS[3], expires_at, ARGV[5])
                    redis.call('EXPIRE', KEYS[3], ARGV[1])
                    return {0, 0}
                    """, List.class);

    private static final DefaultRedisScript<Long> RELEASE_CREDENTIAL =
            new DefaultRedisScript<>("""
                    if redis.call('GET', KEYS[1]) ~= ARGV[2] then
                      return 0
                    end
                    local removed = redis.call('DEL', KEYS[1])
                    redis.call('ZREM', KEYS[2], ARGV[1])
                    redis.call('ZREM', KEYS[3], ARGV[1])
                    if redis.call('ZCARD', KEYS[2]) == 0 then
                      redis.call('DEL', KEYS[2])
                    end
                    if redis.call('ZCARD', KEYS[3]) == 0 then
                      redis.call('DEL', KEYS[3])
                    end
                    return removed
                    """, Long.class);

    private final StringRedisTemplate redis;
    private final LegacySessionExchangeProperties properties;
    private final Clock clock;
    private final byte[] keySecret;
    private final SecureRandom reservations = new SecureRandom();

    RedisLegacySessionExchangeGuard(
            StringRedisTemplate redis,
            LegacySessionExchangeProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.keySecret = Objects.requireNonNull(loginProperties, "loginProperties").keySecretBytes();
    }

    @Override
    public AttemptDecision beginAttempt(String remoteAddress) {
        long epochSecond = clock.instant().getEpochSecond();
        long minuteBucket = Math.floorDiv(epochSecond, 60);
        String suffix = ":" + minuteBucket;
        List<String> keys = List.of(
                properties.namespace() + ":global" + suffix,
                properties.namespace() + ":ip:"
                        + pseudonymize("ip\0" + normalizeAddress(remoteAddress)) + suffix);
        Object raw = redis.execute(
                BEGIN_BOUNDED_ATTEMPT,
                keys,
                Integer.toString(COUNTER_TTL_SECONDS),
                Integer.toString(properties.globalRequestsPerMinute()));
        if (!(raw instanceof List<?> values)
                || values.size() != 2
                || values.stream().anyMatch(value -> !(value instanceof Long number) || number < 0)) {
            throw new IllegalStateException("Redis returned invalid legacy Session exchange counters");
        }
        long globalCount = (Long) values.get(0);
        long ipCount = (Long) values.get(1);
        if (globalCount < 1) {
            throw new IllegalStateException("Redis returned invalid legacy Session exchange counters");
        }
        boolean allowed = globalCount <= properties.globalRequestsPerMinute()
                && ipCount >= 1
                && ipCount <= properties.requestsPerMinute();
        int remaining = allowed
                ? (int) Math.max(0, Math.min(
                        properties.globalRequestsPerMinute() - globalCount,
                        properties.requestsPerMinute() - ipCount))
                : 0;
        return new AttemptDecision(
                allowed,
                properties.requestsPerMinute(),
                remaining,
                60 - Math.floorMod(epochSecond, 60));
    }

    @Override
    public CredentialDecision acquireCredential(
            String signedCookie,
            long identityId,
            int sessionVersion,
            Instant credentialExpiresAt
    ) {
        if (identityId <= 0
                || sessionVersion < 0
                || credentialExpiresAt == null
                || !credentialExpiresAt.isAfter(clock.instant())
                || credentialExpiresAt.isAfter(clock.instant().plus(Duration.ofDays(7)))) {
            throw new IllegalArgumentException("Invalid authoritative identity for legacy exchange");
        }
        String credentialKey = properties.namespace() + ":credential:"
                + credentialDigest(signedCookie);
        String identityKey = identityQuotaKey(identityId, sessionVersion);
        String globalKey = properties.namespace() + ":credentials";
        String digest = credentialDigest(signedCookie);
        String reservationToken = reservationToken();
        Object raw = redis.execute(
                ACQUIRE_CREDENTIAL_ONCE,
                List.of(credentialKey, identityKey, globalKey),
                Long.toString(properties.replayMarkerTtl().toSeconds()),
                Integer.toString(properties.maxExchangesPerIdentity()),
                Integer.toString(properties.maxReplayMarkers()),
                reservationToken,
                digest,
                Long.toString(credentialExpiresAt.getEpochSecond()));
        if (!(raw instanceof List<?> values)
                || values.size() != 2
                || values.stream().anyMatch(value -> !(value instanceof Long number) || number < 0)) {
            throw new IllegalStateException("Redis returned an invalid legacy Session replay marker");
        }
        long status = (Long) values.get(0);
        long retryAfter = (Long) values.get(1);
        return switch (Math.toIntExact(status)) {
            case 0 -> new CredentialDecision(CredentialStatus.ACQUIRED, reservationToken, 0);
            case 1 -> rejected(CredentialStatus.REPLAY, retryAfter);
            case 2 -> rejected(CredentialStatus.IDENTITY_LIMITED, retryAfter);
            case 3 -> rejected(CredentialStatus.GLOBAL_LIMITED, retryAfter);
            case 4 -> rejected(CredentialStatus.EXPIRED, retryAfter);
            default -> throw new IllegalStateException(
                    "Redis returned an invalid legacy Session replay marker");
        };
    }

    @Override
    public void releaseCredential(
            String signedCookie,
            long identityId,
            int sessionVersion,
            String reservationToken
    ) {
        if (identityId <= 0
                || sessionVersion < 0
                || reservationToken == null
                || !reservationToken.matches("[A-Za-z0-9_-]{43}")) {
            throw new IllegalArgumentException("Invalid authoritative identity for legacy exchange");
        }
        String digest = credentialDigest(signedCookie);
        Long released = redis.execute(
                RELEASE_CREDENTIAL,
                List.of(
                        properties.namespace() + ":credential:" + digest,
                        identityQuotaKey(identityId, sessionVersion),
                        properties.namespace() + ":credentials"),
                digest,
                reservationToken);
        if (released == null || (released != 0L && released != 1L)) {
            throw new IllegalStateException("Redis returned invalid legacy Session release state");
        }
    }

    private CredentialDecision rejected(CredentialStatus status, long retryAfterSeconds) {
        long bounded = Math.max(
                1,
                Math.min(properties.replayMarkerTtl().toSeconds(), retryAfterSeconds));
        return new CredentialDecision(status, null, bounded);
    }

    private String reservationToken() {
        byte[] entropy = new byte[32];
        reservations.nextBytes(entropy);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
        java.util.Arrays.fill(entropy, (byte) 0);
        return token;
    }

    private String credentialDigest(String signedCookie) {
        return pseudonymize("credential\0" + boundedCredential(signedCookie));
    }

    private String identityQuotaKey(long identityId, int sessionVersion) {
        return properties.namespace() + ":identity:"
                + pseudonymize("identity\0" + identityId + "\0session-version\0" + sessionVersion);
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

    private static String normalizeAddress(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        return normalized.length() <= 128
                ? normalized
                : normalized.substring(0, 128);
    }

    private static String boundedCredential(String value) {
        if (value == null || value.isEmpty()) {
            return "unknown";
        }
        return value.length() <= 4_096 ? value : value.substring(0, 4_096);
    }
}
