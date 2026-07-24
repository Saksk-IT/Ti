package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.web.security.TransactionWriteRateLimiter;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
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
 * Real Tomcat target execution for the nine Phase 4C transaction-write operations.
 *
 * <p>No HTTP, authentication, application, JDBC, transaction, Redis, or Session port is mocked.
 * The test database is disposable and initialized only from test fixtures plus the additive
 * idempotency migration.</p>
 */
@Testcontainers
@ActiveProfiles("test")
@SpringBootTest(
        classes = TiApplication.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "management.endpoint.health.validate-group-membership=false")
@Import(LegacyTransactionWriteRealTomcatIT.FixedEvidenceClock.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Execution(ExecutionMode.SAME_THREAD)
class LegacyTransactionWriteRealTomcatIT {

    private static final long USER_ID = 99_451L;
    private static final int USER_SESSION_VERSION = 11;
    private static final long ADMIN_ID = 99_452L;
    private static final int ADMIN_SESSION_VERSION = 13;
    private static final String USERNAME = "phase4c_write_user";
    private static final String ALLOWED_ORIGIN = "https://write.example";
    private static final String REDIS_PASSWORD = "phase4c-write-http-redis";
    private static final String RATE_NAMESPACE =
            "ti-java:web:phase4c-transaction-write-http-rate";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final byte[] LEGACY_SECRET_BYTES =
            LEGACY_SECRET.getBytes(StandardCharsets.UTF_8);
    private static final Instant CAPTURED_NOW =
            Instant.ofEpochSecond(Instant.now().getEpochSecond());
    private static final Instant CREDENTIAL_EXPIRES_AT =
            CAPTURED_NOW.plus(Duration.ofHours(1));
    private static final String USER_BEARER =
            signedBearer(USER_ID, USER_SESSION_VERSION);
    private static final String ADMIN_BEARER =
            signedBearer(ADMIN_ID, ADMIN_SESSION_VERSION);
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    private static final List<RouteCase> ROUTES = List.of(
            new RouteCase(
                    "favorite-web-alias",
                    "POST",
                    "/api/favorite",
                    "{\"question_id\":\"not-an-integer\"}",
                    "{\"question_id\":93001}",
                    400,
                    "question_id 参数错误",
                    "请先登录后使用此功能",
                    30),
            new RouteCase(
                    "favorite-quiz-api",
                    "POST",
                    "/api/quiz/favorite",
                    "{\"question_id\":\"not-an-integer\"}",
                    "{\"question_id\":93007}",
                    400,
                    "question_id 参数错误",
                    "请先登录",
                    30),
            new RouteCase(
                    "record-result-web-alias",
                    "POST",
                    "/api/record_result",
                    "{\"question_id\":0}",
                    "{\"question_id\":93002,\"is_correct\":false}",
                    400,
                    "参数不完整",
                    "请先登录后使用此功能",
                    60),
            new RouteCase(
                    "record-result-quiz-api",
                    "POST",
                    "/api/quiz/record_result",
                    "{\"question_id\":0}",
                    "{\"question_id\":93008,\"is_correct\":true}",
                    400,
                    "参数不完整",
                    "请先登录",
                    60),
            new RouteCase(
                    "study-learn-record",
                    "POST",
                    "/api/quiz/study/learn/record",
                    "{\"question_id\":\"not-an-integer\"}",
                    "{\"question_id\":93003,\"is_correct\":true,"
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    400,
                    "question_id 参数错误",
                    "请先登录",
                    60),
            new RouteCase(
                    "study-review-record",
                    "POST",
                    "/api/quiz/study/review/record",
                    "{\"question_id\":\"not-an-integer\"}",
                    "{\"question_id\":93004,\"rating\":\"known\","
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    400,
                    "rating 参数错误",
                    "请先登录",
                    60),
            new RouteCase(
                    "study-review-master",
                    "POST",
                    "/api/quiz/study/review/master",
                    "{\"question_id\":\"not-an-integer\"}",
                    "{\"question_id\":93005,\"is_mastered\":true,"
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    400,
                    "question_id 参数错误",
                    "请先登录",
                    30),
            new RouteCase(
                    "user-checkin",
                    "POST",
                    "/api/user/checkin",
                    null,
                    null,
                    200,
                    "",
                    "请先登录",
                    10),
            new RouteCase(
                    "question-edit",
                    "PUT",
                    "/api/quiz/questions/93006",
                    "{\"content\":42}",
                    "{\"content\":\"Updated through real Tomcat\"}",
                    400,
                    "content 必须为字符串",
                    "请先登录",
                    10));

    @Container
    static final PostgreSQLContainer POSTGRES =
            Phase2PostgresContainers.reference18()
                    .withCopyFileToContainer(
                            MountableFile.forClasspathResource(
                                    "db/phase3/030-auth-schema.sql"),
                            "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                    .withCopyFileToContainer(
                            MountableFile.forClasspathResource(
                                    "db/phase4a/040-subject-catalog-schema.sql"),
                            "/docker-entrypoint-initdb.d/040-subject-catalog-schema.sql")
                    .withCopyFileToContainer(
                            MountableFile.forClasspathResource(
                                    "db/phase4c/080-transaction-write-http-schema.sql"),
                            "/docker-entrypoint-initdb.d/080-transaction-write-http-schema.sql")
                    .withCopyFileToContainer(
                            MountableFile.forClasspathResource(
                                    "db/phase4c/081-transaction-write-http-seed.sql"),
                            "/docker-entrypoint-initdb.d/081-transaction-write-http-seed.sql")
                    .withCopyFileToContainer(
                            MountableFile.forClasspathResource(
                                    "db/migration/V001__phase4c_transaction_write_idempotency.sql"),
                            "/docker-entrypoint-initdb.d/"
                                    + "090-phase4c-transaction-write-idempotency.sql");

    @Container
    static final RedisContainer REDIS =
            new RedisContainer(Phase2ContainerImages.redis7())
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
                () -> "ti-java:phase4c:transaction-write-http-sessions");
        registry.add(
                "ti.security.login-rate-limit.key-secret",
                () -> "phase4c-write-http-login-rate-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add(
                "ti.security.legacy-auth.accept-until",
                () -> CAPTURED_NOW.plus(Duration.ofDays(1)).toString());
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
        registry.add(
                "ti.security.transaction-write-rate-limit.namespace",
                () -> RATE_NAMESPACE);
        registry.add(
                "ti.security.transaction-write-rate-limit.multiplier",
                () -> "1");
        registry.add(
                "ti.security.transaction-write-rate-limit.key-secret",
                () -> "phase4c-write-http-rate-key-secret-0001");
        registry.add(
                "ti.security.transaction-write-cors.allowed-origins",
                () -> ALLOWED_ORIGIN);
        registry.add(
                "ti.learning.write-idempotency.key-secret",
                () -> "phase4c-write-http-learning-receipt-key-0001");
        registry.add(
                "ti.catalog.question-edit-idempotency.key-secret",
                () -> "phase4c-write-http-catalog-receipt-key-0001");
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
    TransactionWriteRateLimiter rateLimiter;

    @BeforeEach
    void resetDisposableState() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        resetDatabase();
    }

    @AfterEach
    void leaveRedisAvailable() throws Exception {
        var inspection = REDIS.getDockerClient()
                .inspectContainerCmd(REDIS.getContainerId())
                .exec();
        if (Boolean.TRUE.equals(inspection.getState().getPaused())) {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
        }
        awaitRedis();
    }

    @Test
    @Timeout(value = 90, unit = TimeUnit.SECONDS)
    void allNineWritesTraverseRealCredentialsTomcatApplicationsAndJdbc()
            throws Exception {
        assertThat(serverPort).isPositive();
        assertThat(applicationContext.getClass()
                        .getMethod("getWebServer")
                        .invoke(applicationContext)
                        .getClass()
                        .getName())
                .contains("TomcatWebServer");
        assertThat(AopProxyUtils.ultimateTargetClass(rateLimiter).getName())
                .isEqualTo(
                        "io.saksk.ti.web.security.RedisTransactionWriteRateLimiter");
        assertThat(POSTGRES.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.POSTGRES_18_REFERENCE);
        assertThat(jdbc.queryForObject("SHOW server_version", String.class))
                .isEqualTo("18.4");
        assertThat(REDIS.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.REDIS_7);

        RouteCase favoriteWeb = route("favorite-web-alias");
        HttpResponse<byte[]> flaskFavorite = exchange(
                favoriteWeb,
                favoriteWeb.successBody(),
                Map.of(
                        HttpHeaders.COOKIE,
                        "session=" + signedFlaskCookie("success-flask"),
                        "X-Requested-With",
                        "XMLHttpRequest",
                        "Idempotency-Key",
                        "success-favorite-web"),
                "phase4c-write-success-flask");
        assertSuccess(flaskFavorite, favoriteWeb);
        String targetCookie = targetSessionCookie(flaskFavorite);

        assertSuccess(exchange(
                route("favorite-quiz-api"),
                route("favorite-quiz-api").successBody(),
                targetHeaders(targetCookie, "success-favorite-api"),
                "phase4c-write-success-target-favorite"), route("favorite-quiz-api"));
        assertSuccess(exchange(
                route("record-result-web-alias"),
                route("record-result-web-alias").successBody(),
                targetHeaders(targetCookie, "success-record-web"),
                "phase4c-write-success-target-record"), route("record-result-web-alias"));
        assertSuccess(exchange(
                route("record-result-quiz-api"),
                route("record-result-quiz-api").successBody(),
                bearerHeaders(USER_BEARER, "success-record-api"),
                "phase4c-write-success-bearer-record"), route("record-result-quiz-api"));
        assertSuccess(exchange(
                route("study-learn-record"),
                route("study-learn-record").successBody(),
                bearerHeaders(USER_BEARER, "success-study-learn"),
                "phase4c-write-success-bearer-learn"), route("study-learn-record"));
        assertSuccess(exchange(
                route("study-review-record"),
                route("study-review-record").successBody(),
                targetHeaders(targetCookie, "success-study-review"),
                "phase4c-write-success-target-review"), route("study-review-record"));
        assertSuccess(exchange(
                route("study-review-master"),
                route("study-review-master").successBody(),
                bearerHeaders(USER_BEARER, "success-study-master"),
                "phase4c-write-success-bearer-master"), route("study-review-master"));
        assertSuccess(exchange(
                route("user-checkin"),
                null,
                targetHeaders(targetCookie, "success-checkin"),
                "phase4c-write-success-target-checkin"), route("user-checkin"));
        assertSuccess(exchange(
                route("question-edit"),
                route("question-edit").successBody(),
                bearerHeaders(ADMIN_BEARER, "success-question-edit"),
                "phase4c-write-success-admin-edit"), route("question-edit"));

        assertThat(count("favorites")).isEqualTo(2);
        assertThat(count("user_answers")).isEqualTo(2);
        assertThat(jdbc.queryForObject(
                "SELECT wrong_count FROM mistakes "
                        + "WHERE user_id = ? AND question_id = ?",
                Integer.class,
                USER_ID,
                93_002)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "SELECT streak FROM study_learning "
                        + "WHERE user_id = ? AND question_id = ?",
                Integer.class,
                USER_ID,
                93_003)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "SELECT review_level FROM study_review "
                        + "WHERE user_id = ? AND question_id = ?",
                Integer.class,
                USER_ID,
                93_004)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "SELECT is_mastered FROM study_review "
                        + "WHERE user_id = ? AND question_id = ?",
                Boolean.class,
                USER_ID,
                93_005)).isTrue();
        assertThat(count("user_checkins")).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "SELECT content FROM questions WHERE id = 93006",
                String.class)).isEqualTo("Updated through real Tomcat");
        assertThat(count("learning_idempotency_receipts")).isEqualTo(8);
        assertThat(count("catalog_question_edit_commands")).isEqualTo(1);
        assertIdentityWasNeverWritten();
    }

    @Test
    @Timeout(value = 90, unit = TimeUnit.SECONDS)
    void allFortyFiveCredentialAndSafetyDispositionsUseTheRealFilterChain()
            throws Exception {
        String targetCookie = bootstrapTargetSession();
        for (RouteCase route : ROUTES) {
            for (CredentialMode mode : CredentialMode.values()) {
                if (route.operationId().equals("user-checkin")) {
                    jdbc.update(
                            "DELETE FROM user_checkins WHERE user_id = ?",
                            USER_ID);
                }
                String before = databaseFingerprint();
                String requestId = "phase4c-write-auth-"
                        + route.operationId() + "-" + mode.wireName();
                HttpResponse<byte[]> response = exchange(
                        route,
                        route.invalidBody(),
                        mode.headers(targetCookie),
                        requestId);
                JsonNode body = json.readTree(response.body());

                int expectedStatus = mode.reachesController()
                        ? route.validationStatus()
                        : mode == CredentialMode.TARGET_NO_XHR
                                ? 403
                                : 401;
                String expectedMessage = mode.reachesController()
                        ? route.validationMessage()
                        : mode == CredentialMode.TARGET_NO_XHR
                                ? "请求被拒绝（缺少安全标头）"
                                : route.authenticationMessage();
                assertThat(response.statusCode())
                        .as(route.operationId() + " " + mode)
                        .isEqualTo(expectedStatus);
                assertThat(body.path("message").asString())
                        .as(route.operationId() + " " + mode)
                        .isEqualTo(expectedMessage);
                assertCommonHeaders(response, requestId);
                assertRateHeaders(response, route.limit());

                if (route.operationId().equals("user-checkin")
                        && mode.reachesController()) {
                    assertThat(count("user_checkins")).isEqualTo(1);
                    assertThat(databaseFingerprint()).isNotEqualTo(before);
                } else {
                    assertThat(databaseFingerprint())
                            .as(route.operationId() + " " + mode)
                            .isEqualTo(before);
                }
            }
        }
        assertIdentityWasNeverWritten();
    }

    @Test
    @Timeout(value = 90, unit = TimeUnit.SECONDS)
    void preflightRateExhaustionAndRealRedisOutageKeepCompleteNetworkHeaders()
            throws Exception {
        for (RouteCase route : ROUTES) {
            String requestId = "phase4c-write-preflight-" + route.operationId();
            HttpResponse<byte[]> response = preflight(route, requestId, ALLOWED_ORIGIN);
            assertThat(response.statusCode()).as(route.operationId()).isEqualTo(204);
            assertThat(response.body()).isEmpty();
            assertThat(response.headers().firstValue(
                    HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                    .contains(ALLOWED_ORIGIN);
            assertThat(response.headers().firstValue(
                    HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS))
                    .contains(route.method() + ", OPTIONS");
            assertNoRateHeaders(response);
        }

        HttpResponse<byte[]> rejectedOrigin = preflight(
                route("question-edit"),
                "phase4c-write-preflight-rejected",
                "https://evil.example");
        assertThat(rejectedOrigin.statusCode()).isEqualTo(403);
        assertThat(rejectedOrigin.body()).isEmpty();
        assertThat(rejectedOrigin.headers().allValues(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEmpty();

        RouteCase edit = route("question-edit");
        for (int attempt = 0; attempt < edit.limit(); attempt++) {
            HttpResponse<byte[]> response = exchange(
                    edit,
                    edit.invalidBody(),
                    bearerHeaders(ADMIN_BEARER, null),
                    "phase4c-write-rate-warmup-" + attempt);
            assertThat(response.statusCode()).isEqualTo(400);
        }
        HttpResponse<byte[]> limited = exchange(
                edit,
                edit.invalidBody(),
                bearerHeaders(ADMIN_BEARER, null),
                "phase4c-write-rate-limited");
        assertThat(limited.statusCode()).isEqualTo(429);
        assertThat(json.readTree(limited.body()).path("message").asString())
                .isEqualTo("10 per 1 minute");
        assertCommonHeaders(limited, "phase4c-write-rate-limited");
        assertRateHeaders(limited, 10);
        assertThat(limited.headers().firstValue("X-RateLimit-Remaining"))
                .contains("0");

        REDIS.getDockerClient().pauseContainerCmd(REDIS.getContainerId()).exec();
        HttpResponse<byte[]> unavailable;
        try {
            unavailable = exchange(
                    route("favorite-quiz-api"),
                    route("favorite-quiz-api").invalidBody(),
                    bearerHeaders(USER_BEARER, null),
                    "phase4c-write-redis-unavailable");
        } finally {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
            awaitRedis();
        }
        assertThat(unavailable.statusCode()).isEqualTo(503);
        JsonNode unavailableBody = json.readTree(unavailable.body());
        assertThat(unavailableBody.path("message").asString())
                .isEqualTo("服务暂时不可用");
        assertThat(unavailableBody.toString())
                .doesNotContain("Redis", "Lettuce", REDIS_PASSWORD);
        assertCommonHeaders(unavailable, "phase4c-write-redis-unavailable");
        assertNoRateHeaders(unavailable);
        assertIdentityWasNeverWritten();
    }

    private String bootstrapTargetSession() throws Exception {
        RouteCase favorite = route("favorite-web-alias");
        HttpResponse<byte[]> response = exchange(
                favorite,
                favorite.invalidBody(),
                Map.of(
                        HttpHeaders.COOKIE,
                        "session=" + signedFlaskCookie("auth-matrix-bootstrap"),
                        "X-Requested-With",
                        "XMLHttpRequest"),
                "phase4c-write-auth-bootstrap");
        assertThat(response.statusCode()).isEqualTo(400);
        return targetSessionCookie(response);
    }

    private HttpResponse<byte[]> preflight(
            RouteCase route,
            String requestId,
            String origin
    ) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(
                        URI.create("http://127.0.0.1:" + serverPort + route.path()))
                .timeout(Duration.ofSeconds(10))
                .header("Accept-Encoding", "identity")
                .header("X-Request-ID", requestId)
                .header(HttpHeaders.ORIGIN, origin)
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, route.method())
                .header(
                        HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                        "Content-Type, Authorization, Idempotency-Key, X-Requested-With")
                .method("OPTIONS", HttpRequest.BodyPublishers.noBody())
                .build();
        return HTTP.send(request, HttpResponse.BodyHandlers.ofByteArray());
    }

    private HttpResponse<byte[]> exchange(
            RouteCase route,
            String body,
            Map<String, String> additions,
            String requestId
    ) throws Exception {
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8);
        HttpRequest.Builder request = HttpRequest.newBuilder(
                        URI.create("http://127.0.0.1:" + serverPort + route.path()))
                .timeout(Duration.ofSeconds(10))
                .header("Accept-Encoding", "identity")
                .header(HttpHeaders.ACCEPT, "application/json")
                .header(HttpHeaders.CONTENT_TYPE, "application/json")
                .header(HttpHeaders.ORIGIN, ALLOWED_ORIGIN)
                .header("X-Request-ID", requestId)
                .method(route.method(), publisher);
        additions.forEach((name, value) -> {
            if (value != null) {
                request.header(name, value);
            }
        });
        return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private void assertSuccess(HttpResponse<byte[]> response, RouteCase route)
            throws Exception {
        assertThat(response.statusCode()).as(route.operationId()).isEqualTo(200);
        assertThat(json.readTree(response.body()).path("status").asString())
                .isEqualTo("success");
        String requestId = json.readTree(response.body()).path("request_id").asString();
        assertThat(requestId).isNotBlank();
        assertCommonHeaders(response, requestId);
        assertRateHeaders(response, route.limit());
    }

    private static void assertCommonHeaders(
            HttpResponse<byte[]> response,
            String requestId
    ) {
        assertThat(response.version()).isEqualTo(HttpClient.Version.HTTP_1_1);
        assertThat(response.headers().firstValue(HttpHeaders.CONTENT_TYPE))
                .hasValueSatisfying(value -> assertThat(value)
                        .startsWith("application/json"));
        assertThat(response.headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .contains(ALLOWED_ORIGIN);
        assertThat(varyTokens(response)).containsExactlyInAnyOrder(
                "Origin",
                "Cookie");
        assertThat(response.headers().firstValue("X-Content-Type-Options"))
                .contains("nosniff");
        assertThat(response.headers().firstValue("X-Frame-Options"))
                .contains("SAMEORIGIN");
        assertThat(response.headers().firstValue("Referrer-Policy"))
                .contains("strict-origin-when-cross-origin");
        assertThat(response.headers().firstValue("X-Request-ID"))
                .contains(requestId);
    }

    private static void assertRateHeaders(
            HttpResponse<byte[]> response,
            int limit
    ) {
        assertThat(response.headers().firstValue("X-RateLimit-Limit"))
                .contains(Integer.toString(limit));
        assertThat(response.headers().firstValue("X-RateLimit-Remaining"))
                .isPresent();
        assertThat(response.headers().firstValue("X-RateLimit-Reset"))
                .isPresent();
        assertThat(response.headers().firstValue(HttpHeaders.RETRY_AFTER))
                .isPresent();
    }

    private static void assertNoRateHeaders(HttpResponse<byte[]> response) {
        for (String name : List.of(
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                HttpHeaders.RETRY_AFTER)) {
            assertThat(response.headers().allValues(name)).as(name).isEmpty();
        }
    }

    private static List<String> varyTokens(HttpResponse<byte[]> response) {
        return response.headers().allValues(HttpHeaders.VARY).stream()
                .flatMap(value -> Arrays.stream(value.split(",\\s*")))
                .toList();
    }

    private static Map<String, String> targetHeaders(
            String targetCookie,
            String idempotencyKey
    ) {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put(HttpHeaders.COOKIE, targetCookie);
        headers.put("X-Requested-With", "XMLHttpRequest");
        if (idempotencyKey != null) {
            headers.put("Idempotency-Key", idempotencyKey);
        }
        return Map.copyOf(headers);
    }

    private static Map<String, String> bearerHeaders(
            String token,
            String idempotencyKey
    ) {
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put(HttpHeaders.AUTHORIZATION, "Bearer " + token);
        if (idempotencyKey != null) {
            headers.put("Idempotency-Key", idempotencyKey);
        }
        return Map.copyOf(headers);
    }

    private static String targetSessionCookie(HttpResponse<byte[]> response) {
        String setCookie = response.headers().allValues(HttpHeaders.SET_COOKIE).stream()
                .filter(value -> value.startsWith("ti_dev_session="))
                .findFirst()
                .orElseThrow(() -> new AssertionError(
                        "Flask Session exchange did not issue target Session"));
        return setCookie.substring(0, setCookie.indexOf(';'));
    }

    private RouteCase route(String operationId) {
        return ROUTES.stream()
                .filter(route -> route.operationId().equals(operationId))
                .findFirst()
                .orElseThrow();
    }

    private void resetDatabase() {
        jdbc.execute("""
                TRUNCATE TABLE
                    identity_write_audit,
                    catalog_question_edit_commands,
                    learning_idempotency_receipts,
                    user_checkins,
                    study_review,
                    study_learning,
                    user_answers,
                    user_quiz_stats,
                    mistakes,
                    favorites,
                    user_subjects,
                    questions,
                    system_config,
                    users
                RESTART IDENTITY CASCADE
                """);
        jdbc.update("""
                INSERT INTO users (
                    id, username, password_hash, is_admin, is_locked,
                    session_version, is_subject_admin, is_notification_admin,
                    has_password_set, last_active
                ) VALUES
                    (?, ?, ?, false, false, ?, false, false, true, ?),
                    (?, ?, ?, true, false, ?, false, false, true, ?)
                """,
                USER_ID,
                USERNAME,
                "unused-test-password-hash",
                USER_SESSION_VERSION,
                java.sql.Timestamp.valueOf("2026-01-01 00:00:00"),
                ADMIN_ID,
                "phase4c_write_admin",
                "unused-test-password-hash",
                ADMIN_SESSION_VERSION,
                java.sql.Timestamp.valueOf("2026-01-02 00:00:00"));
        jdbc.update("""
                INSERT INTO questions (
                    id, subject_id, type, content, options, answer, analysis,
                    tags, difficulty, source, created_by, updated_by
                )
                SELECT
                    question_id,
                    1,
                    'single_choice',
                    'Phase 4C transaction-write question ' || question_id,
                    '[{"key":"A","value":"Alpha"},{"key":"B","value":"Beta"}]',
                    '["A"]',
                    'Phase 4C transaction-write explanation',
                    '[]',
                    1,
                    'phase4c-http-fixture',
                    ?,
                    ?
                FROM generate_series(93001, 93008) AS question_id
                """,
                ADMIN_ID,
                ADMIN_ID);
    }

    private long count(String table) {
        if (!Set.of(
                        "favorites",
                        "user_answers",
                        "user_checkins",
                        "learning_idempotency_receipts",
                        "catalog_question_edit_commands")
                .contains(table)) {
            throw new IllegalArgumentException("Unapproved count table");
        }
        return jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Long.class);
    }

    private void assertIdentityWasNeverWritten() {
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM identity_write_audit",
                Long.class)).isZero();
        assertThat(jdbc.queryForList(
                "SELECT id, last_active FROM users ORDER BY id"))
                .extracting(row -> row.get("last_active"))
                .containsExactly(
                        java.sql.Timestamp.valueOf("2026-01-01 00:00:00"),
                        java.sql.Timestamp.valueOf("2026-01-02 00:00:00"));
    }

    private String databaseFingerprint() {
        List<String> projections = new ArrayList<>();
        projections.add(jsonRows("users", "id"));
        projections.add(jsonRows("system_config", "id"));
        projections.add(jsonRows("questions", "id"));
        projections.add(jsonRows("favorites", "id"));
        projections.add(jsonRows("mistakes", "id"));
        projections.add(jsonRows("user_answers", "id"));
        projections.add(jsonRows("user_quiz_stats", "id"));
        projections.add(jsonRows("study_learning", "id"));
        projections.add(jsonRows("study_review", "id"));
        projections.add(jsonRows("user_checkins", "id"));
        projections.add(jsonRows(
                "learning_idempotency_receipts",
                "actor_id, operation, key_hmac"));
        projections.add(jsonRows(
                "catalog_question_edit_commands",
                "actor_id, key_hmac"));
        projections.add(jsonRows("identity_write_audit", "id"));
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (String projection : projections) {
                digest.update(projection.getBytes(StandardCharsets.UTF_8));
                digest.update((byte) 0);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (NoSuchAlgorithmException exception) {
            throw new AssertionError(exception);
        }
    }

    private String jsonRows(String table, String orderBy) {
        if (!Set.of(
                        "users",
                        "system_config",
                        "questions",
                        "favorites",
                        "mistakes",
                        "user_answers",
                        "user_quiz_stats",
                        "study_learning",
                        "study_review",
                        "user_checkins",
                        "learning_idempotency_receipts",
                        "catalog_question_edit_commands",
                        "identity_write_audit")
                .contains(table)) {
            throw new IllegalArgumentException("Unapproved fingerprint table");
        }
        return jdbc.queryForObject(
                "SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]'::jsonb)::text "
                        + "FROM (SELECT * FROM " + table + " ORDER BY " + orderBy + ") t",
                String.class);
    }

    private void awaitRedis() throws Exception {
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
        throw new IllegalStateException("Redis did not recover", lastFailure);
    }

    private static String signedBearer(
            long identityId,
            int sessionVersion
    ) {
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + identityId
                + ",\"openid\":\"\",\"session_version\":" + sessionVersion
                + ",\"exp\":" + CREDENTIAL_EXPIRES_AT.getEpochSecond()
                + ",\"iat\":" + CAPTURED_NOW.getEpochSecond()
                + ",\"jti\":\"" + String.format("%032x", identityId) + "\"}";
        String unsigned = base64Url(header) + "." + base64Url(payload);
        return unsigned + "." + encode(hmac(
                "HmacSHA256",
                LEGACY_SECRET_BYTES,
                unsigned.getBytes(StandardCharsets.US_ASCII)));
    }

    private static String signedFlaskCookie(String nonce) {
        String payload = "{\"_permanent\":true,\"user_id\":" + USER_ID
                + ",\"username\":\"" + USERNAME + "\""
                + ",\"session_version\":" + USER_SESSION_VERSION
                + ",\"remember\":true,\"csrf_token\":\"" + nonce + "\"}";
        String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
        String encodedTimestamp = encode(minimalBigEndian(
                CAPTURED_NOW.getEpochSecond()));
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

    private enum CredentialMode {
        TARGET_XHR("session-xhr", true),
        BEARER("bearer", true),
        TARGET_NO_XHR("session-no-xhr", false),
        ANONYMOUS_XHR("anonymous-xhr", false),
        INVALID_BEARER_XHR("invalid-bearer-xhr", false);

        private final String wireName;
        private final boolean reachesController;

        CredentialMode(String wireName, boolean reachesController) {
            this.wireName = wireName;
            this.reachesController = reachesController;
        }

        String wireName() {
            return wireName;
        }

        boolean reachesController() {
            return reachesController;
        }

        Map<String, String> headers(String targetCookie) {
            return switch (this) {
                case TARGET_XHR -> Map.of(
                        HttpHeaders.COOKIE,
                        targetCookie,
                        "X-Requested-With",
                        "XMLHttpRequest");
                case BEARER -> Map.of(
                        HttpHeaders.AUTHORIZATION,
                        "Bearer " + USER_BEARER);
                case TARGET_NO_XHR -> Map.of(
                        HttpHeaders.COOKIE,
                        targetCookie);
                case ANONYMOUS_XHR -> Map.of(
                        "X-Requested-With",
                        "XMLHttpRequest");
                case INVALID_BEARER_XHR -> Map.of(
                        HttpHeaders.AUTHORIZATION,
                        "Bearer invalid-phase4c-write-token",
                        "X-Requested-With",
                        "XMLHttpRequest");
            };
        }
    }

    private record RouteCase(
            String operationId,
            String method,
            String path,
            String invalidBody,
            String successBody,
            int validationStatus,
            String validationMessage,
            String authenticationMessage,
            int limit
    ) {
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedEvidenceClock {

        @Bean
        @Primary
        Clock transactionWriteEvidenceClock() {
            return Clock.fixed(CAPTURED_NOW, ZoneOffset.UTC);
        }
    }
}
