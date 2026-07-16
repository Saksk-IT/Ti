package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.support.Phase2ContainerImages;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
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
class RedisPublicBankReadRateLimiterIT {

    private static final String REDIS_PASSWORD = "public-bank-rate-limit-it-redis";
    private static final String KEY_SECRET = "public-bank-rate-limit-it-key-secret-0001";
    private static final String NAMESPACE = "it:catalog:public-bank-read-rate";
    private static final Instant NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final String IDENTITY_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:identity:v1\0";
    private static final String ADDRESS_DOMAIN =
            "ti-java:catalog:public-bank-read-rate:ip:v1\0";

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
    void realLuaUsesFirstHitTtlAndStopsBeforeEveryLongerWindowOnBreach() {
        RedisPublicBankReadRateLimiter limiter = limiter(NAMESPACE + ":sequential", 2, 3, 4);
        String actor = hmac(ADDRESS_DOMAIN, "198.51.100.41");
        String prefix = NAMESPACE + ":sequential:boards:ip:v1:" + actor;

        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41"))
                .isEqualTo(decision(true, 2, 1, 2, "2 per 1 second"));
        PublicBankReadRateLimiter.Decision second = limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41");
        assertThat(second.allowed()).isTrue();
        assertThat(second.limit()).isEqualTo(2);
        assertThat(second.remaining()).isZero();
        PublicBankReadRateLimiter.Decision secondRejected = limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41");
        assertThat(secondRejected.allowed()).isFalse();
        assertThat(secondRejected.limit()).isEqualTo(2);
        assertThat(secondRejected.remaining()).isZero();
        assertThat(secondRejected.legacyLimitDescription()).isEqualTo("2 per 1 second");

        assertCounter(prefix + ":second", 3);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 2);
        assertTtl(prefix + ":second", 1_000);
        assertTtl(prefix + ":hour", 3_600_000);
        assertTtl(prefix + ":day", 86_400_000);

        redis.delete(prefix + ":second");
        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41").allowed())
                .isTrue();
        PublicBankReadRateLimiter.Decision hourRejected = limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41");
        assertThat(hourRejected.allowed()).isFalse();
        assertThat(hourRejected.limit()).isEqualTo(3);
        assertThat(hourRejected.legacyLimitDescription()).isEqualTo("3 per 1 hour");
        assertCounter(prefix + ":hour", 4);
        assertCounter(prefix + ":day", 3);

        redis.delete(List.of(prefix + ":second", prefix + ":hour"));
        assertThat(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41").allowed())
                .isTrue();
        PublicBankReadRateLimiter.Decision dayRejected = limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, "198.51.100.41");
        assertThat(dayRejected.allowed()).isFalse();
        assertThat(dayRejected.limit()).isEqualTo(4);
        assertThat(dayRejected.legacyLimitDescription()).isEqualTo("4 per 1 day");
        assertCounter(prefix + ":second", 2);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 5);
    }

    @Test
    @Timeout(value = 20, unit = TimeUnit.SECONDS)
    void realLuaRemainsAtomicUnderConcurrentFirstWindowContention() throws Exception {
        String namespace = NAMESPACE + ":concurrent";
        RedisPublicBankReadRateLimiter limiter = limiter(namespace, 10, 500, 5_000);
        int requests = 32;
        CountDownLatch ready = new CountDownLatch(requests);
        CountDownLatch start = new CountDownLatch(1);
        try (var executor = Executors.newFixedThreadPool(requests)) {
            List<Future<PublicBankReadRateLimiter.Decision>> futures = new ArrayList<>();
            for (int index = 0; index < requests; index++) {
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    assertThat(start.await(5, TimeUnit.SECONDS)).isTrue();
                    return limiter.acquireForIdentity(
                            PublicBankReadRequestResolver.Route.SUMMARY, 4101);
                }));
            }
            assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            List<PublicBankReadRateLimiter.Decision> decisions = new ArrayList<>();
            for (Future<PublicBankReadRateLimiter.Decision> future : futures) {
                decisions.add(future.get(5, TimeUnit.SECONDS));
            }
            assertThat(decisions).filteredOn(PublicBankReadRateLimiter.Decision::allowed)
                    .hasSize(10);
            assertThat(decisions).filteredOn(decision -> !decision.allowed())
                    .hasSize(requests - 10)
                    .allMatch(decision -> decision.limit() == 10);
        }

        String actor = hmac(IDENTITY_DOMAIN, "4101");
        String prefix = namespace + ":summary:identity:v1:" + actor;
        assertCounter(prefix + ":second", requests);
        assertCounter(prefix + ":hour", 10);
        assertCounter(prefix + ":day", 10);
        assertThat(redis.keys(namespace + ":*")).hasSize(3)
                .allMatch(key -> !key.contains("4101") && !key.contains("198.51.100"));
    }

    private static RedisPublicBankReadRateLimiter limiter(
            String namespace,
            int second,
            int hour,
            int day
    ) {
        return new RedisPublicBankReadRateLimiter(
                redis,
                new PublicBankReadRateLimitProperties(namespace, second, hour, day, 1),
                new LoginRateLimitProperties(
                        "it:identity:login-rate", 5, KEY_SECRET),
                Clock.fixed(NOW, ZoneOffset.UTC));
    }

    private static PublicBankReadRateLimiter.Decision decision(
            boolean allowed,
            int limit,
            int remaining,
            long retryAfter,
            String description
    ) {
        return new PublicBankReadRateLimiter.Decision(
                allowed,
                limit,
                remaining,
                retryAfter,
                NOW.getEpochSecond() + retryAfter,
                description);
    }

    private static void assertCounter(String key, long expected) {
        assertThat(redis.opsForValue().get(key)).isEqualTo(Long.toString(expected));
    }

    private static void assertTtl(String key, long maximumMillis) {
        assertThat(redis.getExpire(key, TimeUnit.MILLISECONDS)).isBetween(1L, maximumMillis);
    }

    private static String hmac(String domain, String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (domain + value).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }
}
