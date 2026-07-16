package io.saksk.ti.web.security;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.public-bank-read-rate-limit")
public final class PublicBankReadRateLimitProperties {

    private final String namespace;
    private final int requestsPerSecond;
    private final int requestsPerHour;
    private final int requestsPerDay;
    private final int multiplier;

    public PublicBankReadRateLimitProperties(
            String namespace,
            int requestsPerSecond,
            int requestsPerHour,
            int requestsPerDay,
            int multiplier
    ) {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe public-bank rate-limit namespace");
        }
        if (requestsPerSecond < 1
                || requestsPerHour < requestsPerSecond
                || requestsPerDay < requestsPerHour) {
            throw new IllegalArgumentException("Invalid public-bank base rate limits");
        }
        if (multiplier < 1 || multiplier > 1_000) {
            throw new IllegalArgumentException(
                    "Public-bank rate-limit multiplier must be 1..1000");
        }
        this.namespace = namespace;
        this.requestsPerSecond = requestsPerSecond;
        this.requestsPerHour = requestsPerHour;
        this.requestsPerDay = requestsPerDay;
        this.multiplier = multiplier;
        effectiveLimit(requestsPerSecond);
        effectiveLimit(requestsPerHour);
        effectiveLimit(requestsPerDay);
    }

    public String namespace() {
        return namespace;
    }

    public int requestsPerSecond() {
        return effectiveLimit(requestsPerSecond);
    }

    public int requestsPerHour() {
        return effectiveLimit(requestsPerHour);
    }

    public int requestsPerDay() {
        return effectiveLimit(requestsPerDay);
    }

    public int multiplier() {
        return multiplier;
    }

    private int effectiveLimit(int base) {
        return Math.toIntExact(Math.multiplyExact((long) base, multiplier));
    }
}
