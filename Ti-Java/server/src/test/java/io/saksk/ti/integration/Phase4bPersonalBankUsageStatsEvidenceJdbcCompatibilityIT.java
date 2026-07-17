package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUsageStatsEvidenceSql;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = usageStatsFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = usageStatsFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres18() {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres16() {
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
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:bank_id) AS text)")
                .param("bank_id", 7_101)
                .query(String.class)
                .single())
                .isEqualTo("integer");

        TableCounts before = tableCounts(jdbc);
        assertBankProbeSemantics(jdbc);
        assertSharedUserPairProjection(jdbc);
        assertPublicUserProjection(jdbc);
        assertLegacyIndexShape(jdbc);
        assertThat(tableCounts(jdbc)).isEqualTo(before);

        assertIndependentFailureBoundaries(jdbc);
        assertThat(tableCounts(jdbc)).isEqualTo(before);
    }

    private static void assertBankProbeSemantics(JdbcClient jdbc) {
        assertThat(bankProbe(jdbc, 7_101))
                .singleElement()
                .isEqualTo(new EvidenceBankRow(7_101, 7_001, false, 1));
        assertThat(bankProbe(jdbc, 7_102))
                .singleElement()
                .isEqualTo(new EvidenceBankRow(7_102, 7_001, false, 0));
        assertThat(bankProbe(jdbc, 7_103))
                .singleElement()
                .isEqualTo(new EvidenceBankRow(7_103, 7_001, false, null));
        assertThat(bankProbe(jdbc, 79_999)).isEmpty();
    }

    private static void assertSharedUserPairProjection(JdbcClient jdbc) {
        assertThat(sharedUsers(jdbc, 7_101)).containsExactlyInAnyOrder(
                new EvidenceSharedUserRow(7_003, LocalDateTime.of(2099, 1, 1, 0, 0)),
                new EvidenceSharedUserRow(7_004, LocalDateTime.of(2020, 1, 1, 0, 0)),
                new EvidenceSharedUserRow(7_003, null),
                new EvidenceSharedUserRow(7_005, null),
                new EvidenceSharedUserRow(7_007, null),
                new EvidenceSharedUserRow(7_001, null),
                new EvidenceSharedUserRow(7_006, null));
        assertThat(sharedUsers(jdbc, 7_105)).isEmpty();
        assertThat(sharedUsers(jdbc, 79_999)).isEmpty();
    }

    private static void assertPublicUserProjection(JdbcClient jdbc) {
        assertThat(publicUsers(jdbc, 7_101))
                .containsExactlyInAnyOrder(7_001, 7_003, 7_006, 7_007);
        assertThat(publicUsers(jdbc, 7_105)).containsExactly(7_004);
        assertThat(publicUsers(jdbc, 79_999)).isEmpty();
    }

    private static void assertLegacyIndexShape(JdbcClient jdbc) {
        List<String> recordIndexes = indexDefinitions(jdbc, "bank_share_records");
        assertThat(recordIndexes).hasSize(2);
        assertThat(recordIndexes).noneMatch(definition ->
                definition.matches("(?is).*\\(\\s*bank_id(?:\\s|,|\\)).*"));

        List<String> publicIndexes = indexDefinitions(jdbc, "public_bank_users");
        assertThat(publicIndexes).hasSize(2);
        assertThat(publicIndexes).anyMatch(definition ->
                definition.matches("(?is).*\\(\\s*bank_id\\s*,\\s*user_id\\s*\\).*"));
    }

    private static List<String> indexDefinitions(JdbcClient jdbc, String table) {
        return jdbc.sql("""
                        SELECT indexdef
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                          AND tablename = :table
                        ORDER BY indexname
                        """)
                .param("table", table)
                .query(String.class)
                .list();
    }

    private static void assertIndependentFailureBoundaries(JdbcClient jdbc) {
        renameAndAssertFailure(
                jdbc,
                "user_question_banks",
                "user_question_banks_temporarily_unavailable",
                () -> bankProbe(jdbc, 7_101));
        renameAndAssertFailure(
                jdbc,
                "bank_share_records",
                "bank_share_records_temporarily_unavailable",
                () -> sharedUsers(jdbc, 7_101));
        renameAndAssertFailure(
                jdbc,
                "bank_shares",
                "bank_shares_temporarily_unavailable",
                () -> sharedUsers(jdbc, 7_101));
        renameAndAssertFailure(
                jdbc,
                "public_bank_users",
                "public_bank_users_temporarily_unavailable",
                () -> publicUsers(jdbc, 7_101));

        assertThat(bankProbe(jdbc, 7_101)).hasSize(1);
        assertThat(sharedUsers(jdbc, 7_101)).hasSize(7);
        assertThat(publicUsers(jdbc, 7_101)).hasSize(4);
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

    private static List<EvidenceBankRow> bankProbe(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankUsageStatsEvidenceSql.BANK_PROBE)
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT::mapBank)
                .list();
    }

    private static List<EvidenceSharedUserRow> sharedUsers(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankUsageStatsEvidenceSql.SHARED_USERS)
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT::mapSharedUser)
                .list();
    }

    private static List<Integer> publicUsers(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankUsageStatsEvidenceSql.PUBLIC_USERS)
                .param("bank_id", bankId)
                .query(Integer.class)
                .list();
    }

    private static EvidenceBankRow mapBank(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new EvidenceBankRow(
                resultSet.getInt("id"),
                resultSet.getInt("user_id"),
                resultSet.getObject("is_public", Boolean.class),
                resultSet.getObject("status", Integer.class));
    }

    private static EvidenceSharedUserRow mapSharedUser(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new EvidenceSharedUserRow(
                resultSet.getInt("user_id"),
                resultSet.getObject("expires_at", LocalDateTime.class));
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

    private record EvidenceBankRow(int id, int ownerId, Boolean publicBank, Integer status) {
    }

    private record EvidenceSharedUserRow(int userId, LocalDateTime expiresAt) {
    }

    private record TableCounts(long banks, long shares, long records, long publicUsers) {
    }
}
