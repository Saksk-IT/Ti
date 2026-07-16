package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionExportQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcQuestionExportQueryAdapterTestAccess {

    private JdbcQuestionExportQueryAdapterTestAccess() {
    }

    public static QuestionExportQueryPort create(JdbcClient jdbc) {
        return new JdbcQuestionExportQueryAdapter(jdbc);
    }
}
