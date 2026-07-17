package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import com.redis.testcontainers.RedisContainer;
import com.zaxxer.hikari.HikariDataSource;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource.Family;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource.FaultPlan;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource.TraceSnapshot;
import jakarta.servlet.http.Cookie;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.sql.SQLException;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.TestMethodOrder;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Executes every Phase 4B golden disposition against the real Java target stack. */
@Testcontainers
@ActiveProfiles("test")
@AutoConfigureMockMvc
@SpringBootTest(classes = TiApplication.class)
@Import({
        LegacyPersonalBankUserCountsGoldenTargetExecutionIT.FixedTargetClock.class,
        LegacyPersonalBankUserCountsGoldenTargetExecutionIT.TracingDataSourceConfiguration.class
})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@Execution(ExecutionMode.SAME_THREAD)
class LegacyPersonalBankUserCountsGoldenTargetExecutionIT {

    private static final String GOLDEN_PATH =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String MAPPING_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-mapping-evidence.json";
    private static final String REDIS_PASSWORD = "phase4c-target-execution-redis";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final String RATE_NAMESPACE =
            "ti-java:learning:personal-bank-user-counts-target-execution";
    private static final Pattern RATE_KEY = Pattern.compile(
            "^" + Pattern.quote(RATE_NAMESPACE)
                    + ":(?:api|web):(?:identity:v1|ip:v1):[0-9a-f]{64}:"
                    + "(?:second|hour|day)$");
    private static final Instant FIXED_NOW = Instant.parse("2026-07-17T04:00:00Z");
    private static final int PUBLIC_BANK_ID = 99_555;
    private static final List<String> NORMAL_TYPES =
            List.of("判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题");
    private static final List<String> FAVORITE_TYPES =
            List.of("判断题", "选择题", "选择题", "简答题");
    private static final Set<String> NON_HTTP_TYPED_CASES = Set.of(
            "access-shared-malformed-expiry-value-error",
            "access-shared-aware-expiry-type-error");

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
        registry.add("spring.session.data.redis.namespace",
                () -> "ti-java:phase4c:user-counts-target-sessions");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase4c-target-login-rate-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add("ti.security.legacy-auth.accept-until",
                () -> "2026-07-19T00:00:00Z");
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
        registry.add("ti.security.personal-bank-user-counts-read-rate-limit.namespace",
                () -> RATE_NAMESPACE);
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-second",
                () -> "1000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-hour",
                () -> "10000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-day",
                () -> "100000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.multiplier",
                () -> "1");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.key-secret",
                () -> "phase4c-target-user-counts-rate-key-secret-0001");
        registry.add("ti.security.personal-bank-user-counts-cors.allowed-origins",
                () -> "http://127.0.0.1:3000,https://servicewechat.com");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    ObjectMapper json;

    @Autowired
    Phase4cUserCountsFaultInjectingDataSource sqlTrace;

    private JsonNode golden;
    private Map<String, JsonNode> goldenCases;
    private Map<String, JsonNode> targetMappings;
    private Map<String, Long> actorIds;
    private final Map<String, Cookie> targetSessions = new LinkedHashMap<>();

    @BeforeEach
    void loadEvidenceAndCreateRealTargetSessions() throws Exception {
        golden = readJson(GOLDEN_PATH);
        JsonNode mapping = readJson(MAPPING_PATH);
        goldenCases = casesById(golden.path("cases"));
        targetMappings = casesById(mapping.path("cases"));
        actorIds = longValues(golden.path("fixture").path("actors"));

        assertThat(goldenCases).hasSize(59);
        assertThat(targetMappings.keySet()).containsExactlyElementsOf(goldenCases.keySet());
        assertThat(POSTGRES.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.POSTGRES_18_REFERENCE);
        assertThat(jdbc.queryForObject("SHOW server_version", String.class)).isEqualTo("18.4");

        clearRedis();
        Set<String> sessionActors = new LinkedHashSet<>();
        goldenCases.values().forEach(goldenCase -> {
            String actor = goldenCase.path("session_actor").asString();
            if (!actor.isBlank() && !actor.equals("anonymous")) {
                sessionActors.add(actor);
            }
        });
        for (String actor : sessionActors) {
            targetSessions.put(actor, exchangeFlaskSession(actor, "bootstrap-" + actor));
        }
        clearRouteRateLimits();
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM users WHERE last_active IS NOT NULL",
                Long.class)).isZero();
    }

    @Test
    @Order(1)
    void realFlaskExchangeAndAuthoritativeTargetSessionBothReachApplicationJdbc()
            throws Exception {
        clearRouteRateLimits();
        String databaseBefore = databaseFingerprint();

        TraceSnapshot flaskTrace = executeTraced(null, () -> {
            MvcResult result = mockMvc.perform(get(
                            "/api/user/banks/api/99551/user-counts")
                            .cookie(new Cookie(
                                    "session",
                                    signedFlaskCookie("owner", "explicit-flask-chain")))
                            .header("X-Request-ID", "phase4c-target-explicit-flask"))
                    .andReturn();
            assertThat(result.getResponse().getStatus()).isEqualTo(200);
            assertThat(result.getResponse().getCookie("ti_dev_session")).isNotNull();
        });
        assertRealAuthenticatedBusinessRead(flaskTrace);
        assertNoReadMutation(flaskTrace, databaseBefore);

        clearRouteRateLimits();
        databaseBefore = databaseFingerprint();
        TraceSnapshot targetTrace = executeTraced(null, () -> {
            MvcResult result = mockMvc.perform(get(
                            "/api/user/banks/api/99551/user-counts")
                            .cookie(targetSessions.get("owner"))
                            .header("X-Request-ID", "phase4c-target-authoritative-session"))
                    .andReturn();
            assertThat(result.getResponse().getStatus()).isEqualTo(200);
            assertSuccessView(result, new ExpectedView(
                    9, 5, 3, NORMAL_TYPES, false));
        });
        assertRealAuthenticatedBusinessRead(targetTrace);
        assertNoReadMutation(targetTrace, databaseBefore);
    }

    @TestFactory
    @Order(2)
    Stream<DynamicTest> executesAllFortySixNonFaultHttpCasesThroughTheRealTarget() {
        List<JsonNode> cases = goldenCases.values().stream()
                .filter(goldenCase -> !goldenCase.path("case_id").asString()
                        .startsWith("fault-"))
                .filter(goldenCase -> !NON_HTTP_TYPED_CASES.contains(
                        goldenCase.path("case_id").asString()))
                .toList();
        assertThat(cases).hasSize(46);
        return cases.stream().map(goldenCase -> DynamicTest.dynamicTest(
                goldenCase.path("case_id").asString(),
                () -> executeGoldenHttpCase(goldenCase, null)));
    }

    @TestFactory
    @Order(3)
    Stream<DynamicTest> executesAllElevenFaultCasesWithRealPostgresqlFailures() {
        List<JsonNode> cases = goldenCases.values().stream()
                .filter(goldenCase -> goldenCase.path("case_id").asString()
                        .startsWith("fault-"))
                .toList();
        assertThat(cases).hasSize(11);
        return cases.stream().map(goldenCase -> DynamicTest.dynamicTest(
                goldenCase.path("case_id").asString(),
                () -> executeGoldenHttpCase(
                        goldenCase,
                        faultPlan(goldenCase.path("case_id").asString()))));
    }

    @Test
    @Order(4)
    void rejectsTheMalformedExpiryTypedDispositionWithoutPersistingARow() {
        long sharesBefore = jdbc.queryForObject("SELECT COUNT(*) FROM bank_shares", Long.class);
        long recordsBefore = jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_share_records", Long.class);

        assertThatThrownBy(() -> jdbc.update("""
                INSERT INTO bank_shares (
                    id, bank_id, owner_id, share_code, share_token, permission,
                    expires_at, max_uses, current_uses, is_active, created_at
                ) VALUES (
                    99656, 99551, 99451, 'C00006',
                    'user-count-token-0006', 'read',
                    CAST(? AS timestamp without time zone),
                    NULL, 6, true, TIMESTAMP '2026-07-17 08:06:00'
                )
                """, "malformed-expiry"))
                .isInstanceOf(DataAccessException.class)
                .satisfies(failure -> assertThat(sqlState(failure)).isEqualTo("22007"));
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_shares WHERE id = 99656",
                Long.class)).isZero();
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM bank_shares", Long.class))
                .isEqualTo(sharesBefore);
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_share_records", Long.class))
                .isEqualTo(recordsBefore);
    }

    @Test
    @Order(5)
    void provesTheAwareExpiryCollapseAndApprovedNullExpiryRepresentation() {
        long sharesBefore = jdbc.queryForObject("SELECT COUNT(*) FROM bank_shares", Long.class);
        long recordsBefore = jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_share_records", Long.class);
        LocalDateTime positiveOffset = jdbc.queryForObject(
                "SELECT CAST(? AS timestamp without time zone)",
                LocalDateTime.class,
                "2026-07-17 13:00:00+08:00");
        LocalDateTime negativeOffset = jdbc.queryForObject(
                "SELECT CAST(? AS timestamp without time zone)",
                LocalDateTime.class,
                "2026-07-17 13:00:00-05:00");
        assertThat(positiveOffset)
                .as("timestamp without time zone erases source offset provenance")
                .isEqualTo(negativeOffset)
                .isEqualTo(LocalDateTime.parse("2026-07-17T13:00:00"));

        assertThat(jdbc.queryForObject(
                "SELECT expires_at IS NULL FROM bank_shares WHERE id = 99660",
                Boolean.class)).isTrue();
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM bank_shares", Long.class))
                .isEqualTo(sharesBefore);
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_share_records", Long.class))
                .isEqualTo(recordsBefore);

    }

    private void executeGoldenHttpCase(JsonNode goldenCase, FaultPlan faultPlan)
            throws Exception {
        clearRouteRateLimits();
        String caseId = goldenCase.path("case_id").asString();
        JsonNode mapping = Objects.requireNonNull(targetMappings.get(caseId), caseId);
        String databaseBefore = databaseFingerprint();
        Holder<MvcResult> resultHolder = new Holder<>();

        TraceSnapshot trace = executeTraced(faultPlan, () ->
                resultHolder.value = mockMvc.perform(requestFor(goldenCase, caseId)).andReturn());
        MvcResult result = Objects.requireNonNull(resultHolder.value, "HTTP result");
        int targetStatus = mapping.path("target_status").asInt();
        assertThat(result.getResponse().getStatus())
                .as("target status for %s", caseId)
                .isEqualTo(targetStatus);
        assertTargetBody(caseId, goldenCase, mapping, result, targetStatus);
        assertSqlExecutionBoundary(caseId, targetStatus, trace);
        assertNoReadMutation(trace, databaseBefore);
        assertRealRateLimitState(result);

        if (faultPlan != null) {
            assertThat(trace.faults()).singleElement().satisfies(fault -> {
                assertThat(fault.initialSqlState()).isEqualTo("42703");
                assertThat(fault.poisonedSqlState()).isEqualTo("25P02");
                assertThat(fault.family()).isEqualTo(faultPlan.family());
                assertThat(fault.occurrence()).isEqualTo(faultPlan.occurrence());
                assertThat(fault.connectionReadOnly()).isTrue();
                var faultRollback = trace.rollbacks().stream()
                        .filter(rollback -> rollback.connectionIdentity()
                                == fault.connectionIdentity())
                        .filter(rollback -> rollback.sequence() > fault.sequence())
                        .findFirst()
                        .orElseThrow(() -> new AssertionError(
                                "Missing rollback after injected PostgreSQL abort"));
                assertThat(trace.successes())
                        .noneMatch(success -> success.family() == fault.family()
                                && success.occurrence() == fault.occurrence());
                if (targetStatus == 200
                        && fault.family() == Family.QUESTION_SUMMARY
                        && fault.occurrence() < 4) {
                    assertThat(trace.successes())
                            .anyMatch(success -> success.family() == fault.family()
                                    && success.occurrence() > fault.occurrence()
                                    && success.sequence() > faultRollback.sequence()
                                    && success.connectionIdentity()
                                    != fault.connectionIdentity());
                }
            });
        }
    }

    private org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder requestFor(
            JsonNode goldenCase,
            String caseId
    ) {
        var request = get(goldenCase.path("request").path("path").asString())
                .header(HttpHeaders.ACCEPT,
                        goldenCase.path("request").path("headers").path("Accept").asString())
                .header("X-Request-ID", "phase4c-target-" + caseId)
                .with(raw -> {
                    raw.setRemoteAddr(goldenCase.path("request")
                            .path("remote_address").asString());
                    return raw;
                });

        String sessionActor = goldenCase.path("session_actor").asString();
        if (!sessionActor.isBlank() && !sessionActor.equals("anonymous")) {
            request.cookie(Objects.requireNonNull(
                    targetSessions.get(sessionActor), "target Session for " + sessionActor));
        }

        String bearerActor = goldenCase.path("bearer_actor").asString();
        if (bearerActor.equals("invalid")) {
            request.header(HttpHeaders.AUTHORIZATION, "Bearer invalid-phase4c-target-token");
        } else if (!bearerActor.isBlank() && !bearerActor.equals("none")) {
            request.header(HttpHeaders.AUTHORIZATION, "Bearer " + jwt(bearerActor));
        }
        goldenCase.path("request").path("query").forEach(pair ->
                request.param(pair.path(0).asString(), pair.path(1).asString()));
        return request;
    }

    private void assertTargetBody(
            String caseId,
            JsonNode goldenCase,
            JsonNode mapping,
            MvcResult result,
            int status
    ) throws Exception {
        if (status == 200) {
            assertSuccessView(result, expectedView(caseId, goldenCase, mapping));
            return;
        }
        if (status == 302) {
            assertThat(result.getResponse().getHeader(HttpHeaders.LOCATION)).isEqualTo("/login");
            return;
        }
        if (status == 500
                && goldenCase.path("response").path("body_kind").asString().equals("text")) {
            assertThat(result.getResponse().getContentType()).startsWith("text/html");
            assertThat(result.getResponse().getContentAsString())
                    .isEqualTo(goldenCase.path("response").path("body").asString())
                    .doesNotContain("missing_phase4c_target_execution_column")
                    .doesNotContain("42703")
                    .doesNotContain("25P02");
            return;
        }
        JsonNode body = json.readTree(result.getResponse().getContentAsByteArray());
        if (status == 401) {
            assertThat(body.path("status").asString()).isEqualTo("unauthorized");
            assertThat(body.path("message").asString()).isEqualTo("请先登录");
        } else if (status == 403) {
            assertThat(body.path("status").asString()).isEqualTo("error");
            assertThat(body.path("message").asString()).isEqualTo("无权访问此题库");
        } else if (status == 500) {
            assertThat(body.path("status").asString()).isEqualTo("error");
            assertThat(body.toString())
                    .doesNotContain("missing_phase4c_target_execution_column")
                    .doesNotContain("42703")
                    .doesNotContain("25P02");
        }
    }

    private ExpectedView expectedView(
            String caseId,
            JsonNode goldenCase,
            JsonNode mapping
    ) {
        return switch (caseId) {
            case "tag-normalized-sa2-empty-api-alias",
                    "tag-normalized-sa2-empty-web-alias" ->
                    new ExpectedView(1, 1, 0, List.of("选择题"), true);
            case "fault-favorites-sqlite-continues",
                    "fault-favorites-postgresql-poison-simulation" ->
                    new ExpectedView(9, 0, 3, NORMAL_TYPES, false);
            case "fault-mistakes-sqlite-continues",
                    "fault-mistakes-postgresql-poison-simulation" ->
                    new ExpectedView(9, 5, 0, NORMAL_TYPES, false);
            case "fault-types-degrades" ->
                    new ExpectedView(9, 5, 3, List.of(), false);
            case "fault-source-favorites-second-count-postgresql-poison-simulation" ->
                    new ExpectedView(5, 0, 3, FAVORITE_TYPES, false);
            default -> viewFromGolden(sourceGoldenCase(goldenCase, mapping));
        };
    }

    private JsonNode sourceGoldenCase(JsonNode goldenCase, JsonNode mapping) {
        if (mapping.path("target_data_source_case").isTextual()) {
            return Objects.requireNonNull(
                    goldenCases.get(mapping.path("target_data_source_case").asString()),
                    "target data source case");
        }
        return goldenCase;
    }

    private ExpectedView viewFromGolden(JsonNode goldenCase) {
        JsonNode data = goldenCase.path("response").path("body").path("data");
        assertThat(data.isObject()).as(goldenCase.path("case_id").asString()).isTrue();
        return new ExpectedView(
                data.path("total").asLong(),
                data.path("favorites").asLong(),
                data.path("mistakes").asLong(),
                strings(data.path("types")),
                data.path("shuffle_options_available").asBoolean());
    }

    private void assertSuccessView(MvcResult result, ExpectedView expected) throws Exception {
        JsonNode body = json.readTree(result.getResponse().getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("success");
        assertThat(body.path("code").asInt()).isZero();
        JsonNode data = body.path("data");
        assertThat(data.path("total").asLong()).isEqualTo(expected.total());
        assertThat(data.path("favorites").asLong()).isEqualTo(expected.favorites());
        assertThat(data.path("mistakes").asLong()).isEqualTo(expected.mistakes());
        assertThat(strings(data.path("types"))).containsExactlyElementsOf(expected.types());
        assertThat(data.path("shuffle_options_available").asBoolean())
                .isEqualTo(expected.shuffleOptionsAvailable());
    }

    private Cookie exchangeFlaskSession(String actor, String nonce) throws Exception {
        MvcResult result = mockMvc.perform(get(
                        "/api/user/banks/api/{bankId}/user-counts", PUBLIC_BANK_ID)
                        .cookie(new Cookie("session", signedFlaskCookie(actor, nonce)))
                        .header("X-Request-ID", "phase4c-target-session-" + nonce)
                        .with(request -> {
                            long identityId = Objects.requireNonNull(actorIds.get(actor), actor);
                            request.setRemoteAddr("198.18.0." + (identityId % 200 + 1));
                            return request;
                        }))
                .andReturn();
        assertThat(result.getResponse().getStatus()).as(actor).isEqualTo(200);
        Cookie target = result.getResponse().getCookie("ti_dev_session");
        assertThat(target).as("real target Session for %s", actor).isNotNull();
        return new Cookie(target.getName(), target.getValue());
    }

    private String signedFlaskCookie(String actor, String nonce) {
        long identityId = Objects.requireNonNull(actorIds.get(actor), actor);
        String payload = "{\"user_id\":" + identityId
                + ",\"username\":\"phase4b_counts_" + actor
                + "\",\"session_version\":11"
                + ",\"remember\":false,\"csrf_token\":\"" + nonce + "\"}";
        String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
        String encodedTimestamp = encode(minimalBigEndian(
                FIXED_NOW.minusSeconds(60).getEpochSecond()));
        String unsigned = encodedPayload + "." + encodedTimestamp;
        byte[] derived = hmac(
                "HmacSHA1",
                LEGACY_SECRET.getBytes(StandardCharsets.UTF_8),
                "cookie-session".getBytes(StandardCharsets.UTF_8));
        byte[] signature = hmac(
                "HmacSHA1", derived, unsigned.getBytes(StandardCharsets.US_ASCII));
        Arrays.fill(derived, (byte) 0);
        return unsigned + "." + encode(signature);
    }

    private String jwt(String actor) {
        long identityId = Objects.requireNonNull(actorIds.get(actor), actor);
        int claimVersion = 11;
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + identityId
                + ",\"openid\":\"\",\"session_version\":" + claimVersion
                + ",\"exp\":" + FIXED_NOW.plusSeconds(86_400).getEpochSecond()
                + ",\"iat\":" + FIXED_NOW.minusSeconds(60).getEpochSecond()
                + ",\"jti\":\"" + String.format("%032x", identityId) + "\"}";
        String unsigned = base64Url(header) + "." + base64Url(payload);
        return unsigned + "." + encode(hmac(
                "HmacSHA256",
                LEGACY_SECRET.getBytes(StandardCharsets.UTF_8),
                unsigned.getBytes(StandardCharsets.US_ASCII)));
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

    private FaultPlan faultPlan(String caseId) {
        if (caseId.contains("share-access")) {
            return new FaultPlan(Family.SHARE_ACCESS, 1);
        }
        if (caseId.contains("total")) {
            return new FaultPlan(Family.QUESTION_SUMMARY, 1);
        }
        if (caseId.contains("favorites") || caseId.contains("source-favorites")) {
            return new FaultPlan(Family.QUESTION_SUMMARY, 2);
        }
        if (caseId.contains("mistakes")) {
            return new FaultPlan(Family.QUESTION_SUMMARY, 3);
        }
        if (caseId.contains("types")) {
            return new FaultPlan(Family.QUESTION_SUMMARY, 4);
        }
        throw new IllegalArgumentException("No target fault plan for " + caseId);
    }

    private TraceSnapshot executeTraced(FaultPlan plan, CheckedRunnable action)
            throws Exception {
        sqlTrace.start(plan);
        Holder<TraceSnapshot> trace = new Holder<>();
        try {
            action.run();
        } finally {
            trace.value = sqlTrace.stop();
        }
        return Objects.requireNonNull(trace.value, "SQL trace");
    }

    private void assertRealAuthenticatedBusinessRead(TraceSnapshot trace) {
        assertThat(trace.executions())
                .extracting(Phase4cUserCountsFaultInjectingDataSource.Execution::family)
                .contains(Family.AUTHORITY_USERS, Family.BANK_ACCESS, Family.QUESTION_SUMMARY);
    }

    private void assertSqlExecutionBoundary(
            String caseId,
            int status,
            TraceSnapshot trace
    ) {
        List<Family> families = trace.executions().stream()
                .map(Phase4cUserCountsFaultInjectingDataSource.Execution::family)
                .toList();
        if (status == 302) {
            assertThat(families)
                    .as("Web pre-authentication termination must not reach JDBC")
                    .isEmpty();
            return;
        }
        if (status == 401) {
            assertThat(families)
                    .as("authentication termination must not reach business JDBC")
                    .doesNotContain(
                            Family.BANK_ACCESS,
                            Family.SHARE_ACCESS,
                            Family.TAG_MEMBERSHIP,
                            Family.FAVORITE_MEMBERSHIP,
                            Family.MISTAKE_MEMBERSHIP,
                            Family.QUESTION_SUMMARY);
            if (caseId.equals(
                    "auth-state-invalid-bearer-does-not-fallback-session-api-alias")) {
                assertThat(families).containsExactly(Family.AUTHORITY_USERS);
            } else if (caseId.equals("auth-invalid-bearer-falls-back-session-api-alias")
                    || caseId.equals("auth-anonymous-api-alias")) {
                assertThat(families).isEmpty();
            } else {
                throw new AssertionError("Unclassified 401 target case " + caseId);
            }
            return;
        }
        assertThat(families)
                .contains(Family.AUTHORITY_USERS, Family.BANK_ACCESS);
        assertThat(trace.occurrenceCount(Family.AUTHORITY_USERS)).isEqualTo(1);
        if (Set.of(
                "auth-session-owner-api-alias",
                "auth-session-owner-web-alias",
                "auth-bearer-owner-api-alias").contains(caseId)) {
            assertThat(families).contains(Family.QUESTION_SUMMARY);
        }
        assertThat(trace.executions())
                .filteredOn(execution -> Set.of(
                                Family.BANK_ACCESS,
                                Family.SHARE_ACCESS,
                                Family.TAG_MEMBERSHIP,
                                Family.FAVORITE_MEMBERSHIP,
                                Family.MISTAKE_MEMBERSHIP,
                                Family.QUESTION_SUMMARY)
                        .contains(execution.family()))
                .allMatch(
                        Phase4cUserCountsFaultInjectingDataSource.Execution::connectionReadOnly);
    }

    private void assertNoReadMutation(TraceSnapshot trace, String databaseBefore) {
        assertThat(trace.writeDmlCount()).isZero();
        assertThat(trace.usersLastActiveWriteDmlCount()).isZero();
        assertThat(trace.schemaMutationCount()).isZero();
        assertThat(trace.executions())
                .noneMatch(execution -> execution.usersWriteDml()
                        || (execution.normalizedSql().contains("last_active")
                        && execution.writeDml()));
        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
    }

    private void assertRealRateLimitState(MvcResult result) {
        Set<String> keys = redis.keys(RATE_NAMESPACE + ":*");
        Set<String> observed = keys == null ? Set.of() : Set.copyOf(keys);
        if (result.getResponse().getHeader("X-RateLimit-Limit") == null) {
            assertThat(observed)
                    .as("pre-limiter authentication termination must not create route keys")
                    .isEmpty();
            return;
        }
        assertThat(observed)
                .hasSize(3)
                .allMatch(key -> RATE_KEY.matcher(key).matches())
                .anyMatch(key -> key.endsWith(":second"))
                .anyMatch(key -> key.endsWith(":hour"))
                .anyMatch(key -> key.endsWith(":day"));
        assertThat(observed)
                .allMatch(key -> "1".equals(redis.opsForValue().get(key)));
    }

    private String databaseFingerprint() {
        return jdbc.queryForObject("""
                SELECT md5(jsonb_build_object(
                    'users', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM users t
                    ), '[]'::jsonb),
                    'user_progress', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_progress t
                    ), '[]'::jsonb),
                    'user_question_banks', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_question_banks t
                    ), '[]'::jsonb),
                    'bank_shares', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM bank_shares t
                    ), '[]'::jsonb),
                    'bank_share_records', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM bank_share_records t
                    ), '[]'::jsonb),
                    'user_bank_questions', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_bank_questions t
                    ), '[]'::jsonb),
                    'user_bank_favorites', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_bank_favorites t
                    ), '[]'::jsonb),
                    'user_bank_mistakes', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_bank_mistakes t
                    ), '[]'::jsonb),
                    'user_question_tag_items', COALESCE((
                        SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)
                        FROM user_question_tag_items t
                    ), '[]'::jsonb)
                )::text)
                """, String.class);
    }

    private void clearRouteRateLimits() {
        Set<String> keys = redis.keys(RATE_NAMESPACE + ":*");
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
    }

    private void clearRedis() {
        Set<String> keys = redis.keys("*");
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
    }

    private JsonNode readJson(String relative) throws Exception {
        Path root = Path.of(Objects.requireNonNull(System.getProperty("basedir"))).getParent();
        return json.readTree(Files.readAllBytes(root.resolve(relative)));
    }

    private static Map<String, JsonNode> casesById(JsonNode cases) {
        Map<String, JsonNode> result = new LinkedHashMap<>();
        cases.forEach(item -> {
            String caseId = item.path("case_id").asString();
            if (result.put(caseId, item) != null) {
                throw new IllegalStateException("Duplicate case " + caseId);
            }
        });
        return Collections.unmodifiableMap(result);
    }

    private static Map<String, Long> longValues(JsonNode object) {
        Map<String, Long> result = new LinkedHashMap<>();
        object.properties().forEach(entry -> result.put(entry.getKey(), entry.getValue().asLong()));
        return Map.copyOf(result);
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(item -> result.add(item.asString()));
        return List.copyOf(result);
    }

    private static String sqlState(Throwable failure) {
        Throwable current = failure;
        while (current != null) {
            if (current instanceof SQLException sqlException) {
                return sqlException.getSQLState();
            }
            current = current.getCause();
        }
        return null;
    }

    private record ExpectedView(
            long total,
            long favorites,
            long mistakes,
            List<String> types,
            boolean shuffleOptionsAvailable
    ) {
        private ExpectedView {
            types = List.copyOf(types);
        }
    }

    private static final class Holder<T> {
        private T value;
    }

    @FunctionalInterface
    private interface CheckedRunnable {
        void run() throws Exception;
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class FixedTargetClock {

        @Bean
        @Primary
        Clock phase4cTargetExecutionClock() {
            return Clock.fixed(FIXED_NOW, ZoneOffset.UTC);
        }
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class TracingDataSourceConfiguration {

        @Bean
        @Primary
        Phase4cUserCountsFaultInjectingDataSource phase4cTargetExecutionDataSource(
                DataSourceProperties properties
        ) {
            HikariDataSource target = properties.initializeDataSourceBuilder()
                    .type(HikariDataSource.class)
                    .build();
            return new Phase4cUserCountsFaultInjectingDataSource(target);
        }
    }
}
