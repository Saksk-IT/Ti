package io.saksk.ti.catalog.api;

import java.util.Objects;

/** Immutable raw catalog context for one legacy subject row. */
public record SubjectContextView(int id, String name) {

    public SubjectContextView {
        Objects.requireNonNull(name, "name");
    }
}

