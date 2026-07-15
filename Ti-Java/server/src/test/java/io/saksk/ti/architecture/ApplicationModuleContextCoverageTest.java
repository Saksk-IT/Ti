package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.Modifier;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;
import org.springframework.test.context.ActiveProfiles;

class ApplicationModuleContextCoverageTest {

    private static final Map<String, String> MODULE_TESTS = moduleTests();

    @Test
    void everyBusinessModuleHasOneConcreteStandaloneContextSmokeTest() throws Exception {
        assertThat(MODULE_TESTS.keySet()).containsExactlyInAnyOrder(
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
                "operations");
        assertThat(MODULE_TESTS).hasSize(11);
        assertThat(Arrays.stream(AbstractPhase2ModuleContextTest.class.getDeclaredMethods())
                        .filter(method -> method.isAnnotationPresent(Test.class)))
                .as("the shared base contributes one real inherited JUnit test")
                .hasSize(1);

        for (Map.Entry<String, String> entry : MODULE_TESTS.entrySet()) {
            Class<?> testType = Class.forName(entry.getValue());
            ApplicationModuleTest moduleTest = testType.getDeclaredAnnotation(ApplicationModuleTest.class);
            ActiveProfiles profiles = testType.getDeclaredAnnotation(ActiveProfiles.class);

            assertThat(testType.getPackageName()).isEqualTo("io.saksk.ti." + entry.getKey());
            assertThat(Modifier.isAbstract(testType.getModifiers())).isFalse();
            assertThat(AbstractPhase2ModuleContextTest.class).isAssignableFrom(testType);
            assertThat(moduleTest).as("@ApplicationModuleTest on %s", testType.getName()).isNotNull();
            assertThat(moduleTest.mode()).isEqualTo(BootstrapMode.STANDALONE);
            assertThat(moduleTest.webEnvironment()).isEqualTo(SpringBootTest.WebEnvironment.NONE);
            assertThat(profiles).as("unit profile on %s", testType.getName()).isNotNull();
            assertThat(Set.of(profiles.value())).containsExactly("unit");
        }
    }

    private static Map<String, String> moduleTests() {
        var tests = new LinkedHashMap<String, String>();
        tests.put("identity", "io.saksk.ti.identity.IdentityModuleContextTest");
        tests.put("catalog", "io.saksk.ti.catalog.CatalogModuleContextTest");
        tests.put("personalbank", "io.saksk.ti.personalbank.PersonalBankModuleContextTest");
        tests.put("assessment", "io.saksk.ti.assessment.AssessmentModuleContextTest");
        tests.put("learning", "io.saksk.ti.learning.LearningModuleContextTest");
        tests.put("community", "io.saksk.ti.community.CommunityModuleContextTest");
        tests.put("campus", "io.saksk.ti.campus.CampusModuleContextTest");
        tests.put("coding", "io.saksk.ti.coding.CodingModuleContextTest");
        tests.put("intelligence", "io.saksk.ti.intelligence.IntelligenceModuleContextTest");
        tests.put("messaging", "io.saksk.ti.messaging.MessagingModuleContextTest");
        tests.put("operations", "io.saksk.ti.operations.OperationsModuleContextTest");
        return Map.copyOf(tests);
    }
}
