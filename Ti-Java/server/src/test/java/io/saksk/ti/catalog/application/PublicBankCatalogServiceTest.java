package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.PublicBankBoardRef;
import io.saksk.ti.catalog.api.PublicBankBoardView;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankRelationView;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSnapshotUnavailableException;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.api.PublicBankSourceBreakdownView;
import io.saksk.ti.catalog.api.PublicBankSummaryView;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankPageSlice;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.domain.PublicBankSnapshotResult;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

class PublicBankCatalogServiceTest {

    private static final Instant NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final long GENERATION = 23;

    @Test
    void searchForwardsTrustedViewerAndBuildsStablePageMetadata() {
        RecordingPort port = new RecordingPort(completeAt(NOW.minusSeconds(20)));
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        PublicBankCatalogService service = service(port, meters);
        PublicBankSearchQuery query = new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.QUESTIONS, 2, 12);

        var page = service.search(query, Optional.of(new AuthenticatedCatalogViewer(41)));

        assertThat(port.searchViewer).hasValue(41);
        assertThat(page.items()).containsExactly(port.card);
        assertThat(page.total()).isEqualTo(31);
        assertThat(page.page()).isEqualTo(2);
        assertThat(page.pageSize()).isEqualTo(12);
        assertThat(page.sort()).isEqualTo(PublicBankSort.QUESTIONS);
        assertThat(page.availableSorts()).containsExactly(
                PublicBankSort.LATEST,
                PublicBankSort.HOT,
                PublicBankSort.ACTIVE,
                PublicBankSort.FEATURED);
        assertThat(counter(meters, "ti.catalog.public_bank.snapshot.served_stale")).isZero();
        assertThat(counter(meters, "ti.catalog.public_bank.snapshot.unavailable")).isZero();
    }

    @Test
    void servesCompleteSoftStaleSnapshotAndIncrementsOnlyStaleCounter() {
        RecordingPort port = new RecordingPort(completeAt(NOW.minusSeconds(301)));
        SimpleMeterRegistry meters = new SimpleMeterRegistry();

        List<PublicBankBoardView> boards = service(port, meters).boards(PublicBankFilter.all());

        assertThat(boards).containsExactly(port.board);
        assertThat(counter(meters, "ti.catalog.public_bank.snapshot.served_stale"))
                .isEqualTo(1.0);
        assertThat(counter(meters, "ti.catalog.public_bank.snapshot.unavailable")).isZero();
    }

    @Test
    void rejectsHardExpiredAndPartialSnapshotsWithFixedSafeException() {
        SimpleMeterRegistry hardMeters = new SimpleMeterRegistry();
        PublicBankCatalogService hardExpired = service(
                new RecordingPort(completeAt(NOW.minusSeconds(901))), hardMeters);

        assertThatThrownBy(() -> hardExpired.boards(PublicBankFilter.all()))
                .isExactlyInstanceOf(PublicBankSnapshotUnavailableException.class)
                .hasMessage("Public bank snapshot is unavailable");
        assertThat(counter(hardMeters, "ti.catalog.public_bank.snapshot.unavailable"))
                .isEqualTo(1.0);

        SimpleMeterRegistry partialMeters = new SimpleMeterRegistry();
        PublicBankCatalogService partial = service(
                new RecordingPort(partialAt(NOW.minusSeconds(10))), partialMeters);

        assertThatThrownBy(() -> partial.hot(
                new PublicBankHotQuery(PublicBankFilter.all(), 5), Optional.empty()))
                .isExactlyInstanceOf(PublicBankSnapshotUnavailableException.class)
                .hasMessage("Public bank snapshot is unavailable");
        assertThat(counter(partialMeters, "ti.catalog.public_bank.snapshot.unavailable"))
                .isEqualTo(1.0);
    }

    @Test
    void hotAcceptsViewerButDeliberatelyUsesViewerFreePortContract() {
        RecordingPort port = new RecordingPort(completeAt(NOW));

        List<PublicBankCardView> cards = service(port, new SimpleMeterRegistry()).hot(
                new PublicBankHotQuery(PublicBankFilter.all(), 3),
                Optional.of(new AuthenticatedCatalogViewer(55)));

        assertThat(cards).containsExactly(port.card);
        assertThat(port.hotCalls).isOne();
        assertThat(cards.getFirst().relation()).isEqualTo(PublicBankRelationView.NONE);
    }

    @Test
    void summaryUsesClockBasedTrueRollingSevenDayCutoff() {
        RecordingPort port = new RecordingPort(completeAt(NOW));

        PublicBankSummaryView summary = service(port, new SimpleMeterRegistry())
                .summary(PublicBankFilter.all());

        assertThat(summary).isEqualTo(port.summary);
        assertThat(port.summaryCutoff).isEqualTo(NOW.minusSeconds(7 * 24 * 60 * 60));
    }

    @Test
    void missingDetailIsAllowedOnlyWhenSnapshotEvidenceIsComplete() {
        RecordingPort available = new RecordingPort(completeAt(NOW));
        available.detail = Optional.empty();

        assertThat(service(available, new SimpleMeterRegistry()).detail(
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 999), Optional.empty()))
                .isEmpty();

        RecordingPort cold = new RecordingPort(PublicBankSnapshot.cold());
        cold.detail = Optional.empty();
        assertThatThrownBy(() -> service(cold, new SimpleMeterRegistry()).detail(
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 999), Optional.empty()))
                .isExactlyInstanceOf(PublicBankSnapshotUnavailableException.class);
    }

    @Test
    void allCatalogReadsAreReadOnlyAndPagedSearchUsesRepeatableRead() throws Exception {
        Set<String> readMethods = Set.of("search", "boards", "hot", "summary", "detail");

        assertThat(Arrays.stream(PublicBankCatalogService.class.getDeclaredMethods())
                        .filter(method -> readMethods.contains(method.getName())))
                .hasSize(5)
                .allSatisfy(method -> assertThat(method.getAnnotation(Transactional.class))
                        .as(method.getName())
                        .isNotNull()
                        .extracting(Transactional::readOnly)
                        .isEqualTo(true));
        Transactional search = PublicBankCatalogService.class.getDeclaredMethod(
                "search", PublicBankSearchQuery.class, Optional.class)
                .getAnnotation(Transactional.class);
        assertThat(search.isolation()).isEqualTo(Isolation.REPEATABLE_READ);
    }

    private static PublicBankCatalogService service(
            RecordingPort port,
            SimpleMeterRegistry meters
    ) {
        return new PublicBankCatalogService(
                port,
                Clock.fixed(NOW, ZoneOffset.UTC),
                meters);
    }

    private static double counter(SimpleMeterRegistry meters, String name) {
        return meters.get(name).counter().count();
    }

    private static PublicBankSnapshot completeAt(Instant lastSuccessAt) {
        return snapshot(lastSuccessAt, 4, 4);
    }

    private static PublicBankSnapshot partialAt(Instant lastSuccessAt) {
        return snapshot(lastSuccessAt, 4, 3);
    }

    private static PublicBankSnapshot snapshot(
            Instant lastSuccessAt,
            long expectedViewerCount,
            long observedViewerCount
    ) {
        String digest = "a".repeat(64);
        return new PublicBankSnapshot(
                true,
                GENERATION,
                "complete",
                lastSuccessAt,
                3,
                expectedViewerCount,
                2,
                1,
                digest,
                "1",
                "source-9",
                new PublicBankSnapshot.ProjectionBoundary(
                        GENERATION, digest, GENERATION, digest),
                observedViewerCount == expectedViewerCount
                        ? new PublicBankSnapshot.ProjectionBoundary(
                                GENERATION, digest, GENERATION, digest)
                        : new PublicBankSnapshot.ProjectionBoundary(
                                GENERATION, digest, GENERATION - 1, digest));
    }

    private static final class RecordingPort implements PublicBankSnapshotQueryPort {

        private final PublicBankSnapshot snapshot;
        private final PublicBankCardView card = card();
        private final PublicBankBoardView board = new PublicBankBoardView(
                7, "algorithms", "算法", "算法题库", 3);
        private final PublicBankSummaryView summary = new PublicBankSummaryView(
                3, 44, 1, 2, 5, new PublicBankSourceBreakdownView(2, 1));
        private OptionalLong searchViewer = OptionalLong.empty();
        private int hotCalls;
        private Instant summaryCutoff;
        private Optional<PublicBankDetailView> detail = Optional.of(
                new PublicBankDetailView(card, 6, 99L, false));

        private RecordingPort(PublicBankSnapshot snapshot) {
            this.snapshot = snapshot;
        }

        @Override
        public PublicBankSnapshotResult<PublicBankPageSlice> search(
                PublicBankSearchQuery query,
                OptionalLong viewerIdentityId
        ) {
            searchViewer = viewerIdentityId;
            return new PublicBankSnapshotResult<>(
                    snapshot, new PublicBankPageSlice(List.of(card), 31));
        }

        @Override
        public PublicBankSnapshotResult<List<PublicBankBoardView>> boards(
                PublicBankFilter filter
        ) {
            return new PublicBankSnapshotResult<>(snapshot, List.of(board));
        }

        @Override
        public PublicBankSnapshotResult<List<PublicBankCardView>> hot(PublicBankHotQuery query) {
            hotCalls++;
            return new PublicBankSnapshotResult<>(snapshot, List.of(card));
        }

        @Override
        public PublicBankSnapshotResult<PublicBankSummaryView> summary(
                PublicBankFilter filter,
                Instant rollingSevenDayCutoff
        ) {
            summaryCutoff = rollingSevenDayCutoff;
            return new PublicBankSnapshotResult<>(snapshot, summary);
        }

        @Override
        public PublicBankSnapshotResult<Optional<PublicBankDetailView>> detail(
                PublicBankRef ref,
                OptionalLong viewerIdentityId
        ) {
            return new PublicBankSnapshotResult<>(snapshot, detail);
        }

        private static PublicBankCardView card() {
            LocalDateTime published = LocalDateTime.of(2026, 7, 15, 8, 0);
            return new PublicBankCardView(
                    99,
                    PublicBankSource.USER_PUBLIC,
                    "算法训练",
                    "算法题库",
                    null,
                    "Wang",
                    null,
                    44,
                    9,
                    2,
                    3,
                    12,
                    88.0,
                    77.0,
                    66.0,
                    published,
                    published.plusHours(1),
                    true,
                    20,
                    new PublicBankBoardRef(7, "algorithms", "算法"),
                    "free",
                    "",
                    true,
                    PublicBankRelationView.NONE);
        }
    }
}
