package io.saksk.ti.catalog.api;

import java.util.Objects;

/** Immutable raw catalog fact for one legacy subject row. */
public record SubjectCatalogRecordView(int id, String name) {

    public SubjectCatalogRecordView {
        Objects.requireNonNull(name, "name");
    }
}
