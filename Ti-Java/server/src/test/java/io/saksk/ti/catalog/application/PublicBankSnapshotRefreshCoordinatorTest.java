package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.application.PublicBankSnapshotRefreshCoordinator.RefreshResult;
import io.saksk.ti.catalog.application.PublicBankSnapshotRefreshCoordinator.State;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort;
import io.saksk.ti.catalog.domain.PublicBankProjectionBatch;
import io.saksk.ti.catalog.domain.PublicBankSnapshotCommit;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class PublicBankSnapshotRefreshCoordinatorTest {

    private static final String REFRESH_DURATION =
            "ti.catalog.public_bank.snapshot.refresh.duration";
    private static final PublicBankRefreshLeasePort.Lease LEASE =
            new PublicBankRefreshLeasePort.Lease("A".repeat(43));
    private static final PublicBankSnapshotMaintenancePort.CommitResult COMMIT =
            new PublicBankSnapshotMaintenancePort.CommitResult(
                    PublicBankSnapshotMaintenancePort.Outcome.COMMITTED,
                    7,
                    "a".repeat(64));

    private SimpleMeterRegistry meters;
    private RecordingLeasePort leases;
    private RecordingMaintenancePort snapshots;
    private PublicBankSnapshotRefreshCoordinator coordinator;

    @BeforeEach
    void setUp() {
        meters = new SimpleMeterRegistry();
        leases = new RecordingLeasePort();
        snapshots = new RecordingMaintenancePort();
        coordinator = new PublicBankSnapshotRefreshCoordinator(leases, snapshots, meters);
    }

    @Test
    void acquiredLeaseWrapsLoadingAndPostgresFinalizedCommit() {
        AtomicInteger loads = new AtomicInteger();

        RefreshResult result = coordinator.refresh(() -> {
            loads.incrementAndGet();
            return projection();
        });

        assertThat(result.state()).isEqualTo(State.COMMITTED);
        assertThat(result.commit()).contains(COMMIT);
        assertThat(loads).hasValue(1);
        assertThat(snapshots.replacements).isEqualTo(1);
        assertThat(snapshots.supplierReplacements).isEqualTo(1);
        assertThat(leases.released).containsExactly(LEASE);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.success", 1);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.failure", 0);
        assertCounter("ti.catalog.public_bank.snapshot.lock.degraded", 0);
        assertDuration(1);
    }

    @Test
    void heldLeaseSuppressesDuplicateWorkBeforeProjectionLoading() {
        leases.acquired = Optional.empty();
        AtomicInteger loads = new AtomicInteger();

        RefreshResult result = coordinator.refresh(() -> {
            loads.incrementAndGet();
            return projection();
        });

        assertThat(result).isEqualTo(RefreshResult.suppressed());
        assertThat(loads).hasValue(0);
        assertThat(snapshots.replacements).isZero();
        assertThat(snapshots.supplierReplacements).isZero();
        assertThat(leases.released).isEmpty();
        assertCounter("ti.catalog.public_bank.snapshot.refresh.suppressed", 1);
        assertDuration(0);
    }

    @Test
    void redisAcquisitionFailureFallsBackToPostgresAndRecordsDegradation() {
        leases.acquireFailure = new IllegalStateException("redis unavailable");

        RefreshResult result = coordinator.refresh(PublicBankSnapshotRefreshCoordinatorTest::projection);

        assertThat(result.state()).isEqualTo(State.COMMITTED_DEGRADED);
        assertThat(result.commit()).contains(COMMIT);
        assertThat(snapshots.replacements).isEqualTo(1);
        assertThat(snapshots.supplierReplacements).isEqualTo(1);
        assertThat(leases.released).isEmpty();
        assertCounter("ti.catalog.public_bank.snapshot.refresh.success", 1);
        assertCounter("ti.catalog.public_bank.snapshot.lock.degraded", 1);
        assertDuration(1);
    }

    @Test
    void lostOrFailedReleaseCannotUndoAnotherOwnerAndMarksCommitDegraded() {
        leases.releaseOutcome = PublicBankRefreshLeasePort.ReleaseOutcome.LOST;

        RefreshResult lost = coordinator.refresh(PublicBankSnapshotRefreshCoordinatorTest::projection);

        assertThat(lost.state()).isEqualTo(State.COMMITTED_DEGRADED);
        assertCounter("ti.catalog.public_bank.snapshot.lock.degraded", 1);

        leases.releaseFailure = new IllegalStateException("redis unavailable");
        RefreshResult failed = coordinator.refresh(PublicBankSnapshotRefreshCoordinatorTest::projection);
        assertThat(failed.state()).isEqualTo(State.COMMITTED_DEGRADED);
        assertCounter("ti.catalog.public_bank.snapshot.lock.degraded", 2);
        assertDuration(2);
    }

    @Test
    void refreshFailureIsCountedAndStillReleasesTheOwnedToken() {
        snapshots.failure = new IllegalStateException("projection rejected");

        assertThatThrownBy(() -> coordinator.refresh(
                        PublicBankSnapshotRefreshCoordinatorTest::projection))
                .isSameAs(snapshots.failure);

        assertThat(leases.released).containsExactly(LEASE);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.success", 0);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.failure", 1);
        assertDuration(1);
    }

    @Test
    void projectionLoaderFailureIsCountedWithoutEnteringBatchReplacement() {
        IllegalStateException failure = new IllegalStateException("projection load failed");

        assertThatThrownBy(() -> coordinator.refresh(() -> {
            throw failure;
        })).isSameAs(failure);

        assertThat(snapshots.supplierReplacements).isEqualTo(1);
        assertThat(snapshots.replacements).isZero();
        assertThat(leases.released).containsExactly(LEASE);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.success", 0);
        assertCounter("ti.catalog.public_bank.snapshot.refresh.failure", 1);
        assertDuration(1);
    }

    private void assertCounter(String name, double expected) {
        assertThat(meters.get(name).counter().count()).isEqualTo(expected);
    }

    private void assertDuration(long expectedCount) {
        Timer timer = meters.get(REFRESH_DURATION).timer();
        assertThat(timer.count()).isEqualTo(expectedCount);
        if (expectedCount == 0) {
            assertThat(timer.totalTime(TimeUnit.NANOSECONDS)).isZero();
        } else {
            assertThat(timer.totalTime(TimeUnit.NANOSECONDS)).isPositive();
        }
    }

    private static PublicBankProjectionBatch projection() {
        return new PublicBankProjectionBatch(
                new PublicBankSnapshotCommit(
                        Instant.parse("2026-07-16T04:00:00Z"), 1, "fixture:42"),
                List.of(),
                List.of());
    }

    private static final class RecordingLeasePort implements PublicBankRefreshLeasePort {

        private Optional<Lease> acquired = Optional.of(LEASE);
        private RuntimeException acquireFailure;
        private RuntimeException releaseFailure;
        private ReleaseOutcome releaseOutcome = ReleaseOutcome.RELEASED;
        private final java.util.ArrayList<Lease> released = new java.util.ArrayList<>();

        @Override
        public Optional<Lease> tryAcquire() {
            if (acquireFailure != null) {
                throw acquireFailure;
            }
            return acquired;
        }

        @Override
        public ReleaseOutcome release(Lease lease) {
            released.add(lease);
            if (releaseFailure != null) {
                throw releaseFailure;
            }
            return releaseOutcome;
        }
    }

    private static final class RecordingMaintenancePort
            implements PublicBankSnapshotMaintenancePort {

        private int replacements;
        private int supplierReplacements;
        private RuntimeException failure;

        @Override
        public CommitResult replace(Supplier<PublicBankProjectionBatch> projectionLoader) {
            supplierReplacements++;
            return PublicBankSnapshotMaintenancePort.super.replace(projectionLoader);
        }

        @Override
        public CommitResult replace(PublicBankProjectionBatch projection) {
            replacements++;
            if (failure != null) {
                throw failure;
            }
            return COMMIT;
        }

        @Override
        public CommitResult tombstone(PublicBankRef reference, PublicBankSnapshotCommit commit) {
            throw new UnsupportedOperationException("not used by refresh coordinator test");
        }
    }
}
