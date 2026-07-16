package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private question-type JDBC adapter. */
public final class JdbcQuestionTypeQueryAdapterTestAccess {

    private JdbcQuestionTypeQueryAdapterTestAccess() {
    }

    public static QuestionTypeQueryPort create(JdbcClient jdbc) {
        return new JdbcQuestionTypeQueryAdapter(jdbc);
    }
}
