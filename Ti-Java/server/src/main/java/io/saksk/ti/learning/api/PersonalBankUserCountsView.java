package io.saksk.ti.learning.api;

import java.util.List;
import java.util.Objects;

/** Immutable legacy-compatible personal-bank counts and display type projection. */
public record PersonalBankUserCountsView(
        long total,
        long favorites,
        long mistakes,
        List<String> types,
        boolean shuffleOptionsAvailable
) {

    public PersonalBankUserCountsView {
        if (total < 0L || favorites < 0L || mistakes < 0L) {
            throw new IllegalArgumentException("user counts must be non-negative");
        }
        types = List.copyOf(Objects.requireNonNull(types, "types"));
    }
}
