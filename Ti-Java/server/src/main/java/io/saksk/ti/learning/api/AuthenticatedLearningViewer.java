package io.saksk.ti.learning.api;

/** Server-derived caller identity for protected learning operations. */
public record AuthenticatedLearningViewer(long identityId) {

    public AuthenticatedLearningViewer {
        if (identityId <= 0L) {
            throw new IllegalArgumentException("identityId must be positive");
        }
    }
}
