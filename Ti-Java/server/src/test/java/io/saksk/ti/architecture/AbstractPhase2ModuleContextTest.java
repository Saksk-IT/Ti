package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;

/** Shared assertion only; each concrete test still performs a real Modulith context bootstrap. */
public abstract class AbstractPhase2ModuleContextTest {

    @Autowired
    private ApplicationContext context;

    @Test
    public final void standaloneModuleContextStarts() {
        assertThat(context).isNotNull();
        assertThat(context.getId()).isNotBlank();
        assertThat(getClass().getPackageName())
                .as("test package must be the actual module root")
                .isEqualTo("io.saksk.ti." + moduleId());
    }

    protected abstract String moduleId();
}
