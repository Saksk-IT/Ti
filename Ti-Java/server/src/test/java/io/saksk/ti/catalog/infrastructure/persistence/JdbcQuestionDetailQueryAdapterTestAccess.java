package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionDetailQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private question-detail JDBC adapter. */
public final class JdbcQuestionDetailQueryAdapterTestAccess {

    private JdbcQuestionDetailQueryAdapterTestAccess() {
    }

    public static QuestionDetailQueryPort create(JdbcClient jdbc) {
        return new JdbcQuestionDetailQueryAdapter(jdbc);
    }
}
