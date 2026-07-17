package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcPersonalBankUsageStatsQueryAdapterTestAccess {

    private JdbcPersonalBankUsageStatsQueryAdapterTestAccess() {
    }

    public static PersonalBankUsageStatsQueryPort create(JdbcClient jdbc) {
        return new JdbcPersonalBankUsageStatsQueryAdapter(jdbc);
    }
}
