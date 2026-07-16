package io.saksk.ti.catalog.api;

/**
 * Immutable raw catalog row used by future export adapters.
 *
 * <p>Every historical value remains unprojected, including nullable fields and malformed JSON
 * text. Transport-specific defaults and JSON parsing belong to the owning operations adapter.
 */
public record QuestionExportRecordView(
        long id,
        Long subjectId,
        String subjectName,
        String type,
        String content,
        String optionsRaw,
        String answerRaw,
        String analysis,
        Integer difficulty,
        String tagsRaw
) {
}
