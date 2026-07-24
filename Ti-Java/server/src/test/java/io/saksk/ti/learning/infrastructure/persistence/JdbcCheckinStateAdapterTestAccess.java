package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.CheckinStatePort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcCheckinStateAdapterTestAccess {

    private JdbcCheckinStateAdapterTestAccess() {
    }

    public static CheckinStatePort create(JdbcClient jdbc) {
        return new JdbcCheckinStateAdapter(jdbc);
    }
}
