package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.cookie;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankSnapshotCommit;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

@Testcontainers
@ActiveProfiles("test")
@AutoConfigureMockMvc
@SpringBootTest(classes = TiApplication.class)
@Import({
        Phase4aPublicBankCatalogIT.FixedPublicBankClock.class,
        Phase4aSubjectCatalogIT.SqlCountingDataSourceConfiguration.class
})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Sql(scripts = {
        "classpath:db/phase4a/041-subject-catalog-seed.sql",
        "classpath:db/phase4a/043-public-bank-snapshot-seed.sql"
}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class Phase4aPublicBankCatalogIT {

    private static final String REDIS_PASSWORD = "phase4a-public-bank-ephemeral-redis";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final Instant FIXED_NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final String REQUEST_ID = "phase4a-public-bank-golden-request";
    private static final String PUBLIC_BANK_RATE_NAMESPACE =
            "ti-java:phase4a-public-bank:read-rate";
    private static final Set<String> ARBITRARY_PRECISION_PATH_ID_CASES = Set.of(
            "detail-arbitrary-precision-id",
            "card-arbitrary-precision-id");
    private static final Pattern PUBLIC_BANK_RATE_KEY = Pattern.compile(
            Pattern.quote(PUBLIC_BANK_RATE_NAMESPACE)
                    + ":(?:legacy-list|boards|card-detail|hot|plaza-list|summary|detail)"
                    + ":(?:identity|ip):v1:[0-9a-f]{64}:(?:second|hour|day)");

    private static final Map<String, ViewerFixture> VIEWERS = Map.of(
            "owner", new ViewerFixture(5101, 11),
            "public", new ViewerFixture(5102, 12),
            "shared", new ViewerFixture(5103, 13),
            "both", new ViewerFixture(5104, 14),
            "system", new ViewerFixture(5105, 15));

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.reference18()
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                    "/docker-entrypoint-initdb.d/030-auth-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4a/040-subject-catalog-schema.sql"),
                    "/docker-entrypoint-initdb.d/040-subject-catalog-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4a/041-subject-catalog-seed.sql"),
                    "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4a/042-public-bank-snapshot-schema.sql"),
                    "/docker-entrypoint-initdb.d/042-public-bank-snapshot-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4a/043-public-bank-snapshot-seed.sql"),
                    "/docker-entrypoint-initdb.d/043-public-bank-snapshot-seed.sql");

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
                () -> "ti-java:phase4a-public-bank:sessions");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase4a-public-bank-login-rate-key-secret-0001");
        registry.add("ti.security.public-bank-read-rate-limit.namespace",
                () -> PUBLIC_BANK_RATE_NAMESPACE);
        registry.add("ti.security.public-bank-read-rate-limit.requests-per-second", () -> "10");
        registry.add("ti.security.public-bank-read-rate-limit.requests-per-hour", () -> "500");
        registry.add("ti.security.public-bank-read-rate-limit.requests-per-day", () -> "5000");
        registry.add("ti.security.public-bank-read-rate-limit.multiplier", () -> "1");
        registry.add("ti.catalog.public-bank.snapshot.readiness-enabled", () -> "true");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add("ti.security.legacy-auth.accept-until", () -> "2026-07-18T00:00:00Z");
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
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
    Clock clock;

    @Autowired
    PublicBankSnapshotQueryPort snapshots;

    @Autowired
    PublicBankSnapshotMaintenancePort maintenance;

    @Autowired
    Phase4aSubjectCatalogIT.CurrentThreadSqlCounter sqlCounter;

    @BeforeEach
    void clearRedis() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @Test
    void readinessGroupIncludesSnapshotStateWithoutLeakingComponentDetails() throws Exception {
        mockMvc.perform(get("/readyz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.components").doesNotExist())
                .andExpect(jsonPath("$.details").doesNotExist());

        assertThat(jdbc.update("""
                UPDATE public_bank_plaza_snapshot_state
                   SET status = 'failed'
                 WHERE snapshot_name = 'public-bank-plaza'
                """)).isEqualTo(1);

        mockMvc.perform(get("/readyz"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.status").value("DOWN"))
                .andExpect(jsonPath("$.components").doesNotExist())
                .andExpect(jsonPath("$.details").doesNotExist());
    }

    @Test
    void allWarmLegacyGoldenCasesMatchExceptTheApprovedDifferences()
            throws Exception {
        Map<String, String> before = databaseFingerprint();
        JsonNode golden = golden();
        assertThat(golden.path("case_count").asInt()).isEqualTo(46);
        assertThat(golden.path("warm_side_effect_free").asBoolean()).isTrue();
        assertThat(clock.instant()).isEqualTo(FIXED_NOW);
        var snapshot = snapshots.summary(
                PublicBankFilter.all(), FIXED_NOW.minusSeconds(7 * 24 * 60 * 60)).snapshot();
        assertThat(snapshot.structurallyComplete()).as(snapshot.toString()).isTrue();
        assertThat(snapshot.assessAt(FIXED_NOW).available()).as(snapshot.toString()).isTrue();

        int requestNumber = 0;
        for (JsonNode goldenCase : golden.path("cases")) {
            String caseId = goldenCase.path("case_id").asString();
            if (caseId.startsWith("partial-")) {
                continue;
            }
            MvcResult result = mockMvc.perform(requestFor(goldenCase, ++requestNumber))
                    .andExpect(cookie().doesNotExist("ti_dev_session"))
                    .andExpect(header().doesNotExist("Cache-Control"))
                    .andReturn();

            JsonNode expectedResponse = goldenCase.path("response");
            assertThat(result.getResponse().getStatus())
                    .as("HTTP status for %s", caseId)
                    .isEqualTo(expectedResponse.path("status").asInt());
            String expectedContentType = ARBITRARY_PRECISION_PATH_ID_CASES.contains(caseId)
                    ? "application/json; charset=utf-8"
                    : expectedResponse.path("headers").path("Content-Type").asText();
            assertThat(result.getResponse().getContentType())
                    .as("content type for %s", caseId)
                    .isEqualTo(expectedContentType);
            assertThat(varyTokens(result))
                    .as("Vary for %s", caseId)
                    .containsExactlyInAnyOrder("Origin", "Cookie");
            if (caseId.endsWith("converter-404")) {
                assertThat(result.getResponse().getHeader("X-RateLimit-Limit")).isNull();
                assertThat(result.getResponse().getHeader("X-RateLimit-Remaining")).isNull();
                assertThat(result.getResponse().getHeader("X-RateLimit-Reset")).isNull();
                assertThat(result.getResponse().getHeader("Retry-After")).isNull();
            } else {
                assertThat(result.getResponse().getHeader("X-RateLimit-Limit"))
                        .as("rate-limit window for %s", caseId)
                        .isEqualTo("10");
                assertThat(result.getResponse().getHeader("X-RateLimit-Remaining"))
                        .as("rate-limit remaining for %s", caseId)
                        .isNotNull();
                assertThat(result.getResponse().getHeader("X-RateLimit-Reset"))
                        .as("rate-limit reset for %s", caseId)
                        .isNotNull();
                assertThat(result.getResponse().getHeader("Retry-After"))
                        .as("rate-limit retry for %s", caseId)
                        .isNotNull();
            }

            ObjectNode expectedBody = (ObjectNode) expectedResponse.path("body").deepCopy();
            ObjectNode actualBody = (ObjectNode) json.readTree(
                    result.getResponse().getContentAsByteArray());
            if (caseId.startsWith("summary-")) {
                long corrected = caseId.equals("summary-anonymous") ? 7 : 3;
                assertThat(actualBody.path("data").path("new_banks_7d").asLong())
                        .as("true rolling seven-day result for %s", caseId)
                        .isEqualTo(corrected);
                assertThat(actualBody.path("data").path("active_users_7d").asLong())
                        .as("true rolling seven-day active identities for %s", caseId)
                        .isEqualTo(5);
                expectedBody.withObject("data").remove("new_banks_7d");
                expectedBody.withObject("data").remove("active_users_7d");
                actualBody.withObject("data").remove("new_banks_7d");
                actualBody.withObject("data").remove("active_users_7d");
            }
            if (ARBITRARY_PRECISION_PATH_ID_CASES.contains(caseId)) {
                expectedBody.removeAll();
                expectedBody.put("status", "error");
                expectedBody.put("code", 1);
                expectedBody.put("message", "服务暂时不可用");
                expectedBody.put("status_code", 500);
                expectedBody.put("request_id", REQUEST_ID);
            }
            assertThat(actualBody)
                    .as("normalized response body for %s", caseId)
                    .isEqualTo(expectedBody);
        }

        assertThat(databaseFingerprint()).isEqualTo(before);
        assertOnlyPublicBankRateLimitState();
    }

    @Test
    void partialFreshSnapshotFailsClosedInsteadOfServingMixedProjectionRows() throws Exception {
        jdbc.update("DELETE FROM public_bank_plaza_metrics "
                + "WHERE NOT (source_type = 'user_public' AND source_id = 5401)");
        Map<String, String> before = databaseFingerprint();

        for (String path : List.of(
                "/api/public/banks/list",
                "/api/public/banks/5401?type=user",
                "/api/public/banks/5301?type=system")) {
            mockMvc.perform(get(path).header("X-Request-ID", "phase4a-partial"))
                    .andExpect(status().isServiceUnavailable())
                    .andExpect(jsonPath("$.status").value("error"))
                    .andExpect(jsonPath("$.code").value(1))
                    .andExpect(jsonPath("$.message").value("服务暂时不可用"))
                    .andExpect(jsonPath("$.status_code").value(503))
                    .andExpect(jsonPath("$.request_id").value("phase4a-partial"));
        }

        assertThat(databaseFingerprint()).isEqualTo(before);
        assertOnlyPublicBankRateLimitState();
    }

    @Test
    void snapshotFreshnessBoundariesAndColdMarkerAreFailClosed() throws Exception {
        assertSnapshotAgeStatus(300, 200);
        assertSnapshotAgeStatus(301, 200);
        assertSnapshotAgeStatus(900, 200);
        assertSnapshotAgeStatus(901, 503);

        jdbc.update("UPDATE public_bank_plaza_snapshot_state "
                + "SET status = 'building', updated_at = ? WHERE snapshot_name = ?",
                timestamp(FIXED_NOW), "public-bank-plaza");
        assertSummaryStatus(503);

        jdbc.update("DELETE FROM public_bank_plaza_snapshot_state "
                + "WHERE snapshot_name = ?", "public-bank-plaza");
        assertSummaryStatus(503);
    }

    @Test
    void aCommittedCompleteTombstoneRemovesVisibilityWithoutGetSideEffects() throws Exception {
        var tombstone = maintenance.tombstone(
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 5401),
                new PublicBankSnapshotCommit(
                        FIXED_NOW, 1, "synthetic:tombstone:user_public:5401"));
        assertThat(tombstone.outcome())
                .isEqualTo(PublicBankSnapshotMaintenancePort.Outcome.COMMITTED);
        Map<String, String> afterCommit = databaseFingerprint();

        mockMvc.perform(get(URI.create(
                        "/api/public/banks/list?keyword=Atlas%20Needle%20User"))
                        .header("X-Request-ID", "phase4a-tombstone-list"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(0))
                .andExpect(jsonPath("$.data.items").isEmpty());
        mockMvc.perform(get("/api/public/banks/5401?type=user")
                        .header("X-Request-ID", "phase4a-tombstone-detail"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("题库不存在或未公开"));

        assertThat(databaseFingerprint()).isEqualTo(afterCommit);
    }

    @Test
    void wrongStateDigestFailsClosedWithoutScanningOrMutatingProjectionRows() throws Exception {
        jdbc.update("UPDATE public_bank_plaza_snapshot_state "
                + "SET projection_digest = ? WHERE snapshot_name = ?",
                "c".repeat(64), "public-bank-plaza");
        Map<String, String> before = databaseFingerprint();

        mockMvc.perform(get("/api/public/banks/summary")
                        .header("X-Request-ID", "phase4a-wrong-state-digest"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.status_code").value(503))
                .andExpect(jsonPath("$.request_id").value("phase4a-wrong-state-digest"));

        assertThat(databaseFingerprint()).isEqualTo(before);
    }

    @Test
    void requestLevelSqlCountsStayConstantForAnonymousAndOptionalBearerReads() throws Exception {
        Map<String, Integer> anonymousBudgets = Map.of(
                "/api/public/banks", 2,
                "/api/public/banks/boards", 1,
                "/api/public/banks/hot", 1,
                "/api/public/banks/list", 2,
                "/api/public/banks/summary", 1,
                "/api/public/banks/5401?type=user", 1,
                "/api/public/banks/card/system/5301", 1);
        for (Map.Entry<String, Integer> route : anonymousBudgets.entrySet()) {
            assertSqlBudget(route.getKey(), null, route.getValue());
        }

        String bearer = jwt(VIEWERS.get("public"));
        Map<String, Integer> bearerBudgets = Map.of(
                "/api/public/banks", 3,
                "/api/public/banks/boards", 2,
                "/api/public/banks/hot", 2,
                "/api/public/banks/list", 3,
                "/api/public/banks/summary", 2,
                "/api/public/banks/5401?type=user", 2,
                "/api/public/banks/card/user/5401", 2);
        for (Map.Entry<String, Integer> route : bearerBudgets.entrySet()) {
            assertSqlBudget(route.getKey(), bearer, route.getValue());
        }
    }

    private void assertSnapshotAgeStatus(long ageSeconds, int status) throws Exception {
        jdbc.update("UPDATE public_bank_plaza_snapshot_state "
                + "SET status = 'complete', last_success_at = ?, updated_at = ? "
                + "WHERE snapshot_name = ?",
                timestamp(FIXED_NOW.minusSeconds(ageSeconds)), timestamp(FIXED_NOW),
                "public-bank-plaza");
        assertSummaryStatus(status);
    }

    private void assertSqlBudget(String path, String bearer, int expectedStatements)
            throws Exception {
        MockHttpServletRequestBuilder request = get(URI.create(path))
                .header("X-Request-ID", "phase4a-sql-budget");
        if (bearer != null) {
            request.header("Authorization", "Bearer " + bearer);
        }
        List<String> statements;
        sqlCounter.start();
        try {
            mockMvc.perform(request).andExpect(status().isOk());
        } finally {
            statements = sqlCounter.stop();
        }
        assertThat(statements)
                .as("constant SELECT budget for %s, bearer=%s", path, bearer != null)
                .hasSize(expectedStatements)
                .allMatch(sql -> sql.startsWith("select ") || sql.startsWith("with "))
                .noneMatch(sql -> sql.matches(".*\\b(insert|update|delete|merge)\\b.*"));
    }

    private void assertSummaryStatus(int expectedStatus) throws Exception {
        assertThat(mockMvc.perform(get("/api/public/banks/summary")
                        .header("X-Request-ID", "phase4a-freshness"))
                .andReturn().getResponse().getStatus()).isEqualTo(expectedStatus);
    }

    private MockHttpServletRequestBuilder requestFor(JsonNode goldenCase, int requestNumber) {
        String path = goldenCase.path("request").path("path").asString();
        String actor = goldenCase.path("actor").asString();
        URI encodedUri = URI.create(URI.create(path).toASCIIString());
        MockHttpServletRequestBuilder request = get(encodedUri)
                .header("X-Request-ID", REQUEST_ID)
                .with(servletRequest -> {
                    servletRequest.setRemoteAddr("198.51.100." + requestNumber);
                    return servletRequest;
                });
        if (actor.equals("invalid_jwt")) {
            request.header(
                    "Authorization",
                    String.join(" ", "Bearer", "not-a-valid-phase4a-jwt"));
        } else if (!actor.equals("anonymous")) {
            ViewerFixture viewer = Objects.requireNonNull(VIEWERS.get(actor), actor);
            request.header("Authorization", "Bearer " + jwt(viewer));
        }
        return request;
    }

    private JsonNode golden() throws Exception {
        Path file = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .getParent()
                .resolve("docs/refactor/phase4a/golden-public-bank-reads.json");
        return json.readTree(Files.readString(file, StandardCharsets.UTF_8));
    }

    private Map<String, String> databaseFingerprint() {
        Map<String, String> result = new LinkedHashMap<>();
        for (String table : Set.of(
                "users",
                "plaza_boards",
                "public_bank_plaza_metrics",
                "public_bank_plaza_viewer_state",
                "public_bank_plaza_snapshot_state")) {
            result.put(table, jdbc.queryForObject(
                    "SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), "
                            + "'[]'::jsonb)::text FROM " + table + " t",
                    String.class));
        }
        return result;
    }

    private void assertOnlyPublicBankRateLimitState() {
        Set<String> keys = redis.keys("*");
        assertThat(keys)
                .as("only endpoint-scoped, HMAC-pseudonymous public-bank rate keys may exist")
                .isNotEmpty()
                .allMatch(key -> PUBLIC_BANK_RATE_KEY.matcher(key).matches())
                .noneMatch(key -> key.contains("198.51.100")
                        || key.matches(".*:(4101|4102|4103|4104|4105):.*")
                        || key.contains(":sessions:"));
        for (String key : keys) {
            String value = redis.opsForValue().get(key);
            if (value != null) {
                assertThat(value).as("integer limiter counter for %s", key)
                        .matches("[1-9][0-9]*");
            } else {
                assertThat(key).as("only the one-second counter may expire during inspection")
                        .endsWith(":second");
            }
        }
    }

    private static Set<String> varyTokens(MvcResult result) {
        String vary = Objects.requireNonNull(result.getResponse().getHeader("Vary"));
        return Set.of(vary.split(",\\s*"));
    }

    private static String jwt(ViewerFixture viewer) {
        long issuedAt = FIXED_NOW.minusSeconds(60).getEpochSecond();
        long expiresAt = FIXED_NOW.plusSeconds(86_400).getEpochSecond();
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + viewer.identityId()
                + ",\"openid\":\"\",\"session_version\":" + viewer.sessionVersion()
                + ",\"exp\":" + expiresAt
                + ",\"iat\":" + issuedAt
                + ",\"jti\":\"" + String.format("%032x", viewer.identityId()) + "\"}";
        String unsigned = base64Url(header) + "." + base64Url(payload);
        try {
            Mac hmac = Mac.getInstance("HmacSHA256");
            hmac.init(new SecretKeySpec(
                    LEGACY_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return unsigned + "." + Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(hmac.doFinal(unsigned.getBytes(StandardCharsets.US_ASCII)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HmacSHA256 must be available", exception);
        }
    }

    private static String base64Url(String value) {
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static OffsetDateTime timestamp(Instant value) {
        return OffsetDateTime.ofInstant(value, ZoneOffset.UTC);
    }

    private record ViewerFixture(long identityId, int sessionVersion) {}

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class FixedPublicBankClock {

        @Bean
        @Primary
        Clock publicBankClock() {
            return Clock.fixed(FIXED_NOW, ZoneOffset.UTC);
        }
    }
}
