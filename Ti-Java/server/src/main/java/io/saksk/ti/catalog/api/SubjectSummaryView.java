package io.saksk.ti.catalog.api;

import java.util.Objects;

/** Immutable catalog projection used by compatibility HTTP adapters. */
public record SubjectSummaryView(int id, String name, long questionCount) {

    public SubjectSummaryView {
        if (id <= 0 || questionCount < 0) {
            throw new IllegalArgumentException("invalid subject summary");
        }
        name = Objects.requireNonNull(name, "name");
    }
}
