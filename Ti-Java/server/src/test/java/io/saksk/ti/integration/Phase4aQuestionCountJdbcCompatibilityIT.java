package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionCountQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.LongStream;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aQuestionCountJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = questionCountFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = questionCountFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void questionCountQueryRemainsCompatibleWithPostgres18() {
        assertQuestionCountCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionCountQueryRemainsCompatibleWithPostgres16() {
        assertQuestionCountCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer questionCountFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/040-subject-catalog-schema.sql"),
                        "/docker-entrypoint-initdb.d/040-subject-catalog-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/041-subject-catalog-seed.sql"),
                        "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/045-question-count-seed.sql"),
                        "/docker-entrypoint-initdb.d/045-question-count-seed.sql");
    }

    private static void assertQuestionCountCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        QuestionCountQueryPort counts = JdbcQuestionCountQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty())))
                .isEqualTo(6);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty())))
                .isEqualTo(4);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(4204),
                Optional.empty(),
                Optional.empty(),
                Optional.empty())))
                .isEqualTo(3);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                Optional.of("算法基础"),
                Optional.of("single_choice"),
                Optional.empty())))
                .isEqualTo(1);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(),
                Optional.of("数据库系统"),
                Optional.of("boolean"),
                Optional.empty())))
                .isEqualTo(1);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(4204),
                Optional.empty(),
                Optional.empty(),
                Optional.of(List.of(4301L, 4304L, 4305L)))))
                .isEqualTo(1);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(List.of(4305L, 4307L)))))
                .isEqualTo(2);
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(List.of(4305L, 4307L)))))
                .isZero();

        List<Long> oneHundredThousandCandidates = LongStream.rangeClosed(1, 100_000)
                .boxed()
                .toList();
        assertThat(counts.countQuestions(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(oneHundredThousandCandidates))))
                .isEqualTo(4);
    }

    private static QuestionCatalogCountQuery query(
            QuestionSubjectAssignmentScope scope,
            Set<Integer> excludedSubjectIds,
            Optional<String> subjectName,
            Optional<String> questionType,
            Optional<List<Long>> candidateQuestionIds
    ) {
        return new QuestionCatalogCountQuery(
                subjectName,
                questionType,
                scope,
                excludedSubjectIds,
                candidateQuestionIds);
    }
}
