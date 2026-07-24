package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.StudyStatePort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcStudyStateAdapterTestAccess {

    private JdbcStudyStateAdapterTestAccess() {
    }

    public static StudyStatePort create(JdbcClient jdbc) {
        return new JdbcStudyStateAdapter(jdbc);
    }
}
