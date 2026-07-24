package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived command for marking or unmarking one review item as mastered. */
public record StudyReviewMasterCommand(
        AuthenticatedLearningViewer viewer,
        long questionId,
        boolean mastered,
        StudyScopeInput scope,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public StudyReviewMasterCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        scope = Objects.requireNonNull(scope, "scope");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "StudyReviewMasterCommand[viewer=<redacted>, questionId=" + questionId
                + ", mastered=" + mastered
                + ", scope=<redacted>, idempotencyKey=<redacted>]";
    }
}
