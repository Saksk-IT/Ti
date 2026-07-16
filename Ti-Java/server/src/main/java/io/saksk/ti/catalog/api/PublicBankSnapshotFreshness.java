package io.saksk.ti.catalog.api;

import java.time.Instant;
import java.util.Objects;

/** Internal observability view; compatibility HTTP bodies do not expose this value. */
public record PublicBankSnapshotFreshness(
        long generation,
        Instant lastSuccessAt,
        long ageSeconds,
        State state
) {

    public enum State {
        FRESH,
        SOFT_STALE
    }

    public PublicBankSnapshotFreshness {
        Objects.requireNonNull(lastSuccessAt, "lastSuccessAt");
        Objects.requireNonNull(state, "state");
        if (generation < 0 || ageSeconds < 0) {
            throw new IllegalArgumentException("snapshot freshness values must be nonnegative");
        }
    }
}
