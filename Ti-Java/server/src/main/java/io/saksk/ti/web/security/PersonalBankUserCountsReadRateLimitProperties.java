package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.util.Objects;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.personal-bank-user-counts-read-rate-limit")
public final class PersonalBankUserCountsReadRateLimitProperties {

    private static final int MINIMUM_SECRET_BYTES = 32;

    private final String namespace;
    private final int requestsPerSecond;
    private final int requestsPerHour;
    private final int requestsPerDay;
    private final int multiplier;
    private final String keySecret;

    public PersonalBankUserCountsReadRateLimitProperties(
            String namespace,
            int requestsPerSecond,
            int requestsPerHour,
            int requestsPerDay,
            int multiplier,
            String keySecret
    ) {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe user-counts rate-limit namespace");
        }
        if (requestsPerSecond < 1
                || requestsPerHour < requestsPerSecond
                || requestsPerDay < requestsPerHour) {
            throw new IllegalArgumentException("Invalid user-counts base rate limits");
        }
        if (multiplier < 1 || multiplier > 1_000) {
            throw new IllegalArgumentException(
                    "User-counts rate-limit multiplier must be 1..1000");
        }
        this.keySecret = Objects.requireNonNull(keySecret, "keySecret");
        if (keySecret.getBytes(StandardCharsets.UTF_8).length < MINIMUM_SECRET_BYTES) {
            throw new IllegalArgumentException(
                    "User-counts rate-limit key secret must contain at least 32 bytes");
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

    byte[] keySecretBytes() {
        return keySecret.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String toString() {
        return "PersonalBankUserCountsReadRateLimitProperties[namespace=" + namespace
                + ", requestsPerSecond=" + requestsPerSecond
                + ", requestsPerHour=" + requestsPerHour
                + ", requestsPerDay=" + requestsPerDay
                + ", multiplier=" + multiplier
                + ", keySecret=<redacted>]";
    }

    private int effectiveLimit(int base) {
        return Math.toIntExact(Math.multiplyExact((long) base, multiplier));
    }
}
