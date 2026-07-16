package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class PublicBankSqlContractTest {

    @Test
    void readinessInspectionUsesTheSameConstantTimeSnapshotBoundaryOnly() {
        String sql = JdbcPublicBankSnapshotQueryAdapter.snapshotInspectionSql();

        assertThat(sql)
                .startsWith(JdbcPublicBankSnapshotQueryAdapter.SNAPSHOT_CTE)
                .contains("FROM snapshot s")
                .doesNotContain(
                        "COUNT(*)",
                        " subjects ",
                        " user_question_banks ",
                        " users ",
                        "INSERT ",
                        "UPDATE ",
                        "DELETE ");
    }

    @Test
    void snapshotEvidenceUsesIndexedFirstAndLastBoundariesWithoutFullTableAggregates() {
        String sql = JdbcPublicBankSnapshotQueryAdapter.SNAPSHOT_CTE;

        assertThat(sql)
                .contains(
                        "FROM public_bank_plaza_metrics",
                        "FROM public_bank_plaza_viewer_state",
                        "FROM public_bank_plaza_snapshot_state",
                        "WHERE state.snapshot_name = 'public-bank-plaza'",
                        "metric_first.snapshot_generation AS metric_first_generation",
                        "metric_last.snapshot_generation AS metric_last_generation",
                        "viewer_first.snapshot_generation AS viewer_first_generation",
                        "viewer_last.snapshot_generation AS viewer_last_generation",
                        "ORDER BY snapshot_generation, projection_digest",
                        "ORDER BY snapshot_generation DESC, projection_digest DESC",
                        "state.metrics_count AS expected_metrics_count",
                        "state.viewer_state_count AS expected_viewer_state_count",
                        "state.system_count AS expected_system_count",
                        "state.user_public_count AS expected_user_public_count",
                        "state.projection_digest",
                        "state.projector_schema_version",
                        "state.source_high_watermark")
                .doesNotContain(
                        "COUNT(*)",
                        "MIN(snapshot_generation)",
                        "MAX(snapshot_generation)",
                        " subjects ",
                        " user_question_banks ",
                        " users ",
                        "INSERT ",
                        "UPDATE ",
                        "DELETE ");
    }

    @Test
    void orderByUsesOnlyClosedEnumFragmentsAndPreservesLegacyRankPrefix() {
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.LATEST, false))
                .isEqualTo("m.published_at DESC, m.source_id DESC, m.source_type ASC");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.HOT, false))
                .isEqualTo("m.hot_score DESC, m.published_at DESC, m.source_id DESC, "
                        + "m.source_type ASC");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.ACTIVE, false))
                .isEqualTo("m.active_score DESC, m.last_activity_at DESC, "
                        + "m.source_id DESC, m.source_type ASC");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.FEATURED, false))
                .isEqualTo("m.featured_weight DESC, m.recommended_score DESC, "
                        + "m.published_at DESC, m.source_id DESC, m.source_type ASC");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.QUESTIONS, false))
                .isEqualTo("m.question_count_total DESC, m.published_at DESC, "
                        + "m.source_id DESC, m.source_type ASC");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.orderBy(PublicBankSort.LATEST, true))
                .startsWith("search_rank DESC, ");
    }

    @Test
    void unfilteredBoardsRetainActiveZeroCountBoards() {
        String sql = JdbcPublicBankSnapshotQueryAdapter.boardsSql(PublicBankFilter.all());

        assertThat(sql)
                .contains("LEFT JOIN public_bank_plaza_metrics m")
                .contains("WHERE board.is_active = true")
                .doesNotContain("HAVING COUNT(m.source_id) > 0");
    }

    @Test
    void everyBoardFilterEliminatesZeroCountBoards() {
        PublicBankFilter keyword = new PublicBankFilter(
                Optional.empty(), "algorithm", Optional.empty());
        PublicBankFilter source = new PublicBankFilter(
                Optional.empty(), "", Optional.of(PublicBankSource.SYSTEM));
        PublicBankFilter board = new PublicBankFilter(
                Optional.of(7L), "", Optional.empty());

        assertThat(JdbcPublicBankSnapshotQueryAdapter.boardsSql(keyword))
                .contains("LOWER(m.name) LIKE :keyword")
                .contains("HAVING COUNT(m.source_id) > 0");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.boardsSql(source))
                .contains("m.source_type = :sourceType")
                .contains("HAVING COUNT(m.source_id) > 0");
        assertThat(JdbcPublicBankSnapshotQueryAdapter.boardsSql(board))
                .contains("board.id = :boardId")
                .contains("HAVING COUNT(m.source_id) > 0");
    }
}
