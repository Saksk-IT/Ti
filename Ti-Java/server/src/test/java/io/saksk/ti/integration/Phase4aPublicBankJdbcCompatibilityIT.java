package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankRelation;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcPublicBankSnapshotQueryAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalLong;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aPublicBankJdbcCompatibilityIT {

    private static final Instant FIXED_NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final Instant ROLLING_SEVEN_DAY_CUTOFF =
            Instant.parse("2026-07-09T04:00:00Z");
    private static final String SNAPSHOT_DIGEST =
            "88f25097554a6789dafe7f0902061a5804bee8526ac2cfd32f8e806fd80b8181";
    private static final String BOUNDARY_DIGEST = "9".repeat(64);
    private static final String TIE_DIGEST = "a".repeat(64);

    @Container
    static final PostgreSQLContainer POSTGRES_18 = publicBankFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = publicBankFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void publicBankJdbcQueriesRemainCompatibleWithPostgres18() {
        assertPublicBankCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void publicBankJdbcQueriesRemainCompatibleWithPostgres16() {
        assertPublicBankCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer publicBankFixture(PostgreSQLContainer postgres) {
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
                        "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/042-public-bank-snapshot-schema.sql"),
                        "/docker-entrypoint-initdb.d/042-public-bank-snapshot-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/043-public-bank-snapshot-seed.sql"),
                        "/docker-entrypoint-initdb.d/043-public-bank-snapshot-seed.sql");
    }

    private static void assertPublicBankCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        JdbcClient jdbc = JdbcClient.create(new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
        PublicBankSnapshotQueryPort catalog =
                JdbcPublicBankSnapshotQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);

        assertAllSortsAndViewerRelation(catalog);
        assertBoards(catalog);
        assertHot(catalog);
        assertSummaryAndCompleteSnapshot(catalog);
        assertDetails(catalog);
        assertRollingSevenDayCutoffBoundaries(jdbc, catalog);
        assertCrossSourceTieBreakers(jdbc, catalog);
    }

    private static void assertAllSortsAndViewerRelation(PublicBankSnapshotQueryPort catalog) {
        Map<PublicBankSort, List<String>> expected = new LinkedHashMap<>();
        expected.put(PublicBankSort.LATEST, List.of(
                "system:5302",
                "user_public:5402",
                "user_public:5401",
                "system:5303",
                "user_public:5404",
                "user_public:5403",
                "system:5301"));
        expected.put(PublicBankSort.HOT, List.of(
                "user_public:5401",
                "system:5301",
                "user_public:5403",
                "user_public:5402",
                "user_public:5404",
                "system:5302",
                "system:5303"));
        expected.put(PublicBankSort.ACTIVE, List.of(
                "system:5301",
                "user_public:5401",
                "user_public:5403",
                "system:5302",
                "user_public:5402",
                "system:5303",
                "user_public:5404"));
        expected.put(PublicBankSort.FEATURED, List.of(
                "system:5301",
                "user_public:5401"));
        expected.put(PublicBankSort.QUESTIONS, List.of(
                "user_public:5403",
                "user_public:5401",
                "user_public:5402",
                "user_public:5404",
                "system:5301",
                "system:5302",
                "system:5303"));

        expected.forEach((sort, expectedIds) -> {
            var result = catalog.search(
                    new PublicBankSearchQuery(PublicBankFilter.all(), sort, 1, 50),
                    OptionalLong.of(5102));

            assertCompleteSnapshot(result.snapshot());
            assertThat(result.data().total()).isEqualTo(expectedIds.size());
            assertThat(result.data().items())
                    .extracting(Phase4aPublicBankJdbcCompatibilityIT::identity)
                    .containsExactlyElementsOf(expectedIds);
            assertThat(result.data().items())
                    .filteredOn(card -> card.source() == PublicBankSource.USER_PUBLIC
                            && card.id() == 5401)
                    .singleElement()
                    .extracting(card -> card.relation().joinedVia())
                    .isEqualTo(PublicBankRelation.PUBLIC);
            assertThat(result.data().items())
                    .filteredOn(card -> card.source() != PublicBankSource.USER_PUBLIC
                            || card.id() != 5401)
                    .allSatisfy(card -> assertThat(card.relation().joinedVia())
                            .isEqualTo(PublicBankRelation.NONE));
        });
    }

    private static void assertBoards(PublicBankSnapshotQueryPort catalog) {
        var all = catalog.boards(PublicBankFilter.all());

        assertCompleteSnapshot(all.snapshot());
        assertThat(all.data())
                .extracting(board -> board.id() + ":" + board.bankCount())
                .containsExactly("5203:0", "5202:2", "5201:3");

        var keyword = catalog.boards(new PublicBankFilter(
                java.util.Optional.empty(), "needle", java.util.Optional.empty()));

        assertCompleteSnapshot(keyword.snapshot());
        assertThat(keyword.data())
                .extracting(board -> board.id() + ":" + board.bankCount())
                .containsExactly("5202:2", "5201:3");
    }

    private static void assertHot(PublicBankSnapshotQueryPort catalog) {
        var hot = catalog.hot(new PublicBankHotQuery(PublicBankFilter.all(), 3));

        assertCompleteSnapshot(hot.snapshot());
        assertThat(hot.data())
                .extracting(Phase4aPublicBankJdbcCompatibilityIT::identity)
                .containsExactly("user_public:5401", "system:5301", "user_public:5403");
        assertThat(hot.data()).allSatisfy(card -> assertThat(card.relation().joinedVia())
                .isEqualTo(PublicBankRelation.NONE));
    }

    private static void assertSummaryAndCompleteSnapshot(PublicBankSnapshotQueryPort catalog) {
        var result = catalog.summary(PublicBankFilter.all(), ROLLING_SEVEN_DAY_CUTOFF);

        assertCompleteSnapshot(result.snapshot());
        assertThat(result.data().totalBanks()).isEqualTo(7);
        assertThat(result.data().totalQuestions()).isEqualTo(32);
        assertThat(result.data().totalBoards()).isEqualTo(3);
        assertThat(result.data().newBanks7d()).isEqualTo(7);
        assertThat(result.data().activeUsers7d()).isEqualTo(5);
        assertThat(result.data().sourceBreakdown().system()).isEqualTo(3);
        assertThat(result.data().sourceBreakdown().userPublic()).isEqualTo(4);
    }

    private static void assertDetails(PublicBankSnapshotQueryPort catalog) {
        var user = catalog.detail(
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 5401),
                OptionalLong.of(5102));

        assertCompleteSnapshot(user.snapshot());
        assertThat(user.data()).isPresent().get().satisfies(detail -> {
            assertThat(identity(detail.card())).isEqualTo("user_public:5401");
            assertThat(detail.shareCount()).isEqualTo(2);
            assertThat(detail.authorId()).isEqualTo(5101);
            assertThat(detail.owner()).isFalse();
            assertThat(detail.card().relation().joinedVia()).isEqualTo(PublicBankRelation.PUBLIC);
            assertThat(detail.card().ownerAvatar()).isEqualTo("/uploads/avatars/owner.png");
            assertThat(detail.card().joinMode()).isEqualTo("approval");
            assertThat(detail.card().joinNote()).isEqualTo("Synthetic approval required");
            assertThat(detail.card().allowCopy()).isFalse();
        });

        var system = catalog.detail(
                new PublicBankRef(PublicBankSource.SYSTEM, 5301),
                OptionalLong.of(5105));

        assertCompleteSnapshot(system.snapshot());
        assertThat(system.data()).isPresent().get().satisfies(detail -> {
            assertThat(identity(detail.card())).isEqualTo("system:5301");
            assertThat(detail.shareCount()).isZero();
            assertThat(detail.authorId()).isNull();
            assertThat(detail.owner()).isFalse();
            assertThat(detail.card().relation().joinedVia()).isEqualTo(PublicBankRelation.PUBLIC);
            assertThat(detail.card().allowCopy()).isFalse();
            assertThat(detail.card().joinMode()).isEqualTo("free");
        });
    }

    private static void assertRollingSevenDayCutoffBoundaries(
            JdbcClient jdbc,
            PublicBankSnapshotQueryPort catalog
    ) {
        beginFixtureMutation(jdbc);
        jdbc.sql("""
                UPDATE public_bank_plaza_metrics
                   SET published_at = TIMESTAMP '2026-07-09 11:59:59.999999'
                """).update();
        jdbc.sql("""
                UPDATE public_bank_plaza_metrics
                   SET published_at = TIMESTAMP '2026-07-09 12:00:00'
                 WHERE source_type = 'system' AND source_id = 5301
                """).update();
        jdbc.sql("""
                UPDATE public_bank_plaza_metrics
                   SET published_at = TIMESTAMP '2026-07-09 12:00:00.000001'
                 WHERE source_type = 'user_public' AND source_id = 5401
                """).update();

        jdbc.sql("""
                UPDATE public_bank_plaza_viewer_state
                   SET last_activity_at = TIMESTAMPTZ '2026-07-09 03:59:59.999999+00:00'
                """).update();
        jdbc.sql("""
                UPDATE public_bank_plaza_viewer_state
                   SET last_activity_at = TIMESTAMPTZ '2026-07-09 04:00:00+00:00'
                 WHERE identity_id = 5101
                   AND source_type = 'system'
                   AND source_id = 5301
                """).update();
        jdbc.sql("""
                UPDATE public_bank_plaza_viewer_state
                   SET last_activity_at = TIMESTAMPTZ '2026-07-09 04:00:00.000001+00:00'
                 WHERE identity_id = 5102
                   AND source_type = 'user_public'
                   AND source_id = 5401
                """).update();

        completeFixtureMutation(jdbc, BOUNDARY_DIGEST, 7, 3, 4);

        var result = catalog.summary(PublicBankFilter.all(), ROLLING_SEVEN_DAY_CUTOFF);

        assertCompleteSnapshot(result.snapshot(), 7, 3, 4, BOUNDARY_DIGEST);
        assertThat(result.data().newBanks7d())
                .as("Asia/Shanghai local cutoff is inclusive to one microsecond")
                .isEqualTo(2);
        assertThat(result.data().activeUsers7d())
                .as("timestamptz cutoff keeps the same absolute instant")
                .isEqualTo(2);
    }

    private static void assertCrossSourceTieBreakers(
            JdbcClient jdbc,
            PublicBankSnapshotQueryPort catalog
    ) {
        beginFixtureMutation(jdbc);
        jdbc.sql("""
                INSERT INTO public_bank_plaza_metrics (
                    source_type,
                    source_id,
                    name,
                    description,
                    cover_image,
                    owner_id,
                    owner_label,
                    owner_avatar,
                    question_count_total,
                    plaza_board_id,
                    is_featured,
                    featured_weight,
                    published_at,
                    last_activity_at,
                    join_count_total,
                    join_users_7d,
                    join_users_30d,
                    answer_count_7d,
                    answer_count_30d,
                    answer_users_7d,
                    answer_users_30d,
                    hot_score,
                    active_score,
                    recommended_score,
                    join_mode,
                    join_note,
                    allow_copy,
                    share_count,
                    snapshot_generation,
                    updated_at
                )
                SELECT 'user_public',
                       source_id,
                       name,
                       description,
                       cover_image,
                       owner_id,
                       owner_label,
                       owner_avatar,
                       question_count_total,
                       plaza_board_id,
                       is_featured,
                       featured_weight,
                       published_at,
                       last_activity_at,
                       join_count_total,
                       join_users_7d,
                       join_users_30d,
                       answer_count_7d,
                       answer_count_30d,
                       answer_users_7d,
                       answer_users_30d,
                       hot_score,
                       active_score,
                       recommended_score,
                       join_mode,
                       join_note,
                       allow_copy,
                       share_count,
                       snapshot_generation,
                       updated_at
                  FROM public_bank_plaza_metrics
                 WHERE source_type = 'system' AND source_id = 5301
                """).update();
        completeFixtureMutation(jdbc, TIE_DIGEST, 8, 3, 5);

        for (PublicBankSort sort : PublicBankSort.values()) {
            for (int repetition = 0; repetition < 3; repetition++) {
                var result = catalog.search(
                        new PublicBankSearchQuery(PublicBankFilter.all(), sort, 1, 50),
                        OptionalLong.empty());

                assertCompleteSnapshot(result.snapshot(), 8, 3, 5, TIE_DIGEST);
                assertThat(result.data().items())
                        .as("stable cross-source tie-breaker for %s, repetition %s",
                                sort, repetition)
                        .filteredOn(card -> card.id() == 5301)
                        .extracting(PublicBankCardView::source)
                        .containsExactly(PublicBankSource.SYSTEM, PublicBankSource.USER_PUBLIC);
            }
        }

        for (int repetition = 0; repetition < 3; repetition++) {
            var result = catalog.hot(new PublicBankHotQuery(PublicBankFilter.all(), 10));

            assertCompleteSnapshot(result.snapshot(), 8, 3, 5, TIE_DIGEST);
            assertThat(result.data())
                    .as("stable hot cross-source tie-breaker, repetition %s", repetition)
                    .filteredOn(card -> card.id() == 5301)
                    .extracting(PublicBankCardView::source)
                    .containsExactly(PublicBankSource.SYSTEM, PublicBankSource.USER_PUBLIC);
        }
    }

    private static void beginFixtureMutation(JdbcClient jdbc) {
        jdbc.sql("""
                UPDATE public_bank_plaza_snapshot_state
                   SET status = 'building'
                 WHERE snapshot_name = 'public-bank-plaza'
                """).update();
    }

    private static void completeFixtureMutation(
            JdbcClient jdbc,
            String digest,
            long metrics,
            long system,
            long userPublic
    ) {
        jdbc.sql("UPDATE public_bank_plaza_metrics SET projection_digest = :digest")
                .param("digest", digest)
                .update();
        jdbc.sql("UPDATE public_bank_plaza_viewer_state SET projection_digest = :digest")
                .param("digest", digest)
                .update();
        jdbc.sql("""
                UPDATE public_bank_plaza_snapshot_state
                   SET status = 'complete',
                       metrics_count = :metrics,
                       system_count = :system,
                       user_public_count = :userPublic,
                       projection_digest = :digest
                 WHERE snapshot_name = 'public-bank-plaza'
                """)
                .param("metrics", metrics)
                .param("system", system)
                .param("userPublic", userPublic)
                .param("digest", digest)
                .update();
    }

    private static void assertCompleteSnapshot(PublicBankSnapshot snapshot) {
        assertCompleteSnapshot(snapshot, 7, 3, 4, SNAPSHOT_DIGEST);
    }

    private static void assertCompleteSnapshot(
            PublicBankSnapshot snapshot,
            long expectedMetricsCount,
            long expectedSystemCount,
            long expectedUserPublicCount,
            String expectedDigest
    ) {
        assertThat(snapshot.structurallyComplete()).as(snapshot.toString()).isTrue();
        assertThat(snapshot.generation()).isEqualTo(1);
        assertThat(snapshot.status()).isEqualTo("complete");
        assertThat(snapshot.lastSuccessAt()).isEqualTo(FIXED_NOW);
        assertThat(snapshot.projectionDigest()).isEqualTo(expectedDigest);
        assertThat(snapshot.projectorSchemaVersion()).isEqualTo("1");
        assertThat(snapshot.sourceHighWatermark())
                .isEqualTo("legacy-golden@700006dfdfa063deb4387be572911e782bcea0d9");
        assertThat(snapshot.expectedMetricsCount()).isEqualTo(expectedMetricsCount);
        assertThat(snapshot.expectedViewerStateCount()).isEqualTo(6);
        assertThat(snapshot.expectedSystemCount()).isEqualTo(expectedSystemCount);
        assertThat(snapshot.expectedUserPublicCount()).isEqualTo(expectedUserPublicCount);
        assertThat(snapshot.assessAt(FIXED_NOW).available()).isTrue();
    }

    private static String identity(PublicBankCardView card) {
        String sourceType = switch (card.source()) {
            case SYSTEM -> "system";
            case USER_PUBLIC -> "user_public";
        };
        return sourceType + ":" + card.id();
    }
}
