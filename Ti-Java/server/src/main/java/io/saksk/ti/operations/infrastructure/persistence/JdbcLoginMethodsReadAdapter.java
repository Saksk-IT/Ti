package io.saksk.ti.operations.infrastructure.persistence;

import io.saksk.ti.operations.application.port.LoginMethodsReadPort;
import io.saksk.ti.operations.domain.LoginMethods;
import java.util.Locale;
import java.util.Optional;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcLoginMethodsReadAdapter implements LoginMethodsReadPort {

    private static final String PHONE_KEY = "auth_phone_login_enabled";
    private static final String WECHAT_KEY = "auth_wechat_login_enabled";
    private static final String PHONE_ENV = "AUTH_PHONE_LOGIN_ENABLED";
    private static final String WECHAT_ENV = "AUTH_WECHAT_LOGIN_ENABLED";

    private final JdbcClient jdbc;
    private final Environment environment;

    JdbcLoginMethodsReadAdapter(JdbcClient jdbc, Environment environment) {
        this.jdbc = jdbc;
        this.environment = environment;
    }

    @Override
    public LoginMethods read() {
        return new LoginMethods(
                resolve(PHONE_KEY, PHONE_ENV),
                resolve(WECHAT_KEY, WECHAT_ENV));
    }

    private boolean resolve(String databaseKey, String environmentKey) {
        Optional<String> databaseValue = jdbc.sql("""
                        SELECT config_value
                        FROM system_config
                        WHERE config_key = :configKey
                        """)
                .param("configKey", databaseKey)
                .query((resultSet, rowNumber) -> resultSet.getString(1))
                .optional()
                .filter(value -> !value.isEmpty());

        if (databaseValue.isPresent()) {
            return parseDatabaseBoolean(databaseValue.orElseThrow(), true);
        }

        String environmentValue = environment.getProperty(environmentKey);
        return environmentValue == null
                ? true
                : parseEnvironmentBoolean(environmentValue);
    }

    static boolean parseDatabaseBoolean(String value, boolean defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        if (normalized.isEmpty()) {
            return defaultValue;
        }
        return switch (normalized) {
            case "1", "true", "yes", "on" -> true;
            default -> false;
        };
    }

    static boolean parseEnvironmentBoolean(String value) {
        String normalized = value == null ? "" : value.strip().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "1", "true", "on" -> true;
            default -> false;
        };
    }
}
