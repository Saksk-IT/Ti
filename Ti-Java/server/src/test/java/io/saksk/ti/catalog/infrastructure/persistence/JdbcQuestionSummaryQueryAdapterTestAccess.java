package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionSummaryQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Test-only constructor access for the package-private question-summary JDBC adapter. */
public final class JdbcQuestionSummaryQueryAdapterTestAccess {

    private JdbcQuestionSummaryQueryAdapterTestAccess() {
    }

    public static QuestionSummaryQueryPort create(JdbcClient jdbc) {
        return new JdbcQuestionSummaryQueryAdapter(jdbc);
    }
}
