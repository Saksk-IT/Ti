package io.saksk.ti.catalog.application;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.PublicBankBoardView;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankCatalogApi;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankPageView;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSnapshotFreshness;
import io.saksk.ti.catalog.api.PublicBankSnapshotUnavailableException;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSummaryView;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankPageSlice;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.domain.PublicBankSnapshotResult;
import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalLong;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
class PublicBankCatalogService implements PublicBankCatalogApi {

    private static final List<PublicBankSort> AVAILABLE_SORTS = List.of(
            PublicBankSort.LATEST,
            PublicBankSort.HOT,
            PublicBankSort.ACTIVE,
            PublicBankSort.FEATURED);

    private final PublicBankSnapshotQueryPort snapshots;
    private final Clock clock;
    private final Counter servedStale;
    private final Counter unavailable;

    @Autowired
    PublicBankCatalogService(
            PublicBankSnapshotQueryPort snapshots,
            MeterRegistry meters,
            ObjectProvider<Clock> clocks
    ) {
        this(snapshots, clocks.getIfAvailable(Clock::systemUTC), meters);
    }

    PublicBankCatalogService(
            PublicBankSnapshotQueryPort snapshots,
            Clock clock,
            MeterRegistry meters
    ) {
        this.snapshots = Objects.requireNonNull(snapshots, "snapshots");
        this.clock = Objects.requireNonNull(clock, "clock");
        Objects.requireNonNull(meters, "meters");
        this.servedStale = Counter.builder("ti.catalog.public_bank.snapshot.served_stale")
                .description("Public-bank GETs served from a soft-stale complete snapshot")
                .register(meters);
        this.unavailable = Counter.builder("ti.catalog.public_bank.snapshot.unavailable")
                .description("Public-bank GETs rejected because the complete snapshot is unavailable")
                .register(meters);
    }

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public PublicBankPageView search(
            PublicBankSearchQuery query,
            Optional<AuthenticatedCatalogViewer> viewer
    ) {
        Objects.requireNonNull(query, "query");
        PublicBankSnapshotResult<PublicBankPageSlice> result = snapshots.search(
                query, viewerId(viewer));
        requireAvailable(result.snapshot());
        return new PublicBankPageView(
                result.data().items(),
                result.data().total(),
                query.page(),
                query.pageSize(),
                query.sort(),
                query.filter(),
                AVAILABLE_SORTS);
    }

    @Override
    @Transactional(readOnly = true)
    public List<PublicBankBoardView> boards(PublicBankFilter filter) {
        PublicBankSnapshotResult<List<PublicBankBoardView>> result =
                snapshots.boards(Objects.requireNonNull(filter, "filter"));
        requireAvailable(result.snapshot());
        return result.data();
    }

    @Override
    @Transactional(readOnly = true)
    public List<PublicBankCardView> hot(
            PublicBankHotQuery query,
            Optional<AuthenticatedCatalogViewer> viewer
    ) {
        Objects.requireNonNull(viewer, "viewer");
        PublicBankSnapshotResult<List<PublicBankCardView>> result =
                snapshots.hot(Objects.requireNonNull(query, "query"));
        requireAvailable(result.snapshot());
        return result.data();
    }

    @Override
    @Transactional(readOnly = true)
    public PublicBankSummaryView summary(PublicBankFilter filter) {
        PublicBankSnapshotResult<PublicBankSummaryView> result = snapshots.summary(
                Objects.requireNonNull(filter, "filter"),
                clock.instant().minus(Duration.ofDays(7)));
        requireAvailable(result.snapshot());
        return result.data();
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<PublicBankDetailView> detail(
            PublicBankRef ref,
            Optional<AuthenticatedCatalogViewer> viewer
    ) {
        PublicBankSnapshotResult<Optional<PublicBankDetailView>> result = snapshots.detail(
                Objects.requireNonNull(ref, "ref"), viewerId(viewer));
        requireAvailable(result.snapshot());
        return result.data();
    }

    private PublicBankSnapshotFreshness requireAvailable(PublicBankSnapshot snapshot) {
        PublicBankSnapshot.Assessment assessment = snapshot.assessAt(clock.instant());
        if (!assessment.available()) {
            unavailable.increment();
            throw new PublicBankSnapshotUnavailableException();
        }
        PublicBankSnapshotFreshness.State state;
        if (assessment.freshness() == PublicBankSnapshot.Freshness.SOFT_STALE) {
            servedStale.increment();
            state = PublicBankSnapshotFreshness.State.SOFT_STALE;
        } else {
            state = PublicBankSnapshotFreshness.State.FRESH;
        }
        return new PublicBankSnapshotFreshness(
                snapshot.generation(),
                snapshot.lastSuccessAt(),
                assessment.age().toSeconds(),
                state);
    }

    private static OptionalLong viewerId(Optional<AuthenticatedCatalogViewer> viewer) {
        Objects.requireNonNull(viewer, "viewer");
        return viewer.isPresent()
                ? OptionalLong.of(viewer.orElseThrow().identityId())
                : OptionalLong.empty();
    }
}
