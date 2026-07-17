package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.redis.testcontainers.RedisContainer;
import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import java.io.IOException;
import java.net.ConnectException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import tools.jackson.databind.json.JsonMapper;

@Testcontainers
class RedisPersonalBankUserCountsReadRateLimiterIT {

    private static final String REDIS_PASSWORD = "user-counts-rate-limit-it-redis";
    private static final String KEY_SECRET = "user-counts-rate-limit-it-key-secret-0001";
    private static final String NAMESPACE = "it:learning:user-counts-read-rate";
    private static final Instant NOW = Instant.parse("2026-07-17T04:00:00Z");
    private static final String DOMAIN_PREFIX =
            "ti-java:learning:personal-bank-user-counts-read-rate:";

    @Container
    static final RedisContainer REDIS = redisContainer();

    private static LettuceConnectionFactory connections;
    private static StringRedisTemplate redis;

    @BeforeAll
    static void connect() {
        connections = connectionFactory();
        redis = template(connections);
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
        RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(
                redis, NAMESPACE + ":sequential", 2, 3, 4);
        String actor = hmac("api", "ip:v1", "198.51.100.41");
        String prefix = NAMESPACE + ":sequential:api:ip:v1:" + actor;

        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41"))
                .isEqualTo(decision(true, Window.SECOND, 2, 1, 2));
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41"))
                .extracting(Decision::allowed, Decision::remaining)
                .containsExactly(true, 0);
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41"))
                .extracting(Decision::allowed, Decision::window, Decision::limit)
                .containsExactly(false, Window.SECOND, 2);

        assertCounter(prefix + ":second", 3);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 2);
        assertTtl(prefix + ":second", 1_000);
        assertTtl(prefix + ":hour", 3_600_000);
        assertTtl(prefix + ":day", 86_400_000);

        redis.delete(prefix + ":second");
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41").allowed()).isTrue();
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41"))
                .extracting(Decision::allowed, Decision::window, Decision::limit)
                .containsExactly(false, Window.HOUR, 3);
        assertCounter(prefix + ":hour", 4);
        assertCounter(prefix + ":day", 3);

        redis.delete(List.of(prefix + ":second", prefix + ":hour"));
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41").allowed()).isTrue();
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.41"))
                .extracting(Decision::allowed, Decision::window, Decision::limit)
                .containsExactly(false, Window.DAY, 4);
        assertCounter(prefix + ":second", 2);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 5);
    }

    @Test
    void realSecondWindowExpiresNaturallyAndStartsAnewFixedWindow() throws Exception {
        String namespace = NAMESPACE + ":natural-expiry";
        RedisPersonalBankUserCountsReadRateLimiter limiter =
                limiter(redis, namespace, 1, 500, 5_000);
        String actor = hmac("api", "ip:v1", "198.51.100.42");
        String secondKey = namespace + ":api:ip:v1:" + actor + ":second";

        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.42").allowed())
                .isTrue();
        assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.42").allowed())
                .isFalse();
        awaitKeyExpiry(secondKey);

        Decision restarted = limiter.acquireForAddress(Alias.API, "198.51.100.42");
        assertThat(restarted.allowed()).isTrue();
        assertThat(restarted.remaining()).isZero();
        assertCounter(secondKey, 1);
    }

    @Test
    @Timeout(value = 20, unit = TimeUnit.SECONDS)
    void independentClientsConvergeAtomicallyAndAliasesRemainIsolated() throws Exception {
        String namespace = NAMESPACE + ":multi-instance";
        RedisPersonalBankUserCountsReadRateLimiter first =
                limiter(redis, namespace, 10, 500, 5_000);
        LettuceConnectionFactory secondConnections = connectionFactory();
        try {
            RedisPersonalBankUserCountsReadRateLimiter second =
                    limiter(template(secondConnections), namespace, 10, 500, 5_000);
            int requests = 32;
            CountDownLatch ready = new CountDownLatch(requests);
            CountDownLatch start = new CountDownLatch(1);
            try (var executor = Executors.newFixedThreadPool(requests)) {
                List<Future<Decision>> futures = new ArrayList<>();
                for (int index = 0; index < requests; index++) {
                    RedisPersonalBankUserCountsReadRateLimiter selected =
                            index % 2 == 0 ? first : second;
                    futures.add(executor.submit(() -> {
                        ready.countDown();
                        assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
                        return selected.acquireForIdentity(Alias.API, 4101);
                    }));
                }
                assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
                start.countDown();
                List<Decision> decisions = new ArrayList<>();
                for (Future<Decision> future : futures) {
                    decisions.add(future.get(10, TimeUnit.SECONDS));
                }
                assertThat(decisions).filteredOn(Decision::allowed).hasSize(10);
                assertThat(decisions).filteredOn(decision -> !decision.allowed())
                        .hasSize(requests - 10)
                        .allMatch(decision -> decision.window() == Window.SECOND);
            }

            String apiActor = hmac("api", "identity:v1", "4101");
            String apiPrefix = namespace + ":api:identity:v1:" + apiActor;
            assertCounter(apiPrefix + ":second", requests);
            assertCounter(apiPrefix + ":hour", 10);
            assertCounter(apiPrefix + ":day", 10);

            Decision web = second.acquireForIdentity(Alias.WEB, 4101);
            assertThat(web.allowed()).isTrue();
            assertThat(web.remaining()).isEqualTo(9);
            String webActor = hmac("web", "identity:v1", "4101");
            assertThat(webActor).isNotEqualTo(apiActor);
            assertCounter(namespace + ":web:identity:v1:" + webActor + ":second", 1);
            assertThat(redis.keys(namespace + ":*"))
                    .containsExactlyInAnyOrder(
                            apiPrefix + ":second",
                            apiPrefix + ":hour",
                            apiPrefix + ":day",
                            namespace + ":web:identity:v1:" + webActor + ":second",
                            namespace + ":web:identity:v1:" + webActor + ":hour",
                            namespace + ":web:identity:v1:" + webActor + ":day");
        } finally {
            secondConnections.destroy();
        }
    }

    @Test
    @Timeout(value = 10, unit = TimeUnit.SECONDS)
    void realConnectionRefusalFailsClosedAtHttpBoundaryWithoutLeakingInfrastructure()
            throws Exception {
        int refusedPort = closedLoopbackPort();
        LettuceConnectionFactory refusedConnections = connectionFactory(
                "127.0.0.1",
                refusedPort,
                Duration.ofMillis(250));
        try {
            RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(
                    template(refusedConnections),
                    NAMESPACE + ":connection-refused",
                    2,
                    500,
                    5_000);

            assertThatThrownBy(() -> limiter.acquireForAddress(
                    Alias.API,
                    "198.51.100.45"))
                    .isInstanceOf(RedisConnectionFailureException.class)
                    .hasRootCauseInstanceOf(ConnectException.class);

            PersonalBankUserCountsReadRequestResolver routes =
                    new PersonalBankUserCountsReadRequestResolver();
            LegacyPersonalBankUserCountsSecurityErrorWriter errors =
                    new LegacyPersonalBankUserCountsSecurityErrorWriter(
                            JsonMapper.builder().build());
            PersonalBankUserCountsReadRateLimitFilter filter =
                    new PersonalBankUserCountsReadRateLimitFilter(
                            limiter,
                            errors,
                            routes,
                            request -> "198.51.100.46");
            MockHttpServletRequest request = new MockHttpServletRequest(
                    "GET", "/api/user/banks/api/41/user-counts");
            request.setAttribute(
                    io.saksk.ti.web.request.RequestId.ATTRIBUTE_NAME,
                    "phase4c-redis-connection-refused");
            MockHttpServletResponse response = new MockHttpServletResponse();
            AtomicBoolean downstreamReached = new AtomicBoolean();
            SecurityContextHolder.clearContext();

            filter.doFilter(
                    request,
                    response,
                    (ignoredRequest, ignoredResponse) -> downstreamReached.set(true));

            String body = response.getContentAsString(StandardCharsets.UTF_8);
            assertThat(response.getStatus()).isEqualTo(503);
            assertThat(body)
                    .isEqualTo("{\"status\":\"error\",\"message\":\"服务暂时不可用\","
                            + "\"status_code\":503,"
                            + "\"request_id\":\"phase4c-redis-connection-refused\"}")
                    .doesNotContain(
                            "127.0.0.1",
                            Integer.toString(refusedPort),
                            "Connection refused",
                            "RedisConnectionFailureException",
                            "Lettuce");
            assertThat(request.getAttribute(
                    PersonalBankUserCountsReadRateLimitFilter.BOUNDARY_ENTERED_ATTRIBUTE))
                    .isEqualTo(Boolean.TRUE);
            assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
            assertThat(response.getHeader("X-RateLimit-Remaining")).isNull();
            assertThat(response.getHeader("X-RateLimit-Reset")).isNull();
            assertThat(response.getHeader("Retry-After")).isNull();
            assertThat(downstreamReached).isFalse();
        } finally {
            refusedConnections.destroy();
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    @Timeout(value = 30, unit = TimeUnit.SECONDS)
    void realRedisInterruptionFailsClosedAtHttpBoundaryAndRecoversAfterUnpause()
            throws Exception {
        try (RedisContainer outage = redisContainer()) {
            outage.start();
            String namespace = NAMESPACE + ":outage";
            LettuceConnectionFactory outageConnections = connectionFactory(
                    outage,
                    Duration.ofSeconds(1));
            try {
                StringRedisTemplate outageRedis = template(outageConnections);
                RedisPersonalBankUserCountsReadRateLimiter limiter = limiter(
                        outageRedis, namespace, 2, 500, 5_000);
                assertThat(limiter.acquireForAddress(Alias.API, "198.51.100.43").allowed())
                        .isTrue();

                String containerId = outage.getContainerId();
                outage.getDockerClient().pauseContainerCmd(containerId).exec();
                try {
                    PersonalBankUserCountsReadRequestResolver routes =
                            new PersonalBankUserCountsReadRequestResolver();
                    LegacyPersonalBankUserCountsSecurityErrorWriter errors =
                            new LegacyPersonalBankUserCountsSecurityErrorWriter(
                                    JsonMapper.builder().build());
                    PersonalBankUserCountsReadRateLimitFilter filter =
                            new PersonalBankUserCountsReadRateLimitFilter(
                                    limiter,
                                    errors,
                                    routes,
                                    request -> "198.51.100.44");
                    MockHttpServletRequest request = new MockHttpServletRequest(
                            "GET", "/api/user/banks/api/41/user-counts");
                    request.setAttribute(
                            io.saksk.ti.web.request.RequestId.ATTRIBUTE_NAME,
                            "phase4c-redis-outage");
                    MockHttpServletResponse response = new MockHttpServletResponse();
                    AtomicBoolean downstreamReached = new AtomicBoolean();
                    SecurityContextHolder.clearContext();

                    filter.doFilter(
                            request,
                            response,
                            (ignoredRequest, ignoredResponse) -> downstreamReached.set(true));

                    assertThat(response.getStatus()).isEqualTo(503);
                    assertThat(response.getContentAsString(
                            StandardCharsets.UTF_8))
                            .isEqualTo(
                                    "{\"status\":\"error\",\"message\":\"服务暂时不可用\","
                                            + "\"status_code\":503,"
                                            + "\"request_id\":\"phase4c-redis-outage\"}");
                    assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
                    assertThat(response.getHeader("X-RateLimit-Remaining")).isNull();
                    assertThat(response.getHeader("X-RateLimit-Reset")).isNull();
                    assertThat(response.getHeader("Retry-After")).isNull();
                    assertThat(downstreamReached).isFalse();
                } finally {
                    outage.getDockerClient().unpauseContainerCmd(containerId).exec();
                }
                awaitRedis(outageConnections);

                Decision recovered = limiter.acquireForAddress(
                        Alias.API,
                        "198.51.100.43");
                assertThat(recovered.allowed()).isTrue();
                assertThat(recovered.remaining()).isBetween(0, 1);
                String actor = hmac("api", "ip:v1", "198.51.100.43");
                String prefix = namespace + ":api:ip:v1:" + actor;
                assertThat(outageRedis.opsForValue().get(prefix + ":hour"))
                        .isEqualTo("2");
                assertThat(outageRedis.opsForValue().get(prefix + ":day"))
                        .isEqualTo("2");
            } finally {
                if (outageConnections.isRunning()) {
                    outageConnections.destroy();
                }
                SecurityContextHolder.clearContext();
            }
        }
    }

    private static RedisPersonalBankUserCountsReadRateLimiter limiter(
            StringRedisTemplate template,
            String namespace,
            int second,
            int hour,
            int day
    ) {
        return new RedisPersonalBankUserCountsReadRateLimiter(
                template,
                new PersonalBankUserCountsReadRateLimitProperties(
                        namespace, second, hour, day, 1, KEY_SECRET),
                Clock.fixed(NOW, ZoneOffset.UTC));
    }

    private static Decision decision(
            boolean allowed,
            Window window,
            int limit,
            int remaining,
            long retryAfter
    ) {
        return new Decision(
                allowed,
                window,
                limit,
                remaining,
                retryAfter,
                NOW.getEpochSecond() + retryAfter);
    }

    private static LettuceConnectionFactory connectionFactory() {
        return connectionFactory(REDIS, Duration.ofSeconds(60));
    }

    private static LettuceConnectionFactory connectionFactory(
            RedisContainer container,
            Duration commandTimeout
    ) {
        return connectionFactory(
                container.getRedisHost(),
                container.getRedisPort(),
                commandTimeout);
    }

    private static LettuceConnectionFactory connectionFactory(
            String host,
            int port,
            Duration commandTimeout
    ) {
        RedisStandaloneConfiguration configuration = new RedisStandaloneConfiguration(
                host, port);
        configuration.setPassword(REDIS_PASSWORD);
        LettuceClientConfiguration client = LettuceClientConfiguration.builder()
                .clientOptions(ClientOptions.builder()
                        .socketOptions(SocketOptions.builder()
                                .connectTimeout(commandTimeout)
                                .build())
                        .build())
                .commandTimeout(commandTimeout)
                .build();
        LettuceConnectionFactory factory = new LettuceConnectionFactory(configuration, client);
        factory.afterPropertiesSet();
        factory.start();
        return factory;
    }

    private static StringRedisTemplate template(LettuceConnectionFactory factory) {
        StringRedisTemplate template = new StringRedisTemplate(factory);
        template.afterPropertiesSet();
        return template;
    }

    private static int closedLoopbackPort() throws IOException {
        try (ServerSocket listener = new ServerSocket(
                0,
                1,
                InetAddress.getByName("127.0.0.1"))) {
            return listener.getLocalPort();
        }
    }

    private static void assertCounter(String key, long expected) {
        assertThat(redis.opsForValue().get(key)).isEqualTo(Long.toString(expected));
    }

    private static void assertTtl(String key, long maximumMillis) {
        assertThat(redis.getExpire(key, TimeUnit.MILLISECONDS)).isBetween(1L, maximumMillis);
    }

    private static RedisContainer redisContainer() {
        return new RedisContainer(Phase2ContainerImages.redis7())
                .withCommand(
                        "redis-server",
                        "--requirepass", REDIS_PASSWORD,
                        "--maxmemory", "64mb",
                        "--maxmemory-policy", "noeviction");
    }

    private static void awaitKeyExpiry(String key) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            if (Boolean.FALSE.equals(redis.hasKey(key))) {
                return;
            }
            Thread.sleep(25);
        }
        assertThat(redis.hasKey(key)).as("Redis key must expire naturally").isFalse();
    }

    private static void awaitRedis(LettuceConnectionFactory connections) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        RuntimeException lastFailure = null;
        while (System.nanoTime() < deadline) {
            try (RedisConnection connection = connections.getConnection()) {
                if ("PONG".equals(connection.ping())) {
                    return;
                }
            } catch (RuntimeException failure) {
                lastFailure = failure;
            }
            Thread.sleep(100);
        }
        throw new IllegalStateException(
                "The original Lettuce client did not recover within 10 seconds",
                lastFailure);
    }

    private static String hmac(String alias, String actorType, String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (DOMAIN_PREFIX + alias + ":" + actorType + "\0" + value)
                            .getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }
}
