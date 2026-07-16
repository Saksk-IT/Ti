package io.saksk.ti.web.security;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.csrf-issuance-rate-limit")
public record CsrfIssuanceRateLimitProperties(
        String namespace,
        int requestsPerMinute,
        int globalRequestsPerMinute,
        Duration anonymousSessionTimeout
) {

    public CsrfIssuanceRateLimitProperties {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe CSRF issuance rate-limit namespace");
        }
        if (requestsPerMinute < 1 || requestsPerMinute > 100_000) {
            throw new IllegalArgumentException(
                    "CSRF issuance rate limit must be between 1 and 100000");
        }
        if (globalRequestsPerMinute < requestsPerMinute
                || globalRequestsPerMinute > 100_000) {
            throw new IllegalArgumentException(
                    "Global CSRF issuance rate limit must cover the per-IP limit and be at most 100000");
        }
        if (anonymousSessionTimeout == null
                || anonymousSessionTimeout.compareTo(Duration.ofMinutes(1)) < 0
                || anonymousSessionTimeout.compareTo(Duration.ofHours(1)) > 0) {
            throw new IllegalArgumentException(
                    "Anonymous CSRF session timeout must be between one minute and one hour");
        }
    }
}
