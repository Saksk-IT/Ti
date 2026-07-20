package io.saksk.ti.learning.infrastructure.migration;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Objects;
import java.util.Set;
import javax.sql.DataSource;

/**
 * Opens a fresh JDBC connection and transaction for every bounded attempt.
 *
 * <p>Only a genuine root {@code 40001} or {@code 40P01} raised before commit is
 * retryable. Connection acquisition, rollback, close, and ambiguous commit
 * failures are deliberately terminal.</p>
 */
final class BoundedSqlRetry {

    static final int DEFAULT_MAX_ATTEMPTS = 3;
    static final String STATEMENT_TIMEOUT_SQL =
            "SET LOCAL statement_timeout = '30s'";
    static final String LOCK_TIMEOUT_SQL =
            "SET LOCAL lock_timeout = '5s'";
    static final String IDLE_TRANSACTION_TIMEOUT_SQL =
            "SET LOCAL idle_in_transaction_session_timeout = '60s'";
    private static final Set<String> RETRYABLE_SQL_STATES =
            Set.of("40001", "40P01");

    private final DataSource dataSource;
    private final int maxAttempts;

    BoundedSqlRetry(DataSource dataSource) {
        this(dataSource, DEFAULT_MAX_ATTEMPTS);
    }

    BoundedSqlRetry(DataSource dataSource, int maxAttempts) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
        if (maxAttempts < 1 || maxAttempts > DEFAULT_MAX_ATTEMPTS) {
            throw new IllegalArgumentException("maxAttempts must be between 1 and 3");
        }
        this.maxAttempts = maxAttempts;
    }

    <T> Execution<T> execute(TransactionWork<T> work) throws SqlOperationException {
        Objects.requireNonNull(work, "work");
        int retries = 0;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            Attempt<T> outcome = attempt(work, attempt);
            if (outcome.value() != null) {
                return new Execution<>(outcome.value(), attempt, retries);
            }
            SqlOperationException failure = outcome.failure();
            if (!failure.retryable() || attempt == maxAttempts) {
                throw failure.withCounts(attempt, retries);
            }
            retries++;
        }
        throw new IllegalStateException("bounded retry loop fell through");
    }

    private <T> Attempt<T> attempt(TransactionWork<T> work, int attempt) {
        Connection connection = null;
        boolean acquired = false;
        boolean transactionOpen = false;
        boolean workStarted = false;
        boolean commitStarted = false;
        T value = null;
        Throwable primary = null;
        FailureKind kind = FailureKind.SQL;
        try {
            connection = dataSource.getConnection();
            acquired = true;
            connection.setAutoCommit(false);
            connection.setReadOnly(false);
            connection.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
            transactionOpen = true;
            configureTransactionTimeouts(connection);
            workStarted = true;
            value = Objects.requireNonNull(
                    work.execute(connection, attempt), "transaction result");
            commitStarted = true;
            connection.commit();
            transactionOpen = false;
        } catch (Exception failure) {
            primary = failure;
            kind = !acquired
                    ? FailureKind.CONNECTION_ACQUISITION
                    : !workStarted
                            ? FailureKind.CONNECTION_SETUP
                    : commitStarted
                            ? FailureKind.COMMIT_OUTCOME_UNKNOWN
                            : FailureKind.SQL;
        } catch (Error fatal) {
            if (connection != null && transactionOpen && !commitStarted) {
                try {
                    connection.rollback();
                } catch (SQLException | RuntimeException rollbackFailure) {
                    fatal.addSuppressed(rollbackFailure);
                }
            }
            if (connection != null) {
                try {
                    connection.close();
                } catch (SQLException | RuntimeException closeFailure) {
                    fatal.addSuppressed(closeFailure);
                }
            }
            throw fatal;
        }

        if (connection != null && transactionOpen && !commitStarted) {
            try {
                connection.rollback();
                transactionOpen = false;
            } catch (SQLException | RuntimeException rollbackFailure) {
                primary = combine(primary, rollbackFailure);
                kind = FailureKind.ROLLBACK;
            }
        }
        if (connection != null) {
            try {
                connection.close();
            } catch (SQLException | RuntimeException closeFailure) {
                primary = combine(primary, closeFailure);
                if (kind == FailureKind.SQL) {
                    kind = FailureKind.CLOSE;
                }
            }
        }

        if (primary == null) {
            return Attempt.success(value);
        }
        String rootSqlState = rootSqlState(primary);
        boolean retryable = kind == FailureKind.SQL
                && workStarted
                && !commitStarted
                && rootSqlState != null
                && RETRYABLE_SQL_STATES.contains(rootSqlState);
        return Attempt.failure(new SqlOperationException(
                kind, rootSqlState, retryable, 1, 0, primary));
    }

    static String rootSqlState(Throwable failure) {
        if (failure == null) {
            return null;
        }
        return failure instanceof SQLException sqlFailure
                ? sqlFailure.getSQLState()
                : null;
    }

    static java.util.List<String> statementSurface() {
        return java.util.List.of(
                STATEMENT_TIMEOUT_SQL,
                LOCK_TIMEOUT_SQL,
                IDLE_TRANSACTION_TIMEOUT_SQL);
    }

    static void configureTransactionTimeouts(Connection connection)
            throws SQLException {
        try (Statement statement = connection.createStatement()) {
            statement.execute(STATEMENT_TIMEOUT_SQL);
            statement.execute(LOCK_TIMEOUT_SQL);
            statement.execute(IDLE_TRANSACTION_TIMEOUT_SQL);
        }
    }

    private static Throwable combine(Throwable primary, Throwable secondary) {
        if (primary == null) {
            return secondary;
        }
        primary.addSuppressed(secondary);
        return primary;
    }

    @FunctionalInterface
    interface TransactionWork<T> {
        T execute(Connection connection, int attempt) throws Exception;
    }

    record Execution<T>(T value, int attempts, int retries) {
        Execution {
            value = Objects.requireNonNull(value, "value");
            if (attempts < 1 || retries < 0 || retries >= attempts) {
                throw new IllegalArgumentException("invalid retry counts");
            }
        }
    }

    enum FailureKind {
        CONNECTION_ACQUISITION,
        CONNECTION_SETUP,
        SQL,
        ROLLBACK,
        COMMIT_OUTCOME_UNKNOWN,
        CLOSE
    }

    static final class SqlOperationException extends Exception {
        private final FailureKind kind;
        private final String rootSqlState;
        private final boolean retryable;
        private final int attempts;
        private final int retries;

        private SqlOperationException(
                FailureKind kind,
                String rootSqlState,
                boolean retryable,
                int attempts,
                int retries,
                Throwable cause
        ) {
            super("tag migration SQL operation failed", cause);
            this.kind = Objects.requireNonNull(kind, "kind");
            this.rootSqlState = rootSqlState;
            this.retryable = retryable;
            this.attempts = attempts;
            this.retries = retries;
        }

        FailureKind kind() {
            return kind;
        }

        String rootSqlState() {
            return rootSqlState;
        }

        boolean retryable() {
            return retryable;
        }

        int attempts() {
            return attempts;
        }

        int retries() {
            return retries;
        }

        private SqlOperationException withCounts(int newAttempts, int newRetries) {
            return new SqlOperationException(
                    kind,
                    rootSqlState,
                    retryable,
                    newAttempts,
                    newRetries,
                    getCause());
        }
    }

    private record Attempt<T>(T value, SqlOperationException failure) {
        private static <T> Attempt<T> success(T value) {
            return new Attempt<>(Objects.requireNonNull(value, "value"), null);
        }

        private static <T> Attempt<T> failure(SqlOperationException failure) {
            return new Attempt<>(null, Objects.requireNonNull(failure, "failure"));
        }
    }
}
