package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.learning.application.port.PersonalBankUserCountsQueryPort;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.core.MethodParameter;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.converter.json.JacksonJsonHttpMessageConverter;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DelegatingDataSource;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

@Testcontainers
class Phase4cPersonalBankUserCountsJdbcCompatibilityIT {

    private static final int BANK_ID = 7_101;
    private static final long OWNER_ID = 7_001L;
    private static final long SHARED_VIEWER_ID = 7_003L;
    private static final long UNKNOWN_PERMISSION_VIEWER_ID = 7_005L;
    private static final long CROSS_BANK_VIEWER_ID = 7_006L;
    private static final long NULL_PERMISSION_VIEWER_ID = 7_008L;
    private static final List<String> SUCCESS_SQL_FINGERPRINT = List.of(
            "bank-access",
            "tag-membership",
            "bank-access",
            "question-summary",
            "favorite-membership",
            "bank-access",
            "question-summary",
            "mistake-membership",
            "bank-access",
            "question-summary",
            "bank-access",
            "question-summary");
    private static final List<String> DENIED_SQL_FINGERPRINT = List.of(
            "bank-access",
            "share-access");
    private static final Clock ACCESS_CLOCK = Clock.fixed(
            Instant.parse("2026-07-17T04:00:00Z"), ZoneOffset.UTC);
    private static final List<String> BUSINESS_TABLES = List.of(
            "users",
            "system_config",
            "user_question_banks",
            "bank_shares",
            "bank_share_records",
            "public_bank_users",
            "user_bank_questions",
            "user_bank_favorites",
            "user_bank_mistakes",
            "user_progress",
            "user_question_tag_items");

    @Container
    static final PostgreSQLContainer POSTGRES_18 = userCountsFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = userCountsFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void runsOnPostgres16And18() throws Exception {
        assertRuntimeCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
        assertRuntimeCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void recoversFromTwentyFiveP02WithIndependentTransactions() throws Exception {
        assertPoisonedOuterTransactionRecovery(POSTGRES_16);
        assertPoisonedOuterTransactionRecovery(POSTGRES_18);
    }

    @Test
    void preservesSchemaAndBusinessRows() throws Exception {
        assertReadOnlySurface(POSTGRES_16);
        assertReadOnlySurface(POSTGRES_18);
    }

    @Test
    void servesRealControllerResponsesThroughReadOnlyJdbcOnPostgres16And18()
            throws Exception {
        ControllerHttpSqlEvidence postgres16 = assertControllerSurface(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
        ControllerHttpSqlEvidence postgres18 = assertControllerSurface(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
        assertThat(postgres18)
                .as("PostgreSQL 16.14 and 18.4 must expose identical complete HTTP and SQL "
                        + "fingerprints")
                .isEqualTo(postgres16);
    }

    private static PostgreSQLContainer userCountsFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        phase4bFixture("062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
                .withCopyFileToContainer(
                        phase4bFixture("063-personal-bank-share-list-seed.sql"),
                        "/docker-entrypoint-initdb.d/063-personal-bank-share-list-seed.sql")
                .withCopyFileToContainer(
                        phase4bFixture("064-personal-bank-all-shares-seed.sql"),
                        "/docker-entrypoint-initdb.d/064-personal-bank-all-shares-seed.sql")
                .withCopyFileToContainer(
                        phase4bFixture("065-personal-bank-usage-stats-schema.sql"),
                        "/docker-entrypoint-initdb.d/065-personal-bank-usage-stats-schema.sql")
                .withCopyFileToContainer(
                        phase4bFixture("066-personal-bank-usage-stats-seed.sql"),
                        "/docker-entrypoint-initdb.d/066-personal-bank-usage-stats-seed.sql")
                .withCopyFileToContainer(
                        phase4bFixture("067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
                .withCopyFileToContainer(
                        phase4bFixture("068-personal-bank-user-counts-seed.sql"),
                        "/docker-entrypoint-initdb.d/068-personal-bank-user-counts-seed.sql");
    }

    private static MountableFile phase4bFixture(String name) {
        return MountableFile.forClasspathResource("db/phase4b/" + name);
    }

    private static void assertRuntimeCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        RuntimeHarness runtime = runtime(postgres);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(runtime.jdbc().sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(runtime.jdbc().sql("SELECT CAST(pg_typeof(:bank_id) AS text)")
                .param("bank_id", BANK_ID)
                .query(String.class)
                .single())
                .isEqualTo("integer");

        assertFullReadSurface(runtime);
    }

    private static ControllerHttpSqlEvidence assertControllerSurface(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        RuntimeHarness runtime = runtime(postgres);
        JsonMapper json = JsonMapper.builder()
                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .build();
        MockMvc http = controller(runtime.learning(), json);
        DatabaseSnapshot before = databaseSnapshot(runtime.jdbc());

        assertThat(postgres.getDockerImageName())
                .as("HTTP evidence container image")
                .isEqualTo(expectedImage);
        assertThat(runtime.jdbc().sql("SHOW server_version").query(String.class).single())
                .as("HTTP evidence PostgreSQL runtime")
                .isEqualTo(expectedVersion);

        runtime.sqlTrace().clear();
        MvcResult success = http.perform(get(
                                "/api/user/banks/api/{bankId}/user-counts",
                                BANK_ID)
                        .principal(targetPrincipal(OWNER_ID))
                        .requestAttr(RequestId.ATTRIBUTE_NAME, requestId("success"))
                        .param("q_type", "all")
                        .param("source", "all")
                        .param("tag", "alpha"))
                .andReturn();
        List<SqlExecution> successSql = runtime.sqlTrace().snapshot();

        assertThat(success.getResolvedException()).isNull();
        assertThat(success.getResponse().getStatus()).isEqualTo(200);
        assertThat(success.getResponse().getHeader(HttpHeaders.CONTENT_TYPE))
                .isEqualTo("application/json; charset=utf-8");
        JsonNode successBody = json.readTree(success.getResponse().getContentAsByteArray());
        assertThat(successBody.path("status").asString()).isEqualTo("success");
        assertThat(successBody.path("code").asInt()).isZero();
        assertThat(successBody.path("data").path("total").asLong()).isEqualTo(2L);
        assertThat(successBody.path("data").path("favorites").asLong()).isEqualTo(2L);
        assertThat(successBody.path("data").path("mistakes").asLong()).isEqualTo(1L);
        assertThat(successBody.path("data").path("shuffle_options_available").asBoolean())
                .isTrue();
        assertThat(successBody.path("request_id").asString())
                .isEqualTo(requestId("success"));
        assertSqlFingerprint(successSql, SUCCESS_SQL_FINGERPRINT, expectedVersion, "success");

        runtime.sqlTrace().clear();
        MvcResult denied = http.perform(get(
                                "/api/user/banks/api/{bankId}/user-counts",
                                BANK_ID)
                        .principal(targetPrincipal(CROSS_BANK_VIEWER_ID))
                        .requestAttr(RequestId.ATTRIBUTE_NAME, requestId("denied")))
                .andReturn();
        List<SqlExecution> deniedSql = runtime.sqlTrace().snapshot();

        assertThat(denied.getResolvedException()).isNull();
        assertThat(denied.getResponse().getStatus()).isEqualTo(403);
        assertThat(denied.getResponse().getHeader(HttpHeaders.CONTENT_TYPE))
                .isEqualTo("application/json; charset=utf-8");
        JsonNode deniedBody = json.readTree(denied.getResponse().getContentAsByteArray());
        assertThat(deniedBody.path("status").asString()).isEqualTo("error");
        assertThat(deniedBody.path("code").asInt()).isEqualTo(403);
        assertThat(deniedBody.path("message").asString()).isEqualTo("无权访问此题库");
        assertThat(deniedBody.has("data")).isFalse();
        assertThat(deniedBody.path("request_id").asString())
                .isEqualTo(requestId("denied"));
        assertSqlFingerprint(deniedSql, DENIED_SQL_FINGERPRINT, expectedVersion, "denied");

        assertThat(databaseSnapshot(runtime.jdbc()))
                .as("HTTP reads on PostgreSQL %s preserve schema and business rows", expectedVersion)
                .isEqualTo(before);
        return new ControllerHttpSqlEvidence(
                responseFingerprint(success),
                successSql,
                responseFingerprint(denied),
                deniedSql);
    }

    private static MockMvc controller(
            LearningApplicationApi learning,
            JsonMapper json
    ) throws Exception {
        Class<?> controllerType = Class.forName(
                "io.saksk.ti.web.compat.LegacyPersonalBankUserCountsController");
        Constructor<?> constructor = controllerType.getDeclaredConstructor(
                LearningApplicationApi.class,
                PersonalBankUserCountsReadRequestResolver.class,
                LegacyPersonalBankUserCountsSecurityErrorWriter.class);
        constructor.setAccessible(true);
        Object controller = constructor.newInstance(
                learning,
                new PersonalBankUserCountsReadRequestResolver(),
                new LegacyPersonalBankUserCountsSecurityErrorWriter(json));
        return MockMvcBuilders.standaloneSetup(controller)
                .setCustomArgumentResolvers(new TargetPrincipalArgumentResolver())
                .setMessageConverters(new JacksonJsonHttpMessageConverter(json))
                .build();
    }

    private static Principal targetPrincipal(long identityId) {
        return new TargetAuthenticatedPrincipal(
                identityId,
                "phase4c-jdbc-http-evidence");
    }

    private static String requestId(String outcome) {
        return "phase4c-pg-http-" + outcome;
    }

    private static HttpResponseFingerprint responseFingerprint(MvcResult result) {
        Map<String, List<String>> headers = new LinkedHashMap<>();
        result.getResponse().getHeaderNames().forEach(name ->
                headers.put(name, List.copyOf(result.getResponse().getHeaders(name))));
        byte[] body = result.getResponse().getContentAsByteArray();
        return new HttpResponseFingerprint(
                result.getResponse().getStatus(),
                Map.copyOf(headers),
                body.length,
                sha256(body),
                new String(body, StandardCharsets.UTF_8));
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(
                    java.security.MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (java.security.NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 unavailable", exception);
        }
    }

    private static void assertSqlFingerprint(
            List<SqlExecution> actual,
            List<String> expectedFamilies,
            String postgresVersion,
            String outcome
    ) {
        assertThat(actual)
                .as("%s HTTP SQL fingerprint on PostgreSQL %s", outcome, postgresVersion)
                .extracting(SqlExecution::family)
                .containsExactlyElementsOf(expectedFamilies);
        assertThat(actual)
                .as("%s HTTP SQL must execute in read-only transactions on PostgreSQL %s",
                        outcome,
                        postgresVersion)
                .allSatisfy(execution -> {
                    assertThat(execution.readOnly()).isTrue();
                    assertThat(execution.classification())
                            .isEqualTo(SqlClassification.READ_QUERY);
                    assertThat(execution.lockingOperation()).isFalse();
                    assertThat(execution.sequenceOperation()).isFalse();
                });
    }

    private static void assertFullReadSurface(RuntimeHarness runtime) {
        AuthenticatedPersonalBankViewer owner =
                new AuthenticatedPersonalBankViewer(OWNER_ID);
        AuthenticatedPersonalBankViewer shared =
                new AuthenticatedPersonalBankViewer(SHARED_VIEWER_ID);
        AuthenticatedPersonalBankViewer unknownPermission =
                new AuthenticatedPersonalBankViewer(UNKNOWN_PERMISSION_VIEWER_ID);
        AuthenticatedPersonalBankViewer crossBank =
                new AuthenticatedPersonalBankViewer(CROSS_BANK_VIEWER_ID);
        AuthenticatedPersonalBankViewer nullPermission =
                new AuthenticatedPersonalBankViewer(NULL_PERMISSION_VIEWER_ID);

        assertThat(runtime.questionFacts().checkQuestionAccess(owner, BANK_ID).outcome())
                .isEqualTo(PersonalBankQuestionAccessResult.Outcome.AVAILABLE);
        assertThat(runtime.questionFacts().checkQuestionAccess(shared, BANK_ID).outcome())
                .isEqualTo(PersonalBankQuestionAccessResult.Outcome.AVAILABLE);
        assertThat(runtime.questionFacts()
                        .checkQuestionAccess(unknownPermission, BANK_ID)
                        .outcome())
                .isEqualTo(PersonalBankQuestionAccessResult.Outcome.DENIED);
        assertThat(runtime.questionFacts().checkQuestionAccess(crossBank, BANK_ID).outcome())
                .isEqualTo(PersonalBankQuestionAccessResult.Outcome.DENIED);
        assertThat(runtime.questionFacts()
                        .checkQuestionAccess(nullPermission, BANK_ID)
                        .outcome())
                .isEqualTo(PersonalBankQuestionAccessResult.Outcome.DENIED);

        PersonalBankUserCountsResult all = runtime.learning().findPersonalBankUserCounts(
                new AuthenticatedLearningViewer(OWNER_ID),
                new PersonalBankUserCountsQuery(BANK_ID, "all", "all", "all"));
        assertThat(all.outcome()).isEqualTo(PersonalBankUserCountsResult.Outcome.AVAILABLE);
        assertThat(all.data()).contains(new PersonalBankUserCountsView(
                9L,
                4L,
                4L,
                List.of("判断题", "简答题", "填空题", "多选题", "选择题", "简答题"),
                false));

        PersonalBankUserCountsResult tagged = taggedCounts(runtime.learning());
        assertThat(tagged.outcome())
                .isEqualTo(PersonalBankUserCountsResult.Outcome.AVAILABLE);
        assertThat(tagged.data()).contains(new PersonalBankUserCountsView(
                2L,
                2L,
                1L,
                List.of("多选题", "选择题"),
                true));

        PersonalBankUserCountsResult denied = runtime.learning().findPersonalBankUserCounts(
                new AuthenticatedLearningViewer(CROSS_BANK_VIEWER_ID),
                new PersonalBankUserCountsQuery(BANK_ID, "all", "all", "all"));
        assertThat(denied.outcome())
                .isEqualTo(PersonalBankUserCountsResult.Outcome.DENIED);
        assertThat(denied.data()).isEmpty();

        PersonalBankQuestionMembershipView membership =
                runtime.questionFacts().inspectQuestionMembership(
                        BANK_ID, List.of(8_201, 8_102, 8_101, 8_102));
        assertThat(membership.bankExists()).isTrue();
        assertThat(membership.existingQuestionIds()).containsExactly(8_101, 8_102);
        assertThat(membership.membershipDigest())
                .isEqualTo("f2facd9015ce6bbd5c947ad9abcd5c0da076dc51ecdfbcac4e3197f17b917b9d");
    }

    private static PersonalBankUserCountsResult taggedCounts(LearningApplicationApi learning) {
        return learning.findPersonalBankUserCounts(
                new AuthenticatedLearningViewer(OWNER_ID),
                new PersonalBankUserCountsQuery(BANK_ID, "all", "all", "alpha"));
    }

    private static void assertPoisonedOuterTransactionRecovery(
            PostgreSQLContainer postgres
    ) throws Exception {
        RuntimeHarness runtime = runtime(postgres);
        DatabaseSnapshot before = databaseSnapshot(runtime.jdbc());
        PersonalBankUserCountsQueryPort poisoningMemberships = transactionalProxy(
                new PoisoningMemberships(runtime.jdbc(), runtime.membershipQueries()),
                PersonalBankUserCountsQueryPort.class,
                runtime.transactions());
        LearningApplicationApi faultIsolatedLearning = learning(
                runtime.questionFacts(), poisoningMemberships, runtime.transactions());
        TransactionTemplate outer = new TransactionTemplate(runtime.transactions());
        outer.setReadOnly(true);

        outer.executeWithoutResult(status -> {
            DataAccessException initialFailure = assertThrows(
                    DataAccessException.class,
                    () -> runtime.jdbc().sql(
                                    "SELECT missing_phase4c_column FROM user_bank_questions")
                            .query(Integer.class)
                            .list());
            assertThat(sqlState(initialFailure)).isEqualTo("42703");

            DataAccessException poisonedFailure = assertThrows(
                    DataAccessException.class,
                    () -> runtime.jdbc().sql("SELECT COUNT(*) FROM user_bank_questions")
                            .query(Long.class)
                            .single());
            assertThat(sqlState(poisonedFailure)).isEqualTo("25P02");

            PersonalBankUserCountsResult recovered = taggedCounts(faultIsolatedLearning);
            assertThat(recovered.outcome())
                    .isEqualTo(PersonalBankUserCountsResult.Outcome.AVAILABLE);
            assertThat(recovered.data()).contains(new PersonalBankUserCountsView(
                    2L,
                    0L,
                    1L,
                    List.of("多选题", "选择题"),
                    true));
            status.setRollbackOnly();
        });

        assertThat(taggedCounts(faultIsolatedLearning).data()).contains(
                new PersonalBankUserCountsView(
                        2L,
                        2L,
                        1L,
                        List.of("多选题", "选择题"),
                        true));
        assertThat(databaseSnapshot(runtime.jdbc())).isEqualTo(before);
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

    private static void assertReadOnlySurface(PostgreSQLContainer postgres) throws Exception {
        RuntimeHarness runtime = runtime(postgres);
        DatabaseSnapshot before = databaseSnapshot(runtime.jdbc());
        runtime.sqlTrace().clear();
        assertFullReadSurface(runtime);
        assertReadOnlyTrace(
                runtime.sqlTrace().snapshot(),
                postgres.getDockerImageName(),
                "complete application read surface");
        assertThat(databaseSnapshot(runtime.jdbc())).isEqualTo(before);
    }

    private static void assertReadOnlyTrace(
            List<SqlExecution> executions,
            String runtime,
            String surface
    ) {
        assertThat(executions)
                .as("%s on %s must execute SQL", surface, runtime)
                .isNotEmpty()
                .allSatisfy(execution -> {
                    assertThat(execution.readOnly())
                            .as("%s transaction for %s", surface, execution.family())
                            .isTrue();
                    assertThat(execution.classification())
                            .as("%s SQL classification for %s", surface, execution.normalizedSql())
                            .isEqualTo(SqlClassification.READ_QUERY);
                    assertThat(execution.lockingOperation())
                            .as("%s must not acquire explicit/advisory locks", surface)
                            .isFalse();
                    assertThat(execution.sequenceOperation())
                            .as("%s must not advance or alter sequences", surface)
                            .isFalse();
                });
    }

    private static RuntimeHarness runtime(PostgreSQLContainer postgres) throws Exception {
        DriverManagerDataSource targetDataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        SqlExecutionTrace sqlTrace = new SqlExecutionTrace();
        DataSource dataSource = new SqlTracingDataSource(targetDataSource, sqlTrace);
        JdbcClient jdbc = JdbcClient.create(dataSource);
        PlatformTransactionManager transactions = new DataSourceTransactionManager(dataSource);

        PersonalBankQuestionFactsQueryPort factsQueries = instantiate(
                "io.saksk.ti.personalbank.infrastructure.persistence."
                        + "JdbcPersonalBankQuestionFactsQueryAdapter",
                PersonalBankQuestionFactsQueryPort.class,
                new Class<?>[]{JdbcClient.class},
                jdbc);
        PersonalBankQuestionFactsApi questionFacts = transactionalProxy(
                instantiate(
                        "io.saksk.ti.personalbank.application."
                                + "PersonalBankQuestionFactsService",
                        PersonalBankQuestionFactsApi.class,
                        new Class<?>[]{PersonalBankQuestionFactsQueryPort.class, Clock.class},
                        factsQueries,
                        ACCESS_CLOCK),
                PersonalBankQuestionFactsApi.class,
                transactions);

        PersonalBankUserCountsQueryPort membershipQueries = instantiate(
                "io.saksk.ti.learning.infrastructure.persistence."
                        + "JdbcPersonalBankUserCountsQueryAdapter",
                PersonalBankUserCountsQueryPort.class,
                new Class<?>[]{JdbcClient.class},
                jdbc);
        PersonalBankUserCountsQueryPort memberships = transactionalProxy(
                membershipQueries,
                PersonalBankUserCountsQueryPort.class,
                transactions);
        LearningApplicationApi learning = learning(questionFacts, memberships, transactions);

        return new RuntimeHarness(
                jdbc,
                transactions,
                questionFacts,
                membershipQueries,
                learning,
                sqlTrace);
    }

    private static LearningApplicationApi learning(
            PersonalBankQuestionFactsApi questionFacts,
            PersonalBankUserCountsQueryPort memberships,
            PlatformTransactionManager transactions
    ) throws Exception {
        return transactionalProxy(
                instantiate(
                        "io.saksk.ti.learning.application.PersonalBankUserCountsService",
                        LearningApplicationApi.class,
                        new Class<?>[]{
                            PersonalBankQuestionFactsApi.class,
                            PersonalBankUserCountsQueryPort.class
                        },
                        questionFacts,
                        memberships),
                LearningApplicationApi.class,
                transactions);
    }

    private static <T> T instantiate(
            String className,
            Class<T> contract,
            Class<?>[] constructorTypes,
            Object... arguments
    ) throws Exception {
        Class<?> implementation = Class.forName(className);
        Constructor<?> constructor = implementation.getDeclaredConstructor(constructorTypes);
        constructor.setAccessible(true);
        return contract.cast(constructor.newInstance(arguments));
    }

    private static <T> T transactionalProxy(
            T target,
            Class<T> contract,
            PlatformTransactionManager transactions
    ) {
        TransactionInterceptor interceptor = new TransactionInterceptor();
        interceptor.setTransactionManager(transactions);
        interceptor.setTransactionAttributeSource(
                new AnnotationTransactionAttributeSource());
        ProxyFactory proxy = new ProxyFactory(target);
        proxy.addAdvice(interceptor);
        return contract.cast(proxy.getProxy());
    }

    private static DatabaseSnapshot databaseSnapshot(JdbcClient jdbc) {
        return new DatabaseSnapshot(
                schemaFingerprint(jdbc),
                businessRows(jdbc),
                sequenceFingerprint(jdbc));
    }

    private static SchemaFingerprint schemaFingerprint(JdbcClient jdbc) {
        List<String> columns = jdbc.sql("""
                        SELECT concat_ws('|', table_name, ordinal_position, column_name,
                                         data_type, is_nullable, coalesce(column_default, ''))
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        ORDER BY table_name, ordinal_position
                        """)
                .query(String.class)
                .list();
        List<String> constraints = jdbc.sql("""
                        SELECT concat_ws('|', conrelid::regclass::text, conname,
                                         pg_get_constraintdef(oid, true))
                        FROM pg_constraint
                        WHERE connamespace = current_schema()::regnamespace
                        ORDER BY conrelid::regclass::text, conname
                        """)
                .query(String.class)
                .list();
        List<String> indexes = jdbc.sql("""
                        SELECT concat_ws('|', tablename, indexname, indexdef)
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                        ORDER BY tablename, indexname
                        """)
                .query(String.class)
                .list();
        List<String> views = jdbc.sql("""
                        SELECT concat_ws('|', viewname, definition)
                        FROM pg_views
                        WHERE schemaname = current_schema()
                        ORDER BY viewname
                        """)
                .query(String.class)
                .list();
        List<String> relations = jdbc.sql("""
                        SELECT concat_ws('|', c.relname, c.relkind, c.relpersistence,
                                         c.relrowsecurity, c.relforcerowsecurity,
                                         coalesce(am.amname, ''))
                        FROM pg_class c
                        LEFT JOIN pg_am am ON am.oid = c.relam
                        WHERE c.relnamespace = current_schema()::regnamespace
                        ORDER BY c.relname
                        """)
                .query(String.class)
                .list();
        List<String> triggers = jdbc.sql("""
                        SELECT concat_ws('|', event_object_table, trigger_name,
                                         action_timing, event_manipulation,
                                         action_orientation, action_statement)
                        FROM information_schema.triggers
                        WHERE trigger_schema = current_schema()
                        ORDER BY event_object_table, trigger_name, event_manipulation
                        """)
                .query(String.class)
                .list();
        return new SchemaFingerprint(
                columns,
                constraints,
                indexes,
                views,
                relations,
                triggers);
    }

    private static Map<String, List<String>> businessRows(JdbcClient jdbc) {
        Map<String, List<String>> rows = new LinkedHashMap<>();
        for (String table : BUSINESS_TABLES) {
            rows.put(table, List.copyOf(jdbc.sql(
                            "SELECT row_to_json(snapshot_row)::text "
                                    + "FROM (SELECT * FROM " + table + ") snapshot_row "
                                    + "ORDER BY 1")
                    .query(String.class)
                    .list()));
        }
        return Map.copyOf(rows);
    }

    private static List<String> sequenceFingerprint(JdbcClient jdbc) {
        return List.copyOf(jdbc.sql("""
                        SELECT concat_ws('|', schemaname, sequencename, sequenceowner,
                                         data_type, start_value, min_value, max_value,
                                         increment_by, cycle, cache_size,
                                         coalesce(last_value::text, ''))
                        FROM pg_sequences
                        WHERE schemaname = current_schema()
                        ORDER BY sequencename
                        """)
                .query(String.class)
                .list());
    }

    private record RuntimeHarness(
            JdbcClient jdbc,
            PlatformTransactionManager transactions,
            PersonalBankQuestionFactsApi questionFacts,
            PersonalBankUserCountsQueryPort membershipQueries,
            LearningApplicationApi learning,
            SqlExecutionTrace sqlTrace
    ) {
    }

    private static final class TargetPrincipalArgumentResolver
            implements HandlerMethodArgumentResolver {

        @Override
        public boolean supportsParameter(MethodParameter parameter) {
            return parameter.getParameterType() == TargetAuthenticatedPrincipal.class
                    && parameter.hasParameterAnnotation(AuthenticationPrincipal.class);
        }

        @Override
        public Object resolveArgument(
                MethodParameter parameter,
                ModelAndViewContainer modelAndViewContainer,
                NativeWebRequest webRequest,
                WebDataBinderFactory binderFactory
        ) {
            Principal requestPrincipal = webRequest.getUserPrincipal();
            if (requestPrincipal instanceof TargetAuthenticatedPrincipal targetPrincipal) {
                return targetPrincipal;
            }
            return null;
        }
    }

    private static final class SqlExecutionTrace {

        private final List<SqlExecution> executions = new ArrayList<>();

        synchronized void clear() {
            executions.clear();
        }

        synchronized void record(String sql, boolean readOnly) {
            String normalized = sql.replaceAll("\\s+", " ")
                    .strip()
                    .toLowerCase(Locale.ROOT);
            executions.add(new SqlExecution(
                    sqlFamily(normalized),
                    normalized,
                    sqlClassification(normalized),
                    hasLockingOperation(normalized),
                    hasSequenceOperation(normalized),
                    readOnly));
        }

        synchronized List<SqlExecution> snapshot() {
            return List.copyOf(executions);
        }

        private static String sqlFamily(String sql) {
            if (sql.contains("join bank_share_records")) {
                return "share-access";
            }
            if (sql.contains("from user_question_banks requested_bank")) {
                return "bank-access";
            }
            if (sql.contains("from user_question_tag_items")) {
                return "tag-membership";
            }
            if (sql.contains("from user_bank_favorites")) {
                return "favorite-membership";
            }
            if (sql.contains("from user_bank_mistakes")) {
                return "mistake-membership";
            }
            if (sql.contains("from user_bank_questions q")
                    && sql.contains("group by q.type")) {
                return "question-summary";
            }
            return "unclassified";
        }

        private static SqlClassification sqlClassification(String sql) {
            if (hasSequenceOperation(sql)) {
                return SqlClassification.SEQUENCE;
            }
            if (hasLockingOperation(sql)) {
                return SqlClassification.LOCK;
            }
            if (sql.startsWith("select ") || sql.startsWith("with ")) {
                if (containsToken(sql, "insert")
                        || containsToken(sql, "update")
                        || containsToken(sql, "delete")
                        || containsToken(sql, "merge")) {
                    return SqlClassification.WRITE_DML;
                }
                return SqlClassification.READ_QUERY;
            }
            if (sql.startsWith("insert ")
                    || sql.startsWith("update ")
                    || sql.startsWith("delete ")
                    || sql.startsWith("merge ")) {
                return SqlClassification.WRITE_DML;
            }
            if (sql.startsWith("create ")
                    || sql.startsWith("alter ")
                    || sql.startsWith("drop ")
                    || sql.startsWith("truncate ")
                    || sql.startsWith("comment ")
                    || sql.startsWith("grant ")
                    || sql.startsWith("revoke ")) {
                return SqlClassification.DDL_OR_PRIVILEGE;
            }
            if (sql.startsWith("begin")
                    || sql.startsWith("commit")
                    || sql.startsWith("rollback")
                    || sql.startsWith("savepoint")
                    || sql.startsWith("set transaction")) {
                return SqlClassification.TRANSACTION_CONTROL;
            }
            return SqlClassification.UNKNOWN;
        }

        private static boolean hasLockingOperation(String sql) {
            return sql.startsWith("lock ")
                    || sql.contains(" for update")
                    || sql.contains(" for no key update")
                    || sql.contains(" for share")
                    || sql.contains(" for key share")
                    || sql.contains("pg_advisory_lock")
                    || sql.contains("pg_advisory_xact_lock");
        }

        private static boolean hasSequenceOperation(String sql) {
            return sql.startsWith("alter sequence ")
                    || sql.contains("nextval(")
                    || sql.contains("setval(")
                    || sql.contains("currval(")
                    || sql.contains("lastval(");
        }

        private static boolean containsToken(String sql, String token) {
            return (" " + sql + " ").contains(" " + token + " ");
        }
    }

    private static final class SqlTracingDataSource extends DelegatingDataSource {

        private final SqlExecutionTrace trace;

        private SqlTracingDataSource(DataSource targetDataSource, SqlExecutionTrace trace) {
            super(targetDataSource);
            this.trace = trace;
        }

        @Override
        public Connection getConnection() throws SQLException {
            return tracingConnection(super.getConnection());
        }

        @Override
        public Connection getConnection(String username, String password) throws SQLException {
            return tracingConnection(super.getConnection(username, password));
        }

        private Connection tracingConnection(Connection target) throws SQLException {
            ConnectionState state = new ConnectionState(target.isReadOnly());
            return (Connection) Proxy.newProxyInstance(
                    getClass().getClassLoader(),
                    new Class<?>[]{Connection.class},
                    (proxy, method, arguments) -> {
                        Object result = invokeJdbc(target, method, arguments);
                        if (method.getName().equals("setReadOnly")
                                && arguments != null
                                && arguments.length == 1
                                && arguments[0] instanceof Boolean readOnly) {
                            state.readOnly = readOnly;
                        }
                        if (!(result instanceof Statement statement)) {
                            return result;
                        }
                        String preparedSql = arguments != null
                                && arguments.length > 0
                                && arguments[0] instanceof String sql
                                ? sql
                                : null;
                        return tracingStatement(statement, preparedSql, state);
                    });
        }

        private Object tracingStatement(
                Statement target,
                String preparedSql,
                ConnectionState state
        ) {
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
                            trace.record(sql == null ? method.getName() : sql, state.readOnly);
                        }
                        return invokeJdbc(target, method, arguments);
                    });
        }

        private static boolean isExecution(Method method) {
            return switch (method.getName()) {
                case "execute", "executeBatch", "executeLargeBatch", "executeLargeUpdate",
                        "executeQuery", "executeUpdate" -> true;
                default -> false;
            };
        }

        private static Object invokeJdbc(Object target, Method method, Object[] arguments)
                throws Throwable {
            try {
                return method.invoke(target, arguments);
            } catch (InvocationTargetException exception) {
                throw exception.getCause();
            }
        }
    }

    private static final class ConnectionState {

        private boolean readOnly;

        private ConnectionState(boolean readOnly) {
            this.readOnly = readOnly;
        }
    }

    private record SqlExecution(
            String family,
            String normalizedSql,
            SqlClassification classification,
            boolean lockingOperation,
            boolean sequenceOperation,
            boolean readOnly
    ) {
    }

    private enum SqlClassification {
        READ_QUERY,
        WRITE_DML,
        DDL_OR_PRIVILEGE,
        LOCK,
        SEQUENCE,
        TRANSACTION_CONTROL,
        UNKNOWN
    }

    private record HttpResponseFingerprint(
            int status,
            Map<String, List<String>> headers,
            int bodyLength,
            String bodySha256,
            String utf8Body
    ) {
        private HttpResponseFingerprint {
            headers = Map.copyOf(headers);
        }
    }

    private record ControllerHttpSqlEvidence(
            HttpResponseFingerprint successResponse,
            List<SqlExecution> success,
            HttpResponseFingerprint deniedResponse,
            List<SqlExecution> denied
    ) {
        private ControllerHttpSqlEvidence {
            success = List.copyOf(success);
            denied = List.copyOf(denied);
        }
    }

    private static final class PoisoningMemberships
            implements PersonalBankUserCountsQueryPort {

        private final JdbcClient jdbc;
        private final PersonalBankUserCountsQueryPort delegate;
        private boolean poisonNextFavorite = true;

        private PoisoningMemberships(
                JdbcClient jdbc,
                PersonalBankUserCountsQueryPort delegate
        ) {
            this.jdbc = jdbc;
            this.delegate = delegate;
        }

        @Override
        @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
        public List<Integer> findQuestionIdsByTag(
                long viewerId,
                int bankId,
                String tag
        ) {
            return delegate.findQuestionIdsByTag(viewerId, bankId, tag);
        }

        @Override
        @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
        public List<Integer> findFavoriteQuestionIds(
                long viewerId,
                Optional<List<Integer>> candidateQuestionIds
        ) {
            if (!poisonNextFavorite) {
                return delegate.findFavoriteQuestionIds(viewerId, candidateQuestionIds);
            }
            poisonNextFavorite = false;

            DataAccessException initialFailure = assertThrows(
                    DataAccessException.class,
                    () -> jdbc.sql(
                                    "SELECT missing_phase4c_optional_column "
                                            + "FROM user_bank_favorites")
                            .query(Integer.class)
                            .list());
            assertThat(sqlState(initialFailure)).isEqualTo("42703");

            DataAccessException poisonedFailure = assertThrows(
                    DataAccessException.class,
                    () -> jdbc.sql("SELECT COUNT(*) FROM user_bank_favorites")
                            .query(Long.class)
                            .single());
            assertThat(sqlState(poisonedFailure)).isEqualTo("25P02");
            throw poisonedFailure;
        }

        @Override
        @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
        public List<Integer> findMistakeQuestionIds(
                long viewerId,
                Optional<List<Integer>> candidateQuestionIds
        ) {
            return delegate.findMistakeQuestionIds(viewerId, candidateQuestionIds);
        }
    }

    private record DatabaseSnapshot(
            SchemaFingerprint schema,
            Map<String, List<String>> businessRows,
            List<String> sequences
    ) {
        private DatabaseSnapshot {
            businessRows = Map.copyOf(businessRows);
            sequences = List.copyOf(sequences);
        }
    }

    private record SchemaFingerprint(
            List<String> columns,
            List<String> constraints,
            List<String> indexes,
            List<String> views,
            List<String> relations,
            List<String> triggers
    ) {
        private SchemaFingerprint {
            columns = List.copyOf(columns);
            constraints = List.copyOf(constraints);
            indexes = List.copyOf(indexes);
            views = List.copyOf(views);
            relations = List.copyOf(relations);
            triggers = List.copyOf(triggers);
        }
    }
}
