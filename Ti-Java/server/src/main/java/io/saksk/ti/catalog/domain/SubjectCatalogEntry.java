package io.saksk.ti.catalog.domain;

import java.util.Objects;

/** Catalog-owned subject and question-count projection in legacy ID order. */
public record SubjectCatalogEntry(int id, String name, long questionCount) {

    public SubjectCatalogEntry {
        if (id <= 0 || questionCount < 0) {
            throw new IllegalArgumentException("invalid subject catalog entry");
        }
        name = Objects.requireNonNull(name, "name");
    }
}
