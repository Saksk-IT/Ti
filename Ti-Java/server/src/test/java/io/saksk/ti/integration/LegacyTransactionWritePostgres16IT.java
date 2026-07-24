package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.List;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
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
import tools.jackson.databind.ObjectMapper;

/** PostgreSQL 16 compatibility execution of all nine writes through the real filter chain. */
@Testcontainers
@ActiveProfiles("test")
@SpringBootTest(
        classes = TiApplication.class,
        properties = "management.endpoint.health.validate-group-membership=false")
@AutoConfigureMockMvc
@Import(LegacyTransactionWritePostgres16IT.FixedEvidenceClock.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Execution(ExecutionMode.SAME_THREAD)
class LegacyTransactionWritePostgres16IT {

    private static final long USER_ID = 99_451L;
    private static final int USER_SESSION_VERSION = 11;
    private static final long ADMIN_ID = 99_452L;
    private static final int ADMIN_SESSION_VERSION = 13;
    private static final String REDIS_PASSWORD = "phase4c-write-pg16-redis";
    private static final String ALLOWED_ORIGIN = "https://write-pg16.example";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final Instant CAPTURED_NOW =
            Instant.ofEpochSecond(Instant.now().getEpochSecond());
    private static final Instant EXPIRES_AT =
            CAPTURED_NOW.plus(Duration.ofHours(1));
    private static final String USER_BEARER =
            bearer(USER_ID, USER_SESSION_VERSION);
    private static final String ADMIN_BEARER =
            bearer(ADMIN_ID, ADMIN_SESSION_VERSION);
    private static final List<WriteCase> WRITES = List.of(
            new WriteCase(
                    "POST",
                    "/api/favorite",
                    "{\"question_id\":93001}",
                    USER_BEARER,
                    30),
            new WriteCase(
                    "POST",
                    "/api/quiz/favorite",
                    "{\"question_id\":93007}",
                    USER_BEARER,
                    30),
            new WriteCase(
                    "POST",
                    "/api/record_result",
                    "{\"question_id\":93002,\"is_correct\":false}",
                    USER_BEARER,
                    60),
            new WriteCase(
                    "POST",
                    "/api/quiz/record_result",
                    "{\"question_id\":93008,\"is_correct\":true}",
                    USER_BEARER,
                    60),
            new WriteCase(
                    "POST",
                    "/api/quiz/study/learn/record",
                    "{\"question_id\":93003,\"is_correct\":true,"
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    USER_BEARER,
                    60),
            new WriteCase(
                    "POST",
                    "/api/quiz/study/review/record",
                    "{\"question_id\":93004,\"rating\":\"known\","
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    USER_BEARER,
                    60),
            new WriteCase(
                    "POST",
                    "/api/quiz/study/review/master",
                    "{\"question_id\":93005,\"is_mastered\":true,"
                            + "\"source\":\"public\","
                            + "\"subject\":\"Phase 2 reference subject\"}",
                    USER_BEARER,
                    30),
            new WriteCase(
                    "POST",
                    "/api/user/checkin",
                    null,
                    USER_BEARER,
                    10),
            new WriteCase(
                    "PUT",
                    "/api/quiz/questions/93006",
                    "{\"content\":\"Updated through PostgreSQL 16\"}",
                    ADMIN_BEARER,
                    10));

    @Container
    static final PostgreSQLContainer POSTGRES =
            Phase2PostgresContainers.compatibility16()
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
        registry.add(
                "spring.session.data.redis.namespace",
                () -> "ti-java:phase4c:transaction-write-pg16-sessions");
        registry.add(
                "ti.security.login-rate-limit.key-secret",
                () -> "phase4c-write-pg16-login-rate-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add(
                "ti.security.legacy-auth.accept-until",
                () -> CAPTURED_NOW.plus(Duration.ofDays(1)).toString());
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
        registry.add(
                "ti.security.transaction-write-rate-limit.namespace",
                () -> "ti-java:web:phase4c-transaction-write-pg16-rate");
        registry.add(
                "ti.security.transaction-write-rate-limit.multiplier",
                () -> "1");
        registry.add(
                "ti.security.transaction-write-rate-limit.key-secret",
                () -> "phase4c-write-pg16-rate-key-secret-0001");
        registry.add(
                "ti.security.transaction-write-cors.allowed-origins",
                () -> ALLOWED_ORIGIN);
        registry.add(
                "ti.learning.write-idempotency.key-secret",
                () -> "phase4c-write-pg16-learning-receipt-key-0001");
        registry.add(
                "ti.catalog.question-edit-idempotency.key-secret",
                () -> "phase4c-write-pg16-catalog-receipt-key-0001");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper json;

    @Autowired
    JdbcTemplate jdbc;

    @Test
    @Timeout(value = 90)
    void allNineHttpTransactionsCommitOnPostgres16WithoutIdentityDml()
            throws Exception {
        assertThat(POSTGRES.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.POSTGRES_16_COMPATIBILITY);
        assertThat(jdbc.queryForObject("SHOW server_version", String.class))
                .isEqualTo("16.14");

        int index = 0;
        for (WriteCase write : WRITES) {
            String requestId = "phase4c-write-pg16-" + index;
            var builder = request(
                            HttpMethod.valueOf(write.method()),
                            write.path())
                    .accept(MediaType.APPLICATION_JSON)
                    .contentType(MediaType.APPLICATION_JSON)
                    .header(HttpHeaders.ORIGIN, ALLOWED_ORIGIN)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + write.bearer())
                    .header("X-Request-ID", requestId)
                    .header("Idempotency-Key", "phase4c-write-pg16-key-" + index);
            if (write.body() != null) {
                builder.content(write.body());
            }
            MvcResult result = mockMvc.perform(builder)
                    .andExpect(status().isOk())
                    .andExpect(header().string(
                            HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
                            ALLOWED_ORIGIN))
                    .andExpect(header().string(
                            "X-RateLimit-Limit",
                            Integer.toString(write.limit())))
                    .andExpect(header().string("X-Request-ID", requestId))
                    .andReturn();
            assertThat(json.readTree(result.getResponse().getContentAsByteArray())
                    .path("status").asString()).isEqualTo("success");
            index++;
        }

        assertThat(count("favorites")).isEqualTo(2);
        assertThat(count("user_answers")).isEqualTo(2);
        assertThat(count("study_learning")).isEqualTo(1);
        assertThat(count("study_review")).isEqualTo(2);
        assertThat(count("user_checkins")).isEqualTo(1);
        assertThat(count("learning_idempotency_receipts")).isEqualTo(8);
        assertThat(count("catalog_question_edit_commands")).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "SELECT content FROM questions WHERE id = 93006",
                String.class)).isEqualTo("Updated through PostgreSQL 16");
        assertThat(count("identity_write_audit")).isZero();
        assertThat(jdbc.queryForList(
                "SELECT last_active FROM users ORDER BY id"))
                .extracting(row -> row.get("last_active"))
                .containsExactly(
                        java.sql.Timestamp.valueOf("2026-01-01 00:00:00"),
                        java.sql.Timestamp.valueOf("2026-01-02 00:00:00"));
    }

    private long count(String table) {
        if (!SetHolder.TABLES.contains(table)) {
            throw new IllegalArgumentException("Unapproved count table");
        }
        return jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Long.class);
    }

    private static String bearer(long identityId, int sessionVersion) {
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + identityId
                + ",\"openid\":\"\",\"session_version\":" + sessionVersion
                + ",\"exp\":" + EXPIRES_AT.getEpochSecond()
                + ",\"iat\":" + CAPTURED_NOW.getEpochSecond()
                + ",\"jti\":\"" + String.format("%032x", identityId) + "\"}";
        String unsigned = encode(header.getBytes(StandardCharsets.UTF_8))
                + "."
                + encode(payload.getBytes(StandardCharsets.UTF_8));
        return unsigned + "." + encode(hmac(
                LEGACY_SECRET.getBytes(StandardCharsets.UTF_8),
                unsigned.getBytes(StandardCharsets.US_ASCII)));
    }

    private static byte[] hmac(byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(value);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("HmacSHA256 unavailable", exception);
        }
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private record WriteCase(
            String method,
            String path,
            String body,
            String bearer,
            int limit
    ) {
    }

    private static final class SetHolder {

        private static final java.util.Set<String> TABLES = java.util.Set.of(
                "favorites",
                "user_answers",
                "study_learning",
                "study_review",
                "user_checkins",
                "learning_idempotency_receipts",
                "catalog_question_edit_commands",
                "identity_write_audit");

        private SetHolder() {
        }
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedEvidenceClock {

        @Bean
        @Primary
        Clock postgres16EvidenceClock() {
            return Clock.fixed(CAPTURED_NOW, ZoneOffset.UTC);
        }
    }
}
