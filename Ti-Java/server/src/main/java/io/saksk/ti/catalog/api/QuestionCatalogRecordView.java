package io.saksk.ti.catalog.api;

import java.time.LocalDateTime;
import java.util.Objects;

/**
 * Immutable raw catalog fact for one legacy question row.
 *
 * <p>The raw text fields deliberately preserve malformed historical JSON so that each future
 * HTTP owner can apply its own reviewed compatibility projection without losing information.
 */
public record QuestionCatalogRecordView(
        long id,
        Long subjectId,
        String type,
        String content,
        String optionsRaw,
        String answerRaw,
        String analysis,
        String tagsRaw,
        Integer difficulty,
        String imagePathRaw,
        String source,
        Long createdBy,
        Long updatedBy,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {

    public QuestionCatalogRecordView {
        if (id < 0) {
            throw new IllegalArgumentException("id must not be negative");
        }
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(content, "content");
    }
}
