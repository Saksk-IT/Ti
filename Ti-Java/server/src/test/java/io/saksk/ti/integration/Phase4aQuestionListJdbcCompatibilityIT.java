package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import io.saksk.ti.catalog.application.port.QuestionSummaryQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionSummaryQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aQuestionListJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = questionListFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = questionListFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void questionListQueriesRemainCompatibleWithPostgres18() {
        assertQuestionListCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionListQueriesRemainCompatibleWithPostgres16() {
        assertQuestionListCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer questionListFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/047-question-list-seed.sql"),
                        "/docker-entrypoint-initdb.d/047-question-list-seed.sql");
    }

    private static void assertQuestionListCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        QuestionSummaryQueryPort questions =
                JdbcQuestionSummaryQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<QuestionCatalogSummaryView> all = questions.listQuestionSummaries(
                query(Optional.empty(), Optional.empty()));
        assertThat(all).extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4709L, 4708L, 4707L, 4706L, 4705L, 4704L, 0L, -1L);

        assertThat(questions.listQuestionSummaries(
                query(Optional.of(4701), Optional.empty())))
                .extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4709L, 4708L, 0L);
        assertThat(questions.listQuestionSummaries(
                query(Optional.empty(), Optional.of("single_choice"))))
                .extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4709L, 4707L, 0L);
        assertThat(questions.listQuestionSummaries(
                query(Optional.of(4701), Optional.of("single_choice"))))
                .extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4709L, 0L);

        QuestionCatalogSummaryView malformed = all.getFirst();
        assertThat(malformed.subjectId()).isEqualTo(4701L);
        assertThat(malformed.type()).isEqualTo("single_choice");
        assertThat(malformed.content()).isEqualTo("Malformed raw summary text remains untouched");
        assertThat(malformed.difficulty()).isEqualTo(5);
        assertThat(malformed.tagsRaw()).isEqualTo("{not-json-tags");
        assertThat(malformed.imagePathRaw()).isEqualTo("[not-json-image");
        assertThat(malformed.createdBy()).isEqualTo(900000009L);
        assertThat(malformed.updatedAt())
                .isEqualTo(LocalDateTime.of(2026, 7, 16, 9, 10, 11));

        QuestionCatalogSummaryView nullable = all.get(1);
        assertThat(nullable.id()).isEqualTo(4708L);
        assertThat(nullable.subjectId()).isEqualTo(4701L);
        assertThat(nullable.type()).isEqualTo("essay");
        assertThat(nullable.content()).isEqualTo("Nullable summary columns remain null");
        assertThat(nullable.difficulty()).isNull();
        assertThat(nullable.tagsRaw()).isNull();
        assertThat(nullable.imagePathRaw()).isNull();
        assertThat(nullable.createdBy()).isNull();
        assertThat(nullable.updatedAt()).isNull();

        QuestionCatalogSummaryView zeroId = all.get(all.size() - 2);
        assertThat(zeroId.id()).isZero();
        assertThat(zeroId.content()).isEqualTo("Legacy zero-ID list row");

        QuestionCatalogSummaryView negativeId = all.getLast();
        assertThat(negativeId.id()).isEqualTo(-1L);
        assertThat(negativeId.content())
                .isEqualTo("Legacy negative question ID remains a raw database fact");

        assertThat(questions.listQuestionSummaries(
                query(Optional.of(0), Optional.empty())))
                .extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4705L);
        assertThat(questions.listQuestionSummaries(
                query(Optional.of(-7), Optional.empty())))
                .extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4704L);
        List<QuestionCatalogSummaryView> emptyType = questions.listQuestionSummaries(
                query(Optional.empty(), Optional.of("")));
        assertThat(emptyType).extracting(QuestionCatalogSummaryView::id)
                .containsExactly(4706L);
        assertThat(emptyType.getFirst().tagsRaw()).isEmpty();
        assertThat(emptyType.getFirst().imagePathRaw()).isEqualTo("  ");

        assertThat(questions.listQuestionSummaries(
                query(Optional.of(Integer.MAX_VALUE), Optional.empty())))
                .isEmpty();
        assertThat(questions.listQuestionSummaries(
                query(Optional.empty(), Optional.of("missing-type"))))
                .isEmpty();
        assertThat(questions.listQuestionSummaries(
                query(Optional.of(4702), Optional.of("essay"))))
                .isEmpty();

        jdbc.sql("ALTER TABLE questions RENAME TO questions_temporarily_unavailable").update();
        try {
            assertThatThrownBy(() -> questions.listQuestionSummaries(
                    query(Optional.empty(), Optional.empty())))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE questions_temporarily_unavailable RENAME TO questions").update();
        }
    }

    private static QuestionCatalogListQuery query(
            Optional<Integer> subjectId,
            Optional<String> questionType
    ) {
        return new QuestionCatalogListQuery(subjectId, questionType);
    }
}
