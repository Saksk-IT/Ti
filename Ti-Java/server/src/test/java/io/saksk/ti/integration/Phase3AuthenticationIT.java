package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasItem;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.cookie;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.web.security.LoginRateLimiter;
import io.saksk.ti.web.security.LegacySessionExchangeGuard;
import io.saksk.ti.web.security.TargetSessionRegistry;
import jakarta.servlet.http.Cookie;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import java.util.stream.Collectors;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.session.SessionRepository;
import org.springframework.session.data.redis.RedisSessionRepository;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.ObjectMapper;

@Testcontainers
@ActiveProfiles("test")
@AutoConfigureMockMvc
@SpringBootTest(classes = TiApplication.class, webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(Phase3AuthenticationIT.FixedAuthenticationClock.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Sql(scripts = "classpath:db/phase3/031-auth-seed.sql",
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class Phase3AuthenticationIT {

    private static final String REDIS_PASSWORD = "phase3-ephemeral-redis";
    private static final String LEGACY_PASSWORD = "PUBLIC-TEST-ONLY-Passw0rd!";
    private static final String LEGACY_HASH =
            "scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c";
    private static final Instant FIXED_NOW = Instant.now();
    private static final Instant CREDENTIAL_EXPIRES_AT = FIXED_NOW.plus(Duration.ofHours(1));

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.reference18()
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                    "/docker-entrypoint-initdb.d/030-auth-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/031-auth-seed.sql"),
                    "/docker-entrypoint-initdb.d/031-auth-seed.sql");

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
        registry.add("spring.session.data.redis.namespace", () -> "ti-java:identity:sessions");
        registry.add("ti.security.login-rate-limit.requests-per-minute", () -> "5");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase3-test-only-login-rate-key-secret-0001");
        registry.add("ti.security.target-session-limit.max-total-sessions", () -> "3");
        registry.add("ti.security.legacy-session-exchange.max-replay-markers", () -> "3");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add(
                "ti.security.legacy-auth.accept-until",
                () -> FIXED_NOW.plus(Duration.ofDays(1)).toString());
        registry.add("ti.security.legacy-auth.secret",
                () -> "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper objectMapper;

    @LocalServerPort
    int serverPort;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    LoginRateLimiter loginRateLimiter;

    @Autowired
    LegacySessionExchangeGuard legacySessionExchangeGuard;

    @Autowired
    TargetSessionRegistry targetSessionRegistry;

    @Autowired
    SessionRepository<?> sessionRepository;

    @BeforeEach
    void clearRedis() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @Test
    void springBootUsesTheExplicitNonIndexedRedisSessionRepository() {
        assertThat(sessionRepository).isInstanceOf(RedisSessionRepository.class);
    }

    @Test
    void publicLoginMethodsGoldenReadIsExactAndHasNoDatabaseOrRedisSideEffect() throws Exception {
        List<Map<String, Object>> databaseBefore = databaseFingerprint();
        assertThat(redis.keys("*")).isEmpty();

        HttpResponse<byte[]> response = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create(
                                "http://127.0.0.1:" + serverPort + "/api/auth/login-methods"))
                        .header("Accept-Encoding", "identity")
                        .header("User-Agent", "Ti-Java-READ_COMPARE/1")
                        .header("X-Request-ID", "phase3-login-methods-read-001")
                        .GET()
                        .build(),
                HttpResponse.BodyHandlers.ofByteArray());

        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(response.headers().allValues("Content-Type"))
                .containsExactly("application/json;charset=utf-8");
        assertThat(response.headers().allValues("Vary")).containsExactly("Origin, Cookie");
        assertThat(response.headers().allValues("X-Content-Type-Options")).containsExactly("nosniff");
        assertThat(response.headers().allValues("X-Frame-Options")).containsExactly("SAMEORIGIN");
        assertThat(response.headers().allValues("X-Request-ID"))
                .containsExactly("phase3-login-methods-read-001");
        assertThat(response.headers().firstValue("Cache-Control")).isEmpty();
        assertThat(response.headers().firstValue("Content-Encoding")).isEmpty();
        assertThat(response.headers().firstValue("Content-Language")).isEmpty();
        assertThat(response.headers().firstValue("ETag")).isEmpty();
        assertThat(response.headers().firstValue("Last-Modified")).isEmpty();
        assertThat(response.headers().firstValue("Pragma")).isEmpty();
        assertThat(response.headers().firstValue("Expires")).isEmpty();

        Map<?, ?> envelope = objectMapper.readValue(
                response.body(), Map.class);
        assertThat(envelope.keySet().stream().map(String::valueOf).toList())
                .containsExactlyInAnyOrder(
                "status", "code", "data", "request_id", "message");
        assertThat(envelope.get("status")).isEqualTo("success");
        assertThat(envelope.get("code")).isEqualTo(0);
        assertThat(envelope.get("request_id")).isEqualTo("phase3-login-methods-read-001");
        assertThat(envelope.get("message")).isEqualTo("");
        Map<?, ?> data = (Map<?, ?>) envelope.get("data");
        assertThat(data.keySet().stream()
                .map(String::valueOf)
                .toList()).containsExactlyInAnyOrder(
                "phone_login_enabled", "wechat_login_enabled", "default_mode");
        assertThat(data.get("phone_login_enabled")).isEqualTo(false);
        assertThat(data.get("wechat_login_enabled")).isEqualTo(true);
        assertThat(data.get("default_mode")).isEqualTo("qr");

        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
        assertThat(redis.keys("*")).isEmpty();
    }

    @Test
    void csrfProtectedLegacyLoginUpgradesHashAndPersistsOnlySafeTargetSessionScalars()
            throws Exception {
        Csrf csrf = obtainCsrf();

        MvcResult login = mockMvc.perform(post("/api/login")
                        .cookie(csrf.cookie(), csrf.sessionCookie())
                        .header(csrf.headerName(), csrf.token())
                        .header("X-Request-ID", "phase3-login-write")
                        .contentType("application/json")
                        .content("""
                                {"username":"phase3@example.test",
                                 "password":"PUBLIC-TEST-ONLY-Passw0rd!",
                                 "remember":true,"redirect":"/practice"}
                                """))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json;charset=UTF-8"))
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "ti_dev_session="))))
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "Max-Age=604800"))))
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "session=;"))))
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "ti_dev_csrf=;"))))
                .andExpect(jsonPath("$.status").value("success"))
                .andExpect(jsonPath("$.redirect").value("/practice"))
                .andExpect(jsonPath("$.remember").value(true))
                .andExpect(jsonPath("$.needs_password_set").value(false))
                .andExpect(jsonPath("$.request_id").value("phase3-login-write"))
                .andReturn();

        Map<String, Object> user = jdbc.queryForMap("""
                SELECT password_hash, has_password_set, session_version, last_active
                FROM users
                WHERE id = 1
                """);
        assertThat(user.get("password_hash").toString())
                .isEqualTo(LEGACY_HASH)
                .startsWith("scrypt:32768:8:1$")
                .doesNotContain("{scrypt@");
        assertThat(user.get("has_password_set")).isEqualTo(true);
        assertThat(user.get("session_version")).isEqualTo(7);
        assertThat(user.get("last_active")).isNull();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM users", Integer.class)).isEqualTo(5);

        Set<String> allKeys = redis.keys("*");
        Set<String> sessionKeys = allKeys.stream()
                .filter(key -> key.contains("identity:sessions"))
                .collect(Collectors.toSet());
        assertThat(sessionKeys).as("all Redis keys: %s", allKeys).hasSize(1);
        Map<String, String> attributes = rawSessionAttributes(sessionKeys.iterator().next());
        assertThat(attributes)
                .containsEntry("sessionAttr:identity_id", "l:1")
                .containsEntry("sessionAttr:session_version", "i:7")
                .containsEntry("sessionAttr:remember", "b:1")
                .containsKey("sessionAttr:authenticated_at");
        assertThat(attributes.keySet())
                .doesNotContain(
                        "sessionAttr:is_admin",
                        "sessionAttr:username",
                        "sessionAttr:openid",
                        "sessionAttr:csrf_token");
        assertThat(attributes.values()).allSatisfy(value -> assertThat(value)
                .doesNotContain("rO0AB", "java.", "PUBLIC-TEST-ONLY", "phase3@example.test"));

        assertThat(login.getResponse().getHeaders("Set-Cookie"))
                .noneSatisfy(value -> assertThat(value).contains(LEGACY_PASSWORD));

        mockMvc.perform(post("/api/login")
                        .cookie(csrf.cookie(), csrf.sessionCookie())
                        .header(csrf.headerName(), csrf.token())
                        .contentType("application/json")
                        .content("{\"username\":\"phase3@example.test\",\"password\":\"x\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error.code").value("FORBIDDEN"));

        Cookie authenticatedSession = login.getResponse().getCookie("ti_dev_session");
        assertThat(authenticatedSession).isNotNull();
        MvcResult refreshed = mockMvc.perform(get("/api/csrf").cookie(authenticatedSession))
                .andExpect(status().isOk())
                .andExpect(cookie().exists("ti_dev_csrf"))
                .andReturn();
        String refreshedToken = objectMapper.readTree(refreshed.getResponse().getContentAsByteArray())
                .path("token")
                .stringValue();
        assertThat(refreshedToken).isNotEqualTo(csrf.token());
        assertThat(rawSessionAttributes(sessionKeys.iterator().next()))
                .containsEntry("sessionAttr:csrf_token", "s:" + refreshedToken);
    }

    @Test
    void missingCsrfAndInvalidLockedOrDuplicateCredentialsFailClosedWithoutDatabaseMutation()
            throws Exception {
        mockMvc.perform(post("/api/login")
                        .contentType("application/json")
                        .content("{\"username\":\"phase3@example.test\",\"password\":\"x\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error.code").value("FORBIDDEN"));

        Csrf csrf = obtainCsrf();
        performLogin(csrf, "phase3@example.test", "wrong")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("账号或密码错误"));
        performLogin(csrf, "locked@example.test", LEGACY_PASSWORD)
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("账户已被锁定，请联系管理员"));
        performLogin(csrf, "duplicate@example.test", LEGACY_PASSWORD)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("账号或密码错误"));

        assertThat(jdbc.queryForObject(
                "SELECT password_hash FROM users WHERE id = 1", String.class)).isEqualTo(LEGACY_HASH);
        assertThat(jdbc.queryForObject(
                "SELECT has_password_set FROM users WHERE id = 1", Boolean.class)).isFalse();
        Set<String> anonymousSessionKeys = redis.keys("*").stream()
                .filter(key -> key.contains("identity:sessions"))
                .collect(Collectors.toSet());
        assertThat(anonymousSessionKeys).isNotEmpty().allSatisfy(key ->
                assertThat(rawSessionAttributes(key)).doesNotContainKeys(
                        "sessionAttr:identity_id",
                        "sessionAttr:session_version",
                        "sessionAttr:authenticated_at",
                        "sessionAttr:remember"));
    }

    @Test
    void legacyJwtIsRequestScopedWhileFlaskCookieExchangesForAnAuthoritativeTargetSession()
            throws Exception {
        String token = legacyVectors().path("jwt").path("token").stringValue();
        MvcResult jwt = mockMvc.perform(get("/api/auth/login-methods")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn();
        assertThat(jwt.getResponse().getCookie("ti_dev_session")).isNull();
        assertThat(redis.keys("*"))
                .noneMatch(key -> key.contains("identity:sessions"));

        String flaskCookie = legacyVectors()
                .path("flask_sessions")
                .get(1)
                .path("cookie")
                .stringValue();
        MvcResult exchanged = mockMvc.perform(get("/api/auth/login-methods")
                        .cookie(new Cookie("session", flaskCookie)))
                .andExpect(status().isOk())
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "session=;"))))
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "Max-Age=604800"))))
                .andReturn();

        Cookie target = exchanged.getResponse().getCookie("ti_dev_session");
        assertThat(target).isNotNull();
        Set<String> sessionKeys = redis.keys("*").stream()
                .filter(key -> key.contains("identity:sessions"))
                .collect(Collectors.toSet());
        assertThat(sessionKeys).hasSize(1);
        assertThat(rawSessionAttributes(sessionKeys.iterator().next()))
                .containsEntry("sessionAttr:identity_id", "l:4242")
                .containsEntry("sessionAttr:session_version", "i:7")
                .containsEntry("sessionAttr:remember", "b:1")
                .doesNotContainKeys(
                        "sessionAttr:username",
                        "sessionAttr:is_admin",
                        "sessionAttr:is_subject_admin",
                        "sessionAttr:csrf_token");

        MvcResult replay = mockMvc.perform(get("/api/auth/login-methods")
                        .cookie(new Cookie("session", flaskCookie)))
                .andExpect(status().isOk())
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "session=;"))))
                .andReturn();
        assertThat(replay.getResponse().getCookie("ti_dev_session")).isNull();
        for (int index = 0; index < 8; index++) {
            mockMvc.perform(get("/api/auth/login-methods")
                            .cookie(new Cookie("session", flaskCookie)))
                    .andExpect(status().isOk());
        }
        mockMvc.perform(get("/api/auth/login-methods")
                        .cookie(new Cookie("session", flaskCookie)))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0"));
        assertThat(redis.keys("*").stream()
                        .filter(key -> key.contains("identity:sessions")))
                .hasSize(1);
        assertThat(redis.keys("ti-java:identity:legacy-session-exchange:*")).hasSize(5);

        jdbc.update("UPDATE users SET session_version = 8 WHERE id = 4242");
        mockMvc.perform(get("/api/auth/login-methods").cookie(target))
                .andExpect(status().isOk())
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "ti_dev_session=;"))));
        assertThat(redis.keys("*"))
                .noneMatch(key -> key.contains("identity:sessions"));
    }

    @Test
    void invalidLegacyCookiesArePreflightLimitedWithoutCreatingReplayMarkersOrSessions()
            throws Exception {
        for (int index = 0; index < 10; index++) {
            mockMvc.perform(get("/api/auth/login-methods")
                            .cookie(new Cookie("session", "invalid-cookie-" + index)))
                    .andExpect(status().isOk());
        }
        mockMvc.perform(get("/api/auth/login-methods")
                        .cookie(new Cookie("session", "invalid-cookie-over-limit")))
                .andExpect(status().isTooManyRequests());

        assertThat(redis.keys("ti-java:identity:legacy-session-exchange:*")).hasSize(2)
                .noneMatch(key -> key.contains(":credential:"));
        assertThat(redis.keys("*")).noneMatch(key -> key.contains("identity:sessions"));
    }

    @Test
    void oversizedLoginBodyIsRejectedBeforeCsrfOrJsonCanAllocateAnUnboundedTree()
            throws Exception {
        mockMvc.perform(post("/api/login")
                        .contentType("application/json")
                        .content(new byte[16 * 1_024 + 1]))
                .andExpect(status().isContentTooLarge())
                .andExpect(jsonPath("$.error.code").value("PAYLOAD_TOO_LARGE"));

        assertThat(redis.keys("*")).noneMatch(key -> key.contains("identity:sessions"));
    }

    @Test
    void passwordAndLegacyIssuanceShareAThreeSessionHardCapWithSlidingRememberCookie()
            throws Exception {
        List<Cookie> issued = new ArrayList<>();
        for (int index = 0; index < 5; index++) {
            Csrf csrf = obtainCsrf();
            MvcResult login = mockMvc.perform(post("/api/login")
                            .cookie(csrf.cookie(), csrf.sessionCookie())
                            .header(csrf.headerName(), csrf.token())
                            .contentType("application/json")
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "username", "phase3@example.test",
                                    "password", LEGACY_PASSWORD,
                                    "remember", true))))
                    .andExpect(status().isOk())
                    .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                            "Max-Age=604800"))))
                    .andReturn();
            Cookie session = login.getResponse().getCookie("ti_dev_session");
            assertThat(session).isNotNull();
            issued.add(session);
        }

        Set<String> sessionKeys = redis.keys("*identity:sessions*");
        assertThat(sessionKeys).hasSize(3);
        Set<String> registryKeys = redis.keys("ti-java:identity:target-session-index:*");
        assertThat(registryKeys).hasSize(5);
        String indexKey = registryKeys.stream()
                .filter(key -> key.contains(":{") && key.endsWith(":sessions"))
                .findFirst()
                .orElseThrow();
        assertThat(redis.opsForZSet().size(indexKey)).isEqualTo(3);

        mockMvc.perform(get("/api/auth/login-methods").cookie(issued.get(0)))
                .andExpect(status().isOk());
        mockMvc.perform(get("/api/auth/login-methods").cookie(issued.get(1)))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/auth/login-methods").cookie(issued.get(4)))
                .andExpect(status().isOk())
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "Max-Age=604800"))));
        assertThat(redis.keys("*identity:sessions*")).hasSize(3);
    }

    @Test
    void oneLegacyExchangeAndThreePasswordLoginsShareTheSameIdentitySessionIndex()
            throws Exception {
        String flaskCookie = legacyVectors()
                .path("flask_sessions")
                .get(1)
                .path("cookie")
                .stringValue();
        MvcResult exchanged = mockMvc.perform(get("/api/auth/login-methods")
                        .cookie(new Cookie("session", flaskCookie)))
                .andExpect(status().isOk())
                .andReturn();
        Cookie legacyTarget = exchanged.getResponse().getCookie("ti_dev_session");
        assertThat(legacyTarget).isNotNull();

        List<Cookie> passwordTargets = new ArrayList<>();
        for (int index = 0; index < 3; index++) {
            Csrf csrf = obtainCsrf();
            MvcResult login = mockMvc.perform(post("/api/login")
                            .cookie(csrf.cookie(), csrf.sessionCookie())
                            .header(csrf.headerName(), csrf.token())
                            .contentType("application/json")
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "username", "legacy-vector@example.test",
                                    "password", LEGACY_PASSWORD,
                                    "remember", true))))
                    .andExpect(status().isOk())
                    .andReturn();
            passwordTargets.add(login.getResponse().getCookie("ti_dev_session"));
        }

        assertThat(redis.keys("*identity:sessions*")).hasSize(3);
        Set<String> indexKeys = redis.keys("ti-java:identity:target-session-index:*");
        assertThat(indexKeys).hasSize(5);
        assertThat(redis.opsForZSet().size(indexKeys.stream()
                .filter(key -> key.contains(":{") && key.endsWith(":sessions"))
                .findFirst()
                .orElseThrow())).isEqualTo(3);

        mockMvc.perform(get("/api/auth/login-methods").cookie(legacyTarget))
                .andExpect(status().isOk());
        assertThat(redis.keys("*identity:sessions*")).hasSize(3);
        mockMvc.perform(get("/api/auth/login-methods").cookie(passwordTargets.getLast()))
                .andExpect(status().isOk())
                .andExpect(header().stringValues("Set-Cookie", hasItem(containsString(
                        "Max-Age=604800"))));
    }

    @Test
    void targetSessionRegistryIsAtomicUnderConcurrencyAndRecoversItsSequenceKey() {
        List<List<String>> evictionBatches = IntStream.range(0, 100)
                .parallel()
                .mapToObj(index -> targetSessionRegistry.registerAndSelectEvictions(
                        9001,
                        "parallel-session-" + index))
                .toList();

        Set<String> indexKeys = redis.keys("ti-java:identity:target-session-index:*");
        assertThat(indexKeys).hasSize(5)
                .allSatisfy(key -> assertThat(key)
                        .doesNotContain("9001", "phase3-test-only-login-rate-key-secret-0001"));
        String sessionsKey = indexKeys.stream()
                .filter(key -> key.contains(":{") && key.endsWith(":sessions"))
                .findFirst()
                .orElseThrow();
        String sequenceKey = indexKeys.stream()
                .filter(key -> key.contains(":{") && key.endsWith(":sequence"))
                .findFirst()
                .orElseThrow();
        Set<String> active = redis.opsForZSet().range(sessionsKey, 0, -1);
        assertThat(active).hasSize(3);
        List<String> evicted = evictionBatches.stream().flatMap(List::stream).toList();
        assertThat(evicted).doesNotHaveDuplicates().hasSize(97);
        assertThat(IntStream.range(0, 100)
                        .filter(index -> targetSessionRegistry.isActive(
                                9001,
                                "parallel-session-" + index))
                        .count())
                .isEqualTo(3);

        double maximumScore = active.stream()
                .mapToDouble(sessionId -> redis.opsForZSet().score(sessionsKey, sessionId))
                .max()
                .orElseThrow();
        assertThat(redis.delete(sequenceKey)).isTrue();
        assertThat(targetSessionRegistry.registerAndSelectEvictions(
                        9001,
                        "after-sequence-loss"))
                .hasSize(1);
        assertThat(redis.opsForZSet().score(sessionsKey, "after-sequence-loss"))
                .isGreaterThan(maximumScore);
        assertThat(redis.opsForZSet().size(sessionsKey)).isEqualTo(3);
        assertThat(redis.keys("ti-java:identity:target-session-index:*")).allSatisfy(key ->
                assertThat(redis.getExpire(key, TimeUnit.SECONDS)).isBetween(1L, 604_800L));
    }

    @Test
    void targetSessionRegistryEvictsTheGloballyOldestSessionAcrossIdentities() {
        List<String> evicted = new ArrayList<>();
        for (int index = 1; index <= 5; index++) {
            evicted.addAll(targetSessionRegistry.registerAndSelectEvictions(
                    9_100L + index,
                    "global-session-" + index));
        }

        assertThat(evicted).containsExactly("global-session-1", "global-session-2");
        assertThat(targetSessionRegistry.isActive(9_101, "global-session-1")).isFalse();
        assertThat(targetSessionRegistry.isActive(9_102, "global-session-2")).isFalse();
        assertThat(targetSessionRegistry.isActive(9_103, "global-session-3")).isTrue();
        assertThat(targetSessionRegistry.isActive(9_104, "global-session-4")).isTrue();
        assertThat(targetSessionRegistry.isActive(9_105, "global-session-5")).isTrue();
        String global = redis.keys("ti-java:identity:target-session-index:global:sessions")
                .stream()
                .findFirst()
                .orElseThrow();
        assertThat(redis.opsForZSet().size(global)).isEqualTo(3);
        assertThat(redis.opsForHash().size(
                "ti-java:identity:target-session-index:global:owners")).isEqualTo(3);

        targetSessionRegistry.unregister(9_104, "global-session-4");
        assertThat(targetSessionRegistry.isActive(9_104, "global-session-4")).isFalse();
        assertThat(redis.opsForZSet().size(global)).isEqualTo(2);
        assertThat(redis.opsForHash().size(
                "ti-java:identity:target-session-index:global:owners")).isEqualTo(2);

        assertThat(targetSessionRegistry.registerAndSelectEvictions(
                9_106, "global-session-6")).isEmpty();
        assertThat(targetSessionRegistry.isActive(9_106, "global-session-6")).isTrue();
        assertThat(redis.opsForZSet().size(global)).isEqualTo(3);
        assertThat(redis.opsForHash().size(
                "ti-java:identity:target-session-index:global:owners")).isEqualTo(3);

        assertThat(targetSessionRegistry.registerAndSelectEvictions(
                9_107, "global-session-7")).containsExactly("global-session-3");
        assertThat(targetSessionRegistry.isActive(9_103, "global-session-3")).isFalse();
        assertThat(targetSessionRegistry.isActive(9_105, "global-session-5")).isTrue();
        assertThat(targetSessionRegistry.isActive(9_106, "global-session-6")).isTrue();
        assertThat(targetSessionRegistry.isActive(9_107, "global-session-7")).isTrue();
        assertThat(redis.opsForZSet().size(global)).isEqualTo(3);
        assertThat(redis.opsForHash().size(
                "ti-java:identity:target-session-index:global:owners")).isEqualTo(3);
    }

    @Test
    void legacyReplayMarkersHaveStrictIdentityVersionAndGlobalCardinalityCapsWithRollback() {
        for (int index = 0; index < 3; index++) {
            assertThat(legacySessionExchangeGuard.acquireCredential(
                            "identity-cookie-" + index,
                            42,
                            7,
                            CREDENTIAL_EXPIRES_AT).status())
                    .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        }
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "identity-cookie-over-limit",
                        42,
                        7,
                        CREDENTIAL_EXPIRES_AT).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.IDENTITY_LIMITED);

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "identity-version-7",
                        42,
                        7,
                        CREDENTIAL_EXPIRES_AT).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "identity-version-8",
                        42,
                        8,
                        CREDENTIAL_EXPIRES_AT).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        assertThat(redis.keys("ti-java:identity:legacy-session-exchange:identity:*"))
                .as("one authoritative identity must have a distinct quota per Session version")
                .hasSize(2);

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        LegacySessionExchangeGuard.CredentialDecision firstGlobal = null;
        for (int index = 0; index < 3; index++) {
            LegacySessionExchangeGuard.CredentialDecision acquired =
                    legacySessionExchangeGuard.acquireCredential(
                            "global-cookie-" + index,
                            100 + index,
                            1,
                            CREDENTIAL_EXPIRES_AT);
            if (index == 0) {
                firstGlobal = acquired;
            }
            assertThat(acquired.status())
                    .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        }
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "global-cookie-over-limit",
                        999,
                        1,
                        CREDENTIAL_EXPIRES_AT).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.GLOBAL_LIMITED);

        assertThat(firstGlobal).isNotNull();
        legacySessionExchangeGuard.releaseCredential(
                "global-cookie-0", 100, 1, "x".repeat(43));
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "global-cookie-0",
                        100,
                        1,
                        CREDENTIAL_EXPIRES_AT).status())
                .as("a stale release token must not delete a newer reservation")
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.REPLAY);
        legacySessionExchangeGuard.releaseCredential(
                "global-cookie-0", 100, 1, firstGlobal.reservationToken());
        assertThat(legacySessionExchangeGuard.acquireCredential(
                        "global-cookie-over-limit",
                        999,
                        1,
                        CREDENTIAL_EXPIRES_AT).status())
                .isEqualTo(LegacySessionExchangeGuard.CredentialStatus.ACQUIRED);
        Set<String> markerKeys = redis.keys("ti-java:identity:legacy-session-exchange:*");
        assertThat(markerKeys).filteredOn(key -> key.contains(":credential:")).hasSize(3);
        assertThat(markerKeys).filteredOn(key -> key.contains(":credential:"))
                .allSatisfy(key -> assertThat(redis.getExpire(key, TimeUnit.SECONDS))
                        .isBetween(1L, 86_400L));
        assertThat(redis.opsForZSet().size(
                "ti-java:identity:legacy-session-exchange:credentials")).isEqualTo(3);
        assertThat(markerKeys).allSatisfy(key ->
                assertThat(redis.getExpire(key, TimeUnit.SECONDS)).isBetween(1L, 604_800L));
    }

    @Test
    void redisLoginLimiterIsAtomicAcrossIpAccountAndGlobalDimensionsWithBoundedTtl() {
        List<LoginRateLimiter.Decision> decisions = IntStream.range(0, 20)
                .parallel()
                .mapToObj(index -> loginRateLimiter.acquire(
                        "198.51.100.77", "victim@example.test"))
                .toList();

        assertThat(decisions).filteredOn(LoginRateLimiter.Decision::allowed).hasSize(5);
        assertThat(decisions).filteredOn(decision -> !decision.allowed()).hasSize(15);
        Set<String> keys = redis.keys("ti-java:identity:login-rate:*");
        assertThat(keys).hasSize(3)
                .anyMatch(key -> key.contains(":global:"))
                .anyMatch(key -> key.contains(":ip:"))
                .anyMatch(key -> key.contains(":account:"));
        assertThat(keys).allSatisfy(key -> assertThat(redis.getExpire(key, TimeUnit.SECONDS))
                .isBetween(1L, 120L));

        assertThat(loginRateLimiter.acquire(
                        "203.0.113.88", "VICTIM@example.test").allowed())
                .as("account HMAC normalization must stop distributed-IP retries")
                .isFalse();
    }

    @Test
    void loginLimiterCapsHighCardinalityKeysBeforeCreatingIpOrAccountBuckets() {
        IntStream.range(0, 200).forEach(index -> loginRateLimiter.acquire(
                "198.51.100." + index,
                "rotating-" + index + "@example.test"));

        Set<String> distributedKeys = redis.keys("ti-java:identity:login-rate:*");
        assertThat(distributedKeys).filteredOn(key -> key.contains(":global:")).hasSize(1);
        assertThat(distributedKeys).filteredOn(key -> key.contains(":ip:")).hasSize(100);
        assertThat(distributedKeys).filteredOn(key -> key.contains(":account:")).hasSize(100);
        assertThat(distributedKeys).hasSize(201);

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        IntStream.range(0, 200).forEach(index -> loginRateLimiter.acquire(
                "203.0.113.77",
                "rotating-" + index + "@example.test"));

        Set<String> singleIpKeys = redis.keys("ti-java:identity:login-rate:*");
        assertThat(singleIpKeys).filteredOn(key -> key.contains(":global:")).hasSize(1);
        assertThat(singleIpKeys).filteredOn(key -> key.contains(":ip:")).hasSize(1);
        assertThat(singleIpKeys).filteredOn(key -> key.contains(":account:")).hasSize(5);
        assertThat(singleIpKeys).hasSize(7);
        assertThat(singleIpKeys).allSatisfy(key -> assertThat(redis.getExpire(key, TimeUnit.SECONDS))
                .isBetween(1L, 120L));
    }

    @Test
    void csrfIssuanceIsLimitedBeforeGetOrTokenlessLoginCanCreateLongLivedSessions()
            throws Exception {
        for (int index = 0; index < 30; index++) {
            mockMvc.perform(get("/api/csrf"))
                    .andExpect(status().isOk());
        }
        mockMvc.perform(get("/api/csrf"))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0"));
        assertAnonymousSessionPopulationIsBounded();

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        for (int index = 0; index < 30; index++) {
            mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                            .head("/api/csrf"))
                    .andExpect(status().isOk());
        }
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .head("/api/csrf"))
                .andExpect(status().isTooManyRequests());
        assertAnonymousSessionPopulationIsBounded();

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        for (int index = 0; index < 30; index++) {
            mockMvc.perform(post("/api/login")
                            .contentType("application/json")
                            .content("{}"))
                    .andExpect(status().isForbidden());
        }
        mockMvc.perform(post("/api/login")
                        .contentType("application/json")
                        .content("{}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0"));
        assertAnonymousSessionPopulationIsBounded();

        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        org.springframework.http.HttpMethod[] unsafeMethods = {
            org.springframework.http.HttpMethod.POST,
            org.springframework.http.HttpMethod.PUT,
            org.springframework.http.HttpMethod.PATCH,
            org.springframework.http.HttpMethod.DELETE
        };
        for (int index = 0; index < 30; index++) {
            mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                            .request(unsafeMethods[index % unsafeMethods.length], "/not-declared"))
                    .andExpect(status().isForbidden());
        }
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .request(org.springframework.http.HttpMethod.POST, "/not-declared"))
                .andExpect(status().isTooManyRequests());
        assertAnonymousSessionPopulationIsBounded();
    }

    @Test
    void anonymousCsrfSessionTtlShrinksToItsAbsoluteDeadlineAndExpiresInRedis()
            throws Exception {
        Csrf csrf = obtainCsrf();
        String sessionKey = redis.keys("*identity:sessions:sessions:*")
                .stream()
                .findFirst()
                .orElseThrow();
        long fixedNow = FIXED_NOW.getEpochSecond();
        redis.opsForHash().put(
                sessionKey,
                "sessionAttr:anonymous_expires_at",
                "l:" + (fixedNow + 60));

        mockMvc.perform(get("/api/auth/login-methods").cookie(csrf.sessionCookie()))
                .andExpect(status().isOk());

        assertThat(redis.getExpire(sessionKey, TimeUnit.SECONDS)).isBetween(1L, 60L);
        redis.opsForHash().put(
                sessionKey,
                "sessionAttr:anonymous_expires_at",
                "l:" + (fixedNow - 1));

        mockMvc.perform(get("/api/auth/login-methods").cookie(csrf.sessionCookie()))
                .andExpect(status().isOk());

        assertThat(redis.hasKey(sessionKey)).isFalse();
    }

    private org.springframework.test.web.servlet.ResultActions performLogin(
            Csrf csrf,
            String username,
            String password
    ) throws Exception {
        return mockMvc.perform(post("/api/login")
                .cookie(csrf.cookie(), csrf.sessionCookie())
                .header(csrf.headerName(), csrf.token())
                .contentType("application/json")
                .content(objectMapper.writeValueAsString(Map.of(
                        "username", username,
                        "password", password))));
    }

    private Csrf obtainCsrf() throws Exception {
        MvcResult result = mockMvc.perform(get("/api/csrf"))
                .andExpect(status().isOk())
                .andExpect(cookie().exists("ti_dev_csrf"))
                .andExpect(jsonPath("$.header_name").value("X-CSRF-TOKEN"))
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andReturn();
        MockHttpServletResponse response = result.getResponse();
        return new Csrf(
                objectMapper.readTree(response.getContentAsByteArray()).path("header_name").stringValue(),
                objectMapper.readTree(response.getContentAsByteArray()).path("token").stringValue(),
                response.getCookie("ti_dev_csrf"),
                response.getCookie("ti_dev_session"));
    }

    private tools.jackson.databind.JsonNode legacyVectors() throws Exception {
        try (var stream = getClass().getClassLoader()
                .getResourceAsStream("compat/legacy-auth-vectors.json")) {
            assertThat(stream).isNotNull();
            return objectMapper.readTree(stream);
        }
    }

    private List<Map<String, Object>> databaseFingerprint() {
        List<Map<String, Object>> users = jdbc.queryForList("""
                SELECT id, username, password_hash, is_admin, is_locked, session_version,
                       is_subject_admin, is_notification_admin, has_password_set,
                       email, phone, openid, last_active
                FROM users
                ORDER BY id
                """);
        List<Map<String, Object>> config = jdbc.queryForList("""
                SELECT id, config_key, config_value
                FROM system_config
                ORDER BY id
                """);
        return List.of(Map.of("users", users), Map.of("system_config", config));
    }

    private Map<String, String> rawSessionAttributes(String key) {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            Map<byte[], byte[]> raw = connection.hashCommands().hGetAll(
                    key.getBytes(StandardCharsets.UTF_8));
            return raw.entrySet().stream().collect(Collectors.toMap(
                    entry -> new String(entry.getKey(), StandardCharsets.UTF_8),
                    entry -> new String(entry.getValue(), StandardCharsets.UTF_8),
                    (left, right) -> right,
                    LinkedHashMap::new));
        }
    }

    private void assertAnonymousSessionPopulationIsBounded() {
        Set<String> sessions = redis.keys("*").stream()
                .filter(key -> key.contains("identity:sessions:sessions:"))
                .collect(Collectors.toSet());
        assertThat(sessions).hasSize(30);
        assertThat(sessions).allSatisfy(key -> assertThat(redis.getExpire(key, TimeUnit.SECONDS))
                .isBetween(1L, 600L));
        Set<String> limiterKeys = redis.keys("ti-java:identity:csrf-issuance-rate:*");
        assertThat(limiterKeys).hasSize(2)
                .anyMatch(key -> key.contains(":global:"))
                .anyMatch(key -> key.contains(":ip:"));
    }

    private record Csrf(
            String headerName,
            String token,
            Cookie cookie,
            Cookie sessionCookie
    ) {
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedAuthenticationClock {

        @Bean
        @Primary
        Clock phase3AuthenticationClock() {
            return Clock.fixed(FIXED_NOW, ZoneOffset.UTC);
        }
    }
}
