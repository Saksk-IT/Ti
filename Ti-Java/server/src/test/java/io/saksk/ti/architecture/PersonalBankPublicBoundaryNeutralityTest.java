package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import java.io.IOException;
import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

class PersonalBankPublicBoundaryNeutralityTest {

    private static final List<String> FORBIDDEN_TRANSPORT_FRAGMENTS = List.of(
            "org.springframework.web.",
            "org.springframework.http.",
            "org.springframework.security.",
            "jakarta.servlet.",
            "tools.jackson.",
            "com.fasterxml.jackson.",
            "io.saksk.ti.web.",
            "ResponseEntity",
            "HttpServletRequest",
            "@Controller",
            "@RestController",
            "@GetMapping",
            "@RequestMapping",
            "/api/user/banks/api/categories",
            "/user/banks/api/categories",
            "success_response",
            "successResponse");
    private static final Pattern CHINESE_STRING_LITERAL =
            Pattern.compile("\"[^\"\\n]*\\p{IsHan}[^\"\\n]*\"");

    @Test
    void categoryQueryUsesOnlyAReviewedServerDerivedViewerAndRawFacts() throws Exception {
        assertThat(PersonalBankApplicationApi.class.isInterface()).isTrue();
        assertThat(Modifier.isPublic(PersonalBankApplicationApi.class.getModifiers())).isTrue();

        var method = PersonalBankApplicationApi.class.getDeclaredMethod(
                "listCategories", AuthenticatedPersonalBankViewer.class);
        assertThat(method.getGenericReturnType().getTypeName())
                .isEqualTo(
                        "java.util.List<io.saksk.ti.personalbank.api.PersonalBankCategoryView>");
        assertThat(method.getParameterTypes())
                .containsExactly(AuthenticatedPersonalBankViewer.class);
        assertThat(Modifier.isPublic(method.getModifiers())).isTrue();
        assertThat(Modifier.isAbstract(method.getModifiers())).isTrue();

        assertThat(AuthenticatedPersonalBankViewer.class.isRecord()).isTrue();
        assertThat(componentNames(AuthenticatedPersonalBankViewer.class))
                .containsExactly("identityId");
        assertThat(componentTypes(AuthenticatedPersonalBankViewer.class))
                .containsExactly("long");

        assertThat(PersonalBankCategoryView.class.isRecord()).isTrue();
        assertThat(componentNames(PersonalBankCategoryView.class))
                .containsExactly(
                        "id",
                        "userId",
                        "name",
                        "description",
                        "sortOrder",
                        "createdAt",
                        "updatedAt",
                        "bankCount")
                .doesNotContain(
                        "success",
                        "message",
                        "code",
                        "requestId",
                        "categories",
                        "url",
                        "viewer",
                        "principal",
                        "identityId");
        assertThat(componentTypes(PersonalBankCategoryView.class))
                .containsExactly(
                        "int",
                        "long",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.Integer",
                        "java.time.LocalDateTime",
                        "java.time.LocalDateTime",
                        "long");
    }

    @Test
    void personalBankModuleContainsNoHttpControllerEnvelopeOrPresentationMapping()
            throws IOException {
        Path personalBankRoot = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath()
                .resolve("src/main/java/io/saksk/ti/personalbank");

        try (var files = Files.walk(personalBankRoot)) {
            for (Path sourceFile : files
                    .filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().endsWith(".java"))
                    .toList()) {
                String source = Files.readString(sourceFile, StandardCharsets.UTF_8);
                assertThat(source)
                        .as("HTTP-neutral personalbank source %s", sourceFile)
                        .doesNotContain(FORBIDDEN_TRANSPORT_FRAGMENTS.toArray(String[]::new));

                String relative = personalBankRoot.relativize(sourceFile)
                        .toString()
                        .replace('\\', '/');
                if (relative.startsWith("api/")
                        || relative.startsWith("application/")
                        || relative.startsWith("domain/")) {
                    assertThat(CHINESE_STRING_LITERAL.matcher(source).find())
                            .as("personalbank boundary has no fixed Chinese display strings: %s", sourceFile)
                            .isFalse();
                }
            }
        }
    }

    private static List<String> componentNames(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(RecordComponent::getName)
                .toList();
    }

    private static List<String> componentTypes(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(component -> component.getGenericType().getTypeName())
                .toList();
    }
}
