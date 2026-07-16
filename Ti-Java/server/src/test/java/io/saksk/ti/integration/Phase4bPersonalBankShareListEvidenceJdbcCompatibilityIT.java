package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankShareListEvidenceSql;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4bPersonalBankShareListEvidenceJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = shareFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = shareFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres18() {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres16() {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer shareFixture(PostgreSQLContainer postgres) {
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
                        "/docker-entrypoint-initdb.d/063-personal-bank-share-list-seed.sql");
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
                          AND table_name = 'user_question_banks'
                          AND column_name = 'user_id'
                        """)
                .query(String.class)
                .single())
                .isEqualTo("int4");
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:viewer_id) AS text)")
                .param("viewer_id", 7_001L)
                .query(String.class)
                .single())
                .isEqualTo("bigint");

        EvidenceRead owner = readShares(jdbc, 7_101, 7_001L);
        assertThat(owner.available()).isTrue();
        assertPostgresOrderingAndRawMapping(owner.shares());

        List<EvidenceShareRow> legacy = legacyShares(jdbc, 7_101);
        assertThat(legacy).extracting(EvidenceShareRow::id)
                .containsExactlyInAnyOrderElementsOf(
                        owner.shares().stream().map(EvidenceShareRow::id).toList());
        assertThat(legacy.getFirst().id()).isEqualTo(-2);
        assertThat(legacy).extracting(EvidenceShareRow::createdAt)
                .containsExactlyElementsOf(owner.shares().stream()
                        .map(EvidenceShareRow::createdAt).toList());

        assertThat(readShares(jdbc, 0, 7_001L).shares())
                .singleElement()
                .satisfies(row -> {
                    assertThat(row.id()).isEqualTo(7_206);
                    assertThat(row.bankId()).isZero();
                });
        assertThat(readShares(jdbc, 7_106, 7_001L))
                .satisfies(read -> {
                    assertThat(read.available()).isTrue();
                    assertThat(read.shares()).isEmpty();
                });
        for (int bankId : new int[] {7_102, 7_103, 7_104, 7_105, 79_999}) {
            assertThat(readShares(jdbc, bankId, 7_001L))
                    .satisfies(read -> {
                        assertThat(read.available()).isFalse();
                        assertThat(read.shares()).isEmpty();
                    });
        }
        assertThat(readShares(jdbc, 7_101, (long) Integer.MAX_VALUE + 1L))
                .isEqualTo(new EvidenceRead(false, List.of()));

        List<String> shareIndexes = jdbc.sql("""
                        SELECT indexdef
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                          AND tablename = 'bank_shares'
                        ORDER BY indexname
                        """)
                .query(String.class)
                .list();
        assertThat(shareIndexes).hasSize(3);
        assertThat(shareIndexes).noneMatch(definition ->
                definition.matches("(?is).*\\(\\s*bank_id(?:\\s|,|\\)).*"));

        assertIndependentFailureBoundaries(jdbc);
    }

    private static void assertPostgresOrderingAndRawMapping(List<EvidenceShareRow> rows) {
        assertThat(rows).hasSize(6);
        assertThat(rows.getFirst()).satisfies(row -> {
            assertThat(row.id()).isEqualTo(-2);
            assertThat(row.bankId()).isEqualTo(7_101);
            assertThat(row.ownerId()).isEqualTo(7_002);
            assertThat(row.shareCode()).isNull();
            assertThat(row.shareToken()).isNull();
            assertThat(row.permission()).isNull();
            assertThat(row.expiresAt()).isNull();
            assertThat(row.maxUses()).isNull();
            assertThat(row.currentUses()).isNull();
            assertThat(row.active()).isNull();
            assertThat(row.createdAt()).isNull();
        });
        assertThat(rows.subList(1, 4)).extracting(EvidenceShareRow::id)
                .containsExactly(0, 7_201, 7_202);
        assertThat(rows.subList(4, 6)).extracting(EvidenceShareRow::id)
                .containsExactlyInAnyOrder(7_203, 7_204);

        EvidenceShareRow inactive = byId(rows, 7_201);
        assertThat(inactive.active()).isFalse();
        assertThat(inactive.expiresAt()).isEqualTo(LocalDateTime.of(2027, 1, 1, 0, 0));
        EvidenceShareRow expiredCrossOwner = byId(rows, 7_202);
        assertThat(expiredCrossOwner.ownerId()).isEqualTo(7_002);
        assertThat(expiredCrossOwner.active()).isTrue();
        assertThat(expiredCrossOwner.expiresAt())
                .isEqualTo(LocalDateTime.of(2020, 1, 1, 0, 0));
        EvidenceShareRow malformed = byId(rows, 7_203);
        assertThat(malformed.permission()).isEqualTo("unexpected-value");
        assertThat(malformed.maxUses()).isEqualTo(-1);
        assertThat(malformed.currentUses()).isEqualTo(-2);
        assertThat(byId(rows, 7_204).permission()).isEmpty();
    }

    private static EvidenceShareRow byId(List<EvidenceShareRow> rows, int id) {
        return rows.stream().filter(row -> row.id() == id).findFirst().orElseThrow();
    }

    private static void assertIndependentFailureBoundaries(JdbcClient jdbc) {
        jdbc.sql("ALTER TABLE bank_shares RENAME TO bank_shares_temporarily_unavailable")
                .update();
        try {
            assertThat(readShares(jdbc, 79_999, 7_001L))
                    .isEqualTo(new EvidenceRead(false, List.of()));
            assertThatThrownBy(() -> readShares(jdbc, 7_101, 7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE bank_shares_temporarily_unavailable RENAME TO bank_shares")
                    .update();
        }

        jdbc.sql("ALTER TABLE user_question_banks "
                        + "RENAME TO user_question_banks_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> readShares(jdbc, 7_101, 7_001L))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE user_question_banks_temporarily_unavailable "
                            + "RENAME TO user_question_banks")
                    .update();
        }
    }

    private static EvidenceRead readShares(JdbcClient jdbc, int bankId, long viewerId) {
        Optional<Integer> bank = jdbc.sql(PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE)
                .param("bank_id", bankId)
                .param("viewer_id", viewerId)
                .query(Integer.class)
                .optional();
        if (bank.isEmpty()) {
            return new EvidenceRead(false, List.of());
        }
        return new EvidenceRead(true, targetShares(jdbc, bankId));
    }

    private static List<EvidenceShareRow> targetShares(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankShareListEvidenceSql.SHARE_LIST)
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankShareListEvidenceJdbcCompatibilityIT::mapShare)
                .list();
    }

    private static List<EvidenceShareRow> legacyShares(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankShareListEvidenceSql.LEGACY_SHARE_LIST)
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankShareListEvidenceJdbcCompatibilityIT::mapShare)
                .list();
    }

    private static EvidenceShareRow mapShare(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new EvidenceShareRow(
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
                resultSet.getObject("created_at", LocalDateTime.class));
    }

    private record EvidenceRead(boolean available, List<EvidenceShareRow> shares) {
    }

    private record EvidenceShareRow(
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
            LocalDateTime createdAt
    ) {
    }
}
