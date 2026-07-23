package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived command shared by the two legacy record-result aliases. */
public record RecordResultCommand(
        AuthenticatedLearningViewer viewer,
        long questionId,
        boolean correct,
        boolean clearMistakeOnCorrect,
        QuizLimitPolicy quizLimitPolicy,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public RecordResultCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        quizLimitPolicy = Objects.requireNonNull(quizLimitPolicy, "quizLimitPolicy");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "RecordResultCommand[viewer=<redacted>, questionId=" + questionId
                + ", correct=" + correct
                + ", clearMistakeOnCorrect=" + clearMistakeOnCorrect
                + ", quizLimitPolicy=<redacted>, idempotencyKey=<redacted>]";
    }
}
