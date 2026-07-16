package io.saksk.ti.catalog.infrastructure.coordination;

import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

/** Redis advisory lease with token-owned atomic release. */
@Component
final class RedisPublicBankRefreshLeaseAdapter implements PublicBankRefreshLeasePort {

    private static final DefaultRedisScript<Long> RELEASE = new DefaultRedisScript<>("""
            if redis.call('GET', KEYS[1]) ~= ARGV[1] then
              return 0
            end
            return redis.call('DEL', KEYS[1])
            """, Long.class);

    private final StringRedisTemplate redis;
    private final PublicBankSnapshotProperties properties;
    private final SecureRandom tokens;

    @Autowired
    RedisPublicBankRefreshLeaseAdapter(
            StringRedisTemplate redis,
            PublicBankSnapshotProperties properties
    ) {
        this(redis, properties, new SecureRandom());
    }

    RedisPublicBankRefreshLeaseAdapter(
            StringRedisTemplate redis,
            PublicBankSnapshotProperties properties,
            SecureRandom tokens
    ) {
        this.redis = Objects.requireNonNull(redis, "redis");
        this.properties = Objects.requireNonNull(properties, "properties");
        this.tokens = Objects.requireNonNull(tokens, "tokens");
    }

    @Override
    public Optional<Lease> tryAcquire() {
        Lease lease = new Lease(nextToken());
        Boolean acquired = redis.opsForValue().setIfAbsent(
                properties.refreshLockKey(),
                lease.token(),
                properties.refreshLockTtl());
        if (acquired == null) {
            throw new IllegalStateException("Redis returned no public-bank lease result");
        }
        return acquired ? Optional.of(lease) : Optional.empty();
    }

    @Override
    public ReleaseOutcome release(Lease lease) {
        Objects.requireNonNull(lease, "lease");
        Long removed = redis.execute(
                RELEASE,
                List.of(properties.refreshLockKey()),
                lease.token());
        if (removed == null || (removed != 0L && removed != 1L)) {
            throw new IllegalStateException("Redis returned an invalid public-bank lease release");
        }
        return removed == 1L ? ReleaseOutcome.RELEASED : ReleaseOutcome.LOST;
    }

    private String nextToken() {
        byte[] bytes = new byte[32];
        tokens.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
