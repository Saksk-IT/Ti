package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private subject-inventory JDBC adapter. */
public final class JdbcSubjectInventoryQueryAdapterTestAccess {

    private JdbcSubjectInventoryQueryAdapterTestAccess() {
    }

    public static SubjectInventoryQueryPort create(JdbcClient jdbc) {
        return new JdbcSubjectInventoryQueryAdapter(jdbc);
    }
}
