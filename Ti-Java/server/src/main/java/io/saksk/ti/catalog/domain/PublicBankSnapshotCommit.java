package io.saksk.ti.catalog.domain;

import java.time.Instant;
import java.util.Objects;

/** Auditable metadata attached to one atomically completed projection generation. */
public record PublicBankSnapshotCommit(
        Instant completedAt,
        int projectorSchemaVersion,
        String sourceHighWatermark
) {

    public PublicBankSnapshotCommit {
        Objects.requireNonNull(completedAt, "completedAt");
        if (projectorSchemaVersion <= 0) {
            throw new IllegalArgumentException("projectorSchemaVersion must be positive");
        }
        if (sourceHighWatermark == null || sourceHighWatermark.isBlank()) {
            throw new IllegalArgumentException("sourceHighWatermark must not be blank");
        }
    }
}
