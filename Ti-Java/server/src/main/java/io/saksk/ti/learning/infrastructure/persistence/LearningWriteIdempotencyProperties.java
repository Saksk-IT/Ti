package io.saksk.ti.learning.infrastructure.persistence;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Arrays;
import java.util.Objects;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.learning.write-idempotency")
public final class LearningWriteIdempotencyProperties {

    private static final int MINIMUM_SECRET_BYTES = 32;
    private static final int MAXIMUM_SECRET_BYTES = 1024;
    private static final Duration DEFAULT_RECEIPT_TTL = Duration.ofHours(24);
    private static final Duration MINIMUM_RECEIPT_TTL = Duration.ofMinutes(5);
    private static final Duration MAXIMUM_RECEIPT_TTL = Duration.ofDays(30);

    private final byte[] keySecret;
    private final Duration receiptTtl;

    public LearningWriteIdempotencyProperties(String keySecret, Duration receiptTtl) {
        byte[] secretBytes = Objects.requireNonNull(keySecret, "keySecret")
                .getBytes(StandardCharsets.UTF_8);
        if (secretBytes.length < MINIMUM_SECRET_BYTES
                || secretBytes.length > MAXIMUM_SECRET_BYTES) {
            throw new IllegalArgumentException(
                    "Learning write-idempotency key secret must contain between 32 and 1024"
                            + " UTF-8 bytes");
        }
        receiptTtl = receiptTtl == null ? DEFAULT_RECEIPT_TTL : receiptTtl;
        if (receiptTtl.compareTo(MINIMUM_RECEIPT_TTL) < 0
                || receiptTtl.compareTo(MAXIMUM_RECEIPT_TTL) > 0) {
            throw new IllegalArgumentException(
                    "Learning write-idempotency receipt TTL must be between 5 minutes and 30 days");
        }
        this.keySecret = Arrays.copyOf(secretBytes, secretBytes.length);
        this.receiptTtl = receiptTtl;
    }

    byte[] keySecretBytes() {
        return Arrays.copyOf(keySecret, keySecret.length);
    }

    Duration receiptTtl() {
        return receiptTtl;
    }

    @Override
    public String toString() {
        return "LearningWriteIdempotencyProperties[keySecret=<redacted>, receiptTtl="
                + receiptTtl + "]";
    }
}
