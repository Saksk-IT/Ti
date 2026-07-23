package io.saksk.ti.operations.infrastructure.persistence;

import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcQuizLimitPolicyReadAdapterTestAccess {

    private JdbcQuizLimitPolicyReadAdapterTestAccess() {
    }

    public static QuizLimitPolicyReadPort create(JdbcClient jdbc) {
        return new JdbcQuizLimitPolicyReadAdapter(jdbc);
    }
}
