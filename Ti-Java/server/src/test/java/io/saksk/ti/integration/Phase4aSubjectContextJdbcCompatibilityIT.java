package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.application.port.SubjectContextQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcSubjectContextQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aSubjectContextJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = subjectContextFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = subjectContextFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void subjectContextQueryRemainsCompatibleWithPostgres18() {
        assertSubjectContextCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void subjectContextQueryRemainsCompatibleWithPostgres16() {
        assertSubjectContextCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer subjectContextFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/049-subject-context-seed.sql"),
                        "/docker-entrypoint-initdb.d/049-subject-context-seed.sql");
    }

    private static void assertSubjectContextCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        SubjectContextQueryPort subjects = JdbcSubjectContextQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        assertThat(subjects.findSubjectById(Integer.MIN_VALUE))
                .contains(new SubjectContextView(Integer.MIN_VALUE, ""));
        assertThat(subjects.findSubjectById(0L))
                .contains(new SubjectContextView(0, "  "));
        assertThat(subjects.findSubjectById(4901L))
                .contains(new SubjectContextView(
                        4901, "科目 🧪 <strong>raw</strong>"));
        assertThat(subjects.findSubjectById(Integer.MAX_VALUE))
                .contains(new SubjectContextView(
                        Integer.MAX_VALUE, "Maximum signed subject ID"));
        assertThat(subjects.findSubjectById(4903L)).isEmpty();
        assertThat(subjects.findSubjectById(Long.MAX_VALUE)).isEmpty();

        assertThat(jdbc.sql("SELECT COUNT(*) FROM subjects")
                .query(Long.class)
                .single()).isEqualTo(5);
        assertThat(jdbc.sql("SELECT is_locked FROM subjects WHERE id = 4901")
                .query(Boolean.class)
                .single()).isTrue();

        jdbc.sql("ALTER TABLE subjects RENAME TO subjects_temporarily_unavailable").update();
        try {
            assertThatThrownBy(() -> subjects.findSubjectById(0L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE subjects_temporarily_unavailable RENAME TO subjects").update();
        }
    }
}
