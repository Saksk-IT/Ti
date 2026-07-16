package io.saksk.ti.operations.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class JdbcLoginMethodsReadAdapterTest {

    @Test
    void databaseBooleanParsingMatchesTheLegacyRuntimeHelper() {
        for (String value : new String[]{"1", "true", "TRUE", "yes", " on "}) {
            assertThat(JdbcLoginMethodsReadAdapter.parseDatabaseBoolean(value, false)).isTrue();
        }
        for (String value : new String[]{"0", "false", "no", "off", "unexpected"}) {
            assertThat(JdbcLoginMethodsReadAdapter.parseDatabaseBoolean(value, true)).isFalse();
        }
        assertThat(JdbcLoginMethodsReadAdapter.parseDatabaseBoolean(" ", true)).isTrue();
        assertThat(JdbcLoginMethodsReadAdapter.parseDatabaseBoolean(null, true)).isTrue();
    }

    @Test
    void environmentBooleanParsingMatchesTheLegacyConfigClass() {
        for (String value : new String[]{"1", "true", "TRUE", " on "}) {
            assertThat(JdbcLoginMethodsReadAdapter.parseEnvironmentBoolean(value)).isTrue();
        }
        for (String value : new String[]{"", "yes", "0", "false", "off", "unexpected"}) {
            assertThat(JdbcLoginMethodsReadAdapter.parseEnvironmentBoolean(value)).isFalse();
        }
    }
}
