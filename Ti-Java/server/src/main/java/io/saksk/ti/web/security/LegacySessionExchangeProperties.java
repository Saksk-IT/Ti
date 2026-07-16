package io.saksk.ti.web.security;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.legacy-session-exchange")
public record LegacySessionExchangeProperties(
        String namespace,
        int requestsPerMinute,
        int globalRequestsPerMinute,
        int maxExchangesPerIdentity,
        int maxReplayMarkers,
        Duration replayMarkerTtl
) {

    public LegacySessionExchangeProperties {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe legacy Session exchange namespace");
        }
        if (requestsPerMinute < 1 || requestsPerMinute > 100_000) {
            throw new IllegalArgumentException(
                    "Legacy Session exchange rate limit must be between 1 and 100000");
        }
        if (globalRequestsPerMinute < requestsPerMinute
                || globalRequestsPerMinute > 100_000) {
            throw new IllegalArgumentException(
                    "Global legacy Session exchange limit must cover the per-IP limit and be at most 100000");
        }
        if (maxExchangesPerIdentity < 1 || maxExchangesPerIdentity > 10) {
            throw new IllegalArgumentException(
                    "Legacy Session exchanges per identity must be between 1 and 10");
        }
        if (maxReplayMarkers < maxExchangesPerIdentity || maxReplayMarkers > 100_000) {
            throw new IllegalArgumentException(
                    "Global legacy Session replay marker limit must cover the identity limit and be at most 100000");
        }
        if (!Duration.ofDays(7).equals(replayMarkerTtl)) {
            throw new IllegalArgumentException(
                    "Legacy Session replay marker TTL must cover the full seven-day credential lifetime");
        }
    }
}
