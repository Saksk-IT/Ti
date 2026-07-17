package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import io.saksk.ti.personalbank.infrastructure.persistence.JdbcPersonalBankOwnedShareQueryAdapterTestAccess;
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
class Phase4bPersonalBankOwnedShareJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = allSharesFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = allSharesFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void runtimeAdapterRemainsCompatibleWithPostgres18() {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void runtimeAdapterRemainsCompatibleWithPostgres16() {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer allSharesFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/063-personal-bank-share-list-seed.sql"),
                        "/docker-entrypoint-initdb.d/063-personal-bank-share-list-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/064-personal-bank-all-shares-seed.sql"),
                        "/docker-entrypoint-initdb.d/064-personal-bank-all-shares-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        PersonalBankOwnedShareQueryPort ownedShares =
                JdbcPersonalBankOwnedShareQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(jdbc.sql("""
                        SELECT udt_name
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'bank_shares'
                          AND column_name = 'owner_id'
                        """)
                .query(String.class)
                .single())
                .isEqualTo("int4");

        long bankCountBefore = tableCount(jdbc, "user_question_banks");
        long shareCountBefore = tableCount(jdbc, "bank_shares");
        List<PersonalBankOwnedShareView> owner = ownedShares.listOwnedShares(7_001L);
        assertRawMappingFilteringAndOrdering(owner);
        assertThatThrownBy(() -> owner.add(owner.getFirst()))
                .isInstanceOf(UnsupportedOperationException.class);

        assertThat(ownedShares.listOwnedShares(7_002L))
                .extracting(PersonalBankOwnedShareView::id)
                .containsExactly(-2, 7_306, 7_205, 7_202);
        assertThat(ownedShares.listOwnedShares((long) Integer.MAX_VALUE + 1L)).isEmpty();
        assertThat(ownedShares.listOwnedShares(0L)).isEmpty();
        assertThat(tableCount(jdbc, "user_question_banks")).isEqualTo(bankCountBefore);
        assertThat(tableCount(jdbc, "bank_shares")).isEqualTo(shareCountBefore);

        assertSingleReadFailureBoundary(jdbc, ownedShares);
    }

    private static void assertRawMappingFilteringAndOrdering(
            List<PersonalBankOwnedShareView> rows
    ) {
        assertThat(rows).hasSize(8);
        assertThat(rows.getFirst()).satisfies(row -> {
            assertThat(row.id()).isEqualTo(7_300);
            assertThat(row.bankId()).isEqualTo(7_101);
            assertThat(row.ownerId()).isEqualTo(7_001L);
            assertThat(row.shareCode()).isNull();
            assertThat(row.shareToken()).isNull();
            assertThat(row.permission()).isNull();
            assertThat(row.expiresAt()).isNull();
            assertThat(row.maxUses()).isNull();
            assertThat(row.currentUses()).isNull();
            assertThat(row.isActive()).isNull();
            assertThat(row.createdAt()).isNull();
            assertThat(row.bankName()).isEqualTo("owner bank 高数・α／🧪");
        });
        assertThat(rows.subList(1, 5)).extracting(PersonalBankOwnedShareView::id)
                .containsExactly(7_304, 7_305, 0, 7_201);
        assertThat(rows.subList(5, 7)).extracting(PersonalBankOwnedShareView::id)
                .containsExactlyInAnyOrder(7_203, 7_204);
        assertThat(rows.getLast().id()).isEqualTo(7_206);
        assertThat(rows).extracting(PersonalBankOwnedShareView::id)
                .doesNotContain(7_301, 7_302, 7_303, 7_306);

        PersonalBankOwnedShareView crossBankOwner = byId(rows, 7_304);
        assertThat(crossBankOwner.bankName()).isEqualTo("other owner bank");
        assertThat(crossBankOwner.isActive()).isFalse();
        assertThat(crossBankOwner.expiresAt())
                .isEqualTo(LocalDateTime.of(2020, 1, 1, 0, 0));
        assertThat(crossBankOwner.currentUses()).isEqualTo(99);

        PersonalBankOwnedShareView malformed = byId(rows, 7_305);
        assertThat(malformed.shareCode()).isEmpty();
        assertThat(malformed.shareToken()).isEmpty();
        assertThat(malformed.permission()).isEmpty();
        assertThat(malformed.maxUses()).isEqualTo(-1);
        assertThat(malformed.currentUses()).isEqualTo(-2);
    }

    private static PersonalBankOwnedShareView byId(
            List<PersonalBankOwnedShareView> rows,
            int id
    ) {
        return rows.stream().filter(row -> row.id() == id).findFirst().orElseThrow();
    }

    private static long tableCount(JdbcClient jdbc, String table) {
        return jdbc.sql("SELECT COUNT(*) FROM " + table).query(Long.class).single();
    }

    private static void assertSingleReadFailureBoundary(
            JdbcClient jdbc,
            PersonalBankOwnedShareQueryPort ownedShares
    ) {
        jdbc.sql("ALTER TABLE bank_shares RENAME TO bank_shares_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> ownedShares.listOwnedShares(7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE bank_shares_temporarily_unavailable RENAME TO bank_shares")
                    .update();
        }

        jdbc.sql("ALTER TABLE user_question_banks "
                        + "RENAME TO user_question_banks_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> ownedShares.listOwnedShares(7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE user_question_banks_temporarily_unavailable "
                            + "RENAME TO user_question_banks")
                    .update();
        }
    }
}
