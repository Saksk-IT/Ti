package io.saksk.ti.catalog;

import io.saksk.ti.architecture.AbstractPhase2ModuleContextTest;
import io.saksk.ti.catalog.infrastructure.persistence.SubjectReadRepository;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;

/** Phase 2 boundary-context smoke test; this does not claim catalog behavior has migrated. */
@ApplicationModuleTest(mode = BootstrapMode.STANDALONE, webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("unit")
@Import(CatalogModuleContextTest.ReadDependency.class)
class CatalogModuleContextTest extends AbstractPhase2ModuleContextTest {

    @Override
    protected String moduleId() {
        return "catalog";
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class ReadDependency {
        @Bean
        SubjectReadRepository subjectReadRepository() {
            return new SubjectReadRepository() {
                @Override
                public Optional<io.saksk.ti.catalog.infrastructure.persistence.SubjectReadEntity> findById(
                        Integer id) {
                    return Optional.empty();
                }

                @Override
                public List<io.saksk.ti.catalog.infrastructure.persistence.SubjectReadEntity>
                        findAllByOrderByNameAsc() {
                    return List.of();
                }
            };
        }

        @Bean
        JdbcClient jdbcClient() {
            return org.mockito.Mockito.mock(JdbcClient.class);
        }

        @Bean
        SubjectAccessPolicyApi subjectAccessPolicyApi() {
            return org.mockito.Mockito.mock(SubjectAccessPolicyApi.class);
        }
    }
}
