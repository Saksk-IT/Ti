package io.saksk.ti.catalog.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral optional filters for the catalog-owned raw question summary list. */
public record QuestionCatalogListQuery(
        Optional<Integer> subjectId,
        Optional<String> questionType
) {

    public QuestionCatalogListQuery {
        subjectId = Objects.requireNonNull(subjectId, "subjectId");
        questionType = Objects.requireNonNull(questionType, "questionType");
    }
}
