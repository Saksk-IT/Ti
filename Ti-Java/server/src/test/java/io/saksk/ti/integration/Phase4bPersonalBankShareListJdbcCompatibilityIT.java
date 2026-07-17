package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.PersonalBankShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import io.saksk.ti.personalbank.infrastructure.persistence.JdbcPersonalBankShareQueryAdapterTestAccess;
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
class Phase4bPersonalBankShareListJdbcCompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 = shareFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = shareFixture(
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
        PersonalBankShareQueryPort shares =
                JdbcPersonalBankShareQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        List<PersonalBankShareView> owner = shares.findShares(7_001L, 7_101)
                .orElseThrow();
        assertRawMappingAndOrdering(owner);
        assertThatThrownBy(() -> owner.add(owner.getFirst()))
                .isInstanceOf(UnsupportedOperationException.class);

        assertThat(shares.findShares(7_001L, 0))
                .hasValueSatisfying(rows -> assertThat(rows)
                        .singleElement()
                        .satisfies(row -> {
                            assertThat(row.id()).isEqualTo(7_206);
                            assertThat(row.bankId()).isZero();
                        }));
        assertThat(shares.findShares(7_001L, 7_106))
                .hasValueSatisfying(rows -> assertThat(rows).isEmpty());
        for (int bankId : new int[] {7_102, 7_103, 7_104, 7_105, 79_999, -1}) {
            assertThat(shares.findShares(7_001L, bankId)).isEmpty();
        }
        assertThat(shares.findShares((long) Integer.MAX_VALUE + 1L, 7_101)).isEmpty();

        assertIndependentFailureBoundaries(jdbc, shares);
    }

    private static void assertRawMappingAndOrdering(List<PersonalBankShareView> rows) {
        assertThat(rows).hasSize(6);
        assertThat(rows.getFirst()).satisfies(row -> {
            assertThat(row.id()).isEqualTo(-2);
            assertThat(row.bankId()).isEqualTo(7_101);
            assertThat(row.ownerId()).isEqualTo(7_002L);
            assertThat(row.shareCode()).isNull();
            assertThat(row.shareToken()).isNull();
            assertThat(row.permission()).isNull();
            assertThat(row.expiresAt()).isNull();
            assertThat(row.maxUses()).isNull();
            assertThat(row.currentUses()).isNull();
            assertThat(row.isActive()).isNull();
            assertThat(row.createdAt()).isNull();
        });
        assertThat(rows.subList(1, 4)).extracting(PersonalBankShareView::id)
                .containsExactly(0, 7_201, 7_202);
        assertThat(rows.subList(4, 6)).extracting(PersonalBankShareView::id)
                .containsExactlyInAnyOrder(7_203, 7_204);

        PersonalBankShareView inactive = byId(rows, 7_201);
        assertThat(inactive.isActive()).isFalse();
        assertThat(inactive.expiresAt()).isEqualTo(LocalDateTime.of(2027, 1, 1, 0, 0));
        PersonalBankShareView expiredCrossOwner = byId(rows, 7_202);
        assertThat(expiredCrossOwner.ownerId()).isEqualTo(7_002L);
        assertThat(expiredCrossOwner.isActive()).isTrue();
        assertThat(expiredCrossOwner.expiresAt())
                .isEqualTo(LocalDateTime.of(2020, 1, 1, 0, 0));
        PersonalBankShareView malformed = byId(rows, 7_203);
        assertThat(malformed.permission()).isEqualTo("unexpected-value");
        assertThat(malformed.maxUses()).isEqualTo(-1);
        assertThat(malformed.currentUses()).isEqualTo(-2);
        assertThat(byId(rows, 7_204).permission()).isEmpty();
    }

    private static PersonalBankShareView byId(List<PersonalBankShareView> rows, int id) {
        return rows.stream().filter(row -> row.id() == id).findFirst().orElseThrow();
    }

    private static void assertIndependentFailureBoundaries(
            JdbcClient jdbc,
            PersonalBankShareQueryPort shares
    ) {
        jdbc.sql("ALTER TABLE bank_shares RENAME TO bank_shares_temporarily_unavailable")
                .update();
        try {
            assertThat(shares.findShares(7_001L, 79_999)).isEmpty();
            assertThatThrownBy(() -> shares.findShares(7_001L, 7_101))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE bank_shares_temporarily_unavailable RENAME TO bank_shares")
                    .update();
        }

        jdbc.sql("ALTER TABLE user_question_banks "
                        + "RENAME TO user_question_banks_temporarily_unavailable")
                .update();
        try {
            assertThatThrownBy(() -> shares.findShares(7_001L, 7_101))
                    .isInstanceOf(DataAccessException.class);
        } finally {
            jdbc.sql("ALTER TABLE user_question_banks_temporarily_unavailable "
                            + "RENAME TO user_question_banks")
                    .update();
        }
    }
}
