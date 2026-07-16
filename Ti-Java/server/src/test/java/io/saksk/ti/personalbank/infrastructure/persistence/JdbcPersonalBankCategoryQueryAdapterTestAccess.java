package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcPersonalBankCategoryQueryAdapterTestAccess {

    private JdbcPersonalBankCategoryQueryAdapterTestAccess() {
    }

    public static PersonalBankCategoryQueryPort create(JdbcClient jdbc) {
        return new JdbcPersonalBankCategoryQueryAdapter(jdbc);
    }
}
