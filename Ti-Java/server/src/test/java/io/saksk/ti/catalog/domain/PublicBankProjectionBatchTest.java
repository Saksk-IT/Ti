package io.saksk.ti.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSource;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;

class PublicBankProjectionBatchTest {

    private static final PublicBankRef SYSTEM =
            new PublicBankRef(PublicBankSource.SYSTEM, 101);
    private static final PublicBankRef USER =
            new PublicBankRef(PublicBankSource.USER_PUBLIC, 201);
    private static final PublicBankSnapshotCommit COMMIT = new PublicBankSnapshotCommit(
            Instant.parse("2026-07-16T04:00:00Z"), 1, "fixture:42");

    @Test
    void defensiveCopiesACompleteUniqueProjection() {
        var metrics = new java.util.ArrayList<>(List.of(metric(SYSTEM), metric(USER)));
        var viewers = new java.util.ArrayList<>(List.of(
                new PublicBankViewerProjection(7, USER, true, false, null),
                new PublicBankViewerProjection(
                        8, SYSTEM, false, false, Instant.parse("2026-07-16T03:00:00Z"))));

        PublicBankProjectionBatch batch = new PublicBankProjectionBatch(
                COMMIT, metrics, viewers);
        metrics.clear();
        viewers.clear();

        assertThat(batch.metrics()).hasSize(2);
        assertThat(batch.viewers()).hasSize(2);
        assertThatThrownBy(() -> batch.metrics().clear())
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void rejectsDuplicateMetricsDuplicateViewersAndOrphanViewerRows() {
        assertThatThrownBy(() -> new PublicBankProjectionBatch(
                COMMIT, List.of(metric(USER), metric(USER)), List.of()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("duplicate public-bank metric");

        PublicBankViewerProjection viewer =
                new PublicBankViewerProjection(7, USER, true, false, null);
        assertThatThrownBy(() -> new PublicBankProjectionBatch(
                COMMIT, List.of(metric(USER)), List.of(viewer, viewer)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("duplicate public-bank viewer");

        assertThatThrownBy(() -> new PublicBankProjectionBatch(
                COMMIT, List.of(metric(SYSTEM)), List.of(viewer)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("non-visible bank");
    }

    @Test
    void rejectsProjectionRowsWithoutAUsefulRelationOrActivityAndInvalidMetadata() {
        assertThatThrownBy(() ->
                new PublicBankViewerProjection(7, USER, false, false, null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PublicBankSnapshotCommit(
                Instant.parse("2026-07-16T04:00:00Z"), 0, "fixture"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PublicBankSnapshotCommit(
                Instant.parse("2026-07-16T04:00:00Z"), 1, " "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static PublicBankMetricProjection metric(PublicBankRef reference) {
        return new PublicBankMetricProjection(
                reference,
                "题库 " + reference.id(),
                "description",
                null,
                reference.source() == PublicBankSource.USER_PUBLIC ? 9001L : null,
                reference.source() == PublicBankSource.USER_PUBLIC ? "Owner" : "系统题库",
                null,
                12,
                1,
                false,
                0,
                LocalDateTime.parse("2026-07-10T12:00:00"),
                LocalDateTime.parse("2026-07-15T12:00:00"),
                3,
                2,
                3,
                5,
                8,
                2,
                4,
                1.5,
                2.5,
                3.5,
                "free",
                "",
                true,
                0);
    }
}
