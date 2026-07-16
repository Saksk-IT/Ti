package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionTypeQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aQuestionTypeJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = questionTypeFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = questionTypeFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void questionTypeQueryRemainsCompatibleWithPostgres18() {
        assertQuestionTypeCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionTypeQueryRemainsCompatibleWithPostgres16() {
        assertQuestionTypeCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer questionTypeFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/044-question-type-seed.sql"),
                        "/docker-entrypoint-initdb.d/044-question-type-seed.sql");
    }

    private static void assertQuestionTypeCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        QuestionTypeQueryPort questionTypes =
                JdbcQuestionTypeQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(questionTypes.findDistinctQuestionTypes()).containsExactlyInAnyOrder(
                "", "  ", "boolean", "single_choice", "判断题", "简答题");
    }
}
