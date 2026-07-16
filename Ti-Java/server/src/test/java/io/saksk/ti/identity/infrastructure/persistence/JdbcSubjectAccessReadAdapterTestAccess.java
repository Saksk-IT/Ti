package io.saksk.ti.identity.infrastructure.persistence;

import io.saksk.ti.identity.application.port.SubjectAccessReadPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private identity JDBC adapter. */
public final class JdbcSubjectAccessReadAdapterTestAccess {

    private JdbcSubjectAccessReadAdapterTestAccess() {
    }

    public static SubjectAccessReadPort create(JdbcClient jdbc) {
        return new JdbcSubjectAccessReadAdapter(jdbc);
    }
}
