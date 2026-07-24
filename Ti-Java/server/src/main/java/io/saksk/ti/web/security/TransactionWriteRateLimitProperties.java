package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.util.Objects;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.transaction-write-rate-limit")
public final class TransactionWriteRateLimitProperties {

    private final String namespace;
    private final int multiplier;
    private final String keySecret;

    public TransactionWriteRateLimitProperties(
            String namespace,
            int multiplier,
            String keySecret
    ) {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException(
                    "Unsafe transaction-write rate-limit namespace");
        }
        if (multiplier < 1 || multiplier > 1_000) {
            throw new IllegalArgumentException(
                    "Transaction-write rate-limit multiplier must be 1..1000");
        }
        this.keySecret = Objects.requireNonNull(keySecret, "keySecret");
        if (keySecret.getBytes(StandardCharsets.UTF_8).length < 32) {
            throw new IllegalArgumentException(
                    "Transaction-write rate-limit key secret must contain at least 32 bytes");
        }
        this.namespace = namespace;
        this.multiplier = multiplier;
    }

    public String namespace() {
        return namespace;
    }

    public int effectiveLimit(int baseLimit) {
        if (baseLimit < 1) {
            throw new IllegalArgumentException("baseLimit must be positive");
        }
        return Math.toIntExact(Math.multiplyExact((long) baseLimit, multiplier));
    }

    byte[] keySecretBytes() {
        return keySecret.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String toString() {
        return "TransactionWriteRateLimitProperties[namespace=" + namespace
                + ", multiplier=" + multiplier + ", keySecret=<redacted>]";
    }
}
