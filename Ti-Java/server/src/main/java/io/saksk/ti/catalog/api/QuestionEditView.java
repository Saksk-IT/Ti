package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** User-independent legacy response projection returned by the catalog edit transaction. */
public record QuestionEditView(
        long id,
        String content,
        String questionType,
        List<QuestionEditOptionView> options,
        String answer,
        String explanation,
        Optional<String> imagePath,
        String subject
) {

    public QuestionEditView {
        if (id < 0) {
            throw new IllegalArgumentException("id must not be negative");
        }
        content = Objects.requireNonNull(content, "content");
        questionType = Objects.requireNonNull(questionType, "questionType");
        options = List.copyOf(Objects.requireNonNull(options, "options"));
        answer = Objects.requireNonNull(answer, "answer");
        explanation = Objects.requireNonNull(explanation, "explanation");
        imagePath = Objects.requireNonNull(imagePath, "imagePath");
        subject = Objects.requireNonNull(subject, "subject");
    }
}
