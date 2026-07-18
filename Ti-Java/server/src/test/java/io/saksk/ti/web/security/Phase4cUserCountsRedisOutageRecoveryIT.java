package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.redis.testcontainers.RedisContainer;
import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.support.Phase4cRedisNetworkGate;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.ConnectException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.data.jpa.autoconfigure.DataJpaRepositoriesAutoConfiguration;
import org.springframework.boot.data.redis.autoconfigure.DataRedisRepositoriesAutoConfiguration;
import org.springframework.boot.hibernate.autoconfigure.HibernateJpaAutoConfiguration;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration;
import org.springframework.boot.session.autoconfigure.SessionAutoConfiguration;
import org.springframework.boot.session.data.redis.autoconfigure.SessionDataRedisAutoConfiguration;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.header.HeaderWriterFilter;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.filter.OncePerRequestFilter;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Proves same-process recovery of the Phase 4C user-counts Redis boundary through real Tomcat,
 * Lettuce, TCP failure, and Redis. No Redis command, limiter decision, or network failure is mocked.
 */
@Testcontainers
class Phase4cUserCountsRedisOutageRecoveryIT {

    private static final String API_PATH = "/api/user/banks/api/41/user-counts";
    private static final String WEB_PATH = "/user/banks/api/41/user-counts";
    private static final String REDIS_PASSWORD = "phase4c-user-counts-recovery-redis";
    private static final String KEY_SECRET = "phase4c-user-counts-recovery-key-secret-0001";
    private static final String NAMESPACE = "it:phase4c:user-counts-recovery";
    private static final String DOMAIN_PREFIX =
            "ti-java:learning:personal-bank-user-counts-read-rate:";
    private static final String FIXTURE_IDENTITY_HEADER = "X-Test-Identity";
    private static final String INSTANCE_HEADER = "X-Test-Service-Instance";
    private static final String CLIENT_ADDRESS = "198.51.100.170";
    private static final List<String> RATE_HEADERS = List.of(
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            HttpHeaders.RETRY_AFTER);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "64mb",
                    "--maxmemory-policy", "noeviction");

    private static LettuceConnectionFactory adminConnections;
    private static StringRedisTemplate adminRedis;

    @BeforeAll
    static void connectAdminClient() {
        adminConnections = connectionFactory(
                REDIS.getRedisHost(),
                REDIS.getRedisPort(),
                Duration.ofSeconds(2));
        adminRedis = template(adminConnections);
    }

    @AfterAll
    static void disconnectAdminClient() {
        if (adminConnections != null) {
            adminConnections.destroy();
        }
    }

    @BeforeEach
    void clearRedis() {
        try (RedisConnection connection = adminConnections.getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @Test
    @Timeout(value = 90, unit = TimeUnit.SECONDS)
    void same_service_redis_outage_and_recovery_complete() throws Exception {
        int gatePort = Phase4cRedisNetworkGate.reserveRefusedPort();
        try (Phase4cRedisNetworkGate gate = new Phase4cRedisNetworkGate(
                gatePort,
                REDIS.getRedisHost(),
                REDIS.getRedisPort());
                RunningService first = startService("first", gatePort)) {
            int originalPort = first.port();
            int originalContextIdentity = System.identityHashCode(first.context());

            assertThat(first.context().isActive()).isTrue();
            assertThat(gate.isOpen()).isFalse();
            assertConnectionRefused(gatePort);
            assertUnavailable(
                    exchange(first, API_PATH, "startup-refused", null, 0),
                    Alias.API,
                    "startup-refused",
                    FailureRepresentation.JSON);
            assertThat(first.downstreamHits()).isZero();

            gate.open();
            HttpResponse<byte[]> startupRecovered = awaitStatus(
                    first,
                    API_PATH,
                    "startup-recovered",
                    null,
                    0,
                    200);
            assertAllowed(startupRecovered, "first", 2);
            assertThat(first.port()).isEqualTo(originalPort);
            assertThat(System.identityHashCode(first.context()))
                    .isEqualTo(originalContextIdentity);
            assertThat(first.downstreamHits()).isEqualTo(1);
            assertIpNamespaceWasPseudonymized();

            proveRuntimeInterruptionAndSameInstanceRecovery(
                    gate,
                    first,
                    originalPort,
                    originalContextIdentity);
            proveAllWindowsTtlAndAliasScope(first);

            try (RunningService second = startService("second", gatePort)) {
                proveTwoJavaInstancesConverge(first, second);
            }
        }
    }

    private static void proveRuntimeInterruptionAndSameInstanceRecovery(
            Phase4cRedisNetworkGate gate,
            RunningService first,
            int originalPort,
            int originalContextIdentity
    ) throws Exception {
        int hitsBeforeOutage = first.downstreamHits();
        gate.refuseConnections();
        assertThat(gate.isOpen()).isFalse();

        assertUnavailable(
                exchange(first, API_PATH, "runtime-api", null, 4_201),
                Alias.API,
                "runtime-api",
                FailureRepresentation.JSON);
        assertUnavailable(
                exchange(first, WEB_PATH, "runtime-web-html", null, 4_202),
                Alias.WEB,
                "runtime-web-html",
                FailureRepresentation.HTML);
        assertUnavailable(
                exchange(
                        first,
                        WEB_PATH,
                        "runtime-web-json",
                        MediaType.APPLICATION_JSON_VALUE,
                        4_203),
                Alias.WEB,
                "runtime-web-json",
                FailureRepresentation.JSON);
        assertThat(first.downstreamHits()).isEqualTo(hitsBeforeOutage);
        assertActorKeysAbsent(Alias.API, "identity:v1", "4201");
        assertActorKeysAbsent(Alias.WEB, "identity:v1", "4202");
        assertActorKeysAbsent(Alias.WEB, "identity:v1", "4203");

        gate.open();
        HttpResponse<byte[]> recovered = awaitStatus(
                first,
                API_PATH,
                "runtime-recovered-1",
                null,
                4_201,
                200);
        assertAllowed(recovered, "first", 2);
        assertThat(first.port()).isEqualTo(originalPort);
        assertThat(System.identityHashCode(first.context()))
                .isEqualTo(originalContextIdentity);

        long recoveryGuardActor = 4_204;
        assertSecondWindowBurst(
                concurrentBurst(
                        first,
                        API_PATH,
                        "runtime-recovered-guard",
                        recoveryGuardActor,
                        3),
                "first");

        String secondKey = key(
                Alias.API,
                "identity:v1",
                Long.toString(recoveryGuardActor),
                "second");
        awaitKeyExpiry(secondKey);
        HttpResponse<byte[]> allowedAfterExpiry = exchange(
                first,
                API_PATH,
                "runtime-recovered-after-expiry",
                null,
                recoveryGuardActor);
        assertAllowed(allowedAfterExpiry, "first", 2);
        assertThat(first.downstreamHits()).isEqualTo(hitsBeforeOutage + 4);
    }

    private static void proveAllWindowsTtlAndAliasScope(RunningService first)
            throws Exception {
        long identityId = 4_301;
        String actor = Long.toString(identityId);
        String prefix = prefix(Alias.API, "identity:v1", actor);

        proveFirstHitTtlDoesNotRefresh(first);
        assertSecondWindowBurst(
                concurrentBurst(first, API_PATH, "windows-second", identityId, 3),
                "first");
        assertCounter(prefix + ":second", 3);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 2);
        assertTtl(prefix + ":second", 1_000);
        assertTtl(prefix + ":hour", 3_600_000);
        assertTtl(prefix + ":day", 86_400_000);

        adminRedis.delete(prefix + ":second");
        assertAllowed(exchange(first, API_PATH, "windows-3", null, identityId), "first", 2);
        assertRateLimited(
                exchange(first, API_PATH, "windows-hour", null, identityId),
                Window.HOUR,
                3,
                "windows-hour");
        assertCounter(prefix + ":hour", 4);
        assertCounter(prefix + ":day", 3);

        adminRedis.delete(List.of(prefix + ":second", prefix + ":hour"));
        assertAllowed(exchange(first, API_PATH, "windows-4", null, identityId), "first", 2);
        assertRateLimited(
                exchange(first, API_PATH, "windows-day", null, identityId),
                Window.DAY,
                4,
                "windows-day");
        assertCounter(prefix + ":second", 2);
        assertCounter(prefix + ":hour", 2);
        assertCounter(prefix + ":day", 5);

        HttpResponse<byte[]> webAllowed = exchange(
                first, WEB_PATH, "windows-web", null, identityId);
        assertAllowed(webAllowed, "first", 2);
        String webPrefix = prefix(Alias.WEB, "identity:v1", actor);
        assertCounter(webPrefix + ":second", 1);
        assertCounter(webPrefix + ":hour", 1);
        assertCounter(webPrefix + ":day", 1);
        assertThat(hmac("api", "identity:v1", actor))
                .isNotEqualTo(hmac("web", "identity:v1", actor));

        Set<String> keys = keys();
        assertThat(keys)
                .contains(
                        prefix + ":second",
                        prefix + ":hour",
                        prefix + ":day",
                        webPrefix + ":second",
                        webPrefix + ":hour",
                        webPrefix + ":day")
                .allMatch(key -> !key.contains(actor))
                .allMatch(key -> !key.contains(CLIENT_ADDRESS));
    }

    private static void proveFirstHitTtlDoesNotRefresh(RunningService first)
            throws Exception {
        long identityId = 4_351;
        String actor = Long.toString(identityId);
        String prefix = prefix(Alias.API, "identity:v1", actor);
        String secondKey = prefix + ":second";
        String hourKey = prefix + ":hour";
        String dayKey = prefix + ":day";

        assertAllowed(
                exchange(first, API_PATH, "ttl-first-hit", null, identityId),
                "first",
                2);
        long firstSecondTtl = ttl(secondKey);
        long firstHourTtl = ttl(hourKey);
        long firstDayTtl = ttl(dayKey);
        assertThat(firstSecondTtl).isBetween(500L, 1_000L);
        long beforeSecondHitTtl = awaitTtlAtMost(secondKey, firstSecondTtl - 100);

        assertAllowed(
                exchange(first, API_PATH, "ttl-second-hit", null, identityId),
                "first",
                2);
        assertThat(ttl(secondKey)).isBetween(1L, beforeSecondHitTtl);
        assertThat(ttl(hourKey)).isBetween(1L, firstHourTtl - 1);
        assertThat(ttl(dayKey)).isBetween(1L, firstDayTtl - 1);
        assertCounter(secondKey, 2);
        assertCounter(hourKey, 2);
        assertCounter(dayKey, 2);
    }

    private static void proveTwoJavaInstancesConverge(
            RunningService first,
            RunningService second
    ) throws Exception {
        assertThat(second.context()).isNotSameAs(first.context());
        assertThat(second.port()).isNotEqualTo(first.port());
        assertThat(second.context().getBean(LettuceConnectionFactory.class))
                .isNotSameAs(first.context().getBean(LettuceConnectionFactory.class));
        assertAllowed(
                awaitStatus(second, API_PATH, "second-warm", null, 4_499, 200),
                "second",
                2);

        long sharedIdentity = 4_401;
        String sharedPrefix = prefix(
                Alias.API,
                "identity:v1",
                Long.toString(sharedIdentity));
        assertAllowed(
                exchange(first, API_PATH, "shared-first", null, sharedIdentity),
                "first",
                2);
        adminRedis.delete(sharedPrefix + ":second");
        assertAllowed(
                exchange(second, API_PATH, "shared-second", null, sharedIdentity),
                "second",
                2);
        adminRedis.delete(sharedPrefix + ":second");
        assertAllowed(
                exchange(first, API_PATH, "shared-first-third", null, sharedIdentity),
                "first",
                2);
        adminRedis.delete(sharedPrefix + ":second");
        assertRateLimited(
                exchange(second, API_PATH, "shared-second-limited", null, sharedIdentity),
                Window.HOUR,
                3,
                "shared-second-limited");

        assertCounter(sharedPrefix + ":second", 1);
        assertCounter(sharedPrefix + ":hour", 4);
        assertCounter(sharedPrefix + ":day", 3);
    }

    private static List<ExchangeResult> concurrentBurst(
            RunningService service,
            String path,
            String requestIdPrefix,
            long identityId,
            int requests
    ) throws Exception {
        CountDownLatch ready = new CountDownLatch(requests);
        CountDownLatch start = new CountDownLatch(1);
        try (var executor = Executors.newFixedThreadPool(requests)) {
            List<Future<ExchangeResult>> futures = new ArrayList<>();
            for (int index = 0; index < requests; index++) {
                int requestIndex = index;
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    if (!start.await(5, TimeUnit.SECONDS)) {
                        throw new IllegalStateException("Redis burst start barrier timed out");
                    }
                    String requestId = requestIdPrefix + "-" + requestIndex;
                    return new ExchangeResult(
                            requestId,
                            exchange(service, path, requestId, null, identityId));
                }));
            }
            assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            List<ExchangeResult> results = new ArrayList<>();
            for (Future<ExchangeResult> future : futures) {
                results.add(future.get(10, TimeUnit.SECONDS));
            }
            return List.copyOf(results);
        }
    }

    private static void assertSecondWindowBurst(
            List<ExchangeResult> results,
            String expectedInstance
    ) throws Exception {
        assertThat(results.stream()
                .map(result -> result.response().statusCode())
                .toList())
                .containsExactlyInAnyOrder(200, 200, 429);
        for (ExchangeResult result : results) {
            if (result.response().statusCode() == 200) {
                assertAllowed(result.response(), expectedInstance, 2);
            } else {
                assertRateLimited(
                        result.response(),
                        Window.SECOND,
                        2,
                        result.requestId());
            }
        }
    }

    private static RunningService startService(String instanceId, int gatePort) {
        ConfigurableApplicationContext context = new SpringApplicationBuilder(
                RecoveryApplication.class)
                .web(WebApplicationType.SERVLET)
                .properties(
                        "spring.main.banner-mode=off",
                        "spring.jmx.enabled=false",
                        "management.endpoint.health.validate-group-membership=false",
                        "spring.data.redis.repositories.enabled=false",
                        "spring.data.redis.lettuce.shutdown-timeout=0ms",
                        "logging.level.root=WARN")
                .run(
                        "--server.port=0",
                        "--spring.application.name="
                                + "phase4c-user-counts-redis-recovery-" + instanceId,
                        "--spring.data.redis.host=127.0.0.1",
                        "--spring.data.redis.port=" + gatePort,
                        "--spring.data.redis.password=" + REDIS_PASSWORD,
                        "--spring.data.redis.connect-timeout=250ms",
                        "--spring.data.redis.timeout=400ms",
                        "--phase4c.instance-id=" + instanceId);
        WebServerApplicationContext web = (WebServerApplicationContext) context;
        AtomicInteger hits = context.getBean(AtomicInteger.class);
        return new RunningService(context, web.getWebServer().getPort(), hits);
    }

    private static HttpResponse<byte[]> awaitStatus(
            RunningService service,
            String path,
            String requestId,
            String accept,
            long identityId,
            int expectedStatus
    ) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        HttpResponse<byte[]> last = null;
        Exception lastFailure = null;
        while (System.nanoTime() < deadline) {
            try {
                last = exchange(service, path, requestId, accept, identityId);
                if (last.statusCode() == expectedStatus) {
                    return last;
                }
            } catch (IOException exception) {
                lastFailure = exception;
            }
            Thread.sleep(100);
        }
        throw new AssertionError(
                "HTTP status did not recover to " + expectedStatus
                        + "; last=" + (last == null ? "none" : last.statusCode()),
                lastFailure);
    }

    private static HttpResponse<byte[]> exchange(
            RunningService service,
            String path,
            String requestId,
            String accept,
            long identityId
    ) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(
                        URI.create("http://127.0.0.1:" + service.port() + path))
                .timeout(Duration.ofSeconds(5))
                .header("Accept-Encoding", "identity")
                .header("X-Request-ID", requestId)
                .GET();
        if (accept != null) {
            request.header(HttpHeaders.ACCEPT, accept);
        }
        if (identityId > 0) {
            request.header(FIXTURE_IDENTITY_HEADER, Long.toString(identityId));
        }
        return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private static void assertUnavailable(
            HttpResponse<byte[]> response,
            Alias alias,
            String requestId,
            FailureRepresentation representation
    ) throws Exception {
        assertThat(response.statusCode()).isEqualTo(503);
        assertThat(response.headers().firstValue("X-Request-ID")).contains(requestId);
        assertSecurityHeaders(response);
        assertNoRateHeaders(response);
        assertVary(response, alias == Alias.API
                ? List.of("origin", "cookie")
                : List.of("cookie"));

        String body = body(response);
        if (representation == FailureRepresentation.HTML) {
            assertThat(alias).isEqualTo(Alias.WEB);
            assertThat(response.headers().firstValue(HttpHeaders.CONTENT_TYPE))
                    .hasValueSatisfying(value -> assertThat(value)
                            .startsWith(MediaType.TEXT_HTML_VALUE));
            assertThat(body).isEqualTo(
                    "<h1>503 - 服务不可用</h1><p>服务暂时不可用，请稍后再试。</p>");
        } else {
            assertThat(response.headers().firstValue(HttpHeaders.CONTENT_TYPE))
                    .hasValueSatisfying(value -> assertThat(value)
                            .startsWith(MediaType.APPLICATION_JSON_VALUE));
            JsonNode json = JSON.readTree(body);
            assertThat(json.path("status").asText()).isEqualTo("error");
            assertThat(json.path("message").asText()).isEqualTo("服务暂时不可用");
            assertThat(json.path("status_code").asInt()).isEqualTo(503);
            assertThat(json.path("request_id").asText()).isEqualTo(requestId);
            assertThat(json.size()).isEqualTo(4);
        }
        assertThat(body).doesNotContain(
                "Redis",
                "Lettuce",
                "Connection refused",
                REDIS_PASSWORD,
                REDIS.getRedisHost(),
                Integer.toString(REDIS.getRedisPort()));
    }

    private static void assertAllowed(
            HttpResponse<byte[]> response,
            String expectedInstance,
            int expectedLimit
    ) {
        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(response.headers().firstValue(INSTANCE_HEADER)).contains(expectedInstance);
        assertThat(response.headers().firstValue("X-RateLimit-Limit"))
                .contains(Integer.toString(expectedLimit));
        assertThat(response.headers().firstValue("X-RateLimit-Remaining")).isPresent();
        assertThat(response.headers().firstValue("X-RateLimit-Reset")).isPresent();
        assertThat(response.headers().firstValue(HttpHeaders.RETRY_AFTER)).isPresent();
        assertSecurityHeaders(response);
    }

    private static void assertRateLimited(
            HttpResponse<byte[]> response,
            Window window,
            int limit,
            String requestId
    ) throws Exception {
        assertThat(response.statusCode()).isEqualTo(429);
        assertThat(response.headers().firstValue("X-Request-ID")).contains(requestId);
        assertThat(response.headers().firstValue("X-RateLimit-Limit"))
                .contains(Integer.toString(limit));
        assertThat(response.headers().firstValue("X-RateLimit-Remaining")).contains("0");
        assertThat(response.headers().firstValue("X-RateLimit-Reset")).isPresent();
        assertThat(response.headers().firstValue(HttpHeaders.RETRY_AFTER)).isPresent();
        assertSecurityHeaders(response);
        JsonNode json = JSON.readTree(body(response));
        assertThat(json.path("status_code").asInt()).isEqualTo(429);
        assertThat(json.path("message").asText())
                .isEqualTo(limit + " per 1 " + window.name().toLowerCase());
        assertThat(json.path("request_id").asText()).isEqualTo(requestId);
    }

    private static void assertSecurityHeaders(HttpResponse<byte[]> response) {
        assertThat(response.headers().firstValue("X-Content-Type-Options"))
                .contains("nosniff");
        assertThat(response.headers().firstValue("X-Frame-Options"))
                .contains("SAMEORIGIN");
        assertThat(response.headers().firstValue("Referrer-Policy"))
                .contains("strict-origin-when-cross-origin");
    }

    private static void assertNoRateHeaders(HttpResponse<byte[]> response) {
        for (String header : RATE_HEADERS) {
            assertThat(response.headers().firstValue(header)).isEmpty();
        }
    }

    private static void assertVary(
            HttpResponse<byte[]> response,
            List<String> expectedTokens
    ) {
        assertThat(response.headers().allValues(HttpHeaders.VARY))
                .flatMap(value -> List.of(value.toLowerCase().split(",\\s*")))
                .containsExactlyInAnyOrderElementsOf(expectedTokens);
    }

    private static void assertIpNamespaceWasPseudonymized() {
        String ipPrefix = prefix(Alias.API, "ip:v1", CLIENT_ADDRESS);
        assertCounter(ipPrefix + ":second", 1);
        assertCounter(ipPrefix + ":hour", 1);
        assertCounter(ipPrefix + ":day", 1);
        assertThat(keys())
                .contains(
                        ipPrefix + ":second",
                        ipPrefix + ":hour",
                        ipPrefix + ":day")
                .allMatch(key -> !key.contains(CLIENT_ADDRESS));
    }

    private static void assertActorKeysAbsent(Alias alias, String actorType, String actor) {
        String actorPrefix = prefix(alias, actorType, actor);
        assertThat(keys()).noneMatch(key -> key.startsWith(actorPrefix + ":"));
    }

    private static void assertCounter(String key, long expected) {
        assertThat(adminRedis.opsForValue().get(key)).isEqualTo(Long.toString(expected));
    }

    private static void assertTtl(String key, long maximumMillis) {
        assertThat(ttl(key)).isBetween(1L, maximumMillis);
    }

    private static long ttl(String key) {
        return adminRedis.getExpire(key, TimeUnit.MILLISECONDS);
    }

    private static long awaitTtlAtMost(String key, long maximumMillis)
            throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        long lastTtl = ttl(key);
        while (System.nanoTime() < deadline) {
            lastTtl = ttl(key);
            if (lastTtl > 0 && lastTtl <= maximumMillis) {
                return lastTtl;
            }
            Thread.sleep(10);
        }
        throw new AssertionError(
                "Redis TTL did not decrease to " + maximumMillis + "ms; last=" + lastTtl);
    }

    private static void awaitKeyExpiry(String key) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            if (Boolean.FALSE.equals(adminRedis.hasKey(key))) {
                return;
            }
            Thread.sleep(25);
        }
        assertThat(adminRedis.hasKey(key)).as("Redis second key must expire naturally").isFalse();
    }

    private static Set<String> keys() {
        Set<String> keys = adminRedis.keys(NAMESPACE + ":*");
        return keys == null ? Set.of() : keys;
    }

    private static String prefix(Alias alias, String actorType, String actor) {
        String aliasKey = alias == Alias.API ? "api" : "web";
        return NAMESPACE + ":" + aliasKey + ":" + actorType + ":"
                + hmac(aliasKey, actorType, actor);
    }

    private static String key(Alias alias, String actorType, String actor, String window) {
        return prefix(alias, actorType, actor) + ":" + window;
    }

    private static String hmac(String alias, String actorType, String actor) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    KEY_SECRET.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(
                    (DOMAIN_PREFIX + alias + ":" + actorType + "\0" + actor)
                            .getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new AssertionError(exception);
        }
    }

    private static String body(HttpResponse<byte[]> response) {
        return new String(response.body(), StandardCharsets.UTF_8);
    }

    private static void assertConnectionRefused(int port) {
        assertThatThrownBy(() -> {
            try (Socket socket = new Socket()) {
                socket.connect(new InetSocketAddress("127.0.0.1", port), 500);
            }
        }).isInstanceOf(ConnectException.class);
    }

    private static LettuceConnectionFactory connectionFactory(
            String host,
            int port,
            Duration timeout
    ) {
        RedisStandaloneConfiguration configuration = new RedisStandaloneConfiguration(host, port);
        configuration.setPassword(REDIS_PASSWORD);
        LettuceClientConfiguration client = LettuceClientConfiguration.builder()
                .clientOptions(ClientOptions.builder()
                        .socketOptions(SocketOptions.builder()
                                .connectTimeout(timeout)
                                .build())
                        .build())
                .commandTimeout(timeout)
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

    private record RunningService(
            ConfigurableApplicationContext context,
            int port,
            AtomicInteger hits
    ) implements AutoCloseable {

        private int downstreamHits() {
            return hits.get();
        }

        @Override
        public void close() {
            context.close();
        }
    }

    private record ExchangeResult(
            String requestId,
            HttpResponse<byte[]> response
    ) {
    }

    private enum FailureRepresentation {
        JSON,
        HTML
    }

    @SpringBootConfiguration
    @EnableAutoConfiguration(exclude = {
            DataSourceAutoConfiguration.class,
            HibernateJpaAutoConfiguration.class,
            DataJpaRepositoriesAutoConfiguration.class,
            DataRedisRepositoriesAutoConfiguration.class,
            SessionAutoConfiguration.class,
            SessionDataRedisAutoConfiguration.class,
            UserDetailsServiceAutoConfiguration.class
    })
    static class RecoveryApplication {

        @Bean
        Clock recoveryClock() {
            return Clock.systemUTC();
        }

        @Bean
        PersonalBankUserCountsReadRateLimitProperties recoveryProperties() {
            return new PersonalBankUserCountsReadRateLimitProperties(
                    NAMESPACE,
                    2,
                    3,
                    4,
                    1,
                    KEY_SECRET);
        }

        @Bean
        PersonalBankUserCountsReadRateLimiter recoveryRateLimiter(
                StringRedisTemplate redis,
                PersonalBankUserCountsReadRateLimitProperties properties,
                Clock clock
        ) {
            return new RedisPersonalBankUserCountsReadRateLimiter(redis, properties, clock);
        }

        @Bean
        PersonalBankUserCountsReadRequestResolver recoveryRoutes() {
            return new PersonalBankUserCountsReadRequestResolver();
        }

        @Bean
        LegacyPersonalBankUserCountsSecurityErrorWriter recoveryErrors() {
            return new LegacyPersonalBankUserCountsSecurityErrorWriter(JSON);
        }

        @Bean
        ClientAddressResolver recoveryClientAddressResolver() {
            return request -> CLIENT_ADDRESS;
        }

        @Bean
        RequestIdFilter recoveryRequestIdFilter() {
            return new RequestIdFilter();
        }

        @Bean
        AtomicInteger recoveryDownstreamHits() {
            return new AtomicInteger();
        }

        @Bean
        RecoveryProbeController recoveryProbeController(
                @Value("${phase4c.instance-id}") String instanceId,
                AtomicInteger hits
        ) {
            return new RecoveryProbeController(instanceId, hits);
        }

        @Bean
        SecurityFilterChain recoverySecurityChain(
                HttpSecurity http,
                PersonalBankUserCountsReadRateLimiter rateLimiter,
                LegacyPersonalBankUserCountsSecurityErrorWriter errors,
                PersonalBankUserCountsReadRequestResolver routes,
                ClientAddressResolver clientAddresses
        ) throws Exception {
            IdentityFixtureFilter identity = new IdentityFixtureFilter();
            PersonalBankUserCountsReadRateLimitFilter limiter =
                    new PersonalBankUserCountsReadRateLimitFilter(
                            rateLimiter,
                            errors,
                            routes,
                            clientAddresses);
            http.authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll())
                    .csrf(AbstractHttpConfigurer::disable)
                    .requestCache(cache -> cache.disable())
                    .sessionManagement(session -> session.sessionCreationPolicy(
                            SessionCreationPolicy.STATELESS))
                    .formLogin(AbstractHttpConfigurer::disable)
                    .httpBasic(AbstractHttpConfigurer::disable)
                    .logout(AbstractHttpConfigurer::disable)
                    .headers(headers -> headers
                            .frameOptions(frame -> frame.sameOrigin())
                            .referrerPolicy(referrer -> referrer.policy(
                                    ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN)))
                    .addFilterAfter(identity, SecurityContextHolderFilter.class)
                    .addFilterAfter(limiter, HeaderWriterFilter.class);
            return http.build();
        }
    }

    static final class IdentityFixtureFilter extends OncePerRequestFilter {

        @Override
        protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
        ) throws ServletException, IOException {
            String rawIdentity = request.getHeader(FIXTURE_IDENTITY_HEADER);
            if (rawIdentity == null) {
                filterChain.doFilter(request, response);
                return;
            }
            long identityId = Long.parseLong(rawIdentity);
            var principal = new TargetAuthenticatedPrincipal(identityId, "redis-recovery-fixture");
            var authentication = new UsernamePasswordAuthenticationToken(
                    principal,
                    "redacted",
                    List.of());
            var context = SecurityContextHolder.createEmptyContext();
            context.setAuthentication(authentication);
            SecurityContextHolder.setContext(context);
            try {
                filterChain.doFilter(request, response);
            } finally {
                SecurityContextHolder.clearContext();
            }
        }
    }

    @RestController
    static final class RecoveryProbeController {

        private final String instanceId;
        private final AtomicInteger hits;

        RecoveryProbeController(String instanceId, AtomicInteger hits) {
            this.instanceId = instanceId;
            this.hits = hits;
        }

        @GetMapping({
                "/api/user/banks/api/{bankId}/user-counts",
                "/user/banks/api/{bankId}/user-counts"
        })
        ResponseEntity<Map<String, Object>> read(
                @PathVariable String bankId
        ) {
            int hit = hits.incrementAndGet();
            return ResponseEntity.ok()
                    .header(INSTANCE_HEADER, instanceId)
                    .body(Map.of(
                            "status", "ok",
                            "bank_id", bankId,
                            "instance", instanceId,
                            "hit", hit));
        }
    }
}
