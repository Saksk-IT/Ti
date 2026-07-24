package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import java.util.Objects;
import java.util.Optional;

/** Transaction-local row-lock and mutation boundary for catalog-owned questions. */
public interface QuestionEditStatePort {

    Optional<QuestionEditSnapshot> findForUpdate(long questionId);

    void update(QuestionEditMutation mutation);

    record QuestionEditSnapshot(
            QuestionCatalogRecordView question,
            String subjectName
    ) {
        public QuestionEditSnapshot {
            question = Objects.requireNonNull(question, "question");
            subjectName = Objects.requireNonNull(subjectName, "subjectName");
        }
    }

    record QuestionEditMutation(
            long questionId,
            String type,
            String content,
            String optionsJson,
            String answerJson,
            String analysis,
            String tagsJson,
            int difficulty
    ) {
        public QuestionEditMutation {
            if (questionId < 0) {
                throw new IllegalArgumentException("questionId must not be negative");
            }
            type = Objects.requireNonNull(type, "type");
            content = Objects.requireNonNull(content, "content");
            optionsJson = Objects.requireNonNull(optionsJson, "optionsJson");
            answerJson = Objects.requireNonNull(answerJson, "answerJson");
            analysis = Objects.requireNonNull(analysis, "analysis");
            tagsJson = Objects.requireNonNull(tagsJson, "tagsJson");
            if (difficulty < 1 || difficulty > 5) {
                throw new IllegalArgumentException("difficulty must be between 1 and 5");
            }
        }
    }
}
