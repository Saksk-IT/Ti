package io.saksk.ti.catalog.infrastructure.coordination;

import static org.assertj.core.api.Assertions.assertThat;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort.Lease;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort.ReleaseOutcome;
import io.saksk.ti.support.Phase2ContainerImages;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers
class RedisPublicBankRefreshLeaseAdapterIT {

    private static final String REDIS_PASSWORD = "public-bank-refresh-it-redis";
    private static final String NAMESPACE = "it:catalog:public-bank-snapshot";

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "64mb",
                    "--maxmemory-policy", "noeviction");

    private static LettuceConnectionFactory connections;
    private static StringRedisTemplate redis;

    @BeforeAll
    static void connect() {
        RedisStandaloneConfiguration configuration = new RedisStandaloneConfiguration(
                REDIS.getRedisHost(), REDIS.getRedisPort());
        configuration.setPassword(REDIS_PASSWORD);
        connections = new LettuceConnectionFactory(configuration);
        connections.afterPropertiesSet();
        connections.start();
        redis = new StringRedisTemplate(connections);
        redis.afterPropertiesSet();
    }

    @AfterAll
    static void disconnect() {
        if (connections != null) {
            connections.destroy();
        }
    }

    @BeforeEach
    void clearRedis() {
        try (RedisConnection connection = connections.getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @Test
    void setNxPxAndCompareDeletePreserveTokenOwnership() {
        RedisPublicBankRefreshLeaseAdapter adapter = adapter();

        Lease owned = adapter.tryAcquire().orElseThrow();
        assertThat(owned.token()).hasSize(43).matches("[A-Za-z0-9_-]{43}");
        assertThat(adapter.tryAcquire()).isEmpty();
        assertThat(redis.getExpire(lockKey(), TimeUnit.MILLISECONDS))
                .isBetween(1L, Duration.ofSeconds(30).toMillis());

        Lease foreign = new Lease("B".repeat(43));
        assertThat(adapter.release(foreign)).isEqualTo(ReleaseOutcome.LOST);
        assertThat(redis.opsForValue().get(lockKey())).isEqualTo(owned.token());

        assertThat(adapter.release(owned)).isEqualTo(ReleaseOutcome.RELEASED);
        assertThat(redis.hasKey(lockKey())).isFalse();
        assertThat(adapter.release(owned)).isEqualTo(ReleaseOutcome.LOST);
    }

    @Test
    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    void expiredLeaseAllowsNewOwnerWithoutLettingOldOwnerDeleteItsToken()
            throws InterruptedException {
        RedisPublicBankRefreshLeaseAdapter adapter = adapter();
        Lease expiredOwner = adapter.tryAcquire().orElseThrow();

        assertThat(redis.expire(lockKey(), Duration.ofMillis(150))).isTrue();
        assertThat(redis.getExpire(lockKey(), TimeUnit.MILLISECONDS)).isBetween(1L, 250L);

        Optional<Lease> replacement = Optional.empty();
        Instant deadline = Instant.now().plusSeconds(3);
        while (replacement.isEmpty() && Instant.now().isBefore(deadline)) {
            replacement = adapter.tryAcquire();
            if (replacement.isEmpty()) {
                Thread.sleep(10);
            }
        }

        Lease currentOwner = replacement.orElseThrow(
                () -> new AssertionError("Redis lease did not expire within the bounded poll"));
        assertThat(currentOwner.token()).isNotEqualTo(expiredOwner.token());
        assertThat(adapter.release(expiredOwner)).isEqualTo(ReleaseOutcome.LOST);
        assertThat(redis.opsForValue().get(lockKey())).isEqualTo(currentOwner.token());
        assertThat(adapter.release(currentOwner)).isEqualTo(ReleaseOutcome.RELEASED);
        assertThat(redis.hasKey(lockKey())).isFalse();
    }

    @Test
    @Timeout(value = 20, unit = TimeUnit.SECONDS)
    void concurrentAcquisitionHasExactlyOneOwner() throws Exception {
        RedisPublicBankRefreshLeaseAdapter adapter = adapter();
        int contenders = 24;
        CountDownLatch ready = new CountDownLatch(contenders);
        CountDownLatch start = new CountDownLatch(1);
        List<Optional<Lease>> results = new ArrayList<>();

        try (var executor = Executors.newFixedThreadPool(contenders)) {
            List<Future<Optional<Lease>>> futures = new ArrayList<>();
            for (int index = 0; index < contenders; index++) {
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    assertThat(start.await(5, TimeUnit.SECONDS)).isTrue();
                    return adapter.tryAcquire();
                }));
            }
            assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            for (Future<Optional<Lease>> future : futures) {
                results.add(future.get(5, TimeUnit.SECONDS));
            }
        }

        assertThat(results).filteredOn(Optional::isPresent).hasSize(1);
        Lease winner = results.stream().flatMap(Optional::stream).findFirst().orElseThrow();
        assertThat(redis.opsForValue().get(lockKey())).isEqualTo(winner.token());
        assertThat(adapter.release(winner)).isEqualTo(ReleaseOutcome.RELEASED);
    }

    private static RedisPublicBankRefreshLeaseAdapter adapter() {
        return new RedisPublicBankRefreshLeaseAdapter(
                redis,
                new PublicBankSnapshotProperties(false, NAMESPACE, Duration.ofSeconds(30)));
    }

    private static String lockKey() {
        return NAMESPACE + ":refresh-lock";
    }
}
