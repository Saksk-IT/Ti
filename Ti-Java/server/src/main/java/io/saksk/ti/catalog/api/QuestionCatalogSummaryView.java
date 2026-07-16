package io.saksk.ti.catalog.api;

import java.time.LocalDateTime;
import java.util.Objects;

/** Immutable raw catalog summary for one legacy question row. */
public record QuestionCatalogSummaryView(
        long id,
        Long subjectId,
        String type,
        String content,
        Integer difficulty,
        String tagsRaw,
        String imagePathRaw,
        Long createdBy,
        LocalDateTime updatedAt
) {

    public QuestionCatalogSummaryView {
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(content, "content");
    }
}
