package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.SharedUserAccess;
import io.saksk.ti.personalbank.infrastructure.persistence.JdbcPersonalBankUsageStatsQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Timestamp;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4bPersonalBankUsageStatsJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = usageStatsFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = usageStatsFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void runtimeAdapterRemainsCompatibleWithPostgres18() {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void runtimeAdapterRemainsCompatibleWithPostgres16() {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer usageStatsFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/063-personal-bank-share-list-seed.sql"),
                        "/docker-entrypoint-initdb.d/063-personal-bank-share-list-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/064-personal-bank-all-shares-seed.sql"),
                        "/docker-entrypoint-initdb.d/064-personal-bank-all-shares-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/065-personal-bank-usage-stats-schema.sql"),
                        "/docker-entrypoint-initdb.d/065-personal-bank-usage-stats-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/066-personal-bank-usage-stats-seed.sql"),
                        "/docker-entrypoint-initdb.d/066-personal-bank-usage-stats-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        JdbcClient jdbc = JdbcClient.create(dataSource);
        PlatformTransactionManager transactions = new DataSourceTransactionManager(dataSource);
        PersonalBankUsageStatsQueryPort query = transactionalProxy(
                JdbcPersonalBankUsageStatsQueryAdapterTestAccess.create(jdbc),
                transactions);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:bank_id) AS text)")
                .param("bank_id", 7_101)
                .query(String.class)
                .single())
                .isEqualTo("integer");

        TableCounts before = tableCounts(jdbc);
        assertBankProjection(query);
        assertSharedProjection(query);
        assertPublicProjection(query);
        assertThat(tableCounts(jdbc)).isEqualTo(before);

        assertIndependentFailureBoundaries(jdbc, query, transactions);
        assertThat(tableCounts(jdbc)).isEqualTo(before);
    }

    private static PersonalBankUsageStatsQueryPort transactionalProxy(
            PersonalBankUsageStatsQueryPort target,
            PlatformTransactionManager transactions
    ) {
        TransactionInterceptor interceptor = new TransactionInterceptor();
        interceptor.setTransactionManager(transactions);
        interceptor.setTransactionAttributeSource(
                new AnnotationTransactionAttributeSource());
        ProxyFactory proxy = new ProxyFactory(target);
        proxy.addAdvice(interceptor);
        return (PersonalBankUsageStatsQueryPort) proxy.getProxy();
    }

    private static void assertBankProjection(PersonalBankUsageStatsQueryPort query) {
        assertThat(query.findBank(7_101))
                .contains(new BankAccess(7_101, 7_001L, false, 1));
        assertThat(query.findBank(7_102))
                .contains(new BankAccess(7_102, 7_001L, false, 0));
        assertThat(query.findBank(7_103))
                .contains(new BankAccess(7_103, 7_001L, false, null));
        assertThat(query.findBank(0))
                .contains(new BankAccess(0, 7_001L, false, 1));
        assertThat(query.findBank(-1)).isEmpty();
        assertThat(query.findBank(79_999)).isEmpty();
    }

    private static void assertSharedProjection(PersonalBankUsageStatsQueryPort query) {
        List<SharedUserAccess> rows = query.listSharedUsers(7_101);
        assertThat(rows).containsExactlyInAnyOrder(
                new SharedUserAccess(7_003, Timestamp.valueOf("2099-01-01 00:00:00")),
                new SharedUserAccess(7_004, Timestamp.valueOf("2020-01-01 00:00:00")),
                new SharedUserAccess(7_003, null),
                new SharedUserAccess(7_005, null),
                new SharedUserAccess(7_007, null),
                new SharedUserAccess(7_001, null),
                new SharedUserAccess(7_006, null));
        assertThatThrownBy(() -> rows.add(rows.getFirst()))
                .isInstanceOf(UnsupportedOperationException.class);
        assertThat(query.listSharedUsers(7_105)).isEmpty();
        assertThat(query.listSharedUsers(79_999)).isEmpty();
    }

    private static void assertPublicProjection(PersonalBankUsageStatsQueryPort query) {
        List<Object> rows = query.listPublicUserIds(7_101);
        assertThat(rows).containsExactlyInAnyOrder(7_001, 7_003, 7_006, 7_007);
        assertThatThrownBy(() -> rows.add(7_999))
                .isInstanceOf(UnsupportedOperationException.class);
        assertThat(query.listPublicUserIds(7_105)).containsExactly(7_004);
        assertThat(query.listPublicUserIds(79_999)).isEmpty();
    }

    private static void assertIndependentFailureBoundaries(
            JdbcClient jdbc,
            PersonalBankUsageStatsQueryPort query,
            PlatformTransactionManager transactions
    ) {
        renameAndAssertFailure(
                jdbc,
                "user_question_banks",
                "user_question_banks_temporarily_unavailable",
                () -> query.findBank(7_101));
        renameAndAssertFailure(
                jdbc,
                "bank_share_records",
                "bank_share_records_temporarily_unavailable",
                () -> query.listSharedUsers(7_101));
        renameAndAssertFailure(
                jdbc,
                "bank_shares",
                "bank_shares_temporarily_unavailable",
                () -> query.listSharedUsers(7_101));
        renameAndAssertFailure(
                jdbc,
                "public_bank_users",
                "public_bank_users_temporarily_unavailable",
                () -> query.listPublicUserIds(7_101));
        renameAndAssertOptionalFailureIsolation(jdbc, query, transactions);

        assertThat(query.findBank(7_101)).isPresent();
        assertThat(query.listSharedUsers(7_101)).hasSize(7);
        assertThat(query.listPublicUserIds(7_101)).hasSize(4);
    }

    private static void renameAndAssertFailure(
            JdbcClient jdbc,
            String table,
            String temporaryTable,
            Runnable read
    ) {
        jdbc.sql("ALTER TABLE " + table + " RENAME TO " + temporaryTable).update();
        try {
            assertThatThrownBy(read::run).isInstanceOf(DataAccessException.class);
        } finally {
                jdbc.sql("ALTER TABLE " + temporaryTable + " RENAME TO " + table).update();
        }
    }

    private static void renameAndAssertOptionalFailureIsolation(
            JdbcClient jdbc,
            PersonalBankUsageStatsQueryPort query,
            PlatformTransactionManager transactions
    ) {
        String table = "bank_share_records";
        String temporaryTable = "bank_share_records_transactionally_unavailable";
        jdbc.sql("ALTER TABLE " + table + " RENAME TO " + temporaryTable).update();
        try {
            TransactionTemplate outerRead = new TransactionTemplate(transactions);
            outerRead.setReadOnly(true);
            outerRead.executeWithoutResult(ignored -> {
                assertThatThrownBy(() -> query.listSharedUsers(7_101))
                        .isInstanceOf(DataAccessException.class);
                assertThat(query.listPublicUserIds(7_101)).hasSize(4);
            });
        } finally {
            jdbc.sql("ALTER TABLE " + temporaryTable + " RENAME TO " + table).update();
        }
    }

    private static TableCounts tableCounts(JdbcClient jdbc) {
        return new TableCounts(
                count(jdbc, "user_question_banks"),
                count(jdbc, "bank_shares"),
                count(jdbc, "bank_share_records"),
                count(jdbc, "public_bank_users"));
    }

    private static long count(JdbcClient jdbc, String table) {
        return jdbc.sql("SELECT COUNT(*) FROM " + table).query(Long.class).single();
    }

    private record TableCounts(long banks, long shares, long records, long publicUsers) {
    }
}
