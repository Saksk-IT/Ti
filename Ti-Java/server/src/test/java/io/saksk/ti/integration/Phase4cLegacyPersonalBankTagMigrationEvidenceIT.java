package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RowOutcome;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RowResult;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RunResult;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.TagInsert;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4cLegacyPersonalBankTagMigrationEvidenceIT {

    private static final long INHERITED_PRECEDENCE_SOURCE_ID = 8_501L;
    private static final long NORMAL_SOURCE_ID = 8_701L;
    private static final long PRECEDENCE_SOURCE_ID = 8_702L;
    private static final long FAULT_SOURCE_ID = 8_703L;
    private static final long AFTER_FAULT_SOURCE_ID = 8_704L;
    private static final long MISSING_BANK_SOURCE_ID = 8_705L;
    private static final long ORPHAN_QUESTION_SOURCE_ID = 8_706L;
    private static final long OVERFLOW_KEY_SOURCE_ID = 8_716L;
    private static final List<Long> DISCOVERED_SOURCE_IDS = List.of(
            INHERITED_PRECEDENCE_SOURCE_ID,
            NORMAL_SOURCE_ID,
            PRECEDENCE_SOURCE_ID,
            FAULT_SOURCE_ID,
            AFTER_FAULT_SOURCE_ID,
            MISSING_BANK_SOURCE_ID,
            ORPHAN_QUESTION_SOURCE_ID,
            OVERFLOW_KEY_SOURCE_ID);

    @Container
    static final PostgreSQLContainer POSTGRES_18 = migrationFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = migrationFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void rowTransactionPrimitiveEvidenceHoldsOnPostgres18() throws Exception {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void rowTransactionPrimitiveEvidenceHoldsOnPostgres16() throws Exception {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer migrationFixture(PostgreSQLContainer postgres) {
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
                        "/docker-entrypoint-initdb.d/066-personal-bank-usage-stats-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/068-personal-bank-user-counts-seed.sql"),
                        "/docker-entrypoint-initdb.d/068-personal-bank-user-counts-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/069-legacy-personal-bank-tag-migration-schema.sql"),
                        "/docker-entrypoint-initdb.d/069-legacy-personal-bank-tag-migration-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/070-legacy-personal-bank-tag-migration-seed.sql"),
                        "/docker-entrypoint-initdb.d/070-legacy-personal-bank-tag-migration-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        JdbcClient jdbc = JdbcClient.create(dataSource);
        LegacyPersonalBankTagMigrationEvidence operator =
                new LegacyPersonalBankTagMigrationEvidence(dataSource);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(discoveredSourceIds(jdbc)).containsExactlyElementsOf(DISCOVERED_SOURCE_IDS);

        SchemaFingerprint schemaBefore = schemaFingerprint(jdbc);
        List<ProgressRow> sourceBefore = progressRows(jdbc);
        List<ProgressRow> nonTargetBefore = nonTargetProgressRows(sourceBefore);

        var failed = operator.runSourceRow(FAULT_SOURCE_ID, (source, ordinal) -> {
            if (ordinal == 1) {
                throw new InjectedEvidenceFailure("rollback the complete source row");
            }
        });
        assertThat(failed.outcome()).isEqualTo(RowOutcome.FAILED_ROLLED_BACK);
        assertThat(failed.insertStatementsAttempted()).isEqualTo(1);
        assertThat(failed.insertedRowsCommitted()).isZero();
        assertThat(failed.failure()).contains(InjectedEvidenceFailure.class.getName());
        assertThat(targetRows(jdbc, 7_603L, 7_603)).isEmpty();
        assertThat(schemaFingerprint(jdbc)).isEqualTo(schemaBefore);
        assertThat(progressRows(jdbc)).isEqualTo(sourceBefore);
        assertThat(nonTargetProgressRows(progressRows(jdbc))).isEqualTo(nonTargetBefore);

        // This fixture sweep intentionally exercises each independent row primitive.
        // It is not the global production preflight/apply required by the contract.
        RunResult first = operator.runFixturePrimitiveSweep();
        assertThat(sourceRowIds(first)).containsExactlyElementsOf(DISCOVERED_SOURCE_IDS);
        assertThat(first.rollbackFailureCount()).isZero();
        assertThat(first.blockingRowCount()).isEqualTo(3);
        assertThat(first.isApplyEligible()).isFalse();
        assertThat(first.insertStatementsAttempted()).isEqualTo(13);
        assertThat(first.insertedRowsCommitted()).isEqualTo(13);
        assertThat(first.row(INHERITED_PRECEDENCE_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(first.row(NORMAL_SOURCE_ID).outcome()).isEqualTo(RowOutcome.MIGRATED);
        assertThat(first.row(PRECEDENCE_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(first.row(FAULT_SOURCE_ID).outcome()).isEqualTo(RowOutcome.MIGRATED);
        assertThat(first.row(AFTER_FAULT_SOURCE_ID).outcome()).isEqualTo(RowOutcome.MIGRATED);
        assertThat(first.row(MISSING_BANK_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.BANK_MISSING);
        assertThat(first.row(ORPHAN_QUESTION_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.ORPHAN_QUESTION);
        assertThat(first.row(OVERFLOW_KEY_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.INVALID_KEY);
        assertThat(first.rows())
                .extracting(result -> result.transactionId())
                .doesNotHaveDuplicates();

        assertThat(targetRows(jdbc, 7_601L, 7_601)).containsExactly(
                new TagInsert(0, "12345678901234567890"),
                new TagInsert(0, "alpha"),
                new TagInsert(0, "beta"),
                new TagInsert(0, "gamma"),
                new TagInsert(8_601, "alpha"),
                new TagInsert(8_601, "beta"),
                new TagInsert(8_602, "beta"),
                new TagInsert(8_602, "gamma"));
        assertThat(targetRows(jdbc, 7_601L, 7_601))
                .noneMatch(row -> row.questionId() == 8_699 || row.tag().equals("foreign"));
        assertThat(targetRows(jdbc, 7_602L, 7_602))
                .containsExactly(new TagInsert(0, "target-wins"));
        assertThat(targetRows(jdbc, 7_603L, 7_603)).containsExactly(
                new TagInsert(0, "rollback-a"),
                new TagInsert(0, "rollback-b"),
                new TagInsert(8_621, "rollback-a"));
        assertThat(targetRows(jdbc, 7_604L, 7_604)).containsExactly(
                new TagInsert(0, "after-failure"),
                new TagInsert(8_631, "after-failure"));
        assertThat(targetRows(jdbc, 7_605L, 7_602)).isEmpty();

        RunResult second = operator.runFixturePrimitiveSweep();
        assertThat(sourceRowIds(second)).containsExactlyElementsOf(DISCOVERED_SOURCE_IDS);
        assertThat(second.rollbackFailureCount()).isZero();
        assertThat(second.blockingRowCount()).isEqualTo(3);
        assertThat(second.isApplyEligible()).isFalse();
        assertThat(second.insertStatementsAttempted()).isZero();
        assertThat(second.insertedRowsCommitted()).isZero();
        assertThat(second.row(INHERITED_PRECEDENCE_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(second.row(NORMAL_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(second.row(FAULT_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(second.row(AFTER_FAULT_SOURCE_ID).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);

        assertThat(schemaFingerprint(jdbc)).isEqualTo(schemaBefore);
        assertThat(progressRows(jdbc)).isEqualTo(sourceBefore);
        assertThat(nonTargetProgressRows(progressRows(jdbc))).isEqualTo(nonTargetBefore);
    }

    private static List<Long> discoveredSourceIds(JdbcClient jdbc) {
        return jdbc.sql("""
                        SELECT id
                        FROM user_progress
                        WHERE p_key ~ '^bank_[1-9][0-9]*_tags$'
                        ORDER BY id
                        """)
                .query(Long.class)
                .list();
    }

    private static List<Long> sourceRowIds(RunResult result) {
        return result.rows().stream().map(RowResult::sourceRowId).toList();
    }

    private static List<TagInsert> targetRows(JdbcClient jdbc, long userId, int bankId) {
        return jdbc.sql("""
                        SELECT question_id, tag
                        FROM user_question_tag_items
                        WHERE user_id = :user_id
                          AND scope = 'user_bank'
                          AND scope_id = :bank_id
                        ORDER BY question_id, tag
                        """)
                .param("user_id", userId)
                .param("bank_id", bankId)
                .query((row, rowNumber) -> new TagInsert(
                        row.getInt("question_id"), row.getString("tag")))
                .list();
    }

    private static List<ProgressRow> progressRows(JdbcClient jdbc) {
        return jdbc.sql("""
                        SELECT id, user_id, p_key, data,
                               created_at::text AS created_at,
                               updated_at::text AS updated_at
                        FROM user_progress
                        ORDER BY id
                        """)
                .query((row, rowNumber) -> new ProgressRow(
                        row.getLong("id"),
                        row.getLong("user_id"),
                        row.getString("p_key"),
                        row.getString("data"),
                        row.getString("created_at"),
                        row.getString("updated_at")))
                .list();
    }

    private static List<ProgressRow> nonTargetProgressRows(List<ProgressRow> rows) {
        return rows.stream()
                .filter(row -> LegacyPersonalBankTagMigrationEvidence
                        .strictBankId(row.key()).isEmpty())
                .toList();
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

    private record ProgressRow(
            long id,
            long userId,
            String key,
            String data,
            String createdAt,
            String updatedAt
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

    private static final class InjectedEvidenceFailure extends RuntimeException {
        private InjectedEvidenceFailure(String message) {
            super(message);
        }
    }
}
