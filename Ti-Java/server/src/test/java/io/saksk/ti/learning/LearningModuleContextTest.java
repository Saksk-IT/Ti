package io.saksk.ti.learning;

import io.saksk.ti.architecture.AbstractPhase2ModuleContextTest;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;

/** Phase 2 boundary-context smoke test; this does not claim learning behavior has migrated. */
@ApplicationModuleTest(mode = BootstrapMode.STANDALONE, webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("unit")
@Import(LearningModuleContextTest.ReadDependency.class)
class LearningModuleContextTest extends AbstractPhase2ModuleContextTest {
    @Override
    protected String moduleId() {
        return "learning";
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
        PersonalBankQuestionFactsApi personalBankQuestionFactsApi() {
            return org.mockito.Mockito.mock(PersonalBankQuestionFactsApi.class);
        }
    }
}
