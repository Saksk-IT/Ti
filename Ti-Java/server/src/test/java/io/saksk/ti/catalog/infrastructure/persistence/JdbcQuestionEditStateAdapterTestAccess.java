package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionEditStatePort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcQuestionEditStateAdapterTestAccess {

    private JdbcQuestionEditStateAdapterTestAccess() {
    }

    public static QuestionEditStatePort create(JdbcClient jdbc) {
        return new JdbcQuestionEditStateAdapter(jdbc);
    }
}
