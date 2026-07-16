package io.saksk.ti.catalog.infrastructure.health;

import static org.assertj.core.api.Assertions.assertThat;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotInspectionPort;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.infrastructure.coordination.PublicBankSnapshotProperties;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

class PublicBankSnapshotHealthIndicatorTest {

    private static final Instant NOW = Instant.parse("2026-07-16T04:00:00Z");
    private static final String DIGEST = "a".repeat(64);
    private static final String UNAVAILABLE_COUNTER =
            "ti.catalog.public_bank.snapshot.readiness.unavailable";
    private static final Set<String> UNAVAILABLE_REASONS = Set.of(
            "cold",
            "partial",
            "hard_expired",
            "clock_skew",
            "inspection_unavailable",
            "inspection_failed");

    @Test
    void disabledShadowSliceStaysUpWithoutTouchingAnInactiveSchema() {
        AtomicInteger inspections = new AtomicInteger();
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        PublicBankSnapshotHealthIndicator indicator = indicator(
                () -> {
                    inspections.incrementAndGet();
                    throw new AssertionError("disabled readiness must not query the snapshot");
                },
                false,
                meters);

        Health health = indicator.health();

        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("participation", "disabled");
        assertThat(inspections).hasValue(0);
        assertGauge(meters, -1);
        assertUnavailableCounter(meters, null);
    }

    @Test
    void freshAndSoftStaleCompleteSnapshotsRemainReadyAndExposeAgeOnlyInternally() {
        SimpleMeterRegistry freshMeters = new SimpleMeterRegistry();
        Health fresh = indicator(() -> complete(Duration.ofSeconds(300)), true, freshMeters)
                .health();
        assertThat(fresh.getStatus()).isEqualTo(Status.UP);
        assertThat(fresh.getDetails()).containsEntry("freshness", "fresh");
        assertGauge(freshMeters, 300);
        assertUnavailableCounter(freshMeters, null);

        SimpleMeterRegistry staleMeters = new SimpleMeterRegistry();
        Health stale = indicator(() -> complete(Duration.ofSeconds(301)), true, staleMeters)
                .health();
        assertThat(stale.getStatus()).isEqualTo(Status.UP);
        assertThat(stale.getDetails()).containsEntry("freshness", "soft_stale");
        assertGauge(staleMeters, 301);
        assertUnavailableCounter(staleMeters, null);
    }

    @Test
    void unavailableStatesExposeBoundedReasonsCountersAndOnlyTrustHardExpiredAge() {
        List<UnavailableCase> cases = List.of(
                new UnavailableCase("cold", PublicBankSnapshot::cold, -1),
                new UnavailableCase("partial", PublicBankSnapshotHealthIndicatorTest::partial, -1),
                new UnavailableCase(
                        "hard_expired",
                        () -> complete(Duration.ofSeconds(901)),
                        901),
                new UnavailableCase(
                        "clock_skew",
                        () -> complete(Duration.ofSeconds(-1)),
                        -1),
                new UnavailableCase("inspection_unavailable", null, -1));

        for (UnavailableCase unavailableCase : cases) {
            SimpleMeterRegistry meters = new SimpleMeterRegistry();
            Health health = indicator(unavailableCase.inspection(), true, meters).health();

            assertThat(health.getStatus()).isEqualTo(Status.DOWN);
            assertThat(health.getDetails()).containsExactlyEntriesOf(
                    Map.of("reason", unavailableCase.reason()));
            assertGauge(meters, unavailableCase.expectedAge());
            assertUnavailableCounter(meters, unavailableCase.reason());
        }
    }

    @Test
    @ExtendWith(OutputCaptureExtension.class)
    void inspectionFailuresAreSafeDownResultsWithoutExceptionDetails(CapturedOutput output) {
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        Health health = indicator(
                () -> {
                    throw new IllegalStateException("jdbc:postgresql://secret-host/internal");
                },
                true,
                meters).health();

        assertThat(health.getStatus()).isEqualTo(Status.DOWN);
        assertThat(health.getDetails())
                .containsExactlyEntriesOf(java.util.Map.of("reason", "inspection_failed"));
        assertThat(health.toString()).doesNotContain("secret-host", "jdbc:postgresql");
        assertThat(output).doesNotContain("secret-host", "jdbc:postgresql", "/internal");
        assertGauge(meters, -1);
        assertUnavailableCounter(meters, "inspection_failed");
    }

    private static PublicBankSnapshotHealthIndicator indicator(
            PublicBankSnapshotInspectionPort snapshots,
            boolean enabled,
            SimpleMeterRegistry meters
    ) {
        return new PublicBankSnapshotHealthIndicator(
                snapshots,
                new PublicBankSnapshotProperties(
                        enabled, "test:public-bank-snapshot", Duration.ofMinutes(15)),
                Clock.fixed(NOW, ZoneOffset.UTC),
                meters);
    }

    private static PublicBankSnapshot complete(Duration age) {
        return new PublicBankSnapshot(
                true,
                7,
                "complete",
                NOW.minus(age),
                1,
                1,
                1,
                0,
                DIGEST,
                "1",
                "fixture:42",
                boundary(7, DIGEST),
                boundary(7, DIGEST));
    }

    private static PublicBankSnapshot partial() {
        PublicBankSnapshot complete = complete(Duration.ZERO);
        return new PublicBankSnapshot(
                complete.markerPresent(),
                complete.generation(),
                complete.status(),
                complete.lastSuccessAt(),
                complete.expectedMetricsCount(),
                complete.expectedViewerStateCount(),
                complete.expectedSystemCount(),
                complete.expectedUserPublicCount(),
                complete.projectionDigest(),
                complete.projectorSchemaVersion(),
                complete.sourceHighWatermark(),
                boundary(8, DIGEST),
                complete.viewerBoundary());
    }

    private static PublicBankSnapshot.ProjectionBoundary boundary(long generation, String digest) {
        return new PublicBankSnapshot.ProjectionBoundary(
                generation, digest, generation, digest);
    }

    private static void assertGauge(SimpleMeterRegistry meters, double expected) {
        assertThat(meters.get("ti.catalog.public_bank.snapshot.age.seconds").gauge().value())
                .isEqualTo(expected);
    }

    private static void assertUnavailableCounter(
            SimpleMeterRegistry meters,
            String incrementedReason
    ) {
        var counters = meters.find(UNAVAILABLE_COUNTER).counters();
        Set<String> actualReasons = new LinkedHashSet<>();
        counters.forEach(counter -> actualReasons.add(counter.getId().getTag("reason")));
        assertThat(actualReasons).containsExactlyInAnyOrderElementsOf(UNAVAILABLE_REASONS);
        for (String reason : UNAVAILABLE_REASONS) {
            double expected = reason.equals(incrementedReason) ? 1 : 0;
            assertThat(meters.get(UNAVAILABLE_COUNTER)
                            .tag("reason", reason)
                            .counter()
                            .count())
                    .as(reason)
                    .isEqualTo(expected);
        }
    }

    private record UnavailableCase(
            String reason,
            PublicBankSnapshotInspectionPort inspection,
            double expectedAge
    ) {}
}
