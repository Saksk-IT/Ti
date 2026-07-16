package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.cookie;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.redis.testcontainers.RedisContainer;
import com.zaxxer.hikari.HikariDataSource;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import jakarta.servlet.http.Cookie;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DelegatingDataSource;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
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
        Phase4aSubjectCatalogIT.FixedPhase4aClock.class,
        Phase4aSubjectCatalogIT.SqlCountingDataSourceConfiguration.class
})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Sql(scripts = "classpath:db/phase4a/041-subject-catalog-seed.sql",
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class Phase4aSubjectCatalogIT {

    private static final String REDIS_PASSWORD = "phase4a-ephemeral-redis";
    private static final String ORDINARY_JWT =
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                    + "eyJ1c2VyX2lkIjo0MTAxLCJvcGVuaWQiOiIiLCJzZXNzaW9uX3ZlcnNpb24iOjMs"
                    + "ImV4cCI6MTc4NTQ1NjAwMCwiaWF0IjoxNzg0MTYwMDAwLCJqdGkiOiI0MTAxMDAw"
                    + "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCJ9."
                    + "NSc7AU2c4cDNz-4sOwzeDt_TNtXFmtK4POoUdStgor0";
    private static final String ADMINISTRATOR_JWT =
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                    + "eyJ1c2VyX2lkIjo0MTAyLCJvcGVuaWQiOiIiLCJzZXNzaW9uX3ZlcnNpb24iOjUs"
                    + "ImV4cCI6MTc4NTQ1NjAwMCwiaWF0IjoxNzg0MTYwMDAwLCJqdGkiOiI0MTAyMDAw"
                    + "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMCJ9."
                    + "rfgOlTyDvpS39UvUTBCK1ycCCLl_hj0i_w5OY_vaVZo";

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.reference18()
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                    "/docker-entrypoint-initdb.d/030-auth-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase4a/040-subject-catalog-schema.sql"),
                    "/docker-entrypoint-initdb.d/040-subject-catalog-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase4a/041-subject-catalog-seed.sql"),
                    "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql");

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
        registry.add("spring.session.data.redis.namespace", () -> "ti-java:phase4a:sessions");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase4a-test-only-login-rate-key-secret-0001");
        registry.add("ti.security.subject-read-rate-limit.requests-per-minute", () -> "60");
        registry.add("ti.security.subject-read-rate-limit.requests-per-hour", () -> "600");
        registry.add("ti.security.subject-read-rate-limit.multiplier", () -> "1");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add("ti.security.legacy-auth.accept-until", () -> "2026-07-18T00:00:00Z");
        registry.add("ti.security.legacy-auth.secret",
                () -> "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum");
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
    CurrentThreadSqlCounter sqlCounter;

    @BeforeEach
    void clearRedis() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
    }

    @Test
    void everyLegacyGoldenCaseMatchesInOrderWithoutBusinessStateMutation() throws Exception {
        Map<String, String> databaseBefore = databaseFingerprint();
        assertThat(redis.keys("*")).isEmpty();

        JsonNode golden = json.readTree(Files.readString(
                Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                        .getParent()
                        .resolve("docs/refactor/phase4a/golden-subject-reads.json"),
                StandardCharsets.UTF_8));
        assertThat(golden.path("database_side_effect_free").asBoolean()).isTrue();
        assertThat(golden.path("cases")).hasSize(7);

        for (JsonNode goldenCase : golden.path("cases")) {
            String caseId = goldenCase.path("case_id").asString();
            String path = goldenCase.path("request").path("path").asString();
            String actor = goldenCase.path("actor").asString();
            if (caseId.equals("subjects-rate-limited")) {
                for (int requestNumber = 2; requestNumber <= 60; requestNumber++) {
                    mockMvc.perform(get(path)
                                    .header("Authorization", "Bearer " + ORDINARY_JWT)
                                    .header("X-Request-ID", "phase4a-rate-primer-" + requestNumber))
                            .andExpect(status().isOk());
                }
            }

            var request = get(path).header("X-Request-ID", "phase4a-" + caseId);
            if (actor.equals("ordinary")) {
                request.header("Authorization", "Bearer " + ORDINARY_JWT);
            } else if (actor.equals("administrator")) {
                request.header("Authorization", "Bearer " + ADMINISTRATOR_JWT);
            }
            MvcResult result = mockMvc.perform(request)
                    .andExpect(cookie().doesNotExist("ti_dev_session"))
                    .andReturn();

            JsonNode expectedResponse = goldenCase.path("response");
            assertThat(result.getResponse().getStatus())
                    .as("HTTP status for %s", caseId)
                    .isEqualTo(expectedResponse.path("status").asInt());
            assertThat(result.getResponse().getHeader("Cache-Control")).isNull();
            JsonNode expectedHeaders = expectedResponse.path("headers");
            for (String headerName : List.of(
                    "Content-Type",
                    "Vary",
                    "X-RateLimit-Limit",
                    "X-RateLimit-Remaining",
                    "X-RateLimit-Reset",
                    "Retry-After")) {
                if (!expectedHeaders.has(headerName)) {
                    continue;
                }
                String actualHeader = result.getResponse().getHeader(headerName);
                if (headerName.equals("X-RateLimit-Reset")) {
                    assertThat(actualHeader).matches("[1-9][0-9]*");
                } else if (headerName.equals("Retry-After")
                        && expectedHeaders.path(headerName).asString()
                                .equals("<dynamic-positive-seconds>")) {
                    assertThat(actualHeader)
                            .as("%s for %s", headerName, caseId)
                            .matches("(?:[1-9]|[1-5][0-9]|60)");
                } else {
                    assertThat(actualHeader)
                            .as("%s for %s", headerName, caseId)
                            .isEqualTo(expectedHeaders.path(headerName).asString());
                }
            }

            JsonNode actualBody = json.readTree(result.getResponse().getContentAsByteArray());
            assertThat(actualBody).isInstanceOf(ObjectNode.class);
            ((ObjectNode) actualBody).remove("request_id");
            assertThat(actualBody)
                    .as("normalized response body for %s", caseId)
                    .isEqualTo(expectedResponse.path("body"));
        }

        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
        assertOnlySubjectRateLimitKeys(8);
    }

    @Test
    void unauthenticatedReadsUseTheObservedLegacyEnvelopeAndRevealNoCatalogData()
            throws Exception {
        Map<String, String> databaseBefore = databaseFingerprint();

        for (String path : Set.of("/api/quiz/subjects", "/api/quiz/subjects/meta")) {
            mockMvc.perform(get(path).header("X-Request-ID", "phase4a-unauthenticated"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentType("application/json; charset=utf-8"))
                    .andExpect(header().string("Vary", "Origin, Cookie"))
                    .andExpect(header().doesNotExist("Cache-Control"))
                    .andExpect(jsonPath("$.status").value("unauthorized"))
                    .andExpect(jsonPath("$.message").value("请先登录"))
                    .andExpect(jsonPath("$.status_code").value(401))
                    .andExpect(jsonPath("$.request_id").value("phase4a-unauthenticated"))
                    .andExpect(jsonPath("$.subjects").doesNotExist())
                    .andExpect(jsonPath("$.data").doesNotExist());
        }

        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
        assertThat(redis.keys("*")).isEmpty();
    }

    @Test
    void successfulBearerReadExecutesOneAuthorityAndTwoBusinessQueries() throws Exception {
        List<String> executedSql = null;
        sqlCounter.start();
        try {
            mockMvc.perform(get("/api/quiz/subjects")
                            .header("Authorization", "Bearer " + ORDINARY_JWT)
                            .header("X-Request-ID", "phase4a-sql-count"))
                    .andExpect(status().isOk());
        } finally {
            executedSql = sqlCounter.stop();
        }

        assertSuccessfulSubjectReadSql(executedSql, "legacy Bearer");
    }

    private void assertSuccessfulSubjectReadSql(List<String> executedSql, String credential) {
        assertThat(executedSql)
                .as("%s: one authentication authority SELECT plus two business SELECTs",
                        credential)
                .hasSize(3)
                .allMatch(sql -> sql.startsWith("select "))
                .anyMatch(sql -> sql.contains("session_version")
                        && sql.contains("from users")
                        && !sql.contains("join user_subjects"))
                .anyMatch(sql -> sql.contains("left join user_subjects"))
                .anyMatch(sql -> sql.contains("left join questions"));
    }

    @Test
    void flaskSessionExchangeAndAuthoritativeTargetSessionBothProtectCatalogReads()
            throws Exception {
        Map<String, String> databaseBefore = databaseFingerprint();
        String flaskCookie = legacyVectors()
                .path("flask_sessions")
                .get(1)
                .path("cookie")
                .asString();

        MvcResult exchanged;
        List<String> exchangeSql = null;
        sqlCounter.start();
        try {
            exchanged = mockMvc.perform(get("/api/quiz/subjects")
                            .cookie(new Cookie("session", flaskCookie))
                            .header("X-Request-ID", "phase4a-flask-session"))
                    .andExpect(status().isOk())
                    .andReturn();
        } finally {
            exchangeSql = sqlCounter.stop();
        }
        assertSuccessfulSubjectReadSql(exchangeSql, "legacy Flask Session exchange");
        Cookie targetSession = exchanged.getResponse().getCookie("ti_dev_session");
        assertThat(targetSession).isNotNull();
        assertThat(exchanged.getResponse().getHeaders("Set-Cookie"))
                .anyMatch(value -> value.contains("session=;"))
                .anyMatch(value -> value.contains("ti_dev_session="));
        JsonNode flaskBody = json.readTree(exchanged.getResponse().getContentAsByteArray());
        assertThat(flaskBody.path("subjects")).extracting(JsonNode::asString)
                .containsExactly("算法基础", "数据库系统", "受限科目");

        Set<String> afterExchange = Set.copyOf(redis.keys("*"));
        Set<String> legacyExchangeKeys = afterExchange.stream()
                .filter(key -> key.startsWith("ti-java:identity:legacy-session-exchange:"))
                .collect(java.util.stream.Collectors.toUnmodifiableSet());
        assertThat(afterExchange)
                .anyMatch(key -> key.startsWith("ti-java:phase4a:sessions:sessions:"))
                .anyMatch(key -> key.startsWith("ti-java:identity:legacy-session-exchange:"))
                .anyMatch(key -> key.startsWith("ti-java:identity:target-session-index:"))
                .anyMatch(key -> key.startsWith("ti-java:catalog:subject-read-rate:"));
        assertOnlyExpectedSubjectRuntimeKeys(afterExchange);

        MvcResult targetRead;
        List<String> targetSessionSql = null;
        sqlCounter.start();
        try {
            targetRead = mockMvc.perform(get("/api/quiz/subjects/meta")
                            .cookie(targetSession)
                            .header("X-Request-ID", "phase4a-target-session"))
                    .andExpect(status().isOk())
                    .andReturn();
        } finally {
            targetSessionSql = sqlCounter.stop();
        }
        assertSuccessfulSubjectReadSql(targetSessionSql, "target Session");
        JsonNode targetBody = json.readTree(targetRead.getResponse().getContentAsByteArray());
        assertThat(targetBody.path("data").path("quiz_count").asInt()).isEqualTo(3);
        assertThat(targetBody.path("data").path("subjects")).hasSize(3);
        Set<String> afterTargetSessionRead = Set.copyOf(redis.keys("*"));
        assertOnlyExpectedSubjectRuntimeKeys(afterTargetSessionRead);
        assertThat(afterTargetSessionRead.stream()
                        .filter(key -> key.startsWith(
                                "ti-java:identity:legacy-session-exchange:"))
                        .collect(java.util.stream.Collectors.toUnmodifiableSet()))
                .as("target Session reads must not mutate legacy exchange keys")
                .isEqualTo(legacyExchangeKeys);
        assertThat(afterTargetSessionRead)
                .as("target Session meta read adds only its minute and hour limiter keys")
                .filteredOn(key -> !afterExchange.contains(key))
                .hasSize(2)
                .allMatch(key -> key.startsWith(
                        "ti-java:catalog:subject-read-rate:subjects-meta:identity:v1:"));
        assertThat(databaseFingerprint()).isEqualTo(databaseBefore);
    }

    private void assertOnlyExpectedSubjectRuntimeKeys(Set<String> keys) {
        assertThat(keys)
                .allMatch(key -> key.startsWith("ti-java:phase4a:sessions:")
                        || key.startsWith("ti-java:identity:legacy-session-exchange:")
                        || key.startsWith("ti-java:identity:target-session-index:")
                        || key.startsWith("ti-java:catalog:subject-read-rate:"))
                .noneMatch(key -> key.contains("4101") || key.contains("4242"))
                .noneMatch(key -> key.contains("cache"));
    }

    private Map<String, String> databaseFingerprint() {
        Map<String, String> result = new LinkedHashMap<>();
        for (String table : Set.of(
                "users", "subjects", "questions", "user_subjects", "system_config")) {
            result.put(table, jdbc.queryForObject(
                    "SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY id), '[]'::jsonb)::text "
                            + "FROM " + table + " t",
                    String.class));
        }
        return result;
    }

    private void assertOnlySubjectRateLimitKeys(int expectedCount) {
        Set<String> keys = redis.keys("*");
        assertThat(keys)
                .hasSize(expectedCount)
                .allMatch(key -> key.startsWith("ti-java:catalog:subject-read-rate:"))
                .noneMatch(key -> key.contains("session") || key.contains("cache:quiz"));
    }

    private JsonNode legacyVectors() throws Exception {
        try (var stream = getClass().getClassLoader()
                .getResourceAsStream("compat/legacy-auth-vectors.json")) {
            assertThat(stream).isNotNull();
            return json.readTree(stream);
        }
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class FixedPhase4aClock {

        @Bean
        @Primary
        Clock phase4aClock() {
            return Clock.fixed(Instant.parse("2026-07-16T01:00:00Z"), ZoneOffset.UTC);
        }
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class SqlCountingDataSourceConfiguration {

        @Bean
        CurrentThreadSqlCounter phase4aSqlCounter() {
            return new CurrentThreadSqlCounter();
        }

        @Bean
        @Primary
        DataSource phase4aCountingDataSource(
                DataSourceProperties properties,
                CurrentThreadSqlCounter counter
        ) {
            HikariDataSource target = properties.initializeDataSourceBuilder()
                    .type(HikariDataSource.class)
                    .build();
            return new SqlCountingDataSource(target, counter);
        }
    }

    static final class CurrentThreadSqlCounter {

        private final ThreadLocal<List<String>> activeStatements = new ThreadLocal<>();

        void start() {
            if (activeStatements.get() != null) {
                throw new IllegalStateException("SQL counting is already active on this thread");
            }
            activeStatements.set(new ArrayList<>());
        }

        List<String> stop() {
            List<String> statements = activeStatements.get();
            if (statements == null) {
                throw new IllegalStateException("SQL counting is not active on this thread");
            }
            activeStatements.remove();
            return List.copyOf(statements);
        }

        void record(String sql) {
            List<String> statements = activeStatements.get();
            if (statements != null) {
                statements.add(sql.replaceAll("\\s+", " ").trim().toLowerCase());
            }
        }
    }

    static final class SqlCountingDataSource extends DelegatingDataSource implements AutoCloseable {

        private final CurrentThreadSqlCounter counter;

        SqlCountingDataSource(DataSource targetDataSource, CurrentThreadSqlCounter counter) {
            super(targetDataSource);
            this.counter = counter;
        }

        @Override
        public Connection getConnection() throws SQLException {
            return countingConnection(super.getConnection());
        }

        @Override
        public Connection getConnection(String username, String password) throws SQLException {
            return countingConnection(super.getConnection(username, password));
        }

        @Override
        public void close() {
            if (getTargetDataSource() instanceof HikariDataSource hikari) {
                hikari.close();
            }
        }

        private Connection countingConnection(Connection target) {
            return (Connection) Proxy.newProxyInstance(
                    getClass().getClassLoader(),
                    new Class<?>[]{Connection.class},
                    (proxy, method, arguments) -> {
                        Object result = invoke(target, method, arguments);
                        if (!(result instanceof Statement statement)) {
                            return result;
                        }
                        String preparedSql = arguments != null
                                && arguments.length > 0
                                && arguments[0] instanceof String sql
                                ? sql
                                : null;
                        return countingStatement(statement, preparedSql);
                    });
        }

        private Object countingStatement(Statement target, String preparedSql) {
            Class<?> statementType = target instanceof CallableStatement
                    ? CallableStatement.class
                    : target instanceof PreparedStatement
                            ? PreparedStatement.class
                            : Statement.class;
            return Proxy.newProxyInstance(
                    getClass().getClassLoader(),
                    new Class<?>[]{statementType},
                    (proxy, method, arguments) -> {
                        if (isExecution(method)) {
                            String sql = preparedSql;
                            if (sql == null
                                    && arguments != null
                                    && arguments.length > 0
                                    && arguments[0] instanceof String dynamicSql) {
                                sql = dynamicSql;
                            }
                            counter.record(sql == null ? method.getName() : sql);
                        }
                        return invoke(target, method, arguments);
                    });
        }

        private static boolean isExecution(Method method) {
            return switch (method.getName()) {
                case "execute", "executeBatch", "executeLargeBatch", "executeLargeUpdate",
                        "executeQuery", "executeUpdate" -> true;
                default -> false;
            };
        }

        private static Object invoke(Object target, Method method, Object[] arguments)
                throws Throwable {
            try {
                return method.invoke(target, arguments);
            } catch (InvocationTargetException exception) {
                throw exception.getCause();
            }
        }
    }
}
