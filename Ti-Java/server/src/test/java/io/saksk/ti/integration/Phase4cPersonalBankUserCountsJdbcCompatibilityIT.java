package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

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
import java.lang.reflect.Constructor;
import java.sql.SQLException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4cPersonalBankUserCountsJdbcCompatibilityIT {

    private static final int BANK_ID = 7_101;
    private static final long OWNER_ID = 7_001L;
    private static final long SHARED_VIEWER_ID = 7_003L;
    private static final long UNKNOWN_PERMISSION_VIEWER_ID = 7_005L;
    private static final long CROSS_BANK_VIEWER_ID = 7_006L;
    private static final long NULL_PERMISSION_VIEWER_ID = 7_008L;
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
        assertFullReadSurface(runtime);
        assertThat(databaseSnapshot(runtime.jdbc())).isEqualTo(before);
    }

    private static RuntimeHarness runtime(PostgreSQLContainer postgres) throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
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
                jdbc, transactions, questionFacts, membershipQueries, learning);
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
        return new DatabaseSnapshot(schemaFingerprint(jdbc), businessRows(jdbc));
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
        return new SchemaFingerprint(columns, constraints, indexes, views);
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

    private record RuntimeHarness(
            JdbcClient jdbc,
            PlatformTransactionManager transactions,
            PersonalBankQuestionFactsApi questionFacts,
            PersonalBankUserCountsQueryPort membershipQueries,
            LearningApplicationApi learning
    ) {
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
            Map<String, List<String>> businessRows
    ) {
    }

    private record SchemaFingerprint(
            List<String> columns,
            List<String> constraints,
            List<String> indexes,
            List<String> views
    ) {
        private SchemaFingerprint {
            columns = List.copyOf(columns);
            constraints = List.copyOf(constraints);
            indexes = List.copyOf(indexes);
            views = List.copyOf(views);
        }
    }
}
