package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcPersonalBankOwnedShareQueryAdapterTestAccess {

    private JdbcPersonalBankOwnedShareQueryAdapterTestAccess() {
    }

    public static PersonalBankOwnedShareQueryPort create(JdbcClient jdbc) {
        return new JdbcPersonalBankOwnedShareQueryAdapter(jdbc);
    }
}
