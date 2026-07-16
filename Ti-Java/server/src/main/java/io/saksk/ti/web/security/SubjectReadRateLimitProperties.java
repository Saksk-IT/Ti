package io.saksk.ti.web.security;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.subject-read-rate-limit")
public final class SubjectReadRateLimitProperties {

    private final String namespace;
    private final int requestsPerMinute;
    private final int requestsPerHour;
    private final int multiplier;

    public SubjectReadRateLimitProperties(
            String namespace,
            int requestsPerMinute,
            int requestsPerHour,
            int multiplier
    ) {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe subject-read rate-limit namespace");
        }
        if (requestsPerMinute < 1 || requestsPerHour < requestsPerMinute) {
            throw new IllegalArgumentException("Invalid subject-read base rate limits");
        }
        if (multiplier < 1 || multiplier > 1_000) {
            throw new IllegalArgumentException("Subject-read rate-limit multiplier must be 1..1000");
        }
        this.namespace = namespace;
        this.requestsPerMinute = requestsPerMinute;
        this.requestsPerHour = requestsPerHour;
        this.multiplier = multiplier;
        effectiveLimit(requestsPerMinute);
        effectiveLimit(requestsPerHour);
    }

    public String namespace() {
        return namespace;
    }

    public int requestsPerMinute() {
        return effectiveLimit(requestsPerMinute);
    }

    public int requestsPerHour() {
        return effectiveLimit(requestsPerHour);
    }

    public int multiplier() {
        return multiplier;
    }

    private int effectiveLimit(int base) {
        return Math.toIntExact(Math.multiplyExact((long) base, multiplier));
    }
}
