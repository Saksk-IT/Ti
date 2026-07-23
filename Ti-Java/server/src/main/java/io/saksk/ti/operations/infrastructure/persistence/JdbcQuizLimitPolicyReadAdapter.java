package io.saksk.ti.operations.infrastructure.persistence;

import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuizLimitPolicyReadAdapter implements QuizLimitPolicyReadPort {

    private static final String ENABLED_KEY = "quiz_limit_enabled";
    private static final String LIMIT_KEY = "quiz_limit_count";

    private final JdbcClient jdbc;

    JdbcQuizLimitPolicyReadAdapter(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public RawQuizLimitConfiguration read() {
        List<ConfigRow> rows = jdbc.sql("""
                        SELECT config_key, config_value
                          FROM system_config
                         WHERE config_key IN (:enabledKey, :limitKey)
                         ORDER BY config_key
                        """)
                .param("enabledKey", ENABLED_KEY)
                .param("limitKey", LIMIT_KEY)
                .query((row, rowNumber) -> new ConfigRow(
                        row.getString("config_key"),
                        row.getString("config_value")))
                .list();
        Map<String, String> values = new LinkedHashMap<>();
        for (ConfigRow row : rows) {
            if (values.containsKey(row.key())) {
                throw new IllegalStateException(
                        "Duplicate operations configuration key: " + row.key());
            }
            values.put(row.key(), row.value());
        }
        return new RawQuizLimitConfiguration(
                Optional.ofNullable(values.get(ENABLED_KEY)),
                Optional.ofNullable(values.get(LIMIT_KEY)));
    }

    private record ConfigRow(String key, String value) {
        private ConfigRow {
            key = Objects.requireNonNull(key, "key");
        }
    }
}
