package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcPersonalBankShareQueryAdapterTestAccess {

    private JdbcPersonalBankShareQueryAdapterTestAccess() {
    }

    public static PersonalBankShareQueryPort create(JdbcClient jdbc) {
        return new JdbcPersonalBankShareQueryAdapter(jdbc);
    }
}
