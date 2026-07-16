package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcSubjectInventoryQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aSubjectInventoryJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = subjectInventoryFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = subjectInventoryFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void subjectInventoryQueryRemainsCompatibleWithPostgres18() {
        assertSubjectInventoryCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void subjectInventoryQueryRemainsCompatibleWithPostgres16() {
        assertSubjectInventoryCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer subjectInventoryFixture(PostgreSQLContainer postgres) {
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
                                "db/phase4a/048-subject-inventory-seed.sql"),
                        "/docker-entrypoint-initdb.d/048-subject-inventory-seed.sql");
    }

    private static void assertSubjectInventoryCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        SubjectInventoryQueryPort subjectInventory =
                JdbcSubjectInventoryQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<SubjectInventorySummaryView> rows =
                subjectInventory.listSubjectInventorySummaries();
        assertThat(rows).containsExactly(
                new SubjectInventorySummaryView(Integer.MIN_VALUE, "", null, 1),
                new SubjectInventorySummaryView(-7, "科目 🧪", true, 2),
                new SubjectInventorySummaryView(0, "  ", false, 0),
                new SubjectInventorySummaryView(7, "Unlocked subject", false, 1),
                new SubjectInventorySummaryView(
                        Integer.MAX_VALUE, "Maximum signed subject ID", true, 0));

        jdbc.sql("ALTER TABLE subjects RENAME TO subjects_temporarily_unavailable").update();
        try {
            assertThatThrownBy(subjectInventory::listSubjectInventorySummaries)
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE subjects_temporarily_unavailable RENAME TO subjects").update();
        }
    }
}
