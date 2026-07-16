package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectCatalogQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private catalog JDBC adapter. */
public final class JdbcSubjectCatalogQueryAdapterTestAccess {

    private JdbcSubjectCatalogQueryAdapterTestAccess() {
    }

    public static SubjectCatalogQueryPort create(JdbcClient jdbc) {
        return new JdbcSubjectCatalogQueryAdapter(jdbc);
    }
}
