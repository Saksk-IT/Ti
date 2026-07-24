package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.redis.testcontainers.RedisContainer;
import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.web.compat.LegacyTransactionWriteSecurityErrorWriter;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TransactionWriteRateLimiter.Decision;
import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
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
class RedisTransactionWriteRateLimiterIT {

    private static final String REDIS_PASSWORD = "transaction-write-rate-it-redis";
    private static final String KEY_SECRET =
            "transaction-write-rate-it-key-secret-0001";
    private static final String NAMESPACE = "it:web:transaction-write-rate";
    private static final String DOMAIN = "ti-java:web:transaction-write-rate:v1:";
    private static final Instant NOW = Instant.parse("2026-07-24T04:00:00Z");

    @Container
    static final RedisContainer REDIS = redisContainer();

    private static LettuceConnectionFactory connections;
    private static StringRedisTemplate redis;

    @BeforeAll
    static void connect() {
        connections = connectionFactory(REDIS, Duration.ofSeconds(2));
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
    void realLuaKeepsAllNineRoutesAndActorKindsIndependentWithBoundedTtl() {
        String namespace = NAMESPACE + ":routes";
        RedisTransactionWriteRateLimiter limiter = limiter(redis, namespace);

        for (Route route : Route.values()) {
            Decision first = limiter.acquireForIdentity(route, 91_001);
            assertThat(first.allowed()).isTrue();
            assertThat(first.limit()).isEqualTo(route.requestsPerMinute());
            assertThat(first.remaining()).isEqualTo(route.requestsPerMinute() - 1);

            String key = key(namespace, route, "identity", "91001");
            assertThat(redis.opsForValue().get(key)).isEqualTo("1");
            assertBoundedTtl(key);
        }

        String favoriteIdentityKey =
                key(namespace, Route.FAVORITE_API, "identity", "91001");
        long firstTtl = redis.getExpire(favoriteIdentityKey, TimeUnit.MILLISECONDS);
        Decision second = limiter.acquireForIdentity(Route.FAVORITE_API, 91_001);
        long secondTtl = redis.getExpire(favoriteIdentityKey, TimeUnit.MILLISECONDS);
        assertThat(second.remaining()).isEqualTo(Route.FAVORITE_API.requestsPerMinute() - 2);
        assertThat(secondTtl).isBetween(1L, firstTtl);

        Decision address = limiter.acquireForAddress(
                Route.FAVORITE_API,
                "198.51.100.88");
        assertThat(address.allowed()).isTrue();
        assertThat(address.remaining()).isEqualTo(
                Route.FAVORITE_API.requestsPerMinute() - 1);
        assertThat(redis.opsForValue().get(
                key(namespace, Route.FAVORITE_API, "ip", "198.51.100.88")))
                .isEqualTo("1");

        assertThat(redis.keys(namespace + ":*")).hasSize(Route.values().length + 1);
        assertThat(redis.keys(namespace + ":*").toString())
                .doesNotContain("91001", "198.51.100.88", KEY_SECRET);
    }

    @Test
    @Timeout(value = 20, unit = TimeUnit.SECONDS)
    void twoIndependentClientsConvergeAtomicallyOnTheExactCheckinBudget()
            throws Exception {
        String namespace = NAMESPACE + ":multi-instance";
        RedisTransactionWriteRateLimiter first = limiter(redis, namespace);
        LettuceConnectionFactory secondConnections =
                connectionFactory(REDIS, Duration.ofSeconds(2));
        try {
            RedisTransactionWriteRateLimiter second =
                    limiter(template(secondConnections), namespace);
            int requests = 32;
            CountDownLatch ready = new CountDownLatch(requests);
            CountDownLatch start = new CountDownLatch(1);
            List<Future<Decision>> futures = new ArrayList<>();
            try (var executor = Executors.newFixedThreadPool(requests)) {
                for (int index = 0; index < requests; index++) {
                    RedisTransactionWriteRateLimiter selected =
                            index % 2 == 0 ? first : second;
                    futures.add(executor.submit(() -> {
                        ready.countDown();
                        assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
                        return selected.acquireForIdentity(Route.CHECKIN, 91_002);
                    }));
                }
                assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
                start.countDown();

                List<Decision> decisions = new ArrayList<>();
                for (Future<Decision> future : futures) {
                    decisions.add(future.get(10, TimeUnit.SECONDS));
                }
                assertThat(decisions).filteredOn(Decision::allowed).hasSize(10);
                assertThat(decisions)
                        .filteredOn(decision -> !decision.allowed())
                        .hasSize(requests - 10)
                        .allMatch(decision -> decision.limit() == 10
                                && decision.remaining() == 0);
            }

            String key = key(namespace, Route.CHECKIN, "identity", "91002");
            assertThat(redis.opsForValue().get(key)).isEqualTo("32");
            assertBoundedTtl(key);
        } finally {
            secondConnections.destroy();
        }
    }

    @Test
    @Timeout(value = 10, unit = TimeUnit.SECONDS)
    void realConnectionRefusalFailsClosedAtTheHttpBoundaryWithoutInfrastructureLeak()
            throws Exception {
        int refusedPort = closedLoopbackPort();
        LettuceConnectionFactory refusedConnections = connectionFactory(
                "127.0.0.1",
                refusedPort,
                Duration.ofMillis(250));
        try {
            RedisTransactionWriteRateLimiter limiter =
                    limiter(template(refusedConnections), NAMESPACE + ":refused");
            assertThatThrownBy(() -> limiter.acquireForAddress(
                    Route.CHECKIN,
                    "198.51.100.89"))
                    .isInstanceOf(RedisConnectionFailureException.class)
                    .hasRootCauseInstanceOf(ConnectException.class);

            TransactionWriteRateLimitFilter filter = filter(
                    limiter,
                    "198.51.100.89");
            MockHttpServletRequest request =
                    new MockHttpServletRequest("POST", "/api/user/checkin");
            request.setAttribute(RequestId.ATTRIBUTE_NAME, "transaction-write-refused");
            MockHttpServletResponse response = new MockHttpServletResponse();
            AtomicBoolean downstreamReached = new AtomicBoolean();
            SecurityContextHolder.clearContext();

            filter.doFilter(
                    request,
                    response,
                    (ignoredRequest, ignoredResponse) -> downstreamReached.set(true));

            assertUnavailable(response, "transaction-write-refused");
            assertThat(response.getContentAsString(StandardCharsets.UTF_8))
                    .doesNotContain(
                            "127.0.0.1",
                            Integer.toString(refusedPort),
                            "Connection refused",
                            "RedisConnectionFailureException",
                            "Lettuce");
            assertThat(downstreamReached).isFalse();
        } finally {
            refusedConnections.destroy();
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    @Timeout(value = 30, unit = TimeUnit.SECONDS)
    void theSameLimiterFailsClosedDuringARealInterruptionAndRecoversAfterUnpause()
            throws Exception {
        try (RedisContainer outage = redisContainer()) {
            outage.start();
            String namespace = NAMESPACE + ":outage";
            LettuceConnectionFactory outageConnections =
                    connectionFactory(outage, Duration.ofSeconds(1));
            try {
                StringRedisTemplate outageRedis = template(outageConnections);
                RedisTransactionWriteRateLimiter limiter =
                        limiter(outageRedis, namespace);
                assertThat(limiter.acquireForAddress(
                        Route.STUDY_REVIEW,
                        "198.51.100.90").allowed()).isTrue();

                String containerId = outage.getContainerId();
                outage.getDockerClient().pauseContainerCmd(containerId).exec();
                try {
                    TransactionWriteRateLimitFilter filter =
                            filter(limiter, "198.51.100.91");
                    MockHttpServletRequest request = new MockHttpServletRequest(
                            "POST",
                            "/api/quiz/study/review/record");
                    request.setAttribute(
                            RequestId.ATTRIBUTE_NAME,
                            "transaction-write-outage");
                    MockHttpServletResponse response = new MockHttpServletResponse();
                    AtomicBoolean downstreamReached = new AtomicBoolean();
                    SecurityContextHolder.clearContext();

                    filter.doFilter(
                            request,
                            response,
                            (ignoredRequest, ignoredResponse) ->
                                    downstreamReached.set(true));

                    assertUnavailable(response, "transaction-write-outage");
                    assertThat(downstreamReached).isFalse();
                } finally {
                    outage.getDockerClient().unpauseContainerCmd(containerId).exec();
                }
                awaitRedis(outageConnections);

                Decision recovered = limiter.acquireForAddress(
                        Route.STUDY_REVIEW,
                        "198.51.100.90");
                assertThat(recovered.allowed()).isTrue();
                assertThat(recovered.remaining()).isEqualTo(58);
                String key = key(
                        namespace,
                        Route.STUDY_REVIEW,
                        "ip",
                        "198.51.100.90");
                assertThat(outageRedis.opsForValue().get(key)).isEqualTo("2");
                assertBoundedTtl(outageRedis, key);
            } finally {
                if (outageConnections.isRunning()) {
                    outageConnections.destroy();
                }
                SecurityContextHolder.clearContext();
            }
        }
    }

    private static TransactionWriteRateLimitFilter filter(
            TransactionWriteRateLimiter limiter,
            String address
    ) {
        return new TransactionWriteRateLimitFilter(
                limiter,
                new TransactionWriteRequestResolver(),
                request -> address,
                new LegacyTransactionWriteSecurityErrorWriter(
                        JsonMapper.builder().build()));
    }

    private static void assertUnavailable(
            MockHttpServletResponse response,
            String requestId
    ) throws Exception {
        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentAsString(StandardCharsets.UTF_8))
                .isEqualTo(
                        "{\"status\":\"error\",\"message\":\"服务暂时不可用\","
                                + "\"status_code\":503,\"request_id\":\""
                                + requestId
                                + "\",\"payload\":null}");
        assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
        assertThat(response.getHeader("X-RateLimit-Remaining")).isNull();
        assertThat(response.getHeader("X-RateLimit-Reset")).isNull();
        assertThat(response.getHeader("Retry-After")).isNull();
    }

    private static RedisTransactionWriteRateLimiter limiter(
            StringRedisTemplate template,
            String namespace
    ) {
        return new RedisTransactionWriteRateLimiter(
                template,
                new TransactionWriteRateLimitProperties(
                        namespace,
                        1,
                        KEY_SECRET),
                Clock.fixed(NOW, ZoneOffset.UTC));
    }

    private static String key(
            String namespace,
            Route route,
            String actorType,
            String actor
    ) {
        return namespace
                + ":"
                + route.operationId()
                + ":"
                + actorType
                + ":v1:"
                + hmac(route, actorType, actor);
    }

    private static String hmac(Route route, String actorType, String actor) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (DOMAIN + route.operationId() + ":" + actorType + "\0" + actor)
                            .getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }

    private static void assertBoundedTtl(String key) {
        assertBoundedTtl(redis, key);
    }

    private static void assertBoundedTtl(StringRedisTemplate template, String key) {
        assertThat(template.getExpire(key, TimeUnit.MILLISECONDS))
                .isBetween(1L, 60_000L);
    }

    private static RedisContainer redisContainer() {
        return new RedisContainer(Phase2ContainerImages.redis7())
                .withCommand(
                        "redis-server",
                        "--requirepass", REDIS_PASSWORD,
                        "--maxmemory", "64mb",
                        "--maxmemory-policy", "noeviction");
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
        RedisStandaloneConfiguration configuration =
                new RedisStandaloneConfiguration(host, port);
        configuration.setPassword(REDIS_PASSWORD);
        LettuceClientConfiguration client = LettuceClientConfiguration.builder()
                .clientOptions(ClientOptions.builder()
                        .socketOptions(SocketOptions.builder()
                                .connectTimeout(commandTimeout)
                                .build())
                        .build())
                .commandTimeout(commandTimeout)
                .build();
        LettuceConnectionFactory factory =
                new LettuceConnectionFactory(configuration, client);
        factory.afterPropertiesSet();
        factory.start();
        return factory;
    }

    private static StringRedisTemplate template(
            LettuceConnectionFactory factory
    ) {
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

    private static void awaitRedis(
            LettuceConnectionFactory connectionFactory
    ) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        RuntimeException lastFailure = null;
        while (System.nanoTime() < deadline) {
            try (RedisConnection connection = connectionFactory.getConnection()) {
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
}
