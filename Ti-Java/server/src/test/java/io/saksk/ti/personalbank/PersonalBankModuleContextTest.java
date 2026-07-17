package io.saksk.ti.personalbank;

import io.saksk.ti.architecture.AbstractPhase2ModuleContextTest;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;

/** Standalone boundary smoke test; Phase 4B personal-bank HTTP routes remain pending. */
@ApplicationModuleTest(mode = BootstrapMode.STANDALONE, webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("unit")
@Import(PersonalBankModuleContextTest.ReadDependency.class)
class PersonalBankModuleContextTest extends AbstractPhase2ModuleContextTest {

    @Override
    protected String moduleId() {
        return "personalbank";
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class ReadDependency {

        @Bean
        JdbcClient jdbcClient() {
            return org.mockito.Mockito.mock(JdbcClient.class);
        }

        @Bean
        PlatformTransactionManager transactionManager() {
            return org.mockito.Mockito.mock(PlatformTransactionManager.class);
        }

        @Bean
        Clock clock() {
            return Clock.fixed(
                    Instant.parse("2026-07-17T04:00:00Z"),
                    ZoneId.of("Asia/Shanghai"));
        }
    }
}
