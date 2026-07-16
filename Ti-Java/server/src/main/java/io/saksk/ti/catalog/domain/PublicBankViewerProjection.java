package io.saksk.ti.catalog.domain;

import io.saksk.ti.catalog.api.PublicBankRef;
import java.time.Instant;
import java.util.Objects;

/** Rebuildable viewer relation/activity row for a complete public-bank snapshot. */
public record PublicBankViewerProjection(
        long identityId,
        PublicBankRef reference,
        boolean hasPublic,
        boolean hasShared,
        Instant lastActivityAt
) {

    public PublicBankViewerProjection {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
        Objects.requireNonNull(reference, "reference");
        if (reference.id() <= 0) {
            throw new IllegalArgumentException("projection source ID must be positive");
        }
        if (!hasPublic && !hasShared && lastActivityAt == null) {
            throw new IllegalArgumentException(
                    "viewer projection must contain a relation or activity timestamp");
        }
    }
}
