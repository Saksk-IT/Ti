package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ApplyPrerequisiteBlocker;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.GlobalFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ReportingGroup;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.Status;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;

class LegacyPersonalBankTagGlobalPreflightTest {

    private static final Instant NOW = Instant.parse("2026-07-19T00:00:00Z");
    private static final String DIGEST = "0".repeat(64);

    @Test
    void exposesOnlyReadAndTransactionControlStatements() {
        assertThat(LegacyPersonalBankTagGlobalPreflight.statementSurface())
                .hasSize(7)
                .allSatisfy(sql -> {
                    String normalized = sql.strip().replaceAll("\\s+", " ");
                    assertThat(normalized).matches("(?i)^(SELECT|SET TRANSACTION)\\b.*");
                    assertThat(normalized).doesNotMatch(
                            "(?is).*\\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|"
                                    + "TRUNCATE|GRANT|REVOKE|COPY|CALL|DO)\\b.*");
                });
        assertThat(LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL)
                .contains("p_key LIKE 'bank_%_tags'")
                .contains("AS bounded_data")
                .contains("AS data_utf8_bytes")
                .contains("pg_catalog.octet_length(")
                .contains("pg_catalog.convert_to(data, 'UTF8')) <= ?")
                .doesNotContain("FOR UPDATE");
        assertThat(LegacyPersonalBankTagGlobalPreflight.MAX_RESERVED_SOURCE_ROWS)
                .isEqualTo(100_000);
        assertThat(LegacyPersonalBankTagGlobalPreflight.MAX_RESERVED_SOURCE_UTF8_BYTES)
                .isEqualTo(256L * 1024L * 1024L);
    }

    @Test
    void reducesConnectionAcquisitionFailureToASanitizedGlobalBlocker() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        when(dataSource.getConnection()).thenThrow(new SQLException(
                "jdbc:postgresql://private/db?password=do-not-report", "08001"));

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.FAILED);
        assertThat(report.globalFailures()).singleElement().satisfies(failure -> {
            assertThat(failure.code().name()).isEqualTo("CONNECTION_ACQUISITION_FAILED");
            assertThat(failure.sqlState()).contains("08001");
            assertThat(failure.exceptionType()).contains(SQLException.class.getName());
        });
        assertThat(report.reportingGroupCounts().get(ReportingGroup.GLOBAL_FAILURE))
                .isEqualTo(1L);
        assertThat(report.toString())
                .doesNotContain("private", "password", "do-not-report", "jdbc:postgresql");
        assertThat(report.isDataEligible()).isFalse();
        assertThat(report.isApplyEligible()).isFalse();
        assertThat(report.mutationStatementCount()).isZero();
        assertThat(report.ddlStatementCount()).isZero();
        verifyNoInteractions(memberships);
    }

    @Test
    void lockContentionClosesTheDedicatedConnectionWithoutStartingTheSweep()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        PreparedStatement lockStatement = mock(PreparedStatement.class);
        ResultSet lockRow = mock(ResultSet.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.prepareStatement(LegacyPersonalBankTagGlobalPreflight.TRY_LOCK_SQL))
                .thenReturn(lockStatement);
        when(lockStatement.executeQuery()).thenReturn(lockRow);
        when(lockRow.next()).thenReturn(true);
        when(lockRow.getInt(1)).thenReturn(31_337);
        when(lockRow.getBoolean(2)).thenReturn(false);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.LOCK_BUSY);
        assertThat(report.backendProcessId()).contains(31_337);
        assertThat(report.rows()).isEmpty();
        assertThat(report.globalFailures()).isEmpty();
        assertThat(report.fullSweepComplete()).isFalse();
        assertThat(report.isApplyEligible()).isFalse();
        verify(connection, never()).setReadOnly(true);
        verify(connection, never()).commit();
        verify(connection).close();
        verifyNoInteractions(memberships);
    }

    @Test
    void reducesInitialConnectionSetupFailureToASanitizedGlobalBlocker()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        doThrow(new SQLException("setup-secret-password", "08006"))
                .when(connection).setAutoCommit(true);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.FAILED);
        assertThat(report.globalFailures()).singleElement().satisfies(failure -> {
            assertThat(failure.code().name()).isEqualTo("CONNECTION_SETUP_FAILED");
            assertThat(failure.sqlState()).contains("08006");
        });
        assertThat(report.toString()).doesNotContain("setup-secret-password");
        assertThat(report.isApplyEligible()).isFalse();
        verify(connection).close();
        verifyNoInteractions(memberships);
    }

    @Test
    void closeFailureOverridesLockBusyWithASanitizedGlobalBlocker() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        PreparedStatement lockStatement = mock(PreparedStatement.class);
        ResultSet lockRow = mock(ResultSet.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.prepareStatement(LegacyPersonalBankTagGlobalPreflight.TRY_LOCK_SQL))
                .thenReturn(lockStatement);
        when(lockStatement.executeQuery()).thenReturn(lockRow);
        when(lockRow.next()).thenReturn(true);
        when(lockRow.getInt(1)).thenReturn(31_338);
        when(lockRow.getBoolean(2)).thenReturn(false);
        doThrow(new SQLException("close-secret-credential", "08006"))
                .when(connection).close();

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.FAILED);
        assertThat(report.backendProcessId()).contains(31_338);
        assertThat(report.globalFailures()).singleElement().satisfies(failure -> {
            assertThat(failure.code().name()).isEqualTo("CONNECTION_CLOSE_FAILED");
            assertThat(failure.sqlState()).contains("08006");
        });
        assertThat(report.toString()).doesNotContain("close-secret-credential");
        assertThat(report.isApplyEligible()).isFalse();
        verifyNoInteractions(memberships);
    }

    @Test
    void classifiesMissingBankBeforeDirtyTargetStructure() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);

        ResultSet lockRow = singleRow();
        when(lockRow.getInt(1)).thenReturn(41_141);
        when(lockRow.getBoolean(2)).thenReturn(true);
        stubQuery(connection, LegacyPersonalBankTagGlobalPreflight.TRY_LOCK_SQL, lockRow);

        ResultSet metadataRow = singleRow();
        when(metadataRow.getString(1)).thenReturn("private-database-name");
        when(metadataRow.getString(2)).thenReturn("private-database-user");
        when(metadataRow.getString(3)).thenReturn("18.4");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.CONNECTION_METADATA_SQL,
                metadataRow);

        Statement transactionControl = mock(Statement.class);
        when(connection.createStatement()).thenReturn(transactionControl);
        ResultSet transactionFacts = singleRow();
        when(transactionFacts.getString(1)).thenReturn("serializable");
        when(transactionFacts.getString(2)).thenReturn("on");
        when(transactionFacts.getString(3)).thenReturn("on");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.TRANSACTION_FACTS_SQL,
                transactionFacts);

        ResultSet sourceRows = mock(ResultSet.class);
        when(sourceRows.next()).thenReturn(true, false);
        when(sourceRows.getLong("id")).thenReturn(91_001L);
        when(sourceRows.getLong("user_id")).thenReturn(92_001L);
        when(sourceRows.getString("p_key")).thenReturn("bank_9411_tags");
        String sourceData = """
                {"tags":["source-secret"],"question_tags":{"77":["source-secret"]}}
                """;
        when(sourceRows.getString("bounded_data")).thenReturn(sourceData);
        when(sourceRows.getObject("data_utf8_bytes", Integer.class))
                .thenReturn(sourceData.getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL,
                sourceRows);

        ResultSet targetRows = mock(ResultSet.class);
        when(targetRows.next()).thenReturn(true, false);
        when(targetRows.getObject("question_id", Integer.class)).thenReturn(88);
        when(targetRows.getString("tag")).thenReturn(" dirty-target-secret ");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.TARGET_ROWS_SQL,
                targetRows);

        when(memberships.inspectQuestionMembership(eq(9_411), anyList()))
                .thenReturn(PersonalBankQuestionMembershipView.create(
                        9_411, false, List.of()));

        ResultSet unlockRow = singleRow();
        when(unlockRow.getBoolean(1)).thenReturn(true);
        stubQuery(connection, LegacyPersonalBankTagGlobalPreflight.UNLOCK_SQL, unlockRow);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.COMPLETED);
        assertThat(report.fullSweepComplete()).isTrue();
        assertThat(report.rows()).singleElement().satisfies(row -> {
            assertThat(row.outcome()).isEqualTo(RowOutcome.BANK_MISSING);
            assertThat(row.failureCode()).isEqualTo("BANK_NOT_FOUND");
            assertThat(row.reportingGroup()).isEqualTo(ReportingGroup.UNRESOLVED);
            assertThat(row.targetDigest()).isPresent();
        });
        assertThat(report.toString())
                .doesNotContain(
                        "source-secret",
                        "dirty-target-secret",
                        "private-database-name",
                        "private-database-user");
        assertThat(report.blockingRowCount()).isEqualTo(1L);
        assertThat(report.isApplyEligible()).isFalse();
        verify(memberships).inspectQuestionMembership(9_411, List.of(77));
        verify(transactionControl).execute(
                LegacyPersonalBankTagGlobalPreflight.SET_TRANSACTION_SQL);
        verify(connection).commit();
        verify(connection).close();
    }

    @Test
    void rejectsOversizedPayloadWithoutMaterializingRawDataOrReadingTarget()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        stubSuccessfulSweepPreamble(connection, 51_001);

        ResultSet sourceRows = mock(ResultSet.class);
        when(sourceRows.next()).thenReturn(true, false);
        when(sourceRows.getLong("id")).thenReturn(91_101L);
        when(sourceRows.getLong("user_id")).thenReturn(92_101L);
        when(sourceRows.getString("p_key")).thenReturn("bank_9511_tags");
        when(sourceRows.getString("bounded_data")).thenReturn(null);
        int oversizedBytes = LegacyPersonalBankTagPreflightParser.MAX_PAYLOAD_UTF8_BYTES + 1;
        when(sourceRows.getObject("data_utf8_bytes", Integer.class))
                .thenReturn(oversizedBytes);
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL,
                sourceRows);
        stubSuccessfulUnlock(connection, true);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.COMPLETED);
        assertThat(report.rows()).singleElement().satisfies(row -> {
            assertThat(row.outcome()).isEqualTo(RowOutcome.INVALID_DATA);
            assertThat(row.failureCode()).isEqualTo("PAYLOAD_LIMIT_EXCEEDED");
            assertThat(row.sourceUtf8Bytes()).isEqualTo(oversizedBytes);
            assertThat(row.sourceDigest()).matches("[0-9a-f]{64}");
            assertThat(row.planDigest()).isEmpty();
            assertThat(row.targetDigest()).isEmpty();
        });
        verify(sourceRows, never()).getString("data");
        verify(connection, never()).prepareStatement(
                LegacyPersonalBankTagGlobalPreflight.TARGET_ROWS_SQL);
        verifyNoInteractions(memberships);
        verify(connection).commit();
        verify(connection).close();
    }

    @Test
    void rejectsStructurallyValidTargetQuestionOutsideItsBank() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        stubSuccessfulSweepPreamble(connection, 51_002);

        String sourceData = """
                {"tags":["source-secret"],"question_tags":{"77":["source-secret"]}}
                """;
        ResultSet sourceRows = mock(ResultSet.class);
        when(sourceRows.next()).thenReturn(true, false);
        when(sourceRows.getLong("id")).thenReturn(91_102L);
        when(sourceRows.getLong("user_id")).thenReturn(92_102L);
        when(sourceRows.getString("p_key")).thenReturn("bank_9512_tags");
        when(sourceRows.getString("bounded_data")).thenReturn(sourceData);
        when(sourceRows.getObject("data_utf8_bytes", Integer.class))
                .thenReturn(sourceData.getBytes(StandardCharsets.UTF_8).length);
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL,
                sourceRows);

        ResultSet targetRows = mock(ResultSet.class);
        when(targetRows.next()).thenReturn(true, false);
        when(targetRows.getObject("question_id", Integer.class)).thenReturn(88);
        when(targetRows.getString("tag")).thenReturn("target-secret");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.TARGET_ROWS_SQL,
                targetRows);
        when(memberships.inspectQuestionMembership(9_512, List.of(77, 88)))
                .thenReturn(PersonalBankQuestionMembershipView.create(
                        9_512, true, List.of(77)));
        stubSuccessfulUnlock(connection, true);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.COMPLETED);
        assertThat(report.rows()).singleElement().satisfies(row -> {
            assertThat(row.outcome()).isEqualTo(RowOutcome.TARGET_INVALID);
            assertThat(row.failureCode()).isEqualTo("TARGET_QUESTION_OUTSIDE_BANK");
            assertThat(row.reportingGroup()).isEqualTo(ReportingGroup.CONFLICT);
        });
        assertThat(report.toString()).doesNotContain("source-secret", "target-secret");
        verify(memberships).inspectQuestionMembership(9_512, List.of(77, 88));
        verify(connection).commit();
        verify(connection).close();
    }

    @Test
    void rollsBackThenUnlocksAndClosesWhenTheSourceScanFails() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        stubSuccessfulSweepPreamble(connection, 51_003);

        PreparedStatement sourceStatement = mock(PreparedStatement.class);
        when(connection.prepareStatement(
                LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL))
                .thenReturn(sourceStatement);
        when(sourceStatement.executeQuery()).thenThrow(
                new SQLException("source-scan-secret", "57014"));
        PreparedStatement unlockStatement = stubSuccessfulUnlock(connection, true);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.FAILED);
        assertThat(report.globalFailures()).singleElement().satisfies(failure -> {
            assertThat(failure.code().name()).isEqualTo("SOURCE_SCAN_FAILED");
            assertThat(failure.sqlState()).contains("57014");
        });
        assertThat(report.toString()).doesNotContain("source-scan-secret");
        InOrder cleanup = inOrder(connection, unlockStatement);
        cleanup.verify(connection).rollback();
        cleanup.verify(connection).setAutoCommit(true);
        cleanup.verify(unlockStatement).executeQuery();
        cleanup.verify(connection).close();
        verifyNoInteractions(memberships);
    }

    @Test
    void stillUnlocksAndClosesWhenRollbackFails() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        PersonalBankQuestionFactsApi memberships = mock(PersonalBankQuestionFactsApi.class);
        Connection connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        stubSuccessfulSweepPreamble(connection, 51_004);

        PreparedStatement sourceStatement = mock(PreparedStatement.class);
        when(connection.prepareStatement(
                LegacyPersonalBankTagGlobalPreflight.DISCOVER_RESERVED_SOURCE_SQL))
                .thenReturn(sourceStatement);
        when(sourceStatement.executeQuery()).thenThrow(
                new SQLException("source-scan-secret", "57014"));
        doThrow(new SQLException("rollback-secret", "08006"))
                .when(connection).rollback();
        PreparedStatement unlockStatement = stubSuccessfulUnlock(connection, false);

        var report = preflight(dataSource, memberships).run();

        assertThat(report.status()).isEqualTo(Status.FAILED);
        assertThat(report.globalFailures())
                .extracting(failure -> failure.code().name())
                .containsExactly(
                        "SOURCE_SCAN_FAILED",
                        "READ_ONLY_ROLLBACK_FAILED",
                        "ADVISORY_UNLOCK_REJECTED");
        assertThat(report.toString())
                .doesNotContain("source-scan-secret", "rollback-secret");
        verify(connection).rollback();
        verify(connection, times(2)).setAutoCommit(true);
        verify(unlockStatement).executeQuery();
        verify(connection).close();
        verifyNoInteractions(memberships);
    }

    @Test
    void reportRejectsInternallyInconsistentEvidenceAndNeverAuthorizesApply() {
        var valid = report(
                Status.COMPLETED,
                NOW,
                NOW,
                0,
                0,
                0,
                0,
                List.of(),
                zeroOutcomeCounts(),
                zeroGroupCounts(),
                List.of(),
                0);
        assertThat(valid.isDataEligible()).isTrue();
        assertThat(valid.isApplyEligible()).isFalse();
        assertThat(RowOutcome.TARGET_INVALID.group()).isEqualTo(ReportingGroup.CONFLICT);

        assertThatThrownBy(() -> report(
                Status.COMPLETED, NOW, NOW.minusSeconds(1),
                0, 0, 0, 0, List.of(), zeroOutcomeCounts(), zeroGroupCounts(),
                List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("precedes");
        assertThatThrownBy(() -> report(
                Status.FAILED, NOW, NOW,
                1, 0, 0, 0, List.of(), zeroOutcomeCounts(), zeroGroupCounts(),
                List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("classification totals");
        assertThatThrownBy(() -> report(
                Status.FAILED, NOW, NOW,
                0, 0, 0, 1, List.of(), zeroOutcomeCounts(), zeroGroupCounts(),
                List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("collision count");
        assertThatThrownBy(() -> report(
                Status.COMPLETED, NOW, NOW,
                1, 1, 0, 0, List.of(), zeroOutcomeCounts(), zeroGroupCounts(),
                List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("did not classify every row");

        SourceRow blocker = blockingRow();
        assertThatThrownBy(() -> report(
                Status.COMPLETED, NOW, NOW,
                1, 0, 1, 0, List.of(blocker),
                outcomeCounts(blocker), groupCounts(blocker), List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("blocking row count");

        EnumMap<RowOutcome, Long> missingOutcome = zeroOutcomeCounts();
        missingOutcome.remove(RowOutcome.MIGRATABLE);
        assertThatThrownBy(() -> report(
                Status.COMPLETED, NOW, NOW,
                0, 0, 0, 0, List.of(), missingOutcome, zeroGroupCounts(),
                List.of(), 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("cover every outcome");

        CompletionEvidence complete = CompletionEvidence.valid();
        for (CompletionEvidence invalid : List.of(
                new CompletionEvidence(
                        complete.backendProcessId(),
                        complete.databaseIdentityDigest(),
                        complete.serverVersion(),
                        complete.transactionIsolation(),
                        false,
                        true),
                new CompletionEvidence(
                        complete.backendProcessId(),
                        complete.databaseIdentityDigest(),
                        complete.serverVersion(),
                        complete.transactionIsolation(),
                        true,
                        false),
                new CompletionEvidence(
                        complete.backendProcessId(),
                        complete.databaseIdentityDigest(),
                        complete.serverVersion(),
                        Optional.of("read committed"),
                        true,
                        true),
                new CompletionEvidence(
                        Optional.empty(),
                        complete.databaseIdentityDigest(),
                        complete.serverVersion(),
                        complete.transactionIsolation(),
                        true,
                        true),
                new CompletionEvidence(
                        complete.backendProcessId(),
                        Optional.empty(),
                        complete.serverVersion(),
                        complete.transactionIsolation(),
                        true,
                        true),
                new CompletionEvidence(
                        complete.backendProcessId(),
                        complete.databaseIdentityDigest(),
                        Optional.empty(),
                        complete.transactionIsolation(),
                        true,
                        true))) {
            assertThatThrownBy(() -> emptyCompletedReport(invalid))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("read-only transaction evidence");
        }
    }

    private static LegacyPersonalBankTagGlobalPreflight preflight(
            DataSource dataSource,
            PersonalBankQuestionFactsApi memberships
    ) {
        return new LegacyPersonalBankTagGlobalPreflight(
                dataSource,
                memberships,
                Clock.fixed(NOW, ZoneOffset.UTC),
                LegacyPersonalBankTagGlobalPreflight.advisoryLockKey());
    }

    private static ResultSet singleRow() throws SQLException {
        ResultSet row = mock(ResultSet.class);
        when(row.next()).thenReturn(true, false);
        return row;
    }

    private static Statement stubSuccessfulSweepPreamble(
            Connection connection,
            int backendProcessId
    ) throws SQLException {
        ResultSet lockRow = singleRow();
        when(lockRow.getInt(1)).thenReturn(backendProcessId);
        when(lockRow.getBoolean(2)).thenReturn(true);
        stubQuery(connection, LegacyPersonalBankTagGlobalPreflight.TRY_LOCK_SQL, lockRow);

        ResultSet metadataRow = singleRow();
        when(metadataRow.getString(1)).thenReturn("private-database-name");
        when(metadataRow.getString(2)).thenReturn("private-database-user");
        when(metadataRow.getString(3)).thenReturn("18.4");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.CONNECTION_METADATA_SQL,
                metadataRow);

        Statement transactionControl = mock(Statement.class);
        when(connection.createStatement()).thenReturn(transactionControl);
        ResultSet transactionFacts = singleRow();
        when(transactionFacts.getString(1)).thenReturn("serializable");
        when(transactionFacts.getString(2)).thenReturn("on");
        when(transactionFacts.getString(3)).thenReturn("on");
        stubQuery(connection,
                LegacyPersonalBankTagGlobalPreflight.TRANSACTION_FACTS_SQL,
                transactionFacts);
        return transactionControl;
    }

    private static PreparedStatement stubSuccessfulUnlock(
            Connection connection,
            boolean accepted
    ) throws SQLException {
        PreparedStatement statement = mock(PreparedStatement.class);
        ResultSet row = singleRow();
        when(row.getBoolean(1)).thenReturn(accepted);
        when(connection.prepareStatement(LegacyPersonalBankTagGlobalPreflight.UNLOCK_SQL))
                .thenReturn(statement);
        when(statement.executeQuery()).thenReturn(row);
        return statement;
    }

    private static void stubQuery(Connection connection, String sql, ResultSet rows)
            throws SQLException {
        PreparedStatement statement = mock(PreparedStatement.class);
        when(connection.prepareStatement(sql)).thenReturn(statement);
        when(statement.executeQuery()).thenReturn(rows);
    }

    private static LegacyPersonalBankTagPreflightReport report(
            Status status,
            Instant startedAt,
            Instant completedAt,
            int reservedRows,
            int canonicalRows,
            int nearMissRows,
            int collisionRows,
            List<SourceRow> rows,
            Map<RowOutcome, Long> outcomes,
            Map<ReportingGroup, Long> groups,
            List<GlobalFailure> failures,
            long blockers
    ) {
        CompletionEvidence evidence = status == Status.COMPLETED
                ? CompletionEvidence.valid()
                : CompletionEvidence.empty();
        return report(
                status,
                startedAt,
                completedAt,
                reservedRows,
                canonicalRows,
                nearMissRows,
                collisionRows,
                rows,
                outcomes,
                groups,
                failures,
                blockers,
                evidence);
    }

    private static LegacyPersonalBankTagPreflightReport emptyCompletedReport(
            CompletionEvidence evidence
    ) {
        return report(
                Status.COMPLETED,
                NOW,
                NOW,
                0,
                0,
                0,
                0,
                List.of(),
                zeroOutcomeCounts(),
                zeroGroupCounts(),
                List.of(),
                0,
                evidence);
    }

    private static LegacyPersonalBankTagPreflightReport report(
            Status status,
            Instant startedAt,
            Instant completedAt,
            int reservedRows,
            int canonicalRows,
            int nearMissRows,
            int collisionRows,
            List<SourceRow> rows,
            Map<RowOutcome, Long> outcomes,
            Map<ReportingGroup, Long> groups,
            List<GlobalFailure> failures,
            long blockers,
            CompletionEvidence evidence
    ) {
        return new LegacyPersonalBankTagPreflightReport(
                "DRY_RUN",
                status,
                startedAt,
                completedAt,
                LegacyPersonalBankTagGlobalPreflight.advisoryLockKey(),
                evidence.backendProcessId(),
                evidence.databaseIdentityDigest(),
                evidence.serverVersion(),
                evidence.transactionIsolation(),
                evidence.transactionReadOnly(),
                evidence.transactionDeferrable(),
                reservedRows,
                canonicalRows,
                nearMissRows,
                collisionRows,
                rows,
                outcomes,
                groups,
                failures,
                blockers,
                DIGEST,
                EnumSet.allOf(ApplyPrerequisiteBlocker.class),
                0,
                0);
    }

    private static SourceRow blockingRow() {
        return new SourceRow(
                1,
                2,
                KeyClassification.NEAR_MISS,
                Optional.empty(),
                DIGEST,
                1,
                DIGEST,
                1,
                Optional.empty(),
                0,
                0,
                0,
                Optional.empty(),
                0,
                0,
                Optional.empty(),
                RowOutcome.INVALID_KEY,
                "INVALID_KEY");
    }

    private static EnumMap<RowOutcome, Long> zeroOutcomeCounts() {
        EnumMap<RowOutcome, Long> counts = new EnumMap<>(RowOutcome.class);
        for (RowOutcome outcome : RowOutcome.values()) {
            counts.put(outcome, 0L);
        }
        return counts;
    }

    private static EnumMap<RowOutcome, Long> outcomeCounts(SourceRow row) {
        EnumMap<RowOutcome, Long> counts = zeroOutcomeCounts();
        counts.put(row.outcome(), 1L);
        return counts;
    }

    private static EnumMap<ReportingGroup, Long> zeroGroupCounts() {
        EnumMap<ReportingGroup, Long> counts = new EnumMap<>(ReportingGroup.class);
        for (ReportingGroup group : ReportingGroup.values()) {
            counts.put(group, 0L);
        }
        return counts;
    }

    private static EnumMap<ReportingGroup, Long> groupCounts(SourceRow row) {
        EnumMap<ReportingGroup, Long> counts = zeroGroupCounts();
        counts.put(row.reportingGroup(), 1L);
        return counts;
    }

    private record CompletionEvidence(
            Optional<Integer> backendProcessId,
            Optional<String> databaseIdentityDigest,
            Optional<String> serverVersion,
            Optional<String> transactionIsolation,
            boolean transactionReadOnly,
            boolean transactionDeferrable
    ) {
        private static CompletionEvidence valid() {
            return new CompletionEvidence(
                    Optional.of(41_141),
                    Optional.of(DIGEST),
                    Optional.of("18.4"),
                    Optional.of("serializable"),
                    true,
                    true);
        }

        private static CompletionEvidence empty() {
            return new CompletionEvidence(
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    false,
                    false);
        }
    }
}
