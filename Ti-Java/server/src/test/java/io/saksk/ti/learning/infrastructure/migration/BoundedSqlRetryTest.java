package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.Execution;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.FailureKind;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.SqlOperationException;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullSource;
import org.junit.jupiter.params.provider.ValueSource;

class BoundedSqlRetryTest {

    @ParameterizedTest(name = "root SQLSTATE {0} retries once and succeeds")
    @ValueSource(strings = {"40001", "40P01"})
    void retriesGenuineRootConcurrencyStateAndReportsSuccessCounts(String sqlState)
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second);
        List<Connection> observedConnections = new ArrayList<>();
        List<Integer> observedAttempts = new ArrayList<>();

        Execution<String> execution = new BoundedSqlRetry(dataSource).execute(
                (connection, attempt) -> {
                    observedConnections.add(connection);
                    observedAttempts.add(attempt);
                    if (attempt == 1) {
                        throw new SQLException("retryable", sqlState);
                    }
                    return "committed";
                });

        assertThat(execution.value()).isEqualTo("committed");
        assertThat(execution.attempts()).isEqualTo(2);
        assertThat(execution.retries()).isEqualTo(1);
        assertThat(observedConnections).containsExactly(first, second);
        assertThat(observedAttempts).containsExactly(1, 2);
        verify(dataSource, times(2)).getConnection();
        assertConfigured(first);
        assertConfigured(second);
        verify(first).rollback();
        verify(first, never()).commit();
        verify(first).close();
        verify(second, never()).rollback();
        verify(second).commit();
        verify(second).close();
    }

    @ParameterizedTest(name = "root SQLSTATE {0} exhausts exactly three attempts")
    @ValueSource(strings = {"40001", "40P01"})
    void exhaustsRetryBudgetWithExactAttemptAndRetryCounts(String sqlState)
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        Connection third = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second, third);
        List<SQLException> failures = new ArrayList<>();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((connection, attempt) -> {
                    SQLException failure = new SQLException(
                            "retryable-attempt-" + attempt, sqlState);
                    failures.add(failure);
                    throw failure;
                }));

        assertFailure(error, FailureKind.SQL, sqlState, true, 3, 2,
                failures.get(2));
        assertThat(failures).hasSize(3);
        verify(dataSource, times(3)).getConnection();
        for (Connection connection : List.of(first, second, third)) {
            assertConfigured(connection);
            verify(connection).rollback();
            verify(connection, never()).commit();
            verify(connection).close();
        }
    }

    @Test
    void opensAFreshConnectionForEveryMixedRetryAttempt() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        Connection third = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second, third);
        List<Connection> observed = new ArrayList<>();

        Execution<String> execution = new BoundedSqlRetry(dataSource).execute(
                (connection, attempt) -> {
                    observed.add(connection);
                    if (attempt == 1) {
                        throw new SQLException("serialization", "40001");
                    }
                    if (attempt == 2) {
                        throw new SQLException("deadlock", "40P01");
                    }
                    return "committed-on-fresh-connection";
                });

        assertThat(execution.attempts()).isEqualTo(3);
        assertThat(execution.retries()).isEqualTo(2);
        assertThat(observed).containsExactly(first, second, third);
        verify(dataSource, times(3)).getConnection();
        verify(first).rollback();
        verify(first).close();
        verify(second).rollback();
        verify(second).close();
        verify(third).commit();
        verify(third).close();
    }

    @ParameterizedTest(name = "terminal root SQLSTATE {0}")
    @NullSource
    @ValueSource(strings = {"23505", "42501", "08006", "ZZ999"})
    void doesNotRetryNullOrNonAllowlistedRootSqlState(String sqlState)
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mockConnection();
        when(dataSource.getConnection()).thenReturn(connection);
        SQLException failure = new SQLException("terminal", sqlState);
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((ignored, attempt) -> {
                    workCalls.incrementAndGet();
                    throw failure;
                }));

        assertFailure(error, FailureKind.SQL, sqlState, false, 1, 0, failure);
        assertThat(workCalls).hasValue(1);
        verify(dataSource).getConnection();
        verify(connection).rollback();
        verify(connection, never()).commit();
        verify(connection).close();
    }

    @ParameterizedTest(name = "{0} cannot smuggle a retryable SQLSTATE")
    @MethodSource("retryStateSmugglingCases")
    void doesNotRetryAStateFoundOnlyInCauseOrNextException(
            String description,
            Exception failure,
            String expectedRootState
    ) throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mockConnection();
        when(dataSource.getConnection()).thenReturn(connection);
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((ignored, attempt) -> {
                    workCalls.incrementAndGet();
                    throw failure;
                }),
                description);

        assertFailure(error, FailureKind.SQL, expectedRootState, false, 1, 0,
                failure);
        assertThat(workCalls).hasValue(1);
        verify(dataSource).getConnection();
        verify(connection).rollback();
        verify(connection).close();
    }

    @Test
    void connectionAcquisitionFailureIsTerminalEvenWithRetryableState()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        SQLException acquisition = new SQLException("acquisition", "40001");
        when(dataSource.getConnection()).thenThrow(acquisition);
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((connection, attempt) -> {
                    workCalls.incrementAndGet();
                    return "must-not-run";
                }));

        assertFailure(error, FailureKind.CONNECTION_ACQUISITION, "40001", false,
                1, 0, acquisition);
        assertThat(workCalls).hasValue(0);
        verify(dataSource).getConnection();
    }

    @ParameterizedTest(name = "setup failure at {0} is terminal")
    @EnumSource(SetupFailurePoint.class)
    void connectionSetupFailureIsTerminalEvenWithRetryableState(
            SetupFailurePoint failurePoint
    ) throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mockConnection();
        when(dataSource.getConnection()).thenReturn(connection);
        SQLException setup = new SQLException("setup", "40P01");
        failurePoint.stub(connection, setup);
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((ignored, attempt) -> {
                    workCalls.incrementAndGet();
                    return "must-not-run";
                }));

        assertFailure(error, FailureKind.CONNECTION_SETUP, "40P01", false,
                1, 0, setup);
        assertThat(workCalls).hasValue(0);
        verify(dataSource).getConnection();
        if (failurePoint == SetupFailurePoint.TIMEOUTS) {
            verify(connection).rollback();
        } else {
            verify(connection, never()).rollback();
        }
        verify(connection, never()).commit();
        verify(connection).close();
    }

    @Test
    void rollbackFailureStopsRetryAndRemainsAttachedToThePrimaryFailure()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second);
        SQLException workFailure = new SQLException("work", "40001");
        SQLException rollbackFailure = new SQLException("rollback", "08006");
        doThrow(rollbackFailure).when(first).rollback();
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((connection, attempt) -> {
                    workCalls.incrementAndGet();
                    if (attempt == 1) {
                        throw workFailure;
                    }
                    return "must-not-retry";
                }));

        assertFailure(error, FailureKind.ROLLBACK, "40001", false,
                1, 0, workFailure);
        assertThat(workFailure.getSuppressed()).containsExactly(rollbackFailure);
        assertThat(workCalls).hasValue(1);
        verify(dataSource).getConnection();
        verify(first).rollback();
        verify(first).close();
        verifyNoInteractions(second);
    }

    @Test
    void closeFailureAfterRetryableWorkFailureStopsRetry() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second);
        SQLException workFailure = new SQLException("work", "40001");
        SQLException closeFailure = new SQLException("close", "08006");
        doThrow(closeFailure).when(first).close();
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((connection, attempt) -> {
                    workCalls.incrementAndGet();
                    if (attempt == 1) {
                        throw workFailure;
                    }
                    return "must-not-retry";
                }));

        assertFailure(error, FailureKind.CLOSE, "40001", false,
                1, 0, workFailure);
        assertThat(workFailure.getSuppressed()).containsExactly(closeFailure);
        assertThat(workCalls).hasValue(1);
        verify(dataSource).getConnection();
        verify(first).rollback();
        verify(first).close();
        verifyNoInteractions(second);
    }

    @Test
    void closeFailureAfterCommitIsTerminalEvenWithRetryableState()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mockConnection();
        when(dataSource.getConnection()).thenReturn(connection);
        SQLException closeFailure = new SQLException("close", "40P01");
        doThrow(closeFailure).when(connection).close();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute(
                        (ignored, attempt) -> "committed-before-close"));

        assertFailure(error, FailureKind.CLOSE, "40P01", false,
                1, 0, closeFailure);
        verify(dataSource).getConnection();
        verify(connection).commit();
        verify(connection, never()).rollback();
        verify(connection).close();
    }

    @Test
    void commitFailureHasUnknownOutcomeAndIsNeverRetriedOrRolledBack()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection first = mockConnection();
        Connection second = mockConnection();
        when(dataSource.getConnection()).thenReturn(first, second);
        SQLException commitFailure = new SQLException("ambiguous-commit", "40001");
        doThrow(commitFailure).when(first).commit();
        AtomicInteger workCalls = new AtomicInteger();

        SqlOperationException error = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute((connection, attempt) -> {
                    workCalls.incrementAndGet();
                    return "commit-attempted";
                }));

        assertFailure(error, FailureKind.COMMIT_OUTCOME_UNKNOWN, "40001", false,
                1, 0, commitFailure);
        assertThat(workCalls).hasValue(1);
        verify(dataSource).getConnection();
        verify(first).commit();
        verify(first, never()).rollback();
        verify(first).close();
        verifyNoInteractions(second);
    }

    @Test
    void virtualMachineErrorIsCleanedUpAndTheSameFatalInstanceIsRethrown()
            throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection connection = mockConnection();
        when(dataSource.getConnection()).thenReturn(connection);
        FatalVmError fatal = new FatalVmError("fatal");
        SQLException rollbackFailure = new SQLException("rollback-cleanup", "08006");
        IllegalStateException closeFailure = new IllegalStateException("close-cleanup");
        doThrow(rollbackFailure).when(connection).rollback();
        doThrow(closeFailure).when(connection).close();

        FatalVmError thrown = assertThrows(
                FatalVmError.class,
                () -> new BoundedSqlRetry(dataSource).execute((ignored, attempt) -> {
                    throw fatal;
                }));

        assertThat(thrown).isSameAs(fatal);
        assertThat(thrown.getSuppressed())
                .containsExactly(rollbackFailure, closeFailure);
        verify(dataSource).getConnection();
        assertConfigured(connection);
        verify(connection).rollback();
        verify(connection, never()).commit();
        verify(connection).close();
    }

    @Test
    void rejectsInvalidBoundsAndNullDependenciesBeforeOpeningAConnection() {
        DataSource dataSource = mock(DataSource.class);

        assertThatThrownBy(() -> new BoundedSqlRetry(null))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("dataSource");
        assertThatThrownBy(() -> new BoundedSqlRetry(dataSource, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("between 1 and 3");
        assertThatThrownBy(() -> new BoundedSqlRetry(dataSource, 4))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("between 1 and 3");
        assertThatThrownBy(() -> new BoundedSqlRetry(dataSource).execute(null))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("work");
        verifyNoInteractions(dataSource);
    }

    private static Stream<Arguments> retryStateSmugglingCases() {
        SQLException causeState = new SQLException("nested", "40001");
        IllegalStateException causeWrapper = new IllegalStateException(
                "translated", causeState);

        SQLException nextFromTerminal = new SQLException("outer", "23505");
        nextFromTerminal.setNextException(new SQLException("smuggled", "40P01"));

        SQLException nextFromNull = new SQLException("outer", (String) null);
        nextFromNull.setNextException(new SQLException("smuggled", "40001"));

        return Stream.of(
                Arguments.of("cause", causeWrapper, null),
                Arguments.of("nextException after terminal root", nextFromTerminal,
                        "23505"),
                Arguments.of("nextException after null root", nextFromNull, null));
    }

    private static Connection mockConnection() throws SQLException {
        Connection connection = mock(Connection.class);
        when(connection.createStatement()).thenReturn(mock(Statement.class));
        return connection;
    }

    private static void assertConfigured(Connection connection) throws SQLException {
        verify(connection).setAutoCommit(false);
        verify(connection).setReadOnly(false);
        verify(connection).setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
        verify(connection).createStatement();
    }

    private static void assertFailure(
            SqlOperationException failure,
            FailureKind expectedKind,
            String expectedRootState,
            boolean expectedRetryable,
            int expectedAttempts,
            int expectedRetries,
            Throwable expectedCause
    ) {
        assertThat(failure.kind()).isEqualTo(expectedKind);
        assertThat(failure.rootSqlState()).isEqualTo(expectedRootState);
        assertThat(failure.retryable()).isEqualTo(expectedRetryable);
        assertThat(failure.attempts()).isEqualTo(expectedAttempts);
        assertThat(failure.retries()).isEqualTo(expectedRetries);
        assertThat(failure.getCause()).isSameAs(expectedCause);
    }

    private enum SetupFailurePoint {
        AUTO_COMMIT,
        READ_ONLY,
        ISOLATION,
        TIMEOUTS;

        private void stub(Connection connection, SQLException failure)
                throws SQLException {
            switch (this) {
                case AUTO_COMMIT -> doThrow(failure)
                        .when(connection).setAutoCommit(false);
                case READ_ONLY -> doThrow(failure)
                        .when(connection).setReadOnly(false);
                case ISOLATION -> doThrow(failure)
                        .when(connection).setTransactionIsolation(
                                Connection.TRANSACTION_SERIALIZABLE);
                case TIMEOUTS -> when(connection.createStatement())
                        .thenThrow(failure);
            }
        }
    }

    private static final class FatalVmError extends VirtualMachineError {
        private FatalVmError(String message) {
            super(message);
        }
    }
}
