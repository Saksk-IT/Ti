package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.api.PersonalBankQuestionTypeCount;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.modulith.ApplicationModule;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Gates the exact HTTP-neutral Phase 4C user-counts application shape. */
class Phase4cPersonalBankUserCountsContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final List<String> PHASE4B_PUBLIC_APIS = List.of(
            "io.saksk.ti.identity.api.IdentityApplicationApi",
            "io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi",
            "io.saksk.ti.identity.api.SessionAuthorityApi",
            "io.saksk.ti.identity.api.SubjectAccessPolicyApi",
            "io.saksk.ti.catalog.api.CatalogApplicationApi",
            "io.saksk.ti.catalog.api.PublicBankCatalogApi",
            "io.saksk.ti.catalog.api.QuestionMetadataApplicationApi",
            "io.saksk.ti.catalog.api.SubjectMetadataApplicationApi",
            "io.saksk.ti.operations.api.OperationsApplicationApi",
            PersonalBankApplicationApi.class.getName());
    private static final List<Class<?>> PHASE4C_BOUNDARY_TYPES = List.of(
            LearningApplicationApi.class,
            AuthenticatedLearningViewer.class,
            PersonalBankUserCountsQuery.class,
            PersonalBankUserCountsResult.class,
            PersonalBankUserCountsView.class,
            PersonalBankQuestionFactsApi.class,
            AuthenticatedPersonalBankViewer.class,
            PersonalBankQuestionSelection.class,
            PersonalBankQuestionAccessResult.class,
            PersonalBankQuestionFactsResult.class,
            PersonalBankQuestionFactsView.class,
            PersonalBankQuestionTypeCount.class,
            PersonalBankQuestionMembershipView.class);

    @Test
    void exposesExactTwentySevenMethodHttpNeutralShape() throws Exception {
        JsonNode composition = readJson(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-composition-contract.json");
        JsonNode phase4bShape = readJson(
                "docs/refactor/phase4b/"
                        + "personal-bank-usage-stats-application-api-shape.json");
        assertThat(phase4bShape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(23);
        assertThat(composition.path("production_baseline")
                        .path("implemented_public_application_method_count").asInt())
                .isEqualTo(23);
        assertThat(composition.path("planned_public_api_shape")
                        .path("authorized_future_method_count").asInt())
                .isEqualTo(27);

        List<Class<?>> phase4bApis = new ArrayList<>();
        for (String className : PHASE4B_PUBLIC_APIS) {
            Class<?> api = Class.forName(className);
            assertThat(api.isInterface()).as(className).isTrue();
            assertThat(Modifier.isPublic(api.getModifiers())).as(className).isTrue();
            phase4bApis.add(api);
        }
        assertThat(methodCount(phase4bApis)).isEqualTo(23);
        assertThat(LearningApplicationApi.class.getDeclaredMethods()).hasSize(1);
        assertThat(PersonalBankQuestionFactsApi.class.getDeclaredMethods()).hasSize(3);
        assertThat(methodCount(phase4bApis)
                + LearningApplicationApi.class.getDeclaredMethods().length
                + PersonalBankQuestionFactsApi.class.getDeclaredMethods().length)
                .isEqualTo(27);

        assertMethod(
                LearningApplicationApi.class,
                "findPersonalBankUserCounts",
                PersonalBankUserCountsResult.class,
                AuthenticatedLearningViewer.class,
                PersonalBankUserCountsQuery.class);
        assertMethod(
                PersonalBankQuestionFactsApi.class,
                "checkQuestionAccess",
                PersonalBankQuestionAccessResult.class,
                AuthenticatedPersonalBankViewer.class,
                int.class);
        assertMethod(
                PersonalBankQuestionFactsApi.class,
                "summarizeQuestions",
                PersonalBankQuestionFactsResult.class,
                AuthenticatedPersonalBankViewer.class,
                PersonalBankQuestionSelection.class);
        Method membership = assertMethod(
                PersonalBankQuestionFactsApi.class,
                "inspectQuestionMembership",
                PersonalBankQuestionMembershipView.class,
                int.class,
                List.class);
        assertThat(membership.getGenericParameterTypes()[1].getTypeName())
                .isEqualTo("java.util.List<java.lang.Integer>");

        assertRecord(
                AuthenticatedLearningViewer.class,
                "identityId:long");
        assertRecord(
                PersonalBankUserCountsQuery.class,
                "bankId:int",
                "rawQuestionType:java.lang.String",
                "rawSource:java.lang.String",
                "rawTag:java.lang.String");
        assertRecord(
                PersonalBankUserCountsResult.class,
                "outcome:io.saksk.ti.learning.api.PersonalBankUserCountsResult$Outcome",
                "data:java.util.Optional<io.saksk.ti.learning.api.PersonalBankUserCountsView>");
        assertRecord(
                PersonalBankUserCountsView.class,
                "total:long",
                "favorites:long",
                "mistakes:long",
                "types:java.util.List<java.lang.String>",
                "shuffleOptionsAvailable:boolean");
        assertRecord(AuthenticatedPersonalBankViewer.class, "identityId:long");
        assertRecord(
                PersonalBankQuestionSelection.class,
                "bankId:int",
                "portableType:java.util.Optional<java.lang.String>",
                "candidateQuestionIds:java.util.Optional<java.util.List<java.lang.Integer>>");
        assertRecord(
                PersonalBankQuestionAccessResult.class,
                "outcome:io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult$Outcome");
        assertRecord(
                PersonalBankQuestionFactsResult.class,
                "outcome:io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult$Outcome",
                "data:java.util.Optional<io.saksk.ti.personalbank.api.PersonalBankQuestionFactsView>");
        assertRecord(
                PersonalBankQuestionFactsView.class,
                "total:long",
                "rawTypes:java.util.List<io.saksk.ti.personalbank.api.PersonalBankQuestionTypeCount>");
        assertRecord(
                PersonalBankQuestionTypeCount.class,
                "rawType:java.util.Optional<java.lang.String>",
                "count:long");
        assertRecord(
                PersonalBankQuestionMembershipView.class,
                "bankId:int",
                "bankExists:boolean",
                "existingQuestionIds:java.util.List<java.lang.Integer>",
                "membershipDigest:java.lang.String");

        assertThat(enumNames(PersonalBankUserCountsResult.Outcome.values()))
                .containsExactly("AVAILABLE", "DENIED");
        assertThat(enumNames(PersonalBankQuestionAccessResult.Outcome.values()))
                .containsExactly("AVAILABLE", "DENIED");
        assertThat(enumNames(PersonalBankQuestionFactsResult.Outcome.values()))
                .containsExactly("AVAILABLE", "DENIED");

        for (Class<?> boundaryType : PHASE4C_BOUNDARY_TYPES) {
            assertThat(Modifier.isPublic(boundaryType.getModifiers()))
                    .as(boundaryType.getName())
                    .isTrue();
            String reflectedShape = Arrays.toString(boundaryType.getDeclaredMethods())
                    + Arrays.toString(boundaryType.getRecordComponents());
            assertThat(reflectedShape).doesNotContain(
                    "org.springframework.web",
                    "org.springframework.security",
                    "jakarta.servlet");
        }
        assertProductionSourcesRemainHttpAndSecurityNeutral(composition);
    }

    @Test
    void keepsLearningToPersonalbankApiDependencyOneWay() throws Exception {
        ApplicationModule learning = moduleDeclaration("io.saksk.ti.learning");
        ApplicationModule personalbank = moduleDeclaration("io.saksk.ti.personalbank");
        assertThat(Arrays.asList(learning.allowedDependencies()))
                .contains("personalbank::api")
                .doesNotContain("personalbank");
        assertThat(Arrays.asList(personalbank.allowedDependencies()))
                .noneMatch(dependency -> dependency.startsWith("learning"));

        Path learningRoot = resolve("server/src/main/java/io/saksk/ti/learning");
        try (var sources = Files.walk(learningRoot)) {
            for (Path source : sources.filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".java"))
                    .toList()) {
                String text = Files.readString(source, StandardCharsets.UTF_8);
                assertThat(text.replace("io.saksk.ti.personalbank.api.", ""))
                        .as(source.toString())
                        .doesNotContain("io.saksk.ti.personalbank.");
            }
        }

        Path personalbankRoot = resolve("server/src/main/java/io/saksk/ti/personalbank");
        try (var sources = Files.walk(personalbankRoot)) {
            for (Path source : sources.filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".java"))
                    .toList()) {
                assertThat(Files.readString(source, StandardCharsets.UTF_8))
                        .as(source.toString())
                        .doesNotContain("io.saksk.ti.learning");
            }
        }
    }

    private static int methodCount(List<Class<?>> apiTypes) {
        return apiTypes.stream().mapToInt(type -> type.getDeclaredMethods().length).sum();
    }

    private static Method assertMethod(
            Class<?> api,
            String name,
            Class<?> returnType,
            Class<?>... parameterTypes
    ) throws Exception {
        Method method = api.getDeclaredMethod(name, parameterTypes);
        assertThat(method.getReturnType()).isEqualTo(returnType);
        assertThat(method.getParameterTypes()).containsExactly(parameterTypes);
        assertThat(Modifier.isPublic(method.getModifiers())).isTrue();
        return method;
    }

    private static void assertRecord(Class<?> type, String... expectedComponents) {
        assertThat(type.isRecord()).as(type.getName()).isTrue();
        assertThat(Arrays.stream(type.getRecordComponents())
                        .map(Phase4cPersonalBankUserCountsContractParityTest::componentShape)
                        .toList())
                .containsExactly(expectedComponents);
    }

    private static String componentShape(RecordComponent component) {
        return component.getName() + ":" + component.getGenericType().getTypeName();
    }

    private static List<String> enumNames(Enum<?>[] values) {
        return Arrays.stream(values).map(Enum::name).toList();
    }

    private static ApplicationModule moduleDeclaration(String packageName)
            throws Exception {
        Package modulePackage = Class.forName(packageName + ".package-info").getPackage();
        ApplicationModule declaration = modulePackage.getAnnotation(ApplicationModule.class);
        assertThat(declaration).as(packageName).isNotNull();
        return declaration;
    }

    private static void assertProductionSourcesRemainHttpAndSecurityNeutral(
            JsonNode composition
    ) throws Exception {
        JsonNode requirements = composition.path("successor_handoff")
                .path("future_read_contract_requirements");
        List<String> sources = new ArrayList<>();
        sources.addAll(requirements.path("expected_added_main_sources").propertyNames());
        requirements.path("expected_changed_main_sources")
                .forEach(source -> sources.add(source.asString()));
        assertThat(sources).hasSize(18);
        for (String source : sources) {
            String text = Files.readString(resolve(source), StandardCharsets.UTF_8);
            assertThat(text).as(source).doesNotContain(
                    "org.springframework.web",
                    "org.springframework.security",
                    "jakarta.servlet",
                    "jakarta.ws.rs",
                    "ResponseEntity",
                    "@RestController",
                    "@RequestMapping",
                    "SecurityFilterChain");
        }
    }

    private static JsonNode readJson(String relative) throws Exception {
        return JSON.readTree(Files.readString(resolve(relative), StandardCharsets.UTF_8));
    }

    private static Path resolve(String relative) {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        Path tiJavaRoot = basedir.getParent();
        Path path = tiJavaRoot.resolve(relative).normalize();
        if (!path.startsWith(tiJavaRoot)) {
            throw new IllegalArgumentException("Path escapes Ti-Java: " + relative);
        }
        return path;
    }
}
