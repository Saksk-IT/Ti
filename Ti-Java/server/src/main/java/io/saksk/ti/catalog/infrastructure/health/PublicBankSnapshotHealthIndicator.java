package io.saksk.ti.catalog.infrastructure.health;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotInspectionPort;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.infrastructure.coordination.PublicBankSnapshotProperties;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicLong;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/** Readiness participant for the public-bank projection once its production cutover is enabled. */
@Component
final class PublicBankSnapshotHealthIndicator implements HealthIndicator {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(PublicBankSnapshotHealthIndicator.class);
    private static final long UNAVAILABLE_AGE = -1;

    private final PublicBankSnapshotInspectionPort snapshots;
    private final PublicBankSnapshotProperties properties;
    private final Clock clock;
    private final AtomicLong ageSeconds = new AtomicLong(UNAVAILABLE_AGE);
    private final Map<UnavailableReason, Counter> unavailableCounters;

    @Autowired
    PublicBankSnapshotHealthIndicator(
            ObjectProvider<PublicBankSnapshotInspectionPort> snapshots,
            PublicBankSnapshotProperties properties,
            ObjectProvider<Clock> clock,
            MeterRegistry meters
    ) {
        this(
                snapshots.getIfAvailable(),
                properties,
                clock.getIfAvailable(Clock::systemUTC),
                meters);
    }

    PublicBankSnapshotHealthIndicator(
            PublicBankSnapshotInspectionPort snapshots,
            PublicBankSnapshotProperties properties,
            Clock clock,
            MeterRegistry meters
    ) {
        this.snapshots = snapshots;
        this.properties = Objects.requireNonNull(properties, "properties");
        this.clock = Objects.requireNonNull(clock, "clock");
        MeterRegistry registry = Objects.requireNonNull(meters, "meters");
        Gauge.builder("ti.catalog.public_bank.snapshot.age.seconds", ageSeconds, AtomicLong::get)
                .description("Age of an available or hard-expired complete public-bank snapshot,"
                        + " or -1 when age cannot be trusted")
                .baseUnit("seconds")
                .register(registry);
        EnumMap<UnavailableReason, Counter> counters = new EnumMap<>(UnavailableReason.class);
        for (UnavailableReason reason : UnavailableReason.values()) {
            counters.put(reason, Counter.builder(
                            "ti.catalog.public_bank.snapshot.readiness.unavailable")
                    .description("Public-bank snapshot readiness failures by bounded reason")
                    .tag("reason", reason.value)
                    .register(registry));
        }
        this.unavailableCounters = Map.copyOf(counters);
    }

    @Override
    public Health health() {
        if (!properties.readinessEnabled()) {
            ageSeconds.set(UNAVAILABLE_AGE);
            return Health.up().withDetail("participation", "disabled").build();
        }

        if (snapshots == null) {
            return unavailable(UnavailableReason.INSPECTION_UNAVAILABLE, UNAVAILABLE_AGE);
        }

        try {
            PublicBankSnapshot snapshot = Objects.requireNonNull(
                    snapshots.inspect(), "snapshot inspection result");
            if (!snapshot.markerPresent()) {
                return unavailable(UnavailableReason.COLD, UNAVAILABLE_AGE);
            }
            if (!snapshot.structurallyComplete()) {
                return unavailable(UnavailableReason.PARTIAL, UNAVAILABLE_AGE);
            }

            Instant now = clock.instant();
            Duration observedAge = Duration.between(snapshot.lastSuccessAt(), now);
            if (observedAge.isNegative()) {
                return unavailable(UnavailableReason.CLOCK_SKEW, UNAVAILABLE_AGE);
            }

            PublicBankSnapshot.Assessment assessment = snapshot.assessAt(now);
            if (!assessment.available()) {
                return unavailable(
                        UnavailableReason.HARD_EXPIRED,
                        observedAge.toSeconds());
            }
            ageSeconds.set(assessment.age().toSeconds());
            return Health.up()
                    .withDetail("generation", snapshot.generation())
                    .withDetail("freshness", assessment.freshness().name().toLowerCase())
                    .build();
        } catch (RuntimeException exception) {
            LOGGER.warn("Public-bank snapshot readiness inspection failed type={}",
                    exception.getClass().getName());
            return unavailable(UnavailableReason.INSPECTION_FAILED, UNAVAILABLE_AGE);
        }
    }

    private Health unavailable(UnavailableReason reason, long observableAgeSeconds) {
        ageSeconds.set(observableAgeSeconds);
        unavailableCounters.get(reason).increment();
        return Health.down().withDetail("reason", reason.value).build();
    }

    private enum UnavailableReason {
        COLD("cold"),
        PARTIAL("partial"),
        HARD_EXPIRED("hard_expired"),
        CLOCK_SKEW("clock_skew"),
        INSPECTION_UNAVAILABLE("inspection_unavailable"),
        INSPECTION_FAILED("inspection_failed");

        private final String value;

        UnavailableReason(String value) {
            this.value = value;
        }
    }
}
