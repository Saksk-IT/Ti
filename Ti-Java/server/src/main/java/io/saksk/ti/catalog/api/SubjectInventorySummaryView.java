package io.saksk.ti.catalog.api;

import java.util.Objects;

/** Immutable raw inventory projection for one legacy subject row. */
public record SubjectInventorySummaryView(
        int id,
        String name,
        Boolean isLocked,
        long questionCount
) {

    public SubjectInventorySummaryView {
        Objects.requireNonNull(name, "name");
        if (questionCount < 0) {
            throw new IllegalArgumentException("questionCount must not be negative");
        }
    }
}
