package io.saksk.ti.learning.api;

import java.util.Objects;

/** Server-derived command for the legacy daily check-in write. */
public record CheckinCommand(
        AuthenticatedLearningViewer viewer,
        LearningWriteIdempotencyKey idempotencyKey
) {

    public CheckinCommand {
        viewer = Objects.requireNonNull(viewer, "viewer");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    }

    @Override
    public String toString() {
        return "CheckinCommand[viewer=<redacted>, idempotencyKey=<redacted>]";
    }
}
