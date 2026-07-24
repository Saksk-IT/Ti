package io.saksk.ti.learning.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral outcome for the restored daily check-in write. */
public record CheckinResult(
        Outcome outcome,
        Optional<CheckinView> data,
        boolean replayed
) {

    public CheckinResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        data = Objects.requireNonNull(data, "data");
        if ((outcome == Outcome.SUCCESS) != data.isPresent()) {
            throw new IllegalArgumentException(
                    "Check-in data must be present exactly for success");
        }
        if (replayed && outcome != Outcome.SUCCESS) {
            throw new IllegalArgumentException(
                    "Only successful check-in receipts may be replayed");
        }
    }

    public static CheckinResult success(CheckinView data, boolean replayed) {
        return new CheckinResult(
                Outcome.SUCCESS,
                Optional.of(Objects.requireNonNull(data, "data")),
                replayed);
    }

    public static CheckinResult mutationRejected() {
        return rejected(Outcome.MUTATION_REJECTED);
    }

    public static CheckinResult idempotencyConflict() {
        return rejected(Outcome.IDEMPOTENCY_CONFLICT);
    }

    public static CheckinResult idempotencyInProgress() {
        return rejected(Outcome.IDEMPOTENCY_IN_PROGRESS);
    }

    private static CheckinResult rejected(Outcome outcome) {
        return new CheckinResult(outcome, Optional.empty(), false);
    }

    public enum Outcome {
        SUCCESS,
        MUTATION_REJECTED,
        IDEMPOTENCY_CONFLICT,
        IDEMPOTENCY_IN_PROGRESS
    }
}
