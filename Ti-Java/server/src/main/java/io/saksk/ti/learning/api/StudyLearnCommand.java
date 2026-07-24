package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived command for the legacy study learn transition. */
public record StudyLearnCommand(
        AuthenticatedLearningViewer viewer,
        long questionId,
        boolean correct,
        StudyScopeInput scope,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public StudyLearnCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        scope = Objects.requireNonNull(scope, "scope");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "StudyLearnCommand[viewer=<redacted>, questionId=" + questionId
                + ", correct=" + correct
                + ", scope=<redacted>, idempotencyKey=<redacted>]";
    }
}
