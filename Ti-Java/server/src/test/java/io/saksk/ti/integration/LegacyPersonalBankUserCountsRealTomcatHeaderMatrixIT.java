package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi;
import io.saksk.ti.identity.api.SessionAuthorityApi;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.web.security.LegacySessionExchangeGuard;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.TargetSessionIssuer;
import io.saksk.ti.web.security.TargetSessionRegistry;
import java.lang.reflect.Method;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.TimeUnit;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.aop.framework.AopProxyUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Real-network evidence for {@code real_tomcat_complete_response_header_matrix_complete}.
 *
 * <p>No application, authentication, target-session, or rate-limit port is mocked. Every request
 * uses the random-port Tomcat connector and the full production filter chain. GET and HEAD begin
 * from equivalent route-quota state so all response headers, including the rate-limit envelope,
 * can be compared without one method consuming the other's fixture budget.</p>
 */
@Testcontainers
@ActiveProfiles("test")
@SpringBootTest(
        classes = TiApplication.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "management.endpoint.health.validate-group-membership=false")
@Import(LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.FixedEvidenceClock.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@Execution(ExecutionMode.SAME_THREAD)
class LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT {

    private static final String API_PATH =
            "/api/user/banks/api/99551/user-counts";
    private static final String WEB_PATH =
            "/user/banks/api/99551/user-counts";
    private static final long OWNER_ID = 99_451L;
    private static final int OWNER_SESSION_VERSION = 11;
    private static final String ALLOWED_ORIGIN = "https://servicewechat.com";
    private static final String REQUEST_ID_HEADER = "X-Request-ID";
    private static final String PAIR_REQUEST_ID = "phase4c-real-tomcat-header-pair";
    private static final String REDIS_PASSWORD = "phase4c-real-tomcat-header-redis";
    private static final String RATE_NAMESPACE =
            "ti-java:learning:personal-bank-user-counts-real-tomcat-headers";
    private static final int RATE_HOUR_LIMIT = 500;
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final byte[] LEGACY_SECRET_BYTES =
            LEGACY_SECRET.getBytes(StandardCharsets.UTF_8);
    private static final Instant CAPTURED_NOW =
            Instant.ofEpochSecond(Instant.now().getEpochSecond());
    private static final Instant CREDENTIAL_EXPIRES_AT =
            CAPTURED_NOW.plus(Duration.ofHours(1));
    private static final String OWNER_BEARER = signedOwnerBearer();
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    private static final List<String> CORS_HEADERS = List.of(
            HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
            HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS,
            HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS,
            HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS,
            HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS,
            HttpHeaders.ACCESS_CONTROL_MAX_AGE);
    private static final List<String> SECURITY_HEADERS = List.of(
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy");
    private static final List<String> RATE_HEADERS = List.of(
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            HttpHeaders.RETRY_AFTER);
    private static final List<String> COMPLETE_PARITY_HEADERS = List.of(
            HttpHeaders.CONTENT_TYPE,
            HttpHeaders.LOCATION,
            HttpHeaders.VARY,
            HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
            HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS,
            HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS,
            HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS,
            HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS,
            HttpHeaders.ACCESS_CONTROL_MAX_AGE,
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            REQUEST_ID_HEADER,
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            HttpHeaders.RETRY_AFTER);

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.reference18()
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                    "/docker-entrypoint-initdb.d/030-auth-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4b/062-personal-bank-share-list-schema.sql"),
                    "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4b/065-personal-bank-usage-stats-schema.sql"),
                    "/docker-entrypoint-initdb.d/065-personal-bank-usage-stats-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                    "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4c/071-personal-bank-user-counts-golden-target-seed.sql"),
                    "/docker-entrypoint-initdb.d/071-personal-bank-user-counts-golden-target-seed.sql");

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "128mb",
                    "--maxmemory-policy", "noeviction");

    @DynamicPropertySource
    static void infrastructureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.jpa.generate-ddl", () -> "false");
        registry.add("spring.data.redis.host", REDIS::getRedisHost);
        registry.add("spring.data.redis.port", REDIS::getRedisPort);
        registry.add("spring.data.redis.password", () -> REDIS_PASSWORD);
        registry.add("spring.data.redis.repositories.enabled", () -> "false");
        registry.add("spring.data.redis.connect-timeout", () -> "1s");
        registry.add("spring.data.redis.timeout", () -> "1s");
        registry.add(
                "spring.session.data.redis.namespace",
                () -> "ti-java:phase4c:real-tomcat-header-sessions");
        registry.add(
                "ti.security.login-rate-limit.key-secret",
                () -> "phase4c-real-tomcat-login-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add(
                "ti.security.legacy-auth.accept-until",
                () -> CAPTURED_NOW.plus(Duration.ofDays(1)).toString());
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.namespace",
                () -> RATE_NAMESPACE);
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-second",
                () -> "10");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-hour",
                () -> Integer.toString(RATE_HOUR_LIMIT));
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-day",
                () -> "5000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.multiplier",
                () -> "1");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.key-secret",
                () -> "phase4c-real-tomcat-user-counts-key-secret-0001");
        registry.add(
                "ti.security.personal-bank-user-counts-cors.allowed-origins",
                () -> ALLOWED_ORIGIN);
    }

    @LocalServerPort
    int serverPort;

    @Autowired
    ApplicationContext applicationContext;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    ObjectMapper json;

    @Autowired
    LearningApplicationApi learning;

    @Autowired
    SessionAuthorityApi sessionAuthority;

    @Autowired
    LegacyCredentialAuthenticationApi legacyCredentials;

    @Autowired
    LegacySessionExchangeGuard legacySessionExchanges;

    @Autowired
    TargetSessionRegistry targetSessionRegistry;

    @Autowired
    TargetSessionIssuer targetSessionIssuer;

    @Autowired
    PersonalBankUserCountsReadRateLimiter rateLimiter;

    @BeforeEach
    void resetRealRedis() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @AfterEach
    void leaveRedisAvailable() throws Exception {
        var inspection = REDIS.getDockerClient()
                .inspectContainerCmd(REDIS.getContainerId())
                .exec();
        if (Boolean.TRUE.equals(inspection.getState().getPaused())) {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
        }
        awaitRedisHost();
    }

    @Test
    @Order(1)
    void randomPortTomcatLoadsRealProductionPortsWithPostgresql18AndRedis7()
            throws Exception {
        assertThat(serverPort).isPositive();
        Method getWebServer = applicationContext.getClass().getMethod("getWebServer");
        Object webServer = getWebServer.invoke(applicationContext);
        assertThat(webServer.getClass().getName()).contains("TomcatWebServer");

        assertProductionBean(
                learning,
                "io.saksk.ti.learning.application.PersonalBankUserCountsService");
        assertProductionBean(
                sessionAuthority,
                "io.saksk.ti.identity.application.SessionAuthorityApplicationService");
        assertProductionBean(
                legacyCredentials,
                "io.saksk.ti.identity.infrastructure.security."
                        + "LegacyAuthenticationCompatibilityService");
        assertProductionBean(
                legacySessionExchanges,
                "io.saksk.ti.web.security.RedisLegacySessionExchangeGuard");
        assertProductionBean(
                targetSessionRegistry,
                "io.saksk.ti.web.security.RedisTargetSessionRegistry");
        assertProductionBean(
                targetSessionIssuer,
                "io.saksk.ti.web.security.TargetSessionIssuer");
        assertProductionBean(
                rateLimiter,
                "io.saksk.ti.web.security.RedisPersonalBankUserCountsReadRateLimiter");

        assertThat(POSTGRES.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.POSTGRES_18_REFERENCE);
        assertThat(jdbc.queryForObject("SHOW server_version", String.class))
                .isEqualTo("18.4");
        assertThat(REDIS.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.REDIS_7);
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            assertThat(connection.ping()).isEqualTo("PONG");
        }
        assertThat(jdbc.queryForObject(
                "SELECT username FROM users WHERE id = ?",
                String.class,
                OWNER_ID)).isEqualTo("phase4b_counts_owner");
    }

    @Test
    @Order(2)
    void getAndHead200TraverseRealTargetSessionRateLimiterAndBusinessJdbc()
            throws Exception {
        String targetCookie = issueRememberedTargetSession();
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.COOKIE, targetCookie));

        ResponsePair pair = exchangeFromEquivalentQuotaState(
                API_PATH,
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                200,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                true,
                true));
        JsonNode body = json.readTree(pair.get().body());
        assertThat(body.path("status").asString()).isEqualTo("success");
        assertThat(body.path("data").path("total").asLong()).isEqualTo(9L);
        assertThat(cookieSemantics(pair.get()))
                .extracting(CookieSemantics::name)
                .contains("ti_dev_session");
    }

    @Test
    @Order(3)
    void getAndHead302PreserveWebRedirectHeaders() throws Exception {
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                WEB_PATH,
                Map.of(),
                Map.of(),
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                302,
                true,
                "text/html",
                "/login",
                List.of("Cookie"),
                null,
                true,
                true,
                true,
                false));
    }

    @Test
    @Order(4)
    void getAndHead400PreserveTomcatFirewallHeaders() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.AUTHORIZATION, "Bearer " + OWNER_BEARER));
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                "/api/user/banks/api/99551%3Bignored/user-counts",
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                400,
                false,
                null,
                null,
                null,
                null,
                false,
                false,
                false,
                false));
    }

    @Test
    @Order(5)
    void getAndHead401PreserveApiAuthenticationHeaders() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of());
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                API_PATH,
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                401,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                true,
                false));
        assertThat(json.readTree(pair.get().body()).path("status").asString())
                .isEqualTo("unauthorized");
    }

    @Test
    @Order(6)
    void getAndHead403PreserveDeniedHeaders() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.AUTHORIZATION, "Bearer " + OWNER_BEARER));
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                "/api/user/banks/api/0/user-counts",
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                403,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                true,
                false));
        assertThat(json.readTree(pair.get().body()).path("message").asString())
                .isEqualTo("无权访问此题库");
    }

    @Test
    @Order(7)
    void getAndHead404PreserveConverterMissHeaders() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of());
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                "/api/user/banks/api/not-a-bank/user-counts",
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                404,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                null,
                true,
                true,
                false,
                false));
    }

    @Test
    @Order(8)
    void getAndHead429UseTheRealRedisHourQuotaAndPreserveAllRateHeaders()
            throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.AUTHORIZATION, "Bearer " + OWNER_BEARER));
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                API_PATH,
                headers,
                headers,
                this::primeRealHourQuotaAtLimit);

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                429,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                true,
                false));
        assertThat(pair.get().headers().firstValue("X-RateLimit-Limit"))
                .contains(Integer.toString(RATE_HOUR_LIMIT));
        assertThat(pair.get().headers().firstValue("X-RateLimit-Remaining"))
                .contains("0");
        assertThat(json.readTree(pair.get().body()).path("message").asString())
                .isEqualTo("500 per 1 hour");
    }

    @Test
    @Order(9)
    void getAndHead500PreserveOverflowFailureHeaders() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.AUTHORIZATION, "Bearer " + OWNER_BEARER));
        ResponsePair pair = exchangeFromEquivalentQuotaState(
                "/api/user/banks/api/9223372036854775808/user-counts",
                headers,
                headers,
                () -> { });

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                500,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                true,
                false));
        assertThat(json.readTree(pair.get().body()).path("status_code").asInt())
                .isEqualTo(500);
    }

    @Test
    @Order(10)
    void getAndHead503PreserveHeadersWhenTheRealRedisLimiterIsUnavailable()
            throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.AUTHORIZATION, "Bearer " + OWNER_BEARER));
        clearRouteRateLimits();
        REDIS.getDockerClient().pauseContainerCmd(REDIS.getContainerId()).exec();
        ResponsePair pair;
        try {
            pair = new ResponsePair(
                    exchange("GET", API_PATH, headers),
                    exchange("HEAD", API_PATH, headers));
        } finally {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
            awaitRedisHost();
        }

        assertCompleteHeaderMatrix(pair, new MatrixExpectation(
                503,
                true,
                "application/json",
                null,
                List.of("Origin", "Cookie"),
                ALLOWED_ORIGIN,
                true,
                true,
                false,
                false));
        assertThat(json.readTree(pair.get().body()).path("message").asString())
                .isEqualTo("服务暂时不可用");
    }

    private void assertProductionBean(Object bean, String expectedClassName) {
        assertThat(AopProxyUtils.ultimateTargetClass(bean).getName())
                .isEqualTo(expectedClassName)
                .doesNotContain("Mockito", "Mock");
    }

    private String issueRememberedTargetSession() throws Exception {
        Map<String, String> headers = apiHeaders(Map.of(
                HttpHeaders.COOKIE,
                "session=" + signedOwnerFlaskCookie("remembered-target")));
        HttpResponse<byte[]> response = exchange("GET", API_PATH, headers);
        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(json.readTree(response.body()).path("status").asString())
                .isEqualTo("success");
        String target = response.headers().allValues(HttpHeaders.SET_COOKIE).stream()
                .filter(value -> value.startsWith("ti_dev_session="))
                .findFirst()
                .orElseThrow(() -> new AssertionError(
                        "real Flask exchange did not issue a target Session"));
        return target.substring(0, target.indexOf(';'));
    }

    private ResponsePair exchangeFromEquivalentQuotaState(
            String path,
            Map<String, String> getHeaders,
            Map<String, String> headHeaders,
            CheckedRunnable prepareEach
    ) throws Exception {
        clearRouteRateLimits();
        prepareEach.run();
        HttpResponse<byte[]> get = exchange("GET", path, getHeaders);

        clearRouteRateLimits();
        prepareEach.run();
        HttpResponse<byte[]> head = exchange("HEAD", path, headHeaders);
        return new ResponsePair(get, head);
    }

    private void primeRealHourQuotaAtLimit() throws Exception {
        HttpResponse<byte[]> warmup = exchange(
                "GET",
                API_PATH,
                apiHeaders(Map.of(
                        HttpHeaders.AUTHORIZATION,
                        "Bearer " + OWNER_BEARER)));
        assertThat(warmup.statusCode()).isEqualTo(200);
        Set<String> hourKeys = redis.keys(
                RATE_NAMESPACE + ":api:identity:v1:*:hour");
        assertThat(hourKeys).singleElement();
        String hourKey = hourKeys.iterator().next();
        redis.opsForValue().set(hourKey, Integer.toString(RATE_HOUR_LIMIT));
        assertThat(redis.expire(hourKey, Duration.ofMinutes(30))).isTrue();
    }

    private void clearRouteRateLimits() {
        Set<String> keys = redis.keys(RATE_NAMESPACE + ":*");
        if (!keys.isEmpty()) {
            redis.delete(keys);
        }
    }

    private HttpResponse<byte[]> exchange(
            String method,
            String path,
            Map<String, String> headers
    ) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(
                        URI.create("http://127.0.0.1:" + serverPort + path))
                .timeout(Duration.ofSeconds(10))
                .header("Accept-Encoding", "identity")
                .header(REQUEST_ID_HEADER, PAIR_REQUEST_ID)
                .method(method, HttpRequest.BodyPublishers.noBody());
        headers.forEach((name, value) -> {
            if (!REQUEST_ID_HEADER.equalsIgnoreCase(name)) {
                request.header(name, value);
            }
        });
        return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private static Map<String, String> apiHeaders(Map<String, String> additions) {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put(HttpHeaders.ORIGIN, ALLOWED_ORIGIN);
        headers.putAll(additions);
        return Map.copyOf(headers);
    }

    private static void assertCompleteHeaderMatrix(
            ResponsePair pair,
            MatrixExpectation expected
    ) {
        assertThat(pair.get().statusCode()).isEqualTo(expected.status());
        assertThat(pair.head().statusCode()).isEqualTo(pair.get().statusCode());
        assertThat(pair.get().version()).isEqualTo(HttpClient.Version.HTTP_1_1);
        assertThat(pair.head().version()).isEqualTo(HttpClient.Version.HTTP_1_1);
        if (expected.getHasBody()) {
            assertThat(pair.get().body()).isNotEmpty();
        }
        assertThat(pair.head().body()).isEmpty();

        for (String header : COMPLETE_PARITY_HEADERS) {
            assertThat(pair.head().headers().allValues(header))
                    .as("HEAD %s must equal GET", header)
                    .isEqualTo(pair.get().headers().allValues(header));
        }
        assertSetCookieSemantics(pair);

        if (expected.contentTypePrefix() != null) {
            assertThat(pair.get().headers().firstValue(HttpHeaders.CONTENT_TYPE))
                    .hasValueSatisfying(value -> assertThat(value)
                            .startsWith(expected.contentTypePrefix()));
        }
        if (expected.location() == null) {
            assertThat(pair.get().headers().firstValue(HttpHeaders.LOCATION)).isEmpty();
        } else {
            assertThat(pair.get().headers().firstValue(HttpHeaders.LOCATION))
                    .contains(expected.location());
        }
        if (expected.varyTokens() != null) {
            assertVary(pair.get(), expected.varyTokens());
        }
        if (expected.corsOrigin() == null) {
            assertNoCorsResponseHeaders(pair.get());
        } else {
            assertThat(pair.get().headers().firstValue(
                    HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                    .contains(expected.corsOrigin());
            for (String header : CORS_HEADERS) {
                if (!HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN.equals(header)) {
                    assertThat(pair.get().headers().allValues(header)).isEmpty();
                }
            }
        }
        if (expected.securityHeaders()) {
            assertSecurityHeaders(pair.get());
        } else {
            assertNoSecurityHeaders(pair.get());
        }
        if (expected.requestId()) {
            assertThat(pair.get().headers().firstValue(REQUEST_ID_HEADER))
                    .contains(PAIR_REQUEST_ID);
        } else {
            pair.get().headers().firstValue(REQUEST_ID_HEADER)
                    .ifPresent(value -> assertThat(value).isEqualTo(PAIR_REQUEST_ID));
        }
        if (expected.rateHeaders()) {
            for (String header : RATE_HEADERS) {
                assertThat(pair.get().headers().allValues(header))
                        .as("real rate header %s", header)
                        .isNotEmpty();
            }
        } else {
            assertNoRateHeaders(pair.get());
        }
        if (expected.setCookie()) {
            assertThat(cookieSemantics(pair.get())).isNotEmpty();
        } else {
            assertThat(cookieSemantics(pair.get())).isEmpty();
        }
    }

    private static void assertVary(
            HttpResponse<byte[]> response,
            List<String> expectedTokens
    ) {
        assertThat(response.headers().allValues(HttpHeaders.VARY))
                .flatMap(value -> List.of(value.split(",\\s*")))
                .containsExactlyInAnyOrderElementsOf(expectedTokens);
    }

    private static void assertSecurityHeaders(HttpResponse<byte[]> response) {
        assertThat(response.headers().firstValue("X-Content-Type-Options"))
                .contains("nosniff");
        assertThat(response.headers().firstValue("X-Frame-Options"))
                .contains("SAMEORIGIN");
        assertThat(response.headers().firstValue("Referrer-Policy"))
                .contains("strict-origin-when-cross-origin");
    }

    private static void assertNoSecurityHeaders(HttpResponse<byte[]> response) {
        for (String header : SECURITY_HEADERS) {
            assertThat(response.headers().allValues(header)).isEmpty();
        }
    }

    private static void assertNoRateHeaders(HttpResponse<byte[]> response) {
        for (String header : RATE_HEADERS) {
            assertThat(response.headers().allValues(header)).isEmpty();
        }
    }

    private static void assertNoCorsResponseHeaders(HttpResponse<byte[]> response) {
        for (String header : CORS_HEADERS) {
            assertThat(response.headers().allValues(header)).isEmpty();
        }
    }

    private static void assertSetCookieSemantics(ResponsePair pair) {
        assertThat(cookieSemantics(pair.head()))
                .as("HEAD Set-Cookie semantics must equal GET")
                .containsExactlyInAnyOrderElementsOf(cookieSemantics(pair.get()));
    }

    private static List<CookieSemantics> cookieSemantics(
            HttpResponse<byte[]> response
    ) {
        return response.headers().allValues(HttpHeaders.SET_COOKIE).stream()
                .map(CookieSemantics::parse)
                .toList();
    }

    private void awaitRedisHost() throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
        RuntimeException lastFailure = null;
        while (System.nanoTime() < deadline) {
            try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
                if ("PONG".equals(connection.ping())) {
                    return;
                }
            } catch (RuntimeException failure) {
                lastFailure = failure;
            }
            Thread.sleep(100);
        }
        throw new IllegalStateException("Redis did not recover on its published port", lastFailure);
    }

    private static String signedOwnerBearer() {
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + OWNER_ID
                + ",\"openid\":\"\",\"session_version\":" + OWNER_SESSION_VERSION
                + ",\"exp\":" + CREDENTIAL_EXPIRES_AT.getEpochSecond()
                + ",\"iat\":" + CAPTURED_NOW.getEpochSecond()
                + ",\"jti\":\"" + String.format("%032x", OWNER_ID) + "\"}";
        String unsigned = base64Url(header) + "." + base64Url(payload);
        return unsigned + "." + encode(hmac(
                "HmacSHA256",
                LEGACY_SECRET_BYTES,
                unsigned.getBytes(StandardCharsets.US_ASCII)));
    }

    private static String signedOwnerFlaskCookie(String nonce) {
        String payload = "{\"_permanent\":true,\"user_id\":" + OWNER_ID
                + ",\"username\":\"phase4b_counts_owner\""
                + ",\"session_version\":" + OWNER_SESSION_VERSION
                + ",\"remember\":true,\"csrf_token\":\"" + nonce + "\"}";
        String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
        String encodedTimestamp = encode(minimalBigEndian(CAPTURED_NOW.getEpochSecond()));
        String unsigned = encodedPayload + "." + encodedTimestamp;
        byte[] derived = hmac(
                "HmacSHA1",
                LEGACY_SECRET_BYTES,
                "cookie-session".getBytes(StandardCharsets.UTF_8));
        byte[] signature = hmac(
                "HmacSHA1",
                derived,
                unsigned.getBytes(StandardCharsets.US_ASCII));
        Arrays.fill(derived, (byte) 0);
        return unsigned + "." + encode(signature);
    }

    private static String base64Url(String value) {
        return encode(value.getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] minimalBigEndian(long value) {
        byte[] full = ByteBuffer.allocate(Long.BYTES).putLong(value).array();
        int first = 0;
        while (first < full.length - 1 && full[first] == 0) {
            first++;
        }
        return Arrays.copyOfRange(full, first, full.length);
    }

    private static byte[] hmac(String algorithm, byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance(algorithm);
            mac.init(new SecretKeySpec(key, algorithm));
            return mac.doFinal(value);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException(algorithm + " unavailable", exception);
        }
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private record ResponsePair(
            HttpResponse<byte[]> get,
            HttpResponse<byte[]> head
    ) {
    }

    private record MatrixExpectation(
            int status,
            boolean getHasBody,
            String contentTypePrefix,
            String location,
            List<String> varyTokens,
            String corsOrigin,
            boolean securityHeaders,
            boolean requestId,
            boolean rateHeaders,
            boolean setCookie
    ) {
    }

    private record CookieSemantics(
            String name,
            String value,
            Optional<String> maxAge,
            Optional<String> path,
            Optional<String> domain,
            boolean httpOnly,
            boolean secure,
            Optional<String> sameSite,
            Optional<String> expires,
            Map<String, String> extensions
    ) {

        private static CookieSemantics parse(String header) {
            String[] segments = header.split(";", -1);
            int valueSeparator = segments[0].indexOf('=');
            if (valueSeparator <= 0) {
                throw new IllegalArgumentException("Invalid Set-Cookie name/value pair");
            }
            String name = segments[0].substring(0, valueSeparator).strip();
            String rawValue = segments[0].substring(valueSeparator + 1).strip();
            if (name.isEmpty()) {
                throw new IllegalArgumentException("Set-Cookie name must not be empty");
            }

            Map<String, String> attributes = new TreeMap<>();
            for (int index = 1; index < segments.length; index++) {
                String segment = segments[index].strip();
                if (segment.isEmpty()) {
                    continue;
                }
                int separator = segment.indexOf('=');
                String attributeName = (separator < 0
                                ? segment
                                : segment.substring(0, separator))
                        .strip()
                        .toLowerCase(Locale.ROOT);
                String attributeValue = separator < 0
                        ? ""
                        : segment.substring(separator + 1).strip();
                if (attributeName.isEmpty()
                        || attributes.putIfAbsent(attributeName, attributeValue) != null) {
                    throw new IllegalArgumentException(
                            "Invalid or duplicate Set-Cookie attribute");
                }
            }

            Optional<String> maxAge = optionalAttribute(attributes, "max-age")
                    .map(CookieSemantics::canonicalLong);
            Optional<String> expires = optionalAttribute(attributes, "expires")
                    .map(value -> maxAge.isPresent() ? "present-with-max-age" : value);
            Map<String, String> extensions = new TreeMap<>(attributes);
            for (String standard : List.of(
                    "max-age", "path", "domain", "httponly", "secure",
                    "samesite", "expires")) {
                extensions.remove(standard);
            }
            return new CookieSemantics(
                    name,
                    normalizedCookieValue(name, rawValue),
                    maxAge,
                    optionalAttribute(attributes, "path"),
                    optionalAttribute(attributes, "domain")
                            .map(value -> value.startsWith(".")
                                    ? value.substring(1)
                                    : value)
                            .map(value -> value.toLowerCase(Locale.ROOT)),
                    attributes.containsKey("httponly"),
                    attributes.containsKey("secure"),
                    optionalAttribute(attributes, "samesite")
                            .map(value -> value.toLowerCase(Locale.ROOT)),
                    expires,
                    Map.copyOf(extensions));
        }

        private static Optional<String> optionalAttribute(
                Map<String, String> attributes,
                String name
        ) {
            return Optional.ofNullable(attributes.get(name));
        }

        private static String canonicalLong(String value) {
            try {
                return Long.toString(Long.parseLong(value));
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException("Invalid Set-Cookie Max-Age", exception);
            }
        }

        private static String normalizedCookieValue(String name, String value) {
            return name.equals("ti_dev_session") && !value.isEmpty()
                    ? "<dynamic-session-id>"
                    : value;
        }
    }

    @FunctionalInterface
    private interface CheckedRunnable {

        void run() throws Exception;
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedEvidenceClock {

        @Bean
        @Primary
        Clock realTomcatHeaderEvidenceClock() {
            return Clock.fixed(CAPTURED_NOW, ZoneOffset.UTC);
        }
    }
}
