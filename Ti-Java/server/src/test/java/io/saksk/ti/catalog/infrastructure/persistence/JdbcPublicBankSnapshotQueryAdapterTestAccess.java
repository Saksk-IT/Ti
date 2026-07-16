package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private public-bank JDBC adapter. */
public final class JdbcPublicBankSnapshotQueryAdapterTestAccess {

    private JdbcPublicBankSnapshotQueryAdapterTestAccess() {
    }

    public static PublicBankSnapshotQueryPort create(JdbcClient jdbc) {
        return new JdbcPublicBankSnapshotQueryAdapter(jdbc);
    }
}
