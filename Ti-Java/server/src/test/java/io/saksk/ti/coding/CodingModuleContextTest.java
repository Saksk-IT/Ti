package io.saksk.ti.coding;

import io.saksk.ti.architecture.AbstractPhase2ModuleContextTest;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;

/** Phase 2 boundary-context smoke test; this does not claim coding behavior has migrated. */
@ApplicationModuleTest(mode = BootstrapMode.STANDALONE, webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("unit")
class CodingModuleContextTest extends AbstractPhase2ModuleContextTest {
    @Override
    protected String moduleId() {
        return "coding";
    }
}
