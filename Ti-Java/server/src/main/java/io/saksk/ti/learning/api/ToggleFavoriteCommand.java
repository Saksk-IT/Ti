package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived favorite-toggle command. */
public record ToggleFavoriteCommand(
        AuthenticatedLearningViewer viewer,
        long questionId,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public ToggleFavoriteCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "ToggleFavoriteCommand[viewer=<redacted>, questionId=" + questionId
                + ", idempotencyKey=<redacted>]";
    }
}
