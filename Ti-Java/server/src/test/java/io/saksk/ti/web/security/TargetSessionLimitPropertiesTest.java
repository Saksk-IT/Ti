package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.io.ClassPathResource;
import org.springframework.mock.env.MockEnvironment;

class TargetSessionLimitPropertiesTest {

    @Test
    void applicationDefaultsBindToTheTenThousandSessionCapacity() throws IOException {
        MockEnvironment environment = new MockEnvironment();
        new YamlPropertySourceLoader()
                .load("application", new ClassPathResource("application.yml"))
                .forEach(environment.getPropertySources()::addLast);

        TargetSessionLimitProperties properties = Binder.get(environment)
                .bind(
                        "ti.security.target-session-limit",
                        Bindable.of(TargetSessionLimitProperties.class))
                .orElseThrow(() -> new AssertionError(
                        "target Session limit defaults did not bind"));

        assertThat(properties.namespace())
                .isEqualTo("ti-java:identity:target-session-index");
        assertThat(properties.maxSessionsPerIdentity()).isEqualTo(3);
        assertThat(properties.maxTotalSessions()).isEqualTo(10_000);
        assertThat(properties.registryTtl()).isEqualTo(Duration.ofDays(7));
    }

    @Test
    void invalidGlobalCapacityBoundsFailClosedWhileBothValidEdgesRemainUsable() {
        assertThatThrownBy(() -> properties(3, 2))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("cover the per-identity limit");
        assertThatThrownBy(() -> properties(3, 100_001))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("at most 100000");

        assertThat(properties(3, 3).maxTotalSessions()).isEqualTo(3);
        assertThat(properties(3, 100_000).maxTotalSessions()).isEqualTo(100_000);
    }

    private static TargetSessionLimitProperties properties(
            int maxSessionsPerIdentity,
            int maxTotalSessions
    ) {
        return new TargetSessionLimitProperties(
                "ti-java:identity:target-session-index",
                maxSessionsPerIdentity,
                maxTotalSessions,
                Duration.ofDays(7));
    }
}
