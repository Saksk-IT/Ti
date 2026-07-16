package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.application.port.QuestionDetailQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionDetailQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aQuestionDetailJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = questionDetailFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = questionDetailFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void questionDetailQueryRemainsCompatibleWithPostgres18() {
        assertQuestionDetailCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionDetailQueryRemainsCompatibleWithPostgres16() {
        assertQuestionDetailCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer questionDetailFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/046-question-detail-seed.sql"),
                        "/docker-entrypoint-initdb.d/046-question-detail-seed.sql");
    }

    private static void assertQuestionDetailCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        QuestionDetailQueryPort questions =
                JdbcQuestionDetailQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        QuestionCatalogRecordView complete = questions.findQuestionById(4601L).orElseThrow();
        assertThat(complete.id()).isEqualTo(4601L);
        assertThat(complete.subjectId()).isEqualTo(4501L);
        assertThat(complete.type()).isEqualTo("multiple_choice");
        assertThat(complete.content()).isEqualTo("Complete fifteen-column question");
        assertThat(complete.optionsRaw()).isEqualTo("[\"A\",\"B\"]");
        assertThat(complete.answerRaw()).isEqualTo("[\"A\"]");
        assertThat(complete.analysis()).isEqualTo("Complete analysis");
        assertThat(complete.tagsRaw()).isEqualTo("[\"catalog\",\"detail\"]");
        assertThat(complete.difficulty()).isEqualTo(4);
        assertThat(complete.imagePathRaw())
                .isEqualTo("{\"content\":[\"question.png\"],\"answer\":[],\"explanation\":[]}");
        assertThat(complete.source()).isEqualTo("phase4a-public-fixture");
        assertThat(complete.createdBy()).isEqualTo(900000001L);
        assertThat(complete.updatedBy()).isEqualTo(900000002L);
        assertThat(complete.createdAt()).isEqualTo(LocalDateTime.of(2026, 7, 16, 1, 2, 3));
        assertThat(complete.updatedAt()).isEqualTo(LocalDateTime.of(2026, 7, 16, 4, 5, 6));

        QuestionCatalogRecordView nullable = questions.findQuestionById(4602L).orElseThrow();
        assertThat(nullable.id()).isEqualTo(4602L);
        assertThat(nullable.type()).isEqualTo("essay");
        assertThat(nullable.content()).isEqualTo("Nullable column question");
        assertThat(nullable.subjectId()).isNull();
        assertThat(nullable.optionsRaw()).isNull();
        assertThat(nullable.answerRaw()).isNull();
        assertThat(nullable.analysis()).isNull();
        assertThat(nullable.tagsRaw()).isNull();
        assertThat(nullable.difficulty()).isNull();
        assertThat(nullable.imagePathRaw()).isNull();
        assertThat(nullable.source()).isNull();
        assertThat(nullable.createdBy()).isNull();
        assertThat(nullable.updatedBy()).isNull();
        assertThat(nullable.createdAt()).isNull();
        assertThat(nullable.updatedAt()).isNull();

        QuestionCatalogRecordView malformed = questions.findQuestionById(4603L).orElseThrow();
        assertThat(malformed.optionsRaw()).isEqualTo("{not-json-options");
        assertThat(malformed.answerRaw()).isEqualTo("[not-json-answer");
        assertThat(malformed.tagsRaw()).isEqualTo("not-json-tags]");
        assertThat(malformed.imagePathRaw()).isEqualTo("{not-json-image-path");

        QuestionCatalogRecordView zero = questions.findQuestionById(0L).orElseThrow();
        assertThat(zero.id()).isZero();
        assertThat(zero.content()).isEqualTo("Legacy zero-id question");
        assertThat(zero.difficulty()).isZero();
        assertThat(questions.findQuestionById(4699L)).isEmpty();
        assertThat(questions.findQuestionById(Long.MAX_VALUE)).isEmpty();

        assertThat(jdbc.sql("SELECT COUNT(*) FROM questions WHERE id = 4601")
                .query(Long.class)
                .single()).isOne();
    }
}
