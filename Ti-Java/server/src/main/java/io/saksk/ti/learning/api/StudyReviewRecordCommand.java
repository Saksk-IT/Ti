package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived command for one spaced-review rating transition. */
public record StudyReviewRecordCommand(
        AuthenticatedLearningViewer viewer,
        long questionId,
        StudyReviewRating rating,
        StudyScopeInput scope,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public StudyReviewRecordCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        rating = Objects.requireNonNull(rating, "rating");
        scope = Objects.requireNonNull(scope, "scope");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "StudyReviewRecordCommand[viewer=<redacted>, questionId=" + questionId
                + ", rating=" + rating
                + ", scope=<redacted>, idempotencyKey=<redacted>]";
    }
}
