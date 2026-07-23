package io.saksk.ti.learning.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral outcome for the two legacy public-question favorite aliases. */
public record ToggleFavoriteResult(
        Outcome outcome,
        Optional<Boolean> favorite,
        boolean replayed
) {

    public ToggleFavoriteResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        favorite = Objects.requireNonNull(favorite, "favorite");
        if ((outcome == Outcome.SUCCESS) != favorite.isPresent()) {
            throw new IllegalArgumentException(
                    "Favorite state must be present exactly for a successful outcome");
        }
        if (replayed && outcome != Outcome.SUCCESS) {
            throw new IllegalArgumentException("Only a successful outcome may be replayed");
        }
    }

    public static ToggleFavoriteResult success(boolean favorite, boolean replayed) {
        return new ToggleFavoriteResult(Outcome.SUCCESS, Optional.of(favorite), replayed);
    }

    public static ToggleFavoriteResult questionNotFound() {
        return new ToggleFavoriteResult(Outcome.QUESTION_NOT_FOUND, Optional.empty(), false);
    }

    public static ToggleFavoriteResult subjectAccessDenied() {
        return new ToggleFavoriteResult(Outcome.SUBJECT_ACCESS_DENIED, Optional.empty(), false);
    }

    public static ToggleFavoriteResult identityRejected() {
        return new ToggleFavoriteResult(Outcome.IDENTITY_REJECTED, Optional.empty(), false);
    }

    public static ToggleFavoriteResult mutationRejected() {
        return new ToggleFavoriteResult(Outcome.MUTATION_REJECTED, Optional.empty(), false);
    }

    public static ToggleFavoriteResult idempotencyConflict() {
        return new ToggleFavoriteResult(Outcome.IDEMPOTENCY_CONFLICT, Optional.empty(), false);
    }

    public static ToggleFavoriteResult idempotencyInProgress() {
        return new ToggleFavoriteResult(Outcome.IDEMPOTENCY_IN_PROGRESS, Optional.empty(), false);
    }

    public enum Outcome {
        SUCCESS,
        QUESTION_NOT_FOUND,
        SUBJECT_ACCESS_DENIED,
        IDENTITY_REJECTED,
        MUTATION_REJECTED,
        IDEMPOTENCY_CONFLICT,
        IDEMPOTENCY_IN_PROGRESS
    }
}
