package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.Execution;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.FailureKind;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.SqlOperationException;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.LockSupport;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
class Phase4cBoundedSqlRetryPostgresIT {

    private static final String PROBE = "phase4c_bounded_retry_probe";
    private static final String COMMIT_PARENT =
            "phase4c_bounded_retry_commit_parent";
    private static final String COMMIT_CHILD =
            "phase4c_bounded_retry_commit_child";

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void realStatementFailuresTraverseProductionRetryOnPostgres18()
            throws Exception {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void realStatementFailuresTraverseProductionRetryOnPostgres16()
            throws Exception {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(queryString(dataSource, "SHOW server_version"))
                .isEqualTo(expectedVersion);

        createProbeSchema(dataSource);
        try {
            assertSerializationSuccess(dataSource);
            assertSerializationExhaustion(dataSource);
            assertDeadlockSuccess(dataSource);
            assertDeadlockExhaustion(dataSource);
            assertDeferredCommitFailureIsTerminal(dataSource);
        } finally {
            dropProbeSchema(dataSource);
        }
    }

    private static void assertSerializationSuccess(DataSource dataSource)
            throws Exception {
        AttemptTrace trace = new AttemptTrace();
        Execution<String> execution = new BoundedSqlRetry(dataSource).execute(
                (connection, attempt) -> {
                    trace.observe(connection);
                    if (attempt == 1) {
                        provokeSerializationFailure(connection, dataSource, trace);
                    }
                    return "serialization-committed";
                });

        assertThat(execution.value()).isEqualTo("serialization-committed");
        assertThat(execution.attempts()).isEqualTo(2);
        assertThat(execution.retries()).isOne();
        trace.assertFreshAttempts(2, List.of("40001"));
    }

    private static void assertSerializationExhaustion(DataSource dataSource)
            throws Exception {
        AttemptTrace trace = new AttemptTrace();
        SqlOperationException failure = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute(
                        (connection, attempt) -> {
                            trace.observe(connection);
                            provokeSerializationFailure(
                                    connection, dataSource, trace);
                            return "unreachable";
                        }));

        assertRetryExhausted(failure, "40001");
        trace.assertFreshAttempts(3, List.of("40001", "40001", "40001"));
    }

    private static void assertDeadlockSuccess(DataSource dataSource)
            throws Exception {
        AttemptTrace trace = new AttemptTrace();
        Execution<String> execution = new BoundedSqlRetry(dataSource).execute(
                (connection, attempt) -> {
                    trace.observe(connection);
                    if (attempt == 1) {
                        provokeDeadlockFailure(connection, dataSource, trace);
                    }
                    return "deadlock-committed";
                });

        assertThat(execution.value()).isEqualTo("deadlock-committed");
        assertThat(execution.attempts()).isEqualTo(2);
        assertThat(execution.retries()).isOne();
        trace.assertFreshAttempts(2, List.of("40P01"));
    }

    private static void assertDeadlockExhaustion(DataSource dataSource)
            throws Exception {
        AttemptTrace trace = new AttemptTrace();
        SqlOperationException failure = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute(
                        (connection, attempt) -> {
                            trace.observe(connection);
                            provokeDeadlockFailure(connection, dataSource, trace);
                            return "unreachable";
                        }));

        assertRetryExhausted(failure, "40P01");
        trace.assertFreshAttempts(3, List.of("40P01", "40P01", "40P01"));
    }

    private static void assertDeferredCommitFailureIsTerminal(
            DataSource dataSource
    ) throws Exception {
        AtomicInteger workCalls = new AtomicInteger();
        AtomicInteger statementUpdates = new AtomicInteger();
        AttemptTrace trace = new AttemptTrace();

        SqlOperationException failure = assertThrows(
                SqlOperationException.class,
                () -> new BoundedSqlRetry(dataSource).execute(
                        (connection, attempt) -> {
                            workCalls.incrementAndGet();
                            trace.observe(connection);
                            statementUpdates.set(executeUpdate(
                                    connection,
                                    "INSERT INTO " + COMMIT_CHILD
                                            + " (id, parent_id) VALUES (1, 999)"));
                            return "statement-succeeded-before-deferred-check";
                        }));

        assertThat(workCalls).hasValue(1);
        assertThat(statementUpdates).hasValue(1);
        assertThat(failure.kind()).isEqualTo(FailureKind.COMMIT_OUTCOME_UNKNOWN);
        assertThat(failure.rootSqlState()).isEqualTo("23503");
        assertThat(failure.retryable()).isFalse();
        assertThat(failure.attempts()).isOne();
        assertThat(failure.retries()).isZero();
        assertThat(failure.getCause()).isInstanceOf(SQLException.class);
        assertThat(((SQLException) failure.getCause()).getSQLState())
                .isEqualTo("23503");
        trace.assertFreshAttempts(1, List.of());
        assertThat(queryInt(dataSource, "SELECT count(*) FROM " + COMMIT_CHILD))
                .isZero();
    }

    private static void provokeSerializationFailure(
            Connection attemptConnection,
            DataSource dataSource,
            AttemptTrace trace
    ) throws SQLException {
        int observed = queryInt(
                attemptConnection,
                "SELECT value FROM " + PROBE + " WHERE id = 1");
        try (Connection competitor = dataSource.getConnection()) {
            competitor.setAutoCommit(false);
            competitor.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
            executeUpdate(
                    competitor,
                    "UPDATE " + PROBE + " SET value = value + 1 WHERE id = 1");
            competitor.commit();
        }

        try {
            executeUpdate(
                    attemptConnection,
                    "UPDATE " + PROBE + " SET value = " + (observed + 1)
                            + " WHERE id = 1");
        } catch (SQLException failure) {
            SQLException serialization = requireSqlState(failure, "40001");
            trace.statementSqlStates.add(serialization.getSQLState());
            throw serialization;
        }
        throw new AssertionError(
                "PostgreSQL accepted a stale SERIALIZABLE statement");
    }

    private static void provokeDeadlockFailure(
            Connection attemptConnection,
            DataSource dataSource,
            AttemptTrace trace
    ) throws Exception {
        executeUpdate(attemptConnection, "SET LOCAL deadlock_timeout = '100ms'");
        executeUpdate(
                attemptConnection,
                "UPDATE " + PROBE + " SET value = value + 1 WHERE id = 1");
        int attemptPid = queryInt(attemptConnection, "SELECT pg_backend_pid()");

        ExecutorService executor = Executors.newSingleThreadExecutor();
        try (Connection competitor = dataSource.getConnection()) {
            competitor.setAutoCommit(false);
            competitor.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
            executeUpdate(competitor, "SET LOCAL deadlock_timeout = '30s'");
            executeUpdate(
                    competitor,
                    "UPDATE " + PROBE + " SET value = value + 1 WHERE id = 2");
            int competitorPid = queryInt(competitor, "SELECT pg_backend_pid()");
            CountDownLatch secondStatementStarted = new CountDownLatch(1);
            Future<SQLException> competitorResult = executor.submit(() -> {
                secondStatementStarted.countDown();
                try {
                    executeUpdate(
                            competitor,
                            "UPDATE " + PROBE
                                    + " SET value = value + 1 WHERE id = 1");
                    competitor.commit();
                    return null;
                } catch (SQLException failure) {
                    try {
                        competitor.rollback();
                    } catch (SQLException rollbackFailure) {
                        failure.addSuppressed(rollbackFailure);
                    }
                    return failure;
                }
            });

            assertThat(secondStatementStarted.await(5, TimeUnit.SECONDS)).isTrue();
            awaitBlockedBy(dataSource, competitorPid, attemptPid);

            SQLException deadlock;
            try {
                executeUpdate(
                        attemptConnection,
                        "UPDATE " + PROBE
                                + " SET value = value + 1 WHERE id = 2");
                attemptConnection.rollback();
                SQLException competitorFailure = competitorResult.get(
                        5, TimeUnit.SECONDS);
                throw new AssertionError(
                        "PostgreSQL selected the long-timeout participant",
                        competitorFailure);
            } catch (SQLException failure) {
                deadlock = requireSqlState(failure, "40P01");
            }

            attemptConnection.rollback();
            SQLException competitorFailure = competitorResult.get(5, TimeUnit.SECONDS);
            if (competitorFailure != null) {
                deadlock.addSuppressed(competitorFailure);
                throw new AssertionError(
                        "deadlock competitor did not commit after victim rollback",
                        deadlock);
            }
            trace.statementSqlStates.add(deadlock.getSQLState());
            throw deadlock;
        } finally {
            executor.shutdownNow();
            assertThat(executor.awaitTermination(5, TimeUnit.SECONDS)).isTrue();
        }
    }

    private static void awaitBlockedBy(
            DataSource dataSource,
            int waitingPid,
            int blockingPid
    ) throws SQLException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        try (Connection observer = dataSource.getConnection();
             PreparedStatement statement = observer.prepareStatement("""
                     SELECT ? = ANY(pg_blocking_pids(?))
                     """)) {
            statement.setInt(1, blockingPid);
            statement.setInt(2, waitingPid);
            while (System.nanoTime() < deadline) {
                try (ResultSet row = statement.executeQuery()) {
                    if (row.next() && row.getBoolean(1)) {
                        return;
                    }
                }
                LockSupport.parkNanos(TimeUnit.MILLISECONDS.toNanos(10));
            }
        }
        throw new AssertionError("competitor did not enter the expected lock wait");
    }

    private static void assertRetryExhausted(
            SqlOperationException failure,
            String sqlState
    ) {
        assertThat(failure.kind()).isEqualTo(FailureKind.SQL);
        assertThat(failure.rootSqlState()).isEqualTo(sqlState);
        assertThat(failure.retryable()).isTrue();
        assertThat(failure.attempts()).isEqualTo(3);
        assertThat(failure.retries()).isEqualTo(2);
        assertThat(failure.getCause()).isInstanceOf(SQLException.class);
        assertThat(((SQLException) failure.getCause()).getSQLState())
                .isEqualTo(sqlState);
    }

    private static void createProbeSchema(DataSource dataSource) throws SQLException {
        dropProbeSchema(dataSource);
        executeUpdate(dataSource, """
                CREATE TABLE phase4c_bounded_retry_probe (
                    id integer PRIMARY KEY,
                    value integer NOT NULL
                )
                """);
        executeUpdate(dataSource, """
                INSERT INTO phase4c_bounded_retry_probe (id, value)
                VALUES (1, 0), (2, 0)
                """);
        executeUpdate(dataSource, """
                CREATE TABLE phase4c_bounded_retry_commit_parent (
                    id integer PRIMARY KEY
                )
                """);
        executeUpdate(dataSource, """
                CREATE TABLE phase4c_bounded_retry_commit_child (
                    id integer PRIMARY KEY,
                    parent_id integer NOT NULL,
                    CONSTRAINT phase4c_bounded_retry_commit_fk
                        FOREIGN KEY (parent_id)
                        REFERENCES phase4c_bounded_retry_commit_parent (id)
                        DEFERRABLE INITIALLY DEFERRED
                )
                """);
    }

    private static void dropProbeSchema(DataSource dataSource) throws SQLException {
        executeUpdate(dataSource, "DROP TABLE IF EXISTS " + COMMIT_CHILD);
        executeUpdate(dataSource, "DROP TABLE IF EXISTS " + COMMIT_PARENT);
        executeUpdate(dataSource, "DROP TABLE IF EXISTS " + PROBE);
    }

    private static SQLException requireSqlState(
            SQLException failure,
            String sqlState
    ) {
        SQLException current = failure;
        while (current != null) {
            if (sqlState.equals(current.getSQLState())) {
                return current;
            }
            current = current.getNextException();
        }
        throw new AssertionError(
                "expected SQLSTATE " + sqlState + " but received "
                        + failure.getSQLState(),
                failure);
    }

    private static int executeUpdate(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return executeUpdate(connection, sql);
        }
    }

    private static int executeUpdate(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement()) {
            return statement.executeUpdate(sql);
        }
    }

    private static int queryInt(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return queryInt(connection, sql);
        }
    }

    private static int queryInt(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet row = statement.executeQuery(sql)) {
            assertThat(row.next()).isTrue();
            int value = row.getInt(1);
            assertThat(row.next()).isFalse();
            return value;
        }
    }

    private static String queryString(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return queryString(connection, sql);
        }
    }

    private static String queryString(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet row = statement.executeQuery(sql)) {
            assertThat(row.next()).isTrue();
            String value = row.getString(1);
            assertThat(row.next()).isFalse();
            return value;
        }
    }

    private static final class AttemptTrace {
        private final List<Connection> connections = new ArrayList<>();
        private final List<Integer> backendPids = new ArrayList<>();
        private final List<String> transactionIds = new ArrayList<>();
        private final List<String> statementSqlStates = new ArrayList<>();

        private void observe(Connection connection) throws SQLException {
            connections.add(connection);
            backendPids.add(queryInt(connection, "SELECT pg_backend_pid()"));
            transactionIds.add(queryString(
                    connection, "SELECT pg_current_xact_id()::text"));
        }

        private void assertFreshAttempts(
                int expectedAttempts,
                List<String> expectedStatementStates
        ) {
            Set<Connection> identities = java.util.Collections.newSetFromMap(
                    new IdentityHashMap<>());
            identities.addAll(connections);
            assertThat(connections).hasSize(expectedAttempts);
            assertThat(identities).hasSize(expectedAttempts);
            assertThat(backendPids).hasSize(expectedAttempts);
            assertThat(Set.copyOf(backendPids)).hasSize(expectedAttempts);
            assertThat(transactionIds).hasSize(expectedAttempts);
            assertThat(Set.copyOf(transactionIds)).hasSize(expectedAttempts);
            assertThat(statementSqlStates)
                    .containsExactlyElementsOf(expectedStatementStates);
        }
    }
}
