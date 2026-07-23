package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.RecordResultStatePort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcRecordResultStateAdapterTestAccess {

    private JdbcRecordResultStateAdapterTestAccess() {
    }

    public static RecordResultStatePort create(JdbcClient jdbc) {
        return new JdbcRecordResultStateAdapter(jdbc);
    }
}
