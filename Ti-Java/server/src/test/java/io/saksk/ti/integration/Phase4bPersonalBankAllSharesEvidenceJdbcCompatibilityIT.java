package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankAllSharesEvidenceSql;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.ResultSet;
import java.sql.SQLException;
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
class Phase4bPersonalBankAllSharesEvidenceJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = allSharesFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = allSharesFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void evidenceQueryRemainsCompatibleWithPostgres18() {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void evidenceQueryRemainsCompatibleWithPostgres16() {
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
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:viewer_id) AS text)")
                .param("viewer_id", 7_001L)
                .query(String.class)
                .single())
                .isEqualTo("bigint");

        List<EvidenceAllShareRow> owner = allShares(jdbc, 7_001L);
        assertPostgresOrderingFilteringAndRawMapping(owner);

        List<EvidenceAllShareRow> legacy = legacyAllShares(jdbc, 7_001L);
        assertThat(legacy).extracting(EvidenceAllShareRow::id)
                .containsExactlyInAnyOrderElementsOf(
                        owner.stream().map(EvidenceAllShareRow::id).toList());
        assertThat(legacy).extracting(EvidenceAllShareRow::createdAt)
                .containsExactlyElementsOf(owner.stream()
                        .map(EvidenceAllShareRow::createdAt).toList());

        assertThat(allShares(jdbc, 7_002L)).extracting(EvidenceAllShareRow::id)
                .containsExactly(-2, 7_306, 7_205, 7_202);
        assertThat(allShares(jdbc, (long) Integer.MAX_VALUE + 1L)).isEmpty();
        assertThat(allShares(jdbc, 0L)).isEmpty();

        assertSingleReadFailureBoundary(jdbc);
    }

    private static void assertPostgresOrderingFilteringAndRawMapping(
            List<EvidenceAllShareRow> rows
    ) {
        assertThat(rows).hasSize(8);
        assertThat(rows.getFirst()).satisfies(row -> {
            assertThat(row.id()).isEqualTo(7_300);
            assertThat(row.bankId()).isEqualTo(7_101);
            assertThat(row.ownerId()).isEqualTo(7_001);
            assertThat(row.shareCode()).isNull();
            assertThat(row.shareToken()).isNull();
            assertThat(row.permission()).isNull();
            assertThat(row.expiresAt()).isNull();
            assertThat(row.maxUses()).isNull();
            assertThat(row.currentUses()).isNull();
            assertThat(row.active()).isNull();
            assertThat(row.createdAt()).isNull();
            assertThat(row.bankName()).isEqualTo("owner bank 高数・α／🧪");
        });
        assertThat(rows.subList(1, 5)).extracting(EvidenceAllShareRow::id)
                .containsExactly(7_304, 7_305, 0, 7_201);
        assertThat(rows.subList(5, 7)).extracting(EvidenceAllShareRow::id)
                .containsExactlyInAnyOrder(7_203, 7_204);
        assertThat(rows.get(7).id()).isEqualTo(7_206);
        assertThat(rows).extracting(EvidenceAllShareRow::id)
                .doesNotContain(7_301, 7_302, 7_303, 7_306);

        EvidenceAllShareRow crossBankOwner = byId(rows, 7_304);
        assertThat(crossBankOwner.bankName()).isEqualTo("other owner bank");
        assertThat(crossBankOwner.active()).isFalse();
        assertThat(crossBankOwner.expiresAt())
                .isEqualTo(LocalDateTime.of(2020, 1, 1, 0, 0));
        assertThat(crossBankOwner.currentUses()).isEqualTo(99);

        EvidenceAllShareRow malformed = byId(rows, 7_305);
        assertThat(malformed.shareCode()).isEmpty();
        assertThat(malformed.shareToken()).isEmpty();
        assertThat(malformed.permission()).isEmpty();
        assertThat(malformed.maxUses()).isEqualTo(-1);
        assertThat(malformed.currentUses()).isEqualTo(-2);
    }

    private static EvidenceAllShareRow byId(List<EvidenceAllShareRow> rows, int id) {
        return rows.stream().filter(row -> row.id() == id).findFirst().orElseThrow();
    }

    private static void assertSingleReadFailureBoundary(JdbcClient jdbc) {
        jdbc.sql("ALTER TABLE bank_shares RENAME TO bank_shares_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> allShares(jdbc, 7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE bank_shares_temporarily_unavailable RENAME TO bank_shares")
                    .update();
        }

        jdbc.sql("ALTER TABLE user_question_banks "
                        + "RENAME TO user_question_banks_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> allShares(jdbc, 7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE user_question_banks_temporarily_unavailable "
                            + "RENAME TO user_question_banks")
                    .update();
        }
    }

    private static List<EvidenceAllShareRow> allShares(JdbcClient jdbc, long viewerId) {
        return jdbc.sql(PersonalBankAllSharesEvidenceSql.ALL_SHARES)
                .param("viewer_id", viewerId)
                .query(Phase4bPersonalBankAllSharesEvidenceJdbcCompatibilityIT::mapShare)
                .list();
    }

    private static List<EvidenceAllShareRow> legacyAllShares(JdbcClient jdbc, long viewerId) {
        return jdbc.sql(PersonalBankAllSharesEvidenceSql.LEGACY_ALL_SHARES)
                .param("uid", viewerId)
                .query(Phase4bPersonalBankAllSharesEvidenceJdbcCompatibilityIT::mapShare)
                .list();
    }

    private static EvidenceAllShareRow mapShare(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new EvidenceAllShareRow(
                resultSet.getInt("id"),
                resultSet.getInt("bank_id"),
                resultSet.getInt("owner_id"),
                resultSet.getString("share_code"),
                resultSet.getString("share_token"),
                resultSet.getString("permission"),
                resultSet.getObject("expires_at", LocalDateTime.class),
                resultSet.getObject("max_uses", Integer.class),
                resultSet.getObject("current_uses", Integer.class),
                resultSet.getObject("is_active", Boolean.class),
                resultSet.getObject("created_at", LocalDateTime.class),
                resultSet.getString("bank_name"));
    }

    private record EvidenceAllShareRow(
            int id,
            int bankId,
            int ownerId,
            String shareCode,
            String shareToken,
            String permission,
            LocalDateTime expiresAt,
            Integer maxUses,
            Integer currentUses,
            Boolean active,
            LocalDateTime createdAt,
            String bankName
    ) {
    }
}
