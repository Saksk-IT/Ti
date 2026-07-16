package io.saksk.ti.identity.infrastructure.security;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Objects;

final class LegacyAuthenticationMetrics {

    private final Counter acceptedJwt;
    private final Counter rejectedJwt;
    private final Counter acceptedFlaskSession;
    private final Counter rejectedFlaskSession;

    LegacyAuthenticationMetrics(MeterRegistry registry) {
        Objects.requireNonNull(registry, "registry");
        acceptedJwt = counter(registry, "jwt", "accepted");
        rejectedJwt = counter(registry, "jwt", "rejected");
        acceptedFlaskSession = counter(registry, "flask_session", "accepted");
        rejectedFlaskSession = counter(registry, "flask_session", "rejected");
    }

    void recordJwt(boolean accepted) {
        increment(accepted ? acceptedJwt : rejectedJwt);
    }

    void recordFlaskSession(boolean accepted) {
        increment(accepted ? acceptedFlaskSession : rejectedFlaskSession);
    }

    private static Counter counter(MeterRegistry registry, String format, String outcome) {
        return Counter.builder("ti.security.legacy.authentication")
                .description("Temporary legacy authentication compatibility outcomes")
                .tag("format", format)
                .tag("outcome", outcome)
                .register(registry);
    }

    private static void increment(Counter counter) {
        try {
            counter.increment();
        } catch (RuntimeException ignored) {
            // Authentication decisions must not depend on a metrics backend.
        }
    }
}
