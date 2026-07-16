package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.infrastructure.persistence.JdbcPersonalBankCategoryQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.LocalDateTime;
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
class Phase4bPersonalBankCategoryJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = categoryFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = categoryFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void categoryListRemainsCompatibleWithPostgres18() {
        assertCategoryCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void categoryListRemainsCompatibleWithPostgres16() {
        assertCategoryCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer categoryFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/060-personal-bank-category-schema.sql"),
                        "/docker-entrypoint-initdb.d/060-personal-bank-category-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/061-personal-bank-category-seed.sql"),
                        "/docker-entrypoint-initdb.d/061-personal-bank-category-seed.sql");
    }

    private static void assertCategoryCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        PersonalBankCategoryQueryPort categories =
                JdbcPersonalBankCategoryQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<PersonalBankCategoryView> owner = categories.listCategories(6001L);
        assertThat(owner).extracting(PersonalBankCategoryView::id)
                .containsExactly(-1, 0, 6101, 6102);
        assertThat(owner).extracting(PersonalBankCategoryView::bankCount)
                .containsExactly(2L, 1L, 0L, 1L);

        PersonalBankCategoryView negative = owner.getFirst();
        assertThat(negative.userId()).isEqualTo(6001L);
        assertThat(negative.name()).isEqualTo("Negative category");
        assertThat(negative.description()).isEqualTo("signed category identifier");
        assertThat(negative.sortOrder()).isEqualTo(-5);
        assertThat(negative.createdAt()).isEqualTo(LocalDateTime.of(2026, 7, 17, 8, 0));
        assertThat(negative.updatedAt()).isEqualTo(LocalDateTime.of(2026, 7, 17, 9, 0));

        PersonalBankCategoryView zero = owner.get(1);
        assertThat(zero.id()).isZero();
        assertThat(zero.name()).isEmpty();
        assertThat(zero.description()).isEmpty();
        assertThat(zero.sortOrder()).isZero();

        PersonalBankCategoryView unicode = owner.get(2);
        assertThat(unicode.name()).isEqualTo("高数・α／🧪");
        assertThat(unicode.description()).isEqualTo("Unicode 描述");
        assertThat(unicode.sortOrder()).isZero();

        PersonalBankCategoryView nullable = owner.getLast();
        assertThat(nullable.id()).isEqualTo(6102);
        assertThat(nullable.description()).isNull();
        assertThat(nullable.sortOrder()).isNull();
        assertThat(nullable.createdAt()).isNull();
        assertThat(nullable.updatedAt()).isNull();

        assertThat(categories.listCategories(6002L))
                .singleElement()
                .satisfies(category -> {
                    assertThat(category.id()).isEqualTo(6103);
                    assertThat(category.userId()).isEqualTo(6002L);
                    assertThat(category.bankCount()).isOne();
                });
        assertThat(categories.listCategories(9999L)).isEmpty();

        assertThat(jdbc.sql("SELECT COUNT(*) FROM user_question_banks "
                        + "WHERE category_id = -1 AND status = 1")
                .query(Long.class).single()).isEqualTo(2L);
        assertThat(jdbc.sql("SELECT COUNT(*) FROM user_question_banks "
                        + "WHERE category_id = -1 AND status = 1 AND user_id <> 6001")
                .query(Long.class).single()).isEqualTo(1L);
        assertThat(jdbc.sql("SELECT COUNT(*) FROM user_question_banks "
                        + "WHERE category_id = 6101 AND status IS DISTINCT FROM 1")
                .query(Long.class).single()).isEqualTo(3L);

        jdbc.sql("ALTER TABLE user_question_banks "
                + "RENAME TO user_question_banks_temporarily_unavailable").update();
        try {
            assertThatThrownBy(() -> categories.listCategories(6001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE user_question_banks_temporarily_unavailable "
                    + "RENAME TO user_question_banks").update();
        }
    }
}
