package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagGlobalPreflight;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ApplyPrerequisiteBlocker;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ReportingGroup;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.Status;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4cLegacyPersonalBankTagGlobalPreflightIT {

    private static final String SHA_256 = "[0-9a-f]{64}";
    private static final List<Long> LEGACY_RESERVED_SOURCE_IDS = List.of(
            9_501L, 9_502L, 9_503L, 9_504L, 9_505L, 9_506L, 9_507L,
            9_508L, 9_509L, 9_510L, 9_511L, 9_512L, 9_513L, 9_514L,
            9_517L, 9_518L);

    @Container
    static final PostgreSQLContainer POSTGRES_18 = globalPreflightFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = globalPreflightFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void globalReadOnlyPreflightEvidenceHoldsOnPostgres18() throws Exception {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void globalReadOnlyPreflightEvidenceHoldsOnPostgres16() throws Exception {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer globalPreflightFixture(
            PostgreSQLContainer postgres
    ) {
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
                                "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/071-legacy-personal-bank-tag-global-preflight-schema.sql"),
                        "/docker-entrypoint-initdb.d/071-legacy-tag-global-preflight-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/072-legacy-personal-bank-tag-global-preflight-seed.sql"),
                        "/docker-entrypoint-initdb.d/072-legacy-tag-global-preflight-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource ownerDataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        DriverManagerDataSource readOnlyDataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(),
                Phase2PostgresContainers.READ_ONLY_USER,
                Phase2PostgresContainers.READ_ONLY_PASSWORD);
        JdbcClient ownerJdbc = JdbcClient.create(ownerDataSource);
        JdbcClient readOnlyJdbc = JdbcClient.create(readOnlyDataSource);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(ownerJdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(readOnlyJdbc.sql("SELECT current_user").query(String.class).single())
                .isEqualTo(Phase2PostgresContainers.READ_ONLY_USER);
        assertThat(readOnlyJdbc.sql("SHOW transaction_read_only")
                .query(String.class).single()).isEqualTo("on");
        assertThat(reservedSourceIds(ownerJdbc))
                .containsExactlyElementsOf(LEGACY_RESERVED_SOURCE_IDS);

        DatabaseFingerprint before = databaseFingerprint(ownerJdbc);
        assertThat(before.sourceRows()).hasSize(18);
        assertThat(before.targetRows()).hasSize(7);
        assertThat(before.membershipRows()).isNotEmpty();
        assertThat(before.schema()).isNotEmpty();
        assertThat(before.indexes()).isNotEmpty();

        RecordingMembershipFactsApi membershipFacts =
                new RecordingMembershipFactsApi(readOnlyDataSource);
        LegacyPersonalBankTagGlobalPreflight preflight =
                new LegacyPersonalBankTagGlobalPreflight(
                        readOnlyDataSource, membershipFacts);

        LegacyPersonalBankTagPreflightReport lockBusy;
        try (Connection lockOwner = readOnlyDataSource.getConnection()) {
            acquireSessionLock(
                    lockOwner,
                    LegacyPersonalBankTagGlobalPreflight.advisoryLockKey());
            lockBusy = preflight.run();
            assertThat(lockBusy.mode()).isEqualTo("DRY_RUN");
            assertThat(lockBusy.status()).isEqualTo(Status.LOCK_BUSY);
            assertThat(lockBusy.fullSweepComplete()).isFalse();
            assertThat(lockBusy.isDataEligible()).isFalse();
            assertThat(lockBusy.rows()).isEmpty();
            assertThat(lockBusy.blockingRowCount()).isZero();
            assertThat(lockBusy.isApplyEligible()).isFalse();
            assertThat(lockBusy.globalFailures()).isEmpty();
            assertThat(lockBusy.aggregateDigest()).matches(SHA_256);
            assertThat(lockBusy.applyPrerequisiteBlockers())
                    .hasSize(3)
                    .containsExactlyInAnyOrderElementsOf(
                            EnumSet.allOf(ApplyPrerequisiteBlocker.class));
            assertThat(lockBusy.mutationStatementCount()).isZero();
            assertThat(lockBusy.ddlStatementCount()).isZero();
            assertThat(membershipFacts.requests()).isEmpty();
            assertThat(databaseFingerprint(ownerJdbc)).isEqualTo(before);
        }

        // Closing the dedicated competing session, rather than an explicit
        // unlock, must release its session-level lock.
        assertThat(canAcquireAndReleaseSessionLock(
                readOnlyDataSource,
                LegacyPersonalBankTagGlobalPreflight.advisoryLockKey())).isTrue();

        membershipFacts.resetAndProbeLockDuringMembership();
        LegacyPersonalBankTagPreflightReport completed = preflight.run();
        assertThat(completed.mode()).isEqualTo("DRY_RUN");
        assertThat(completed.status()).isEqualTo(Status.COMPLETED);
        assertThat(completed.fullSweepComplete()).isTrue();
        assertThat(completed.isDataEligible()).isFalse();
        assertThat(completed.isApplyEligible()).isFalse();
        assertThat(completed.advisoryLockKey())
                .isEqualTo(LegacyPersonalBankTagGlobalPreflight.advisoryLockKey());
        assertThat(completed.backendProcessId()).isPresent();
        assertThat(completed.backendProcessId().orElseThrow()).isPositive();
        assertThat(completed.databaseIdentityDigest()).isPresent();
        assertThat(completed.databaseIdentityDigest().orElseThrow()).matches(SHA_256);
        assertThat(completed.serverVersion()).contains(expectedVersion);
        assertThat(completed.transactionIsolation()).contains("serializable");
        assertThat(completed.transactionReadOnly()).isTrue();
        assertThat(completed.transactionDeferrable()).isTrue();
        assertThat(completed.startedAt()).isBeforeOrEqualTo(completed.completedAt());
        assertThat(completed.reservedRowCount()).isEqualTo(16);
        assertThat(completed.canonicalRowCount()).isEqualTo(12);
        assertThat(completed.nearMissRowCount()).isEqualTo(4);
        assertThat(completed.normalizedCollisionRowCount()).isEqualTo(3);
        assertThat(completed.rows()).hasSize(LEGACY_RESERVED_SOURCE_IDS.size());
        assertThat(completed.rows())
                .extracting(SourceRow::sourceRowId)
                .containsExactlyElementsOf(LEGACY_RESERVED_SOURCE_IDS);
        assertExpectedOutcomes(completed);
        assertThat(completed.blockingRowCount()).isEqualTo(12);
        assertThat(completed.outcomeCounts()).containsExactlyInAnyOrderEntriesOf(Map.ofEntries(
                Map.entry(RowOutcome.MIGRATABLE, 2L),
                Map.entry(RowOutcome.EMPTY_NOOP, 1L),
                Map.entry(RowOutcome.TARGET_ALREADY_PRESENT, 1L),
                Map.entry(RowOutcome.TARGET_CONFLICT, 1L),
                Map.entry(RowOutcome.NORMALIZED_BANK_COLLISION, 3L),
                Map.entry(RowOutcome.TARGET_INVALID, 1L),
                Map.entry(RowOutcome.INVALID_KEY, 1L),
                Map.entry(RowOutcome.INVALID_DATA, 3L),
                Map.entry(RowOutcome.BANK_MISSING, 1L),
                Map.entry(RowOutcome.ORPHAN_QUESTION, 1L),
                Map.entry(RowOutcome.MEMBERSHIP_UNAVAILABLE, 1L)));
        assertThat(completed.reportingGroupCounts())
                .containsExactlyInAnyOrderEntriesOf(Map.of(
                        ReportingGroup.ELIGIBLE, 4L,
                        ReportingGroup.CONFLICT, 5L,
                        ReportingGroup.INVALID, 4L,
                        ReportingGroup.UNRESOLVED, 3L,
                        ReportingGroup.GLOBAL_FAILURE, 0L));
        assertThat(completed.globalFailures()).isEmpty();
        assertThat(completed.aggregateDigest()).matches(SHA_256);
        assertThat(completed.applyPrerequisiteBlockers())
                .hasSize(3)
                .containsExactlyInAnyOrderElementsOf(
                        EnumSet.allOf(ApplyPrerequisiteBlocker.class));
        assertThat(completed.mutationStatementCount()).isZero();
        assertThat(completed.ddlStatementCount()).isZero();
        assertRedactedDigestEvidence(completed);
        assertThat(membershipFacts.requests())
                .contains(new MembershipRequest(9_402, List.of(10_411)));
        assertThat(membershipFacts.lockProbeAcquisitions())
                .isNotEmpty()
                .containsOnly(false);
        assertThat(databaseFingerprint(ownerJdbc)).isEqualTo(before);

        // The preflight must close the dedicated sweep connection and thereby
        // release the session-level lock before it returns its report.
        assertThat(canAcquireAndReleaseSessionLock(
                readOnlyDataSource,
                LegacyPersonalBankTagGlobalPreflight.advisoryLockKey())).isTrue();

        membershipFacts.resetAndProbeLockDuringMembership();
        LegacyPersonalBankTagPreflightReport repeated = preflight.run();
        assertThat(repeated.status()).isEqualTo(completed.status());
        assertThat(repeated.fullSweepComplete()).isTrue();
        assertThat(repeated.isDataEligible()).isFalse();
        assertThat(repeated.rows()).isEqualTo(completed.rows());
        assertThat(repeated.outcomeCounts()).isEqualTo(completed.outcomeCounts());
        assertThat(repeated.reportingGroupCounts())
                .isEqualTo(completed.reportingGroupCounts());
        assertThat(repeated.blockingRowCount()).isEqualTo(completed.blockingRowCount());
        assertThat(repeated.aggregateDigest()).isEqualTo(completed.aggregateDigest());
        assertThat(repeated.applyPrerequisiteBlockers())
                .isEqualTo(completed.applyPrerequisiteBlockers());
        assertThat(repeated.isApplyEligible()).isFalse();
        assertThat(repeated.mutationStatementCount()).isZero();
        assertThat(repeated.ddlStatementCount()).isZero();
        assertThat(membershipFacts.lockProbeAcquisitions())
                .isNotEmpty()
                .containsOnly(false);
        assertThat(databaseFingerprint(ownerJdbc)).isEqualTo(before);

        /*
         * This is deliberately a Node A read-only global-preflight test. The
         * mixed blockers keep applyEligible false. A durable migration marker,
         * source/target/membership write freeze, version/digest recheck, backup
         * readiness, apply races, operator credentials and production execution
         * remain unclosed and are not authorized by this evidence.
         */
    }

    private static void assertExpectedOutcomes(
            LegacyPersonalBankTagPreflightReport report
    ) {
        assertThat(row(report, 9_501L).outcome()).isEqualTo(RowOutcome.MIGRATABLE);
        assertThat(row(report, 9_502L).outcome()).isEqualTo(RowOutcome.MIGRATABLE);
        assertThat(row(report, 9_503L).outcome())
                .isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);
        assertThat(row(report, 9_504L).outcome()).isEqualTo(RowOutcome.TARGET_CONFLICT);
        assertThat(row(report, 9_505L).outcome()).isEqualTo(RowOutcome.BANK_MISSING);
        assertThat(row(report, 9_506L).outcome()).isEqualTo(RowOutcome.ORPHAN_QUESTION);
        assertThat(row(report, 9_507L).outcome()).isEqualTo(RowOutcome.INVALID_DATA);
        assertThat(row(report, 9_508L).outcome()).isEqualTo(RowOutcome.INVALID_DATA);
        assertThat(row(report, 9_509L).outcome()).isEqualTo(RowOutcome.INVALID_DATA);
        assertThat(row(report, 9_510L).outcome()).isEqualTo(RowOutcome.TARGET_INVALID);
        for (long sourceId : List.of(9_511L, 9_512L, 9_513L)) {
            SourceRow collision = row(report, sourceId);
            assertThat(collision.keyClassification()).isEqualTo(KeyClassification.NEAR_MISS);
            assertThat(collision.normalizedBankId()).contains(9_411);
            assertThat(collision.outcome()).isEqualTo(RowOutcome.NORMALIZED_BANK_COLLISION);
        }
        assertThat(row(report, 9_514L).keyClassification())
                .isEqualTo(KeyClassification.CANONICAL_INVALID);
        assertThat(row(report, 9_514L).outcome()).isEqualTo(RowOutcome.INVALID_KEY);
        assertThat(row(report, 9_517L).outcome()).isEqualTo(RowOutcome.EMPTY_NOOP);
        assertThat(row(report, 9_518L).outcome())
                .isEqualTo(RowOutcome.MEMBERSHIP_UNAVAILABLE);
    }

    private static void assertRedactedDigestEvidence(
            LegacyPersonalBankTagPreflightReport report
    ) {
        assertThat(report.rows()).allSatisfy(row -> {
            assertThat(row.keyDigest()).matches(SHA_256);
            assertThat(row.sourceDigest()).matches(SHA_256);
            row.planDigest().ifPresent(digest -> assertThat(digest).matches(SHA_256));
            row.targetDigest().ifPresent(digest -> assertThat(digest).matches(SHA_256));
            row.membershipDigest().ifPresent(digest -> assertThat(digest).matches(SHA_256));
        });
        assertThat(report.rows()).anySatisfy(
                row -> assertThat(row.planDigest()).isPresent());
        assertThat(report.rows()).anySatisfy(
                row -> assertThat(row.targetDigest()).isPresent());
        assertThat(report.rows()).anySatisfy(
                row -> assertThat(row.membershipDigest()).isPresent());
        assertThat(report.toString()).doesNotContain(
                "bank_9401_tags",
                "public-test-only-hash",
                "alpha，gamma",
                "membership-unavailable",
                "{\"tags\"");
    }

    private static SourceRow row(
            LegacyPersonalBankTagPreflightReport report,
            long sourceRowId
    ) {
        return report.rows().stream()
                .filter(row -> row.sourceRowId() == sourceRowId)
                .findFirst()
                .orElseThrow();
    }

    private static List<Long> reservedSourceIds(JdbcClient jdbc) {
        return jdbc.sql("""
                        SELECT source_row_id
                        FROM phase4c_legacy_personal_bank_tag_global_source_projection
                        ORDER BY source_row_id
                        """)
                .query(Long.class)
                .list();
    }

    private static DatabaseFingerprint databaseFingerprint(JdbcClient jdbc) {
        List<String> sourceRows = jdbc.sql("""
                        SELECT concat_ws('|', id, user_id, p_key, data,
                                         created_at::text, updated_at::text)
                        FROM user_progress
                        ORDER BY id
                        """)
                .query(String.class)
                .list();
        List<String> targetRows = jdbc.sql("""
                        SELECT concat_ws('|', user_id, scope, scope_id, question_id, tag,
                                         created_at::text, updated_at::text)
                        FROM user_question_tag_items
                        ORDER BY user_id, scope, scope_id, question_id, tag
                        """)
                .query(String.class)
                .list();
        List<String> membershipRows = new ArrayList<>();
        membershipRows.addAll(prefixed("BANK", jdbc.sql("""
                        SELECT concat_ws('|', id, user_id, name, status,
                                         created_at::text, updated_at::text)
                        FROM user_question_banks
                        ORDER BY id
                        """).query(String.class).list()));
        membershipRows.addAll(prefixed("QUESTION", jdbc.sql("""
                        SELECT concat_ws('|', id, bank_id, user_id, type, content,
                                         created_at::text)
                        FROM user_bank_questions
                        ORDER BY id
                        """).query(String.class).list()));

        List<String> schema = new ArrayList<>();
        schema.addAll(prefixed("COLUMN", jdbc.sql("""
                        SELECT concat_ws('|', table_name, ordinal_position, column_name,
                                         data_type, is_nullable, coalesce(column_default, ''))
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                        ORDER BY table_name, ordinal_position
                        """).query(String.class).list()));
        schema.addAll(prefixed("CONSTRAINT", jdbc.sql("""
                        SELECT concat_ws('|', conrelid::regclass::text, conname,
                                         pg_get_constraintdef(oid, true))
                        FROM pg_constraint
                        WHERE connamespace = current_schema()::regnamespace
                        ORDER BY conrelid::regclass::text, conname
                        """).query(String.class).list()));
        schema.addAll(prefixed("VIEW", jdbc.sql("""
                        SELECT concat_ws('|', viewname, definition)
                        FROM pg_views
                        WHERE schemaname = current_schema()
                        ORDER BY viewname
                        """).query(String.class).list()));
        schema.addAll(prefixed("GRANT", jdbc.sql("""
                        SELECT concat_ws('|', grantor, grantee, table_name, privilege_type)
                        FROM information_schema.role_table_grants
                        WHERE table_schema = current_schema()
                        ORDER BY grantor, grantee, table_name, privilege_type
                        """).query(String.class).list()));

        List<String> indexes = jdbc.sql("""
                        SELECT concat_ws('|', tablename, indexname, indexdef)
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                        ORDER BY tablename, indexname
                        """)
                .query(String.class)
                .list();
        return new DatabaseFingerprint(
                sourceRows, targetRows, membershipRows, schema, indexes);
    }

    private static List<String> prefixed(String kind, List<String> values) {
        return values.stream().map(value -> kind + "|" + value).toList();
    }

    private static void acquireSessionLock(Connection connection, long key)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT pg_advisory_lock(?)")) {
            statement.setLong(1, key);
            try (ResultSet ignored = statement.executeQuery()) {
                assertThat(ignored.next()).isTrue();
            }
        }
    }

    private static boolean canAcquireAndReleaseSessionLock(
            DataSource dataSource,
            long key
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement acquire = connection.prepareStatement(
                        "SELECT pg_try_advisory_lock(?)")) {
            acquire.setLong(1, key);
            boolean acquired;
            try (ResultSet result = acquire.executeQuery()) {
                assertThat(result.next()).isTrue();
                acquired = result.getBoolean(1);
            }
            if (acquired) {
                try (PreparedStatement release = connection.prepareStatement(
                        "SELECT pg_advisory_unlock(?)")) {
                    release.setLong(1, key);
                    try (ResultSet result = release.executeQuery()) {
                        assertThat(result.next()).isTrue();
                        assertThat(result.getBoolean(1)).isTrue();
                    }
                }
            }
            return acquired;
        }
    }

    private record DatabaseFingerprint(
            List<String> sourceRows,
            List<String> targetRows,
            List<String> membershipRows,
            List<String> schema,
            List<String> indexes
    ) {
        private DatabaseFingerprint {
            sourceRows = List.copyOf(sourceRows);
            targetRows = List.copyOf(targetRows);
            membershipRows = List.copyOf(membershipRows);
            schema = List.copyOf(schema);
            indexes = List.copyOf(indexes);
        }
    }

    private record MembershipRequest(int bankId, List<Integer> questionIds) {
        private MembershipRequest {
            questionIds = List.copyOf(questionIds.stream().distinct().sorted().toList());
        }
    }

    private static final class RecordingMembershipFactsApi
            implements PersonalBankQuestionFactsApi {

        private final DataSource dataSource;
        private final List<MembershipRequest> requests = new ArrayList<>();
        private final List<Boolean> lockProbeAcquisitions = new ArrayList<>();
        private boolean probeLock;

        private RecordingMembershipFactsApi(DataSource dataSource) {
            this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
        }

        @Override
        public PersonalBankQuestionAccessResult checkQuestionAccess(
                AuthenticatedPersonalBankViewer viewer,
                int bankId
        ) {
            throw new AssertionError("global preflight must use only membership facts");
        }

        @Override
        public PersonalBankQuestionFactsResult summarizeQuestions(
                AuthenticatedPersonalBankViewer viewer,
                PersonalBankQuestionSelection selection
        ) {
            throw new AssertionError("global preflight must use only membership facts");
        }

        @Override
        public PersonalBankQuestionMembershipView inspectQuestionMembership(
                int bankId,
                List<Integer> questionIds
        ) {
            MembershipRequest request = new MembershipRequest(bankId, questionIds);
            requests.add(request);
            if (probeLock) {
                try {
                    lockProbeAcquisitions.add(canAcquireAndReleaseSessionLock(
                            dataSource,
                            LegacyPersonalBankTagGlobalPreflight.advisoryLockKey()));
                } catch (SQLException exception) {
                    throw new AssertionError("advisory-lock probe failed", exception);
                }
            }
            if (bankId == 9_413) {
                throw new MembershipUnavailableEvidenceException(
                        "injected local membership outage");
            }

            JdbcClient jdbc = JdbcClient.create(dataSource);
            boolean bankExists = jdbc.sql("""
                            SELECT EXISTS (
                                SELECT 1
                                FROM user_question_banks
                                WHERE id = :bank_id
                            )
                            """)
                    .param("bank_id", bankId)
                    .query(Boolean.class)
                    .single();
            List<Integer> requested = request.questionIds();
            List<Integer> existing = bankExists
                    ? jdbc.sql("""
                                    SELECT id
                                    FROM user_bank_questions
                                    WHERE bank_id = :bank_id
                                    ORDER BY id
                                    """)
                            .param("bank_id", bankId)
                            .query(Integer.class)
                            .list()
                            .stream()
                            .filter(requested::contains)
                            .toList()
                    : List.of();
            return PersonalBankQuestionMembershipView.create(
                    bankId, bankExists, existing);
        }

        private void resetAndProbeLockDuringMembership() {
            requests.clear();
            lockProbeAcquisitions.clear();
            probeLock = true;
        }

        private List<MembershipRequest> requests() {
            return List.copyOf(requests);
        }

        private List<Boolean> lockProbeAcquisitions() {
            return List.copyOf(lockProbeAcquisitions);
        }
    }

    private static final class MembershipUnavailableEvidenceException
            extends RuntimeException {

        private MembershipUnavailableEvidenceException(String message) {
            super(message);
        }
    }
}
