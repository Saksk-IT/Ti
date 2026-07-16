package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.domain.PublicBankProjectionBatch;
import io.saksk.ti.catalog.domain.PublicBankSnapshotCommit;
import java.util.Objects;
import java.util.function.Supplier;

/** Transactional write boundary for complete refreshes and immediate visibility tombstones. */
public interface PublicBankSnapshotMaintenancePort {

    CommitResult replace(PublicBankProjectionBatch projection);

    /**
     * Loads and replaces a projection inside the implementation's serialized transaction.
     *
     * <p>The default keeps simple test doubles and alternative implementations source-compatible;
     * transactional adapters should override this method so loading happens after their writer
     * boundary has been acquired. Implementations may invoke the loader again when retrying a
     * rolled-back transient database concurrency failure, so loaders must only read source state
     * and must not perform external non-transactional side effects or rely on exactly-once
     * invocation.</p>
     */
    default CommitResult replace(Supplier<PublicBankProjectionBatch> projectionLoader) {
        Objects.requireNonNull(projectionLoader, "projectionLoader");
        return replace(Objects.requireNonNull(
                projectionLoader.get(), "projectionLoader result"));
    }

    CommitResult tombstone(PublicBankRef reference, PublicBankSnapshotCommit commit);

    enum Outcome {
        COMMITTED,
        UNCHANGED
    }

    record CommitResult(Outcome outcome, long generation, String projectionDigest) {

        public CommitResult {
            if (outcome == null || generation <= 0) {
                throw new IllegalArgumentException("Invalid public-bank snapshot commit result");
            }
            if (projectionDigest == null
                    || !projectionDigest.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException("Invalid public-bank projection digest");
            }
        }
    }
}
