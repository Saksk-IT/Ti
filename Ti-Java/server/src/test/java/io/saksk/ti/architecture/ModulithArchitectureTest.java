package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import io.saksk.ti.TiApplication;
import java.util.LinkedHashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModulithArchitectureTest {

    private static final Set<String> EXPECTED_MODULES = Set.of(
            "sharedkernel",
            "identity",
            "catalog",
            "personalbank",
            "assessment",
            "learning",
            "community",
            "campus",
            "coding",
            "intelligence",
            "messaging",
            "operations",
            "web");

    @Test
    void recognizesExactlyTheAcceptedModulesAndVerifiesTheirStructure() {
        var modules = ApplicationModules.of(TiApplication.class);
        var identifiers = new LinkedHashSet<String>();
        modules.forEach(module -> identifiers.add(module.getIdentifier().toString()));

        assertThat(identifiers).containsExactlyInAnyOrderElementsOf(EXPECTED_MODULES);
        assertThatCode(modules::verify).doesNotThrowAnyException();
    }
}
