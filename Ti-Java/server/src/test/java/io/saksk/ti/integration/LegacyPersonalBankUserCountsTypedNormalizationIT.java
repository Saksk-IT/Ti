package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import com.redis.testcontainers.RedisContainer;
import com.zaxxer.hikari.HikariDataSource;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource.Family;
import io.saksk.ti.support.Phase4cUserCountsFaultInjectingDataSource.TraceSnapshot;
import jakarta.servlet.http.Cookie;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
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

/**
 * Successor evidence for the one golden disposition whose offset-aware string is representable
 * by the production PostgreSQL timestamp-without-time-zone column.
 */
@Testcontainers
@ActiveProfiles("test")
@AutoConfigureMockMvc
@SpringBootTest(classes = TiApplication.class)
@Import({
        LegacyPersonalBankUserCountsTypedNormalizationIT.FixedEvidenceClock.class,
        LegacyPersonalBankUserCountsTypedNormalizationIT.TracingDataSourceConfiguration.class
})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Execution(ExecutionMode.SAME_THREAD)
class LegacyPersonalBankUserCountsTypedNormalizationIT {

    private static final Instant CAPTURED_NOW =
            Instant.ofEpochSecond(Instant.now().getEpochSecond());
    private static final Instant HISTORICAL_BEIJING_NOON =
            Instant.parse("2026-07-17T04:00:00Z");
    private static final String POSITIVE_OFFSET_EXPIRY =
            "2026-07-17T13:00:00+08:00";
    private static final String NEGATIVE_OFFSET_EXPIRY =
            "2026-07-17T13:00:00-05:00";
    private static final LocalDateTime CANONICAL_EXPIRY =
            LocalDateTime.parse("2026-07-17T13:00:00");
    private static final List<String> CAST_SESSION_TIME_ZONES =
            List.of("UTC", "America/Los_Angeles");
    private static final String GOLDEN_PATH =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String AWARE_CASE_ID = "access-shared-aware-expiry-type-error";
    private static final String REDIS_PASSWORD = "phase4c-typed-normalization-redis";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final byte[] LEGACY_SECRET_BYTES =
            LEGACY_SECRET.getBytes(StandardCharsets.UTF_8);
    private static final long AWARE_ACTOR_ID = 99_462L;
    private static final int PRIVATE_BANK_ID = 99_551;
    private static final int PUBLIC_BANK_ID = 99_555;
    private static final String RATE_NAMESPACE =
            "ti-java:learning:personal-bank-user-counts-typed-normalization";
    private static final Pattern RATE_KEY = Pattern.compile(
            "^" + Pattern.quote(RATE_NAMESPACE)
                    + ":api:identity:v1:[0-9a-f]{64}:(?:second|hour|day)$");
    private static final List<String> EXPECTED_TYPES =
            List.of("判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题");

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
                    "/docker-entrypoint-initdb.d/071-personal-bank-user-counts-golden-target-seed.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource(
                            "db/phase4c/072-personal-bank-user-counts-typed-normalization-seed.sql"),
                    "/docker-entrypoint-initdb.d/072-personal-bank-user-counts-typed-normalization-seed.sql");

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

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
                () -> "ti-java:phase4c:user-counts-typed-normalization-sessions");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase4c-typed-normalization-login-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add("ti.security.legacy-auth.accept-until",
                () -> CAPTURED_NOW.plus(Duration.ofDays(1)).toString());
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
                () -> "phase4c-typed-normalization-rate-key-secret-0001");
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

    @Autowired
    EvidenceClock evidenceClock;

    private Cookie targetSession;
    private JsonNode awareGoldenCase;

    @BeforeEach
    void proveFixtureAndCreateARealTargetSession() throws Exception {
        evidenceClock.set(CAPTURED_NOW);
        clearRedis();
        JsonNode golden = json.readTree(Files.readAllBytes(Path.of(Objects.requireNonNull(
                        System.getProperty("basedir")))
                .getParent()
                .resolve(GOLDEN_PATH)));
        List<JsonNode> matchingCases = new ArrayList<>();
        golden.path("cases").forEach(goldenCase -> {
            if (AWARE_CASE_ID.equals(goldenCase.path("case_id").asString())) {
                matchingCases.add(goldenCase);
            }
        });
        assertThat(matchingCases).singleElement();
        awareGoldenCase = matchingCases.getFirst();
        assertThat(awareGoldenCase.path("route_id").asString()).isEqualTo("6858f6fa506f");
        assertThat(awareGoldenCase.path("bank_id").asInt()).isEqualTo(PRIVATE_BANK_ID);
        assertThat(awareGoldenCase.path("session_actor").asString())
                .isEqualTo("shared_aware");
        assertThat(awareGoldenCase.path("bearer_actor").asString()).isEqualTo("none");
        assertThat(awareGoldenCase.path("request").path("method").asString())
                .isEqualTo("GET");
        assertThat(awareGoldenCase.path("response").path("status").asInt()).isEqualTo(500);

        JdbcTemplate postgres16 = new JdbcTemplate(new DriverManagerDataSource(
                POSTGRES_16.getJdbcUrl(),
                POSTGRES_16.getUsername(),
                POSTGRES_16.getPassword()));
        List<CastProjection> postgres16Projections = assertStringBindCastCompatibility(
                POSTGRES_16,
                postgres16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
        List<CastProjection> postgres18Projections = assertStringBindCastCompatibility(
                POSTGRES,
                jdbc,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
        assertThat(postgres18Projections)
                .as("PostgreSQL 16.14 and 18.4 must erase offsets identically")
                .isEqualTo(postgres16Projections);

        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM bank_shares WHERE id = 99661",
                Long.class)).isZero();
        assertThat(jdbc.update("""
                INSERT INTO bank_shares (
                    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
                    max_uses, current_uses, is_active, created_at
                ) VALUES (
                    99661, 99551, 99451, 'C00011', 'user-count-token-0011', 'read',
                    CAST(? AS timestamp without time zone),
                    NULL, 11, true, TIMESTAMP '2026-07-17 08:11:00'
                )
                """, POSITIVE_OFFSET_EXPIRY)).isEqualTo(1);
        assertThat(jdbc.update("""
                INSERT INTO bank_share_records (
                    id, share_id, bank_id, user_id, status,
                    last_access_at, access_count, created_at
                ) VALUES (
                    99681, 99661, 99551, 99462, 1,
                    TIMESTAMP '2026-07-17 09:11:00', 11,
                    TIMESTAMP '2026-07-17 08:11:00'
                )
                """)).isEqualTo(1);

        assertThat(CANONICAL_EXPIRY).isAfter(LocalDateTime.ofInstant(
                HISTORICAL_BEIJING_NOON,
                java.time.ZoneId.of("Asia/Shanghai")));
        assertThat(jdbc.queryForObject(
                "SELECT expires_at FROM bank_shares WHERE id = 99661",
                LocalDateTime.class)).isEqualTo(CANONICAL_EXPIRY);
        assertThat(jdbc.queryForObject(
                "SELECT pg_typeof(expires_at)::text FROM bank_shares WHERE id = 99661",
                String.class)).isEqualTo("timestamp without time zone");
        assertThat(jdbc.queryForMap("""
                SELECT share_id, bank_id, user_id, status
                FROM bank_share_records
                WHERE id = 99681
                """))
                .containsEntry("share_id", 99_661)
                .containsEntry("bank_id", PRIVATE_BANK_ID)
                .containsEntry("user_id", 99_462)
                .containsEntry("status", 1);

        targetSession = exchangeFlaskSession();
        clearRouteRateLimits();
        evidenceClock.set(HISTORICAL_BEIJING_NOON);
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM users WHERE last_active IS NOT NULL",
                Long.class)).isZero();
    }

    private static List<CastProjection> assertStringBindCastCompatibility(
            PostgreSQLContainer postgres,
            JdbcTemplate runtime,
            String expectedImage,
            String expectedVersion
    ) {
        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(runtime.queryForObject("SHOW server_version", String.class))
                .isEqualTo(expectedVersion);
        List<CastProjection> projections = CAST_SESSION_TIME_ZONES.stream()
                .map(zone -> projectStringBinds(runtime, zone))
                .toList();
        assertThat(projections)
                .extracting(CastProjection::positiveOffset)
                .containsOnly(CANONICAL_EXPIRY);
        assertThat(projections)
                .extracting(CastProjection::negativeOffset)
                .containsOnly(CANONICAL_EXPIRY);
        assertThat(projections)
                .extracting(CastProjection::sessionTimeZone)
                .containsExactlyElementsOf(CAST_SESSION_TIME_ZONES);
        return projections;
    }

    private static CastProjection projectStringBinds(
            JdbcTemplate runtime,
            String sessionTimeZone
    ) {
        return runtime.execute((Connection connection) -> {
            String originalTimeZone = currentTimeZone(connection);
            try {
                setTimeZone(connection, sessionTimeZone);
                try (PreparedStatement statement = connection.prepareStatement("""
                        SELECT
                            CAST(? AS timestamp without time zone),
                            CAST(? AS timestamp without time zone),
                            current_setting('TimeZone')
                        """)) {
                    statement.setString(1, POSITIVE_OFFSET_EXPIRY);
                    statement.setString(2, NEGATIVE_OFFSET_EXPIRY);
                    try (ResultSet result = statement.executeQuery()) {
                        assertThat(result.next()).isTrue();
                        CastProjection projection = new CastProjection(
                                result.getObject(1, LocalDateTime.class),
                                result.getObject(2, LocalDateTime.class),
                                result.getString(3));
                        assertThat(result.next()).isFalse();
                        return projection;
                    }
                }
            } catch (SQLException failure) {
                throw new IllegalStateException(
                        "typed-normalization String bind projection failed", failure);
            } finally {
                setTimeZone(connection, originalTimeZone);
            }
        });
    }

    private static String currentTimeZone(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT current_setting('TimeZone')");
             ResultSet result = statement.executeQuery()) {
            if (!result.next()) {
                throw new SQLException("PostgreSQL did not return the current TimeZone");
            }
            return result.getString(1);
        }
    }

    private static void setTimeZone(Connection connection, String timeZone) {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT set_config('TimeZone', ?, false)")) {
            statement.setString(1, timeZone);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next() || !timeZone.equals(result.getString(1))) {
                    throw new SQLException("PostgreSQL rejected the requested TimeZone");
                }
            }
        } catch (SQLException failure) {
            throw new IllegalStateException(
                    "cannot set typed-normalization PostgreSQL TimeZone", failure);
        }
    }

    @Test
    void executesAwareExpiryAsARealFullFilterChainHttpRead() throws Exception {
        String databaseBefore = databaseFingerprint();
        sqlTrace.start(null);
        MvcResult result;
        TraceSnapshot trace;
        try {
            JsonNode request = awareGoldenCase.path("request");
            result = mockMvc.perform(get(request.path("path").asString())
                            .cookie(targetSession)
                            .header(
                                    HttpHeaders.ACCEPT,
                                    request.path("headers").path("Accept").asString())
                            .header(
                                    "X-Request-ID",
                                    request.path("headers").path("X-Request-ID").asString())
                            .with(raw -> {
                                raw.setRemoteAddr(request.path("remote_address").asString());
                                return raw;
                            }))
                    .andReturn();
        } finally {
            trace = sqlTrace.stop();
        }

        assertThat(result.getResponse().getStatus()).isEqualTo(200);
        assertThat(result.getResponse().getContentType())
                .isEqualTo("application/json; charset=utf-8");
        assertThat(result.getResponse().getHeader("X-Request-ID"))
                .isEqualTo("phase4b-personal-bank-user-counts-golden-request");
        assertThat(result.getResponse().getHeader("X-RateLimit-Limit")).isEqualTo("1000");
        assertThat(result.getResponse().getHeader("X-RateLimit-Remaining")).isEqualTo("999");
        assertThat(Long.parseLong(Objects.requireNonNull(
                result.getResponse().getHeader("X-RateLimit-Reset"))))
                .isGreaterThan(HISTORICAL_BEIJING_NOON.getEpochSecond());
        assertThat(result.getResponse().getHeader("X-Content-Type-Options"))
                .isEqualTo("nosniff");
        assertThat(result.getResponse().getHeader("X-Frame-Options"))
                .isEqualTo("SAMEORIGIN");
        assertThat(result.getResponse().getHeader("Referrer-Policy"))
                .isEqualTo("strict-origin-when-cross-origin");
        assertThat(result.getResponse().getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .isNull();

        JsonNode body = json.readTree(result.getResponse().getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("success");
        assertThat(body.path("code").asInt()).isZero();
        assertThat(body.path("message").asString()).isEmpty();
        assertThat(body.path("request_id").asString())
                .isEqualTo("phase4b-personal-bank-user-counts-golden-request");
        JsonNode data = body.path("data");
        assertThat(data.path("total").asLong()).isEqualTo(9L);
        assertThat(data.path("favorites").asLong()).isZero();
        assertThat(data.path("mistakes").asLong()).isZero();
        List<String> actualTypes = new ArrayList<>();
        data.path("types").forEach(type -> actualTypes.add(type.asString()));
        assertThat(actualTypes).containsExactlyElementsOf(EXPECTED_TYPES);
        assertThat(data.path("shuffle_options_available").asBoolean()).isFalse();

        assertThat(trace.faults()).isEmpty();
        assertThat(trace.rollbacks()).isEmpty();
        assertThat(trace.occurrenceCount(Family.AUTHORITY_USERS)).isEqualTo(1);
        assertThat(trace.occurrenceCount(Family.BANK_ACCESS)).isEqualTo(5);
        assertThat(trace.occurrenceCount(Family.SHARE_ACCESS)).isEqualTo(5);
        assertThat(trace.occurrenceCount(Family.FAVORITE_MEMBERSHIP)).isEqualTo(1);
        assertThat(trace.occurrenceCount(Family.MISTAKE_MEMBERSHIP)).isEqualTo(1);
        assertThat(trace.occurrenceCount(Family.QUESTION_SUMMARY)).isEqualTo(2);
        assertThat(trace.occurrenceCount(Family.TAG_MEMBERSHIP)).isZero();
        assertThat(trace.executions())
                .filteredOn(execution -> execution.family() != Family.AUTHORITY_USERS)
                .allMatch(Phase4cUserCountsFaultInjectingDataSource.Execution::connectionReadOnly);
        assertThat(trace.writeDmlCount()).isZero();
        assertThat(trace.usersLastActiveWriteDmlCount()).isZero();
        assertThat(trace.schemaMutationCount()).isZero();
        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
        assertThat(jdbc.queryForObject(
                "SELECT COUNT(*) FROM users WHERE last_active IS NOT NULL",
                Long.class)).isZero();

        Set<String> keys = redis.keys(RATE_NAMESPACE + ":*");
        assertThat(keys)
                .isNotNull()
                .hasSize(3)
                .allMatch(key -> RATE_KEY.matcher(key).matches())
                .anyMatch(key -> key.endsWith(":second"))
                .anyMatch(key -> key.endsWith(":hour"))
                .anyMatch(key -> key.endsWith(":day"));
        assertThat(keys).allMatch(key -> "1".equals(redis.opsForValue().get(key)));
    }

    private Cookie exchangeFlaskSession() throws Exception {
        MvcResult result = mockMvc.perform(get(
                        "/api/user/banks/api/{bankId}/user-counts", PUBLIC_BANK_ID)
                        .cookie(new Cookie("session", signedFlaskCookie()))
                        .header("X-Request-ID", "phase4c-aware-expiry-session")
                        .with(request -> {
                            request.setRemoteAddr("198.18.0.162");
                            return request;
                        }))
                .andReturn();
        assertThat(result.getResponse().getStatus()).isEqualTo(200);
        Cookie issued = result.getResponse().getCookie("ti_dev_session");
        assertThat(issued).isNotNull();
        return new Cookie(issued.getName(), issued.getValue());
    }

    private static String signedFlaskCookie() {
        String payload = "{\"user_id\":" + AWARE_ACTOR_ID
                + ",\"username\":\"phase4b_counts_shared_aware\""
                + ",\"session_version\":11"
                + ",\"remember\":false"
                + ",\"csrf_token\":\"typed-normalization\"}";
        String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
        String encodedTimestamp = encode(minimalBigEndian(CAPTURED_NOW.getEpochSecond()));
        String unsigned = encodedPayload + "." + encodedTimestamp;
        byte[] derived = hmac(
                "HmacSHA1",
                LEGACY_SECRET_BYTES,
                "cookie-session".getBytes(StandardCharsets.UTF_8));
        byte[] signature = hmac(
                "HmacSHA1", derived, unsigned.getBytes(StandardCharsets.US_ASCII));
        Arrays.fill(derived, (byte) 0);
        return unsigned + "." + encode(signature);
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

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class FixedEvidenceClock {

        @Bean
        @Primary
        EvidenceClock typedNormalizationClock() {
            return new EvidenceClock(CAPTURED_NOW);
        }
    }

    static final class EvidenceClock extends Clock {

        private final AtomicReference<Instant> instant;

        private EvidenceClock(Instant initial) {
            instant = new AtomicReference<>(Objects.requireNonNull(initial, "initial"));
        }

        private void set(Instant value) {
            instant.set(Objects.requireNonNull(value, "value"));
        }

        @Override
        public ZoneOffset getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(java.time.ZoneId zone) {
            if (!ZoneOffset.UTC.equals(Objects.requireNonNull(zone, "zone"))) {
                throw new IllegalArgumentException("typed-normalization evidence clock is UTC");
            }
            return this;
        }

        @Override
        public Instant instant() {
            return instant.get();
        }
    }

    private record CastProjection(
            LocalDateTime positiveOffset,
            LocalDateTime negativeOffset,
            String sessionTimeZone
    ) {
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class TracingDataSourceConfiguration {

        @Bean
        @Primary
        Phase4cUserCountsFaultInjectingDataSource typedNormalizationDataSource(
                DataSourceProperties properties
        ) {
            HikariDataSource target = properties.initializeDataSourceBuilder()
                    .type(HikariDataSource.class)
                    .build();
            return new Phase4cUserCountsFaultInjectingDataSource(target);
        }
    }
}
