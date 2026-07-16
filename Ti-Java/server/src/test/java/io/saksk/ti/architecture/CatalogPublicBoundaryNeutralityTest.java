package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
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

class CatalogPublicBoundaryNeutralityTest {

    private static final List<String> FORBIDDEN_BOUNDARY_FRAGMENTS = List.of(
            "detailUrl",
            "practiceUrl",
            "sourceLabel",
            "databaseValue",
            "displayLabel",
            "fromDatabaseValue",
            "source_type",
            "detail_url",
            "practice_url",
            "source_label",
            "\"system\"",
            "\"user_public\"",
            "http://",
            "https://",
            "\"/");
    private static final Pattern CHINESE_STRING_LITERAL =
            Pattern.compile("\"[^\"\\n]*\\p{IsHan}[^\"\\n]*\"");

    @Test
    void publicBankCardViewDoesNotExposeLegacyUrlsOrPresentationLabels() {
        assertThat(Arrays.stream(PublicBankCardView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .doesNotContain("detailUrl", "practiceUrl", "sourceLabel")
                .noneMatch(name -> name.toLowerCase(java.util.Locale.ROOT).contains("url"));
    }

    @Test
    void publicBankSourceIsOnlyAClosedBusinessClassification() {
        assertThat(PublicBankSource.values())
                .containsExactly(PublicBankSource.SYSTEM, PublicBankSource.USER_PUBLIC);
        assertThat(Arrays.stream(PublicBankSource.class.getDeclaredFields())
                        .filter(field -> !field.isSynthetic())
                        .filter(field -> !field.isEnumConstant()))
                .isEmpty();
        assertThat(Arrays.stream(PublicBankSource.class.getDeclaredMethods())
                        .filter(method -> Modifier.isPublic(method.getModifiers()))
                        .map(java.lang.reflect.Method::getName))
                .containsExactlyInAnyOrder("values", "valueOf");
    }

    @Test
    void questionCountBoundaryExposesOnlyCatalogCriteria() {
        assertThat(Arrays.stream(QuestionCatalogCountQuery.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly(
                        "subjectName",
                        "questionType",
                        "subjectAssignmentScope",
                        "excludedSubjectIds",
                        "candidateQuestionIds")
                .doesNotContain("mode", "source", "tag", "userId", "favorites", "mistakes");
        assertThat(QuestionSubjectAssignmentScope.values()).containsExactly(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT);
    }

    @Test
    void questionDetailBoundaryExposesOnlyRawCatalogFacts() {
        assertThat(Arrays.stream(QuestionCatalogRecordView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly(
                        "id",
                        "subjectId",
                        "type",
                        "content",
                        "optionsRaw",
                        "answerRaw",
                        "analysis",
                        "tagsRaw",
                        "difficulty",
                        "imagePathRaw",
                        "source",
                        "createdBy",
                        "updatedBy",
                        "createdAt",
                        "updatedAt")
                .doesNotContain(
                        "qType",
                        "explanation",
                        "portableOptions",
                        "questionImageGroups",
                        "username",
                        "owner");
    }

    @Test
    void questionSummaryBoundaryExposesOnlyRawCatalogFiltersAndFacts() {
        assertThat(Arrays.stream(QuestionCatalogListQuery.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly("subjectId", "questionType")
                .doesNotContain("subjectName", "mode", "source", "tag", "username", "userId");
        assertThat(Arrays.stream(QuestionCatalogSummaryView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly(
                        "id",
                        "subjectId",
                        "type",
                        "content",
                        "difficulty",
                        "tagsRaw",
                        "imagePathRaw",
                        "createdBy",
                        "updatedAt")
                .doesNotContain(
                        "qType",
                        "portableType",
                        "portableContent",
                        "username",
                        "createdByUsername",
                        "owner");
    }

    @Test
    void questionExportBoundaryExposesOnlyTypedCatalogCriteriaAndRawFacts() {
        assertThat(Arrays.stream(QuestionExportQuery.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly("subjectId")
                .doesNotContain("rawSubjectId", "request", "meta", "status", "userId");
        assertThat(Arrays.stream(QuestionExportRecordView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly(
                        "id",
                        "subjectId",
                        "subjectName",
                        "type",
                        "content",
                        "optionsRaw",
                        "answerRaw",
                        "analysis",
                        "difficulty",
                        "tagsRaw")
                .doesNotContain(
                        "defaultSubjectName",
                        "portableOptions",
                        "projectedAnswer",
                        "message",
                        "requestId");
    }

    @Test
    void subjectInventoryBoundaryExposesOnlyRawCatalogFacts() {
        assertThat(Arrays.stream(SubjectInventorySummaryView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly("id", "name", "isLocked", "questionCount")
                .doesNotContain(
                        "visible",
                        "restricted",
                        "restrictedSubjectIds",
                        "viewerId",
                        "detailUrl");
    }

    @Test
    void subjectContextBoundaryExposesOnlyRawCatalogFacts() {
        assertThat(Arrays.stream(SubjectContextView.class.getRecordComponents())
                        .map(RecordComponent::getName))
                .containsExactly("id", "name")
                .doesNotContain(
                        "description",
                        "isLocked",
                        "questionCount",
                        "visible",
                        "restricted",
                        "viewerId",
                        "detailUrl");
    }

    @Test
    void catalogApiDomainApplicationAndPortsContainNoTransportPersistenceOrLegacyPresentationMapping()
            throws IOException {
        Path catalogRoot = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath()
                .resolve("src/main/java/io/saksk/ti/catalog");

        for (String boundary : List.of("api", "domain", "application")) {
            Path boundaryRoot = catalogRoot.resolve(boundary);
            try (var files = Files.walk(boundaryRoot)) {
                for (Path sourceFile : files
                        .filter(Files::isRegularFile)
                        .filter(path -> path.getFileName().toString().endsWith(".java"))
                        .toList()) {
                    String source = Files.readString(sourceFile, StandardCharsets.UTF_8);
                    assertThat(source)
                            .as("neutral catalog boundary source %s", sourceFile)
                            .doesNotContain(FORBIDDEN_BOUNDARY_FRAGMENTS.toArray(String[]::new));
                    assertThat(CHINESE_STRING_LITERAL.matcher(source).find())
                            .as("catalog boundary has no fixed Chinese display strings: %s", sourceFile)
                            .isFalse();
                }
            }
        }
    }
}
