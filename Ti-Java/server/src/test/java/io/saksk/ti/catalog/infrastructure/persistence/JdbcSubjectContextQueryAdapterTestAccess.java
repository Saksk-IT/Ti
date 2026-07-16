package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectContextQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private subject-context JDBC adapter. */
public final class JdbcSubjectContextQueryAdapterTestAccess {

    private JdbcSubjectContextQueryAdapterTestAccess() {
    }

    public static SubjectContextQueryPort create(JdbcClient jdbc) {
        return new JdbcSubjectContextQueryAdapter(jdbc);
    }
}
