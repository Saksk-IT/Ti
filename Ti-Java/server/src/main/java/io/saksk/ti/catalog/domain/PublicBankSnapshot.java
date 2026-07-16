package io.saksk.ti.catalog.domain;

import java.time.Duration;
import java.time.Instant;

/** Complete marker plus constant-time first/last projection-boundary evidence. */
public record PublicBankSnapshot(
        boolean markerPresent,
        long generation,
        String status,
        Instant lastSuccessAt,
        long expectedMetricsCount,
        long expectedViewerStateCount,
        long expectedSystemCount,
        long expectedUserPublicCount,
        String projectionDigest,
        String projectorSchemaVersion,
        String sourceHighWatermark,
        ProjectionBoundary metricsBoundary,
        ProjectionBoundary viewerBoundary
) {

    private static final Duration FRESH_LIMIT = Duration.ofSeconds(300);
    private static final Duration HARD_LIMIT = Duration.ofSeconds(900);

    public static PublicBankSnapshot cold() {
        return new PublicBankSnapshot(
                false, 0, null, null,
                0, 0, 0, 0,
                null, null, null,
                ProjectionBoundary.empty(), ProjectionBoundary.empty());
    }

    public Assessment assessAt(Instant now) {
        if (!structurallyComplete() || now == null) {
            return Assessment.unavailable();
        }
        Duration age = Duration.between(lastSuccessAt, now);
        if (age.isNegative() || age.compareTo(HARD_LIMIT) > 0) {
            return Assessment.unavailable();
        }
        Freshness freshness = age.compareTo(FRESH_LIMIT) <= 0
                ? Freshness.FRESH
                : Freshness.SOFT_STALE;
        return new Assessment(freshness, age);
    }

    public boolean structurallyComplete() {
        return markerPresent
                && generation > 0
                && "complete".equals(status)
                && lastSuccessAt != null
                && validDigest(projectionDigest)
                && validSchemaVersion(projectorSchemaVersion)
                && notBlank(sourceHighWatermark)
                && allCountsNonnegative()
                && expectedMetricsCount == expectedSystemCount + expectedUserPublicCount
                && boundaryMatches(expectedMetricsCount, metricsBoundary)
                && boundaryMatches(expectedViewerStateCount, viewerBoundary);
    }

    private boolean allCountsNonnegative() {
        return expectedMetricsCount >= 0
                && expectedViewerStateCount >= 0
                && expectedSystemCount >= 0
                && expectedUserPublicCount >= 0;
    }

    private boolean boundaryMatches(long count, ProjectionBoundary boundary) {
        if (boundary == null) {
            return false;
        }
        if (count == 0) {
            return boundary.emptyBoundary();
        }
        return boundary.firstGeneration() != null
                && boundary.lastGeneration() != null
                && boundary.firstGeneration() == generation
                && boundary.lastGeneration() == generation
                && projectionDigest.equals(boundary.firstDigest())
                && projectionDigest.equals(boundary.lastDigest());
    }

    private static boolean validDigest(String value) {
        return value != null && value.matches("[0-9a-f]{64}");
    }

    private static boolean validSchemaVersion(String value) {
        return value != null && value.matches("[1-9][0-9]*");
    }

    private static boolean notBlank(String value) {
        return value != null && !value.isBlank();
    }

    public record ProjectionBoundary(
            Long firstGeneration,
            String firstDigest,
            Long lastGeneration,
            String lastDigest
    ) {

        public static ProjectionBoundary empty() {
            return new ProjectionBoundary(null, null, null, null);
        }

        boolean emptyBoundary() {
            return firstGeneration == null
                    && firstDigest == null
                    && lastGeneration == null
                    && lastDigest == null;
        }
    }

    public enum Freshness {
        FRESH,
        SOFT_STALE,
        UNAVAILABLE
    }

    public record Assessment(Freshness freshness, Duration age) {

        public Assessment {
            if (freshness == null || age == null || age.isNegative()) {
                throw new IllegalArgumentException("Invalid snapshot assessment");
            }
        }

        public static Assessment unavailable() {
            return new Assessment(Freshness.UNAVAILABLE, Duration.ZERO);
        }

        public boolean available() {
            return freshness != Freshness.UNAVAILABLE;
        }
    }
}
