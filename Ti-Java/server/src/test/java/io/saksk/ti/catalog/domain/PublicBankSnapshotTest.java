package io.saksk.ti.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class PublicBankSnapshotTest {

    private static final Instant NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final long GENERATION = 17;
    private static final String DIGEST = "a".repeat(64);
    private static final String OTHER_DIGEST = "b".repeat(64);

    @Test
    void appliesInclusiveFreshAndSoftStaleBoundaries() {
        PublicBankSnapshot.Assessment fresh = completeAt(NOW.minusSeconds(300)).assessAt(NOW);
        PublicBankSnapshot.Assessment softStart = completeAt(NOW.minusSeconds(301)).assessAt(NOW);
        PublicBankSnapshot.Assessment softEnd = completeAt(NOW.minusSeconds(900)).assessAt(NOW);

        assertThat(fresh.available()).isTrue();
        assertThat(fresh.freshness()).isEqualTo(PublicBankSnapshot.Freshness.FRESH);
        assertThat(fresh.age()).hasSeconds(300);
        assertThat(softStart.available()).isTrue();
        assertThat(softStart.freshness()).isEqualTo(PublicBankSnapshot.Freshness.SOFT_STALE);
        assertThat(softStart.age()).hasSeconds(301);
        assertThat(softEnd.available()).isTrue();
        assertThat(softEnd.freshness()).isEqualTo(PublicBankSnapshot.Freshness.SOFT_STALE);
        assertThat(softEnd.age()).hasSeconds(900);
    }

    @Test
    void rejectsHardExpiredFutureAndColdSnapshots() {
        assertThat(completeAt(NOW.minusSeconds(901)).assessAt(NOW).available()).isFalse();
        assertThat(completeAt(NOW.plusSeconds(1)).assessAt(NOW).available()).isFalse();
        assertThat(PublicBankSnapshot.cold().assessAt(NOW).available()).isFalse();
    }

    @Test
    void requiresCompleteMarkerStrongAuditFieldsAndExactSourceCounts() {
        assertThat(snapshot(true, "ready", DIGEST, "1", 3, 2, 1,
                boundary(3, DIGEST), boundary(4, DIGEST)).structurallyComplete()).isFalse();
        assertThat(snapshot(true, "complete", "digest", "1", 3, 2, 1,
                boundary(3, "digest"), boundary(4, "digest")).structurallyComplete())
                .isFalse();
        assertThat(snapshot(true, "complete", DIGEST, "v1", 3, 2, 1,
                boundary(3, DIGEST), boundary(4, DIGEST)).structurallyComplete()).isFalse();
        assertThat(snapshot(true, "complete", DIGEST, "1", 4, 2, 1,
                boundary(4, DIGEST), boundary(4, DIGEST)).structurallyComplete()).isFalse();
        assertThat(snapshot(false, "complete", DIGEST, "1", 3, 2, 1,
                boundary(3, DIGEST), boundary(4, DIGEST)).structurallyComplete()).isFalse();
    }

    @Test
    void rejectsMissingMixedGenerationOrWrongDigestBoundaries() {
        assertThat(snapshot(true, "complete", DIGEST, "1", 3, 2, 1,
                PublicBankSnapshot.ProjectionBoundary.empty(),
                boundary(4, DIGEST)).structurallyComplete()).isFalse();
        assertThat(snapshot(true, "complete", DIGEST, "1", 3, 2, 1,
                new PublicBankSnapshot.ProjectionBoundary(
                        GENERATION - 1, DIGEST, GENERATION, DIGEST),
                boundary(4, DIGEST)).structurallyComplete()).isFalse();
        assertThat(snapshot(true, "complete", DIGEST, "1", 3, 2, 1,
                boundary(3, DIGEST),
                new PublicBankSnapshot.ProjectionBoundary(
                        GENERATION, DIGEST, GENERATION, OTHER_DIGEST))
                .structurallyComplete()).isFalse();
    }

    @Test
    void acceptsExplicitCompleteEmptySnapshotWithEmptyBoundaries() {
        PublicBankSnapshot empty = new PublicBankSnapshot(
                true,
                GENERATION,
                "complete",
                NOW,
                0,
                0,
                0,
                0,
                DIGEST,
                "1",
                "source-0",
                PublicBankSnapshot.ProjectionBoundary.empty(),
                PublicBankSnapshot.ProjectionBoundary.empty());

        assertThat(empty.structurallyComplete()).isTrue();
        assertThat(empty.assessAt(NOW).freshness()).isEqualTo(PublicBankSnapshot.Freshness.FRESH);
    }

    private static PublicBankSnapshot completeAt(Instant lastSuccessAt) {
        return new PublicBankSnapshot(
                true,
                GENERATION,
                "complete",
                lastSuccessAt,
                3,
                4,
                2,
                1,
                DIGEST,
                "1",
                "source-9",
                boundary(3, DIGEST),
                boundary(4, DIGEST));
    }

    private static PublicBankSnapshot snapshot(
            boolean markerPresent,
            String status,
            String projectionDigest,
            String schemaVersion,
            long metricsCount,
            long systemCount,
            long userPublicCount,
            PublicBankSnapshot.ProjectionBoundary metricsBoundary,
            PublicBankSnapshot.ProjectionBoundary viewerBoundary
    ) {
        return new PublicBankSnapshot(
                markerPresent,
                GENERATION,
                status,
                NOW,
                metricsCount,
                4,
                systemCount,
                userPublicCount,
                projectionDigest,
                schemaVersion,
                "source-9",
                metricsBoundary,
                viewerBoundary);
    }

    private static PublicBankSnapshot.ProjectionBoundary boundary(long count, String digest) {
        return count == 0
                ? PublicBankSnapshot.ProjectionBoundary.empty()
                : new PublicBankSnapshot.ProjectionBoundary(
                        GENERATION, digest, GENERATION, digest);
    }
}
