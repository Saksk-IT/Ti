package io.saksk.ti.catalog.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral optional subject filter for the catalog-owned question export snapshot. */
public record QuestionExportQuery(Optional<Integer> subjectId) {

    public QuestionExportQuery {
        subjectId = Objects.requireNonNull(subjectId, "subjectId");
    }
}
