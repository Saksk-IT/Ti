package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.sql.SQLException;
import org.junit.jupiter.api.Test;

class JdbcPublicBankSnapshotMaintenanceAdapterTest {

    @Test
    void retriesOnlyPostgresSerializationAndDeadlockSqlStates() {
        assertThat(retryable("40001")).isTrue();
        assertThat(retryable("40P01")).isTrue();

        assertThat(retryable("55P03")).as("lock-not-available is not in the retry contract")
                .isFalse();
        assertThat(retryable("23503")).as("foreign-key failures are not transient concurrency")
                .isFalse();
        assertThat(JdbcPublicBankSnapshotMaintenanceAdapter
                .isRetryablePostgresConcurrencyFailure(new IllegalStateException("loader")))
                .isFalse();
    }

    @Test
    void inspectsNestedCausesAndChainedSqlExceptions() {
        SQLException outer = new SQLException("outer", "HY000");
        outer.setNextException(new SQLException("deadlock", "40P01"));

        assertThat(JdbcPublicBankSnapshotMaintenanceAdapter
                .isRetryablePostgresConcurrencyFailure(
                        new IllegalStateException("translated", outer)))
                .isTrue();
    }

    private static boolean retryable(String sqlState) {
        return JdbcPublicBankSnapshotMaintenanceAdapter
                .isRetryablePostgresConcurrencyFailure(
                        new IllegalStateException(
                                "translated", new SQLException("database", sqlState)));
    }
}
