package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fixture.invalid.IllegalFixtureApplication;
import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class IllegalDependencyFixtureTest {

    @Test
    void realModulithVerificationRejectsAnImportOfProviderInternals() {
        assertThatThrownBy(() -> ApplicationModules.of(
                                IllegalFixtureApplication.class,
                                location -> true)
                        .verify())
                .as("the fixture imports provider.domain even though only provider::api is allowed")
                .hasMessageContaining("ProviderSecret")
                .hasMessageContaining("provider")
                .hasMessageContaining("consumer");
    }
}
