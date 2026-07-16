package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.application.port.SubjectCatalogQueryPort;
import io.saksk.ti.catalog.domain.SubjectCatalogEntry;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcSubjectCatalogQueryAdapterTestAccess;
import io.saksk.ti.identity.application.port.SubjectAccessReadPort;
import io.saksk.ti.identity.domain.SubjectAccessState;
import io.saksk.ti.identity.infrastructure.persistence.JdbcSubjectAccessReadAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aSubjectJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = subjectFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = subjectFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void subjectCatalogJdbcQueriesRemainCompatibleWithPostgres18() {
        assertSubjectCatalogCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void subjectCatalogJdbcQueriesRemainCompatibleWithPostgres16() {
        assertSubjectCatalogCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer subjectFixture(PostgreSQLContainer postgres) {
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
                        "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql");
    }

    private static void assertSubjectCatalogCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        SubjectCatalogQueryPort subjectCatalog =
                JdbcSubjectCatalogQueryAdapterTestAccess.create(jdbc);
        SubjectAccessReadPort subjectAccess =
                JdbcSubjectAccessReadAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<SubjectCatalogEntry> unlockedSubjects =
                subjectCatalog.findUnlockedWithQuestionCounts();
        assertThat(unlockedSubjects).containsExactly(
                new SubjectCatalogEntry(4201, "算法基础", 2),
                new SubjectCatalogEntry(4202, "数据库系统", 0),
                new SubjectCatalogEntry(4204, "受限科目", 1));

        SubjectAccessState ordinary = subjectAccess.findByIdentityId(4101).orElseThrow();
        assertThat(ordinary.administrator()).isFalse();
        assertThat(ordinary.restrictedSubjectIds()).containsExactlyInAnyOrder(4204);

        SubjectAccessState administrator = subjectAccess.findByIdentityId(4102).orElseThrow();
        assertThat(administrator.administrator()).isTrue();
        assertThat(administrator.restrictedSubjectIds()).isEmpty();

        assertThat(visibleSubjectIds(unlockedSubjects, ordinary))
                .containsExactly(4201, 4202);
        assertThat(visibleSubjectIds(unlockedSubjects, administrator))
                .containsExactly(4201, 4202, 4204);
    }

    private static List<Integer> visibleSubjectIds(
            List<SubjectCatalogEntry> subjects,
            SubjectAccessState access
    ) {
        return subjects.stream()
                .filter(subject -> access.administrator()
                        || !access.restrictedSubjectIds().contains(subject.id()))
                .map(SubjectCatalogEntry::id)
                .toList();
    }
}
