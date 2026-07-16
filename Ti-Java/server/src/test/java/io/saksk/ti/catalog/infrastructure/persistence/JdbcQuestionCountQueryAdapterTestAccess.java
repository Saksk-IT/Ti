package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private question-count JDBC adapter. */
public final class JdbcQuestionCountQueryAdapterTestAccess {

    private JdbcQuestionCountQueryAdapterTestAccess() {
    }

    public static QuestionCountQueryPort create(JdbcClient jdbc) {
        return new JdbcQuestionCountQueryAdapter(jdbc);
    }
}
