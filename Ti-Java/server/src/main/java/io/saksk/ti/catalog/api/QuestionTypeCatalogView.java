package io.saksk.ti.catalog.api;

import java.util.List;

/** Immutable question-type catalog returned by the metadata application boundary. */
public record QuestionTypeCatalogView(List<String> questionTypes) {

    public QuestionTypeCatalogView {
        questionTypes = List.copyOf(questionTypes);
    }
}
