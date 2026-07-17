package io.saksk.ti.learning.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RowOutcome;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RowResult;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.RunResult;
import io.saksk.ti.learning.infrastructure.persistence.LegacyPersonalBankTagMigrationEvidence.TagInsert;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;

class LegacyPersonalBankTagMigrationEvidenceTest {

    @Test
    void acceptsOnlyCanonicalLegacyKeysWithinPostgresIntegerRange() {
        assertThat(LegacyPersonalBankTagMigrationEvidence.strictBankId("bank_1_tags"))
                .hasValue(1);
        assertThat(LegacyPersonalBankTagMigrationEvidence.strictBankId("bank_7101_tags"))
                .hasValue(7_101);
        assertThat(LegacyPersonalBankTagMigrationEvidence.strictBankId(
                "bank_2147483647_tags")).hasValue(Integer.MAX_VALUE);

        for (String invalid : List.of(
                "bank_07101_tags",
                "bank_0_tags",
                "bank_-1_tags",
                "bank_7101_tags_extra",
                "prefix_bank_7101_tags",
                "BANK_7101_tags",
                "bank_7101_TAGS",
                "bank_7101_tags ",
                "bank_2147483648_tags")) {
            assertThat(LegacyPersonalBankTagMigrationEvidence.strictBankId(invalid))
                    .as(invalid)
                    .isEmpty();
        }
        assertThat(LegacyPersonalBankTagMigrationEvidence.strictBankId(null)).isEmpty();
    }

    @Test
    void plansDefinitionsAndOnlyMembershipValidatedQuestionBindings() throws Exception {
        var plan = LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": [" alpha ", "ALL", "123456789012345678901234", "alpha"],
                  "question_tags": {
                    "11": ["alpha", "beta", "all"],
                    " +12 ": "[\\\"gamma\\\", \\\"beta\\\"]",
                    "13": "delta,epsilon，zeta"
                  }
                }
                """, questionId -> questionId == 11
                        || questionId == 12
                        || questionId == 13);

        assertThat(plan.inserts()).containsExactly(
                new TagInsert(0, "alpha"),
                new TagInsert(0, "12345678901234567890"),
                new TagInsert(0, "beta"),
                new TagInsert(0, "gamma"),
                new TagInsert(0, "delta"),
                new TagInsert(0, "epsilon"),
                new TagInsert(0, "zeta"),
                new TagInsert(11, "alpha"),
                new TagInsert(11, "beta"),
                new TagInsert(12, "gamma"),
                new TagInsert(12, "beta"),
                new TagInsert(13, "delta"),
                new TagInsert(13, "epsilon"),
                new TagInsert(13, "zeta"));
    }

    @Test
    void rejectsMalformedRawStructuresInsteadOfSilentlyCoercingOrDroppingThem() {
        List<String> invalidPayloads = List.of(
                "{\"tags\":\"alpha\",\"question_tags\":{}}",
                "{\"tags\":null,\"question_tags\":{}}",
                "{\"tags\":[\"alpha\",7],\"question_tags\":{}}",
                "{\"tags\":[],\"question_tags\":[]}",
                "{\"tags\":[],\"question_tags\":null}",
                "{\"tags\":[],\"question_tags\":{\"11\":7}}",
                "{\"tags\":[],\"question_tags\":{\"11\":true}}",
                "{\"tags\":[],\"question_tags\":{\"11\":null}}",
                "{\"tags\":[],\"question_tags\":{\"11\":{\"tag\":\"alpha\"}}}",
                "{\"tags\":[],\"question_tags\":{\"11\":[\"alpha\",7]}}",
                "{\"tags\":[],\"question_tags\":{\"11\":\"[\\\"alpha\\\",7]\"}}",
                "{\"tags\":[],\"question_tags\":{\"11\":\"[\\\"alpha\\\"] trailing\"}}",
                "{\"tags\":[],\"question_tags\":{\"11\":\"['alpha','beta']\"}}",
                "{\"tags\":[],\"question_tags\":{\"11\":\"['alpha', unquoted]\"}}"
        );

        for (String raw : invalidPayloads) {
            assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan(
                    raw, questionId -> true))
                    .as(raw)
                    .isInstanceOf(
                            LegacyPersonalBankTagMigrationEvidence.InvalidDataException.class);
        }

        for (String ambiguousJson : List.of(
                "{\"tags\":[\"alpha\"],\"tags\":[\"beta\"],\"question_tags\":{}}",
                "{\"tags\":[],\"question_tags\":{}} {\"trailing\":true}")) {
            assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan(
                    ambiguousJson, questionId -> true))
                    .as(ambiguousJson)
                    .isInstanceOf(
                            LegacyPersonalBankTagMigrationEvidence.InvalidDataException.class);
        }
    }

    @Test
    void rejectsInvalidQuestionIdsAndNormalizedIdConflicts() {
        for (String invalidQuestionId : List.of(
                "not-a-question", "0", "-1", "2147483648")) {
            String raw = "{\"tags\":[],\"question_tags\":{\""
                    + invalidQuestionId + "\":[]}}";
            assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan(
                    raw, questionId -> true))
                    .as(invalidQuestionId)
                    .isInstanceOf(
                            LegacyPersonalBankTagMigrationEvidence.InvalidDataException.class);
        }

        assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": [],
                  "question_tags": {"11": ["alpha"], "011": ["alpha"]}
                }
                """, questionId -> true))
                .isInstanceOf(
                        LegacyPersonalBankTagMigrationEvidence.InvalidDataException.class)
                .hasMessageContaining("same positive ID");
    }

    @Test
    void blocksTheWholePlanWhenAQuestionDoesNotBelongToTheBank() {
        assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": ["must-not-partially-apply"],
                  "question_tags": {"11": ["valid"], "13": ["orphan"]}
                }
                """, questionId -> questionId == 11))
                .isInstanceOf(
                        LegacyPersonalBankTagMigrationEvidence.OrphanQuestionException.class)
                .hasMessageContaining("13");
    }

    @Test
    void truncatesTagsByUnicodeCodePointRatherThanUtf16CodeUnit() throws Exception {
        String oversized = "😀".repeat(21);
        var plan = LegacyPersonalBankTagMigrationEvidence.plan(
                "{\"tags\":[\"" + oversized + "\"],\"question_tags\":{}}",
                questionId -> true);

        assertThat(plan.inserts()).singleElement().satisfies(item -> {
            assertThat(item.tag().codePointCount(0, item.tag().length())).isEqualTo(20);
            assertThat(item.tag()).isEqualTo("😀".repeat(20));
        });
    }

    @Test
    void matchesPythonWhitespaceForTagsCsvAndQuestionIds() throws Exception {
        String whitespace = "\u00a0\u0085\u2007\u202f\u3000";
        var plan = LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": ["%1$salpha%1$s"],
                  "question_tags": {"%1$s+12%1$s": "%1$sbeta%1$s,%1$sgamma%1$s"}
                }
                """.formatted(whitespace), questionId -> questionId == 12);

        assertThat(plan.inserts()).containsExactly(
                new TagInsert(0, "alpha"),
                new TagInsert(0, "beta"),
                new TagInsert(0, "gamma"),
                new TagInsert(12, "beta"),
                new TagInsert(12, "gamma"));
        assertThat(LegacyPersonalBankTagMigrationEvidence.stripPythonWhitespace(
                whitespace + "value" + whitespace)).isEqualTo("value");
        assertThat(LegacyPersonalBankTagMigrationEvidence.stripPythonWhitespace(
                "\u180evalue\u200b")).isEqualTo("\u180evalue\u200b");
        for (String invalidTargetTag : List.of(
                "\u00a0\u3000", "all", "ALL", " padded ")) {
            assertThatThrownBy(() -> new TagInsert(0, invalidTargetTag))
                    .as(invalidTargetTag)
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void rejectsDistinctTagsThatTruncateToTheSameValueButDeduplicatesNormalRepeats()
            throws Exception {
        assertThatThrownBy(() -> LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": ["12345678901234567890-one"],
                  "question_tags": {"11": ["12345678901234567890-two"]}
                }
                """, questionId -> true))
                .isInstanceOf(
                        LegacyPersonalBankTagMigrationEvidence.InvalidDataException.class)
                .hasMessageContaining("truncate to the same");

        var duplicates = LegacyPersonalBankTagMigrationEvidence.plan("""
                {
                  "tags": ["alpha", " alpha "],
                  "question_tags": {"11": ["alpha", " alpha "]}
                }
                """, questionId -> true);
        assertThat(duplicates.inserts()).containsExactly(
                new TagInsert(0, "alpha"),
                new TagInsert(11, "alpha"));
    }

    @Test
    void existingTargetDoesNotHideInvalidRawSource() throws Exception {
        JdbcFixture fixture = jdbcFixture(true, """
                {"tags":"invalid-but-target-wins","question_tags":[]}
                """);

        RowResult result = fixture.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);

        assertThat(result.outcome()).isEqualTo(RowOutcome.INVALID_DATA);
        assertThat(result.failure()).contains("tags must be an array");
        verify(fixture.connection()).prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.BANK_EXISTS_PROJECTION_SQL);
        verify(fixture.connection()).commit();
    }

    @Test
    void existingTargetOnlyWinsWhenSourceRowsAreItsSubset() throws Exception {
        JdbcFixture subset = jdbcFixture(List.of(
                new TagInsert(0, "target"),
                new TagInsert(0, "target-extra")), """
                {"tags":["target"],"question_tags":{}}
                """);
        assertThat(subset.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE)
                .outcome()).isEqualTo(RowOutcome.TARGET_ALREADY_PRESENT);

        JdbcFixture conflict = jdbcFixture(true, """
                {"tags":["source-only"],"question_tags":{}}
                """);
        RowResult result = conflict.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(result.outcome()).isEqualTo(RowOutcome.TARGET_CONFLICT);
        assertThat(result.failure()).contains("not a subset");

        JdbcFixture crossBankTarget = jdbcFixture(List.of(
                new TagInsert(0, "target"),
                new TagInsert(999, "target")), """
                {"tags":["target"],"question_tags":{}}
                """);
        RowResult invalidTarget = crossBankTarget.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(invalidTarget.outcome()).isEqualTo(RowOutcome.TARGET_CONFLICT);
        assertThat(invalidTarget.failure()).contains("does not belong to bank: 999");
    }

    @Test
    void invalidRawSourceBecomesAnExplicitBlockingOutcomeWhenTargetIsAbsent()
            throws Exception {
        JdbcFixture fixture = jdbcFixture(false, """
                {"tags":"invalid-without-target","question_tags":{}}
                """);

        RowResult result = fixture.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);

        assertThat(result.outcome()).isEqualTo(RowOutcome.INVALID_DATA);
        assertThat(result.failure()).contains("tags must be an array");
        verify(fixture.connection()).prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.BANK_EXISTS_PROJECTION_SQL);
        verify(fixture.connection()).commit();
    }

    @Test
    void runEligibilitySeparatesRolledBackRollbackFailedAndCommitUnknownRows() {
        RunResult blocked = new RunResult(List.of(
                row(1, RowOutcome.SOURCE_DISAPPEARED),
                row(2, RowOutcome.INVALID_KEY),
                row(3, RowOutcome.INVALID_DATA),
                row(4, RowOutcome.BANK_MISSING),
                row(5, RowOutcome.ORPHAN_QUESTION),
                row(6, RowOutcome.FAILED_ROLLED_BACK),
                row(7, RowOutcome.ROLLBACK_FAILED, null),
                row(8, RowOutcome.COMMIT_OUTCOME_UNKNOWN, null),
                row(9, RowOutcome.TARGET_CONFLICT),
                row(10, RowOutcome.MIGRATED),
                row(11, RowOutcome.EMPTY_NOOP),
                row(12, RowOutcome.TARGET_ALREADY_PRESENT)));

        assertThat(blocked.blockingRowCount()).isEqualTo(9);
        assertThat(blocked.rollbackFailureCount()).isEqualTo(1);
        assertThat(blocked.commitOutcomeUnknownCount()).isEqualTo(1);
        assertThat(blocked.isApplyEligible()).isFalse();
        assertThatThrownBy(blocked::insertedRowsCommitted)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("unknown");

        RunResult eligible = new RunResult(List.of(
                row(1, RowOutcome.MIGRATED),
                row(2, RowOutcome.EMPTY_NOOP),
                row(3, RowOutcome.TARGET_ALREADY_PRESENT)));
        assertThat(eligible.blockingRowCount()).isZero();
        assertThat(eligible.rollbackFailureCount()).isZero();
        assertThat(eligible.commitOutcomeUnknownCount()).isZero();
        assertThat(eligible.isApplyEligible()).isTrue();
    }

    @Test
    void tracksRollbackFailureAndOnlyTreatsChangedCommitAsUnknown() throws Exception {
        JdbcFixture statementFailed = jdbcFixture(false, """
                {"tags":["attempted"],"question_tags":{}}
                """);
        PreparedStatement failedInsert = mock(PreparedStatement.class);
        when(statementFailed.connection().prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.INSERT_TARGET_SQL))
                .thenReturn(failedInsert);
        when(failedInsert.executeUpdate())
                .thenThrow(new SQLException("insert failed", "23505"));
        RowResult statementResult = statementFailed.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(statementResult.outcome()).isEqualTo(RowOutcome.FAILED_ROLLED_BACK);
        assertThat(statementResult.insertStatementsAttempted()).isEqualTo(1);
        assertThat(statementResult.insertedRowsCommitted()).isZero();

        JdbcFixture rollbackFailed = jdbcFixture(false, """
                {"tags":[],"question_tags":{}}
                """);
        when(rollbackFailed.connection().prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.BANK_EXISTS_PROJECTION_SQL))
                .thenThrow(new SQLException("bank projection unavailable", "08006"));
        doThrow(new SQLException("rollback unavailable", "08007"))
                .when(rollbackFailed.connection()).rollback();

        RowResult rollbackResult = rollbackFailed.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(rollbackResult.outcome()).isEqualTo(RowOutcome.ROLLBACK_FAILED);
        assertThat(rollbackResult.insertedRowsCommitted()).isZero();
        assertThat(rollbackResult.rollbackFailed()).isTrue();
        assertThat(rollbackResult.failure())
                .contains("sqlstate=08006")
                .contains("rollback failed")
                .contains("sqlstate=08007");

        JdbcFixture readOnlyCommitFailed = jdbcFixture(true, """
                {"tags":["target"],"question_tags":{}}
                """);
        doThrow(new SQLException("commit response lost", "08006"))
                .when(readOnlyCommitFailed.connection()).commit();

        RowResult readOnlyResult = readOnlyCommitFailed.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(readOnlyResult.outcome()).isEqualTo(RowOutcome.FAILED_ROLLED_BACK);
        assertThat(readOnlyResult.insertedRowsCommitted()).isZero();
        assertThat(readOnlyResult.rollbackFailed()).isFalse();

        JdbcFixture commitUnknown = jdbcFixture(false, """
                {"tags":["changed-before-commit"],"question_tags":{}}
                """);
        PreparedStatement committedInsert = mock(PreparedStatement.class);
        when(commitUnknown.connection().prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.INSERT_TARGET_SQL))
                .thenReturn(committedInsert);
        when(committedInsert.executeUpdate()).thenReturn(1);
        doThrow(new SQLException("commit response lost", "08006"))
                .when(commitUnknown.connection()).commit();
        RowResult commitResult = commitUnknown.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(commitResult.outcome()).isEqualTo(RowOutcome.COMMIT_OUTCOME_UNKNOWN);
        assertThat(commitResult.insertedRowsCommitted()).isNull();
        assertThat(commitResult.rollbackFailed()).isFalse();
        assertThat(commitResult.failure()).contains("sqlstate=08006");

        for (String definitelyAbortedState : List.of("40001", "40P01", "23514")) {
            JdbcFixture retryable = jdbcFixture(false, """
                    {"tags":["changed-before-retryable-commit"],"question_tags":{}}
                    """);
            PreparedStatement retryableInsert = mock(PreparedStatement.class);
            when(retryable.connection().prepareStatement(
                    LegacyPersonalBankTagMigrationEvidence.INSERT_TARGET_SQL))
                    .thenReturn(retryableInsert);
            when(retryableInsert.executeUpdate()).thenReturn(1);
            doThrow(new SQLException("transaction aborted", definitelyAbortedState))
                    .when(retryable.connection()).commit();
            RowResult retryableResult = retryable.operator().runSourceRow(
                    9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
            assertThat(retryableResult.outcome())
                    .as(definitelyAbortedState)
                    .isEqualTo(RowOutcome.FAILED_ROLLED_BACK);
            assertThat(retryableResult.insertedRowsCommitted()).isZero();
            assertThat(retryableResult.failure())
                    .contains("sqlstate=" + definitelyAbortedState);
        }

        JdbcFixture commitAndRollbackUnknown = jdbcFixture(false, """
                {"tags":["changed-before-both-failures"],"question_tags":{}}
                """);
        PreparedStatement combinedInsert = mock(PreparedStatement.class);
        when(commitAndRollbackUnknown.connection().prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.INSERT_TARGET_SQL))
                .thenReturn(combinedInsert);
        when(combinedInsert.executeUpdate()).thenReturn(1);
        doThrow(new SQLException("commit response lost", "08006"))
                .when(commitAndRollbackUnknown.connection()).commit();
        doThrow(new SQLException("rollback unavailable", "08007"))
                .when(commitAndRollbackUnknown.connection()).rollback();
        RowResult combined = commitAndRollbackUnknown.operator().runSourceRow(
                9_001L, LegacyPersonalBankTagMigrationEvidence.FaultInjector.NONE);
        assertThat(combined.outcome()).isEqualTo(RowOutcome.COMMIT_OUTCOME_UNKNOWN);
        assertThat(combined.insertedRowsCommitted()).isNull();
        assertThat(combined.rollbackFailed()).isTrue();
        assertThat(new RunResult(List.of(combined)).rollbackFailureCount()).isEqualTo(1);
    }

    @Test
    void freezesLockPrecedenceProjectionAndInsertOnlyMutationSql() {
        assertThat(LegacyPersonalBankTagMigrationEvidence.DISCOVER_SOURCE_IDS_SQL)
                .contains("^bank_[1-9][0-9]*_tags$");
        assertThat(LegacyPersonalBankTagMigrationEvidence.LOCK_SOURCE_ROW_SQL)
                .contains("FROM user_progress")
                .contains("FOR UPDATE");
        assertThat(LegacyPersonalBankTagMigrationEvidence.TARGET_ROWS_SQL)
                .contains("FROM user_question_tag_items")
                .contains("question_id, tag")
                .contains("ORDER BY question_id, tag");
        assertThat(LegacyPersonalBankTagMigrationEvidence.BANK_EXISTS_PROJECTION_SQL)
                .contains("phase4c_personal_bank_membership_projection");
        assertThat(LegacyPersonalBankTagMigrationEvidence.QUESTION_MEMBERSHIP_PROJECTION_SQL)
                .contains("phase4c_personal_bank_membership_projection")
                .contains("question_id = ?");

        assertThat(LegacyPersonalBankTagMigrationEvidence.mutationStatements())
                .singleElement()
                .satisfies(sql -> {
                    String normalized = sql.strip().toUpperCase();
                    assertThat(normalized).startsWith("INSERT INTO USER_QUESTION_TAG_ITEMS");
                    assertThat(normalized).contains(
                            "ON CONFLICT (USER_ID, SCOPE, SCOPE_ID, QUESTION_ID, TAG) "
                                    + "DO NOTHING");
                    assertThat(normalized).doesNotContain(
                            "DELETE FROM",
                            "UPDATE USER_QUESTION_TAG_ITEMS",
                            "CREATE ",
                            "ALTER ",
                            "DROP ",
                            "TRUNCATE ");
                });
    }

    private static RowResult row(long sourceRowId, RowOutcome outcome) {
        return row(sourceRowId, outcome, 0);
    }

    private static RowResult row(
            long sourceRowId,
            RowOutcome outcome,
            Integer committedRows
    ) {
        return new RowResult(
                sourceRowId,
                sourceRowId,
                101L,
                201,
                outcome,
                0,
                committedRows,
                outcome == RowOutcome.ROLLBACK_FAILED,
                null);
    }

    private static JdbcFixture jdbcFixture(boolean targetPresent, String rawData)
            throws Exception {
        return jdbcFixture(
                targetPresent ? List.of(new TagInsert(0, "target")) : List.of(),
                rawData);
    }

    private static JdbcFixture jdbcFixture(List<TagInsert> targetRows, String rawData)
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mock(Connection.class);
        PreparedStatement transaction = mock(PreparedStatement.class);
        PreparedStatement lock = mock(PreparedStatement.class);
        PreparedStatement target = mock(PreparedStatement.class);
        PreparedStatement bank = mock(PreparedStatement.class);
        PreparedStatement membership = mock(PreparedStatement.class);
        ResultSet transactionRow = mock(ResultSet.class);
        ResultSet sourceRow = mock(ResultSet.class);
        ResultSet targetRow = mock(ResultSet.class);
        ResultSet bankRow = mock(ResultSet.class);
        ResultSet membershipRow = mock(ResultSet.class);

        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.TRANSACTION_ID_SQL))
                .thenReturn(transaction);
        when(connection.prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.LOCK_SOURCE_ROW_SQL))
                .thenReturn(lock);
        when(connection.prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.TARGET_ROWS_SQL))
                .thenReturn(target);
        when(connection.prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.BANK_EXISTS_PROJECTION_SQL))
                .thenReturn(bank);
        when(connection.prepareStatement(
                LegacyPersonalBankTagMigrationEvidence.QUESTION_MEMBERSHIP_PROJECTION_SQL))
                .thenReturn(membership);

        when(transaction.executeQuery()).thenReturn(transactionRow);
        when(transactionRow.next()).thenReturn(true);
        when(transactionRow.getLong(1)).thenReturn(91L);

        when(lock.executeQuery()).thenReturn(sourceRow);
        when(sourceRow.next()).thenReturn(true);
        when(sourceRow.getLong("id")).thenReturn(9_001L);
        when(sourceRow.getLong("user_id")).thenReturn(101L);
        when(sourceRow.getString("p_key")).thenReturn("bank_201_tags");
        when(sourceRow.getString("data")).thenReturn(rawData);

        AtomicInteger targetIndex = new AtomicInteger(-1);
        when(target.executeQuery()).thenReturn(targetRow);
        when(targetRow.next()).thenAnswer(ignored ->
                targetIndex.incrementAndGet() < targetRows.size());
        when(targetRow.getInt("question_id")).thenAnswer(ignored ->
                targetRows.get(targetIndex.get()).questionId());
        when(targetRow.getString("tag")).thenAnswer(ignored ->
                targetRows.get(targetIndex.get()).tag());
        when(bank.executeQuery()).thenReturn(bankRow);
        when(bankRow.next()).thenReturn(true);
        when(membership.executeQuery()).thenReturn(membershipRow);
        when(membershipRow.next()).thenReturn(false);

        return new JdbcFixture(
                new LegacyPersonalBankTagMigrationEvidence(dataSource), connection);
    }

    private record JdbcFixture(
            LegacyPersonalBankTagMigrationEvidence operator,
            Connection connection
    ) {
    }
}
