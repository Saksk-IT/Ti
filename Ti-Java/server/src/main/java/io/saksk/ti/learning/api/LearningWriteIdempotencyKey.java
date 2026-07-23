package io.saksk.ti.learning.api;

import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.Optional;

/** Optional raw idempotency key whose diagnostic representation is always redacted. */
public final class LearningWriteIdempotencyKey {

    private static final LearningWriteIdempotencyKey ABSENT =
            new LearningWriteIdempotencyKey(null);

    private final String value;

    private LearningWriteIdempotencyKey(String value) {
        this.value = value;
    }

    public static LearningWriteIdempotencyKey absent() {
        return ABSENT;
    }

    public static LearningWriteIdempotencyKey fromNullable(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return absent();
        }
        return of(rawValue);
    }

    public static LearningWriteIdempotencyKey of(String rawValue) {
        Objects.requireNonNull(rawValue, "rawValue");
        int length = rawValue.getBytes(StandardCharsets.UTF_8).length;
        if (rawValue.isBlank() || length > 255) {
            throw new IllegalArgumentException(
                    "Idempotency-Key must contain between 1 and 255 UTF-8 bytes");
        }
        return new LearningWriteIdempotencyKey(rawValue);
    }

    public Optional<String> value() {
        return Optional.ofNullable(value);
    }

    public boolean isPresent() {
        return value != null;
    }

    @Override
    public String toString() {
        return "LearningWriteIdempotencyKey[<redacted>]";
    }
}
