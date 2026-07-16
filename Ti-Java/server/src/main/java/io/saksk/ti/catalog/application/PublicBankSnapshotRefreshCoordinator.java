package io.saksk.ti.catalog.application;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort.Lease;
import io.saksk.ti.catalog.application.port.PublicBankRefreshLeasePort.ReleaseOutcome;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort.CommitResult;
import io.saksk.ti.catalog.domain.PublicBankProjectionBatch;
import java.util.Objects;
import java.util.Optional;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Background-only coordination around the PostgreSQL-finalized snapshot writer.
 *
 * <p>The Redis lease is deliberately advisory. If Redis is unavailable, the refresh continues
 * through the maintenance port, whose transaction-level PostgreSQL advisory lock is the actual
 * single-writer boundary. No HTTP read path invokes this service.</p>
 */
@Service
public final class PublicBankSnapshotRefreshCoordinator {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(PublicBankSnapshotRefreshCoordinator.class);

    private final PublicBankRefreshLeasePort leases;
    private final PublicBankSnapshotMaintenancePort snapshots;
    private final MeterRegistry meters;
    private final Counter refreshSuccess;
    private final Counter refreshFailure;
    private final Counter refreshSuppressed;
    private final Counter lockDegraded;
    private final Timer refreshDuration;

    public PublicBankSnapshotRefreshCoordinator(
            PublicBankRefreshLeasePort leases,
            PublicBankSnapshotMaintenancePort snapshots,
            MeterRegistry meters
    ) {
        this.leases = Objects.requireNonNull(leases, "leases");
        this.snapshots = Objects.requireNonNull(snapshots, "snapshots");
        this.meters = Objects.requireNonNull(meters, "meters");
        this.refreshSuccess = Counter.builder("ti.catalog.public_bank.snapshot.refresh.success")
                .description("Successfully committed public-bank snapshot refreshes")
                .register(meters);
        this.refreshFailure = Counter.builder("ti.catalog.public_bank.snapshot.refresh.failure")
                .description("Failed public-bank snapshot refresh attempts")
                .register(meters);
        this.refreshSuppressed = Counter.builder(
                        "ti.catalog.public_bank.snapshot.refresh.suppressed")
                .description("Duplicate public-bank refreshes suppressed by the Redis lease")
                .register(meters);
        this.lockDegraded = Counter.builder("ti.catalog.public_bank.snapshot.lock.degraded")
                .description("Public-bank refreshes relying on the PostgreSQL lock after a Redis "
                        + "lease failure")
                .register(meters);
        this.refreshDuration = Timer.builder(
                        "ti.catalog.public_bank.snapshot.refresh.duration")
                .description("Duration of executed public-bank snapshot refresh attempts")
                .publishPercentileHistogram()
                .register(meters);
    }

    public RefreshResult refresh(Supplier<PublicBankProjectionBatch> projectionLoader) {
        Objects.requireNonNull(projectionLoader, "projectionLoader");

        Optional<Lease> lease;
        boolean degraded = false;
        try {
            lease = Objects.requireNonNull(leases.tryAcquire(), "lease acquisition result");
        } catch (RuntimeException exception) {
            degraded = true;
            lease = Optional.empty();
            lockDegraded.increment();
            LOGGER.warn("Public-bank Redis refresh lease unavailable type={}; using PostgreSQL lock",
                    exception.getClass().getName());
        }

        if (!degraded && lease.isEmpty()) {
            refreshSuppressed.increment();
            return RefreshResult.suppressed();
        }

        Timer.Sample duration = Timer.start(meters);
        try {
            CommitResult commit;
            try {
                commit = Objects.requireNonNull(
                        snapshots.replace(projectionLoader), "snapshot replacement result");
                refreshSuccess.increment();
            } catch (RuntimeException exception) {
                refreshFailure.increment();
                throw exception;
            } finally {
                if (lease.isPresent()) {
                    degraded |= release(lease.orElseThrow());
                }
            }
            return degraded
                    ? RefreshResult.committedDegraded(commit)
                    : RefreshResult.committed(commit);
        } finally {
            duration.stop(refreshDuration);
        }
    }

    private boolean release(Lease lease) {
        try {
            if (leases.release(lease) == ReleaseOutcome.RELEASED) {
                return false;
            }
            lockDegraded.increment();
            LOGGER.warn("Public-bank Redis refresh lease expired or changed before release");
            return true;
        } catch (RuntimeException exception) {
            lockDegraded.increment();
            LOGGER.warn("Public-bank Redis refresh lease release failed type={}",
                    exception.getClass().getName());
            return true;
        }
    }

    public enum State {
        COMMITTED,
        COMMITTED_DEGRADED,
        SUPPRESSED
    }

    public record RefreshResult(State state, Optional<CommitResult> commit) {

        public RefreshResult {
            Objects.requireNonNull(state, "state");
            commit = Objects.requireNonNull(commit, "commit");
            if ((state == State.SUPPRESSED) == commit.isPresent()) {
                throw new IllegalArgumentException("Invalid public-bank refresh result");
            }
        }

        static RefreshResult committed(CommitResult commit) {
            return new RefreshResult(State.COMMITTED, Optional.of(commit));
        }

        static RefreshResult committedDegraded(CommitResult commit) {
            return new RefreshResult(State.COMMITTED_DEGRADED, Optional.of(commit));
        }

        static RefreshResult suppressed() {
            return new RefreshResult(State.SUPPRESSED, Optional.empty());
        }
    }
}
