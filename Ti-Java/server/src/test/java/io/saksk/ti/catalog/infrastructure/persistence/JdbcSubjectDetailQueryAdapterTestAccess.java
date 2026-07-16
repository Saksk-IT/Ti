package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectDetailQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private subject-detail JDBC adapter. */
public final class JdbcSubjectDetailQueryAdapterTestAccess {

    private JdbcSubjectDetailQueryAdapterTestAccess() {
    }

    public static SubjectDetailQueryPort create(JdbcClient jdbc) {
        return new JdbcSubjectDetailQueryAdapter(jdbc);
    }
}
