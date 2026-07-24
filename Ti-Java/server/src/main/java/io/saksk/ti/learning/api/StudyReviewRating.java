package io.saksk.ti.learning.api;

import java.util.Locale;
import java.util.Optional;

/** Legacy review rating values and their stable wire representation. */
public enum StudyReviewRating {
    KNOWN("known"),
    FUZZY("fuzzy"),
    UNKNOWN("unknown");

    private final String wireValue;

    StudyReviewRating(String wireValue) {
        this.wireValue = wireValue;
    }

    public String wireValue() {
        return wireValue;
    }

    public static Optional<StudyReviewRating> fromWireValue(String value) {
        if (value == null) {
            return Optional.empty();
        }
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        for (StudyReviewRating rating : values()) {
            if (rating.wireValue.equals(normalized)) {
                return Optional.of(rating);
            }
        }
        return Optional.empty();
    }
}
