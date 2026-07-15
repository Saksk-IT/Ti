package io.saksk.ti.messaging;

import io.saksk.ti.architecture.AbstractPhase2ModuleContextTest;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;

/** Phase 2 boundary-context smoke test; this does not claim messaging behavior has migrated. */
@ApplicationModuleTest(mode = BootstrapMode.STANDALONE, webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("unit")
class MessagingModuleContextTest extends AbstractPhase2ModuleContextTest {
    @Override
    protected String moduleId() {
        return "messaging";
    }
}
