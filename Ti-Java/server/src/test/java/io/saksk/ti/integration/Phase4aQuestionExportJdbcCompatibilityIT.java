package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import io.saksk.ti.catalog.application.port.QuestionExportQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionExportQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
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
class Phase4aQuestionExportJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = questionExportFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = questionExportFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void questionExportQueriesRemainCompatibleWithPostgres18() {
        assertQuestionExportCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionExportQueriesRemainCompatibleWithPostgres16() {
        assertQuestionExportCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer questionExportFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/050-question-export-seed.sql"),
                        "/docker-entrypoint-initdb.d/050-question-export-seed.sql");
    }

    private static void assertQuestionExportCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        QuestionExportQueryPort questions =
                JdbcQuestionExportQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<QuestionExportRecordView> all = questions.listQuestionExportRecords(
                query(Optional.empty()));
        assertThat(all).extracting(QuestionExportRecordView::id)
                .containsExactly(-1L, 0L, 5004L, 5005L, 5006L, 5007L, 5008L, 5009L);

        QuestionExportRecordView nullable = all.get(1);
        assertThat(nullable.subjectId()).isNull();
        assertThat(nullable.subjectName()).isNull();
        assertThat(nullable.type()).isNull();
        assertThat(nullable.content()).isNull();
        assertThat(nullable.optionsRaw()).isNull();
        assertThat(nullable.answerRaw()).isNull();
        assertThat(nullable.analysis()).isNull();
        assertThat(nullable.difficulty()).isNull();
        assertThat(nullable.tagsRaw()).isNull();

        QuestionExportRecordView malformed = all.get(2);
        assertThat(malformed.subjectId()).isEqualTo(-7L);
        assertThat(malformed.subjectName())
                .isEqualTo("Question export negative subject fixture");
        assertThat(malformed.type()).isEmpty();
        assertThat(malformed.optionsRaw()).isEqualTo("{not-json-options");
        assertThat(malformed.answerRaw()).isEqualTo("true");
        assertThat(malformed.analysis()).isEmpty();
        assertThat(malformed.difficulty()).isZero();
        assertThat(malformed.tagsRaw()).isEqualTo("42");

        QuestionExportRecordView emptySubjectName = all.get(4);
        assertThat(emptySubjectName.subjectId()).isEqualTo(5001L);
        assertThat(emptySubjectName.subjectName()).isEmpty();
        assertThat(emptySubjectName.optionsRaw()).isEmpty();
        assertThat(emptySubjectName.answerRaw()).isEqualTo("  ");

        QuestionExportRecordView orphanSubject = all.getLast();
        assertThat(orphanSubject.id()).isEqualTo(5009L);
        assertThat(orphanSubject.subjectId()).isEqualTo(5999L);
        assertThat(orphanSubject.subjectName()).isNull();
        assertThat(orphanSubject.type()).isEqualTo("orphan_subject");
        assertThat(orphanSubject.content())
                .isEqualTo("Missing subject join target remains a raw export fact");
        assertThat(orphanSubject.optionsRaw()).isEqualTo("[\"orphan\"]");
        assertThat(orphanSubject.answerRaw()).isEqualTo("\"orphan-answer\"");
        assertThat(orphanSubject.analysis()).isEqualTo("orphan-analysis");
        assertThat(orphanSubject.difficulty()).isEqualTo(-3);
        assertThat(orphanSubject.tagsRaw()).isEqualTo("[\"orphan-subject\"]");

        assertThat(questions.listQuestionExportRecords(query(Optional.of(5002))))
                .extracting(QuestionExportRecordView::id)
                .containsExactly(5007L, 5008L);
        assertThat(questions.listQuestionExportRecords(query(Optional.of(-7))))
                .extracting(QuestionExportRecordView::id)
                .containsExactly(5004L);
        assertThat(questions.listQuestionExportRecords(query(Optional.of(0))))
                .extracting(QuestionExportRecordView::id)
                .containsExactly(5005L);
        assertThat(questions.listQuestionExportRecords(query(Optional.of(Integer.MIN_VALUE))))
                .isEmpty();
        assertThat(questions.listQuestionExportRecords(query(Optional.of(Integer.MAX_VALUE))))
                .isEmpty();
        assertThat(jdbc.sql("SELECT is_locked FROM subjects WHERE id = 5003")
                .query(Boolean.class)
                .single())
                .isTrue();
        assertThat(questions.listQuestionExportRecords(query(Optional.of(5003))))
                .extracting(QuestionExportRecordView::id)
                .containsExactly(-1L);
        assertThat(questions.listQuestionExportRecords(query(Optional.of(5999))))
                .singleElement()
                .isEqualTo(orphanSubject);

        jdbc.sql("ALTER TABLE questions RENAME TO questions_temporarily_unavailable").update();
        try {
            assertThatThrownBy(() -> questions.listQuestionExportRecords(query(Optional.empty())))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE questions_temporarily_unavailable RENAME TO questions").update();
        }
    }

    private static QuestionExportQuery query(Optional<Integer> subjectId) {
        return new QuestionExportQuery(subjectId);
    }
}
