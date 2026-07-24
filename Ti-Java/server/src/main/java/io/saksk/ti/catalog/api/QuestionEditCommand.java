package io.saksk.ti.catalog.api;

import java.util.Objects;
import java.util.Optional;

/**
 * HTTP-neutral question edit.
 *
 * <p>{@code optionsJsonOrText}, when present, contains either the original string value or the
 * JSON serialization of a structured request value. A missing or JSON-null request field is
 * represented by {@link Optional#empty()} and therefore retains the existing options.
 */
public record QuestionEditCommand(
        QuestionEditorIdentity editor,
        long questionId,
        Optional<String> content,
        Optional<String> questionType,
        Optional<String> answer,
        Optional<String> explanation,
        Optional<String> optionsJsonOrText,
        QuestionEditIdempotencyKey idempotencyKey
) {

    public QuestionEditCommand {
        editor = Objects.requireNonNull(editor, "editor");
        if (questionId < 0) {
            throw new IllegalArgumentException("questionId must not be negative");
        }
        content = requireOptional(content, "content");
        questionType = requireOptional(questionType, "questionType");
        answer = requireOptional(answer, "answer");
        explanation = requireOptional(explanation, "explanation");
        optionsJsonOrText = requireOptional(optionsJsonOrText, "optionsJsonOrText");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "QuestionEditCommand[editor=<redacted>, questionId=" + questionId
                + ", content=<redacted>, questionType=<redacted>, answer=<redacted>"
                + ", explanation=<redacted>, optionsJsonOrText=<redacted>"
                + ", idempotencyKey=<redacted>]";
    }

    private static Optional<String> requireOptional(Optional<String> value, String name) {
        return Objects.requireNonNull(value, name);
    }
}
