package io.saksk.ti.learning.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral result for one record-result attempt. */
public record RecordResultResult(
        Outcome outcome,
        Optional<RecordResultAction> action,
        Optional<QuizLimitReached> quizLimit,
        boolean replayed
) {

    public RecordResultResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        action = Objects.requireNonNull(action, "action");
        quizLimit = Objects.requireNonNull(quizLimit, "quizLimit");
        if ((outcome == Outcome.SUCCESS) != action.isPresent()) {
            throw new IllegalArgumentException(
                    "Record-result action must be present exactly for success");
        }
        if ((outcome == Outcome.QUIZ_LIMIT_REACHED) != quizLimit.isPresent()) {
            throw new IllegalArgumentException(
                    "Quiz-limit facts must be present exactly for a quota rejection");
        }
        if (replayed
                && outcome != Outcome.SUCCESS
                && outcome != Outcome.QUIZ_LIMIT_REACHED) {
            throw new IllegalArgumentException(
                    "Only durable success or quota outcomes may be replayed");
        }
    }

    public static RecordResultResult success(
            RecordResultAction action,
            boolean replayed
    ) {
        return new RecordResultResult(
                Outcome.SUCCESS,
                Optional.of(Objects.requireNonNull(action, "action")),
                Optional.empty(),
                replayed);
    }

    public static RecordResultResult quizLimitReached(
            long currentCount,
            int limitCount,
            boolean replayed
    ) {
        return new RecordResultResult(
                Outcome.QUIZ_LIMIT_REACHED,
                Optional.empty(),
                Optional.of(new QuizLimitReached(currentCount, limitCount)),
                replayed);
    }

    public static RecordResultResult questionNotFound() {
        return rejected(Outcome.QUESTION_NOT_FOUND);
    }

    public static RecordResultResult subjectAccessDenied() {
        return rejected(Outcome.SUBJECT_ACCESS_DENIED);
    }

    public static RecordResultResult identityRejected() {
        return rejected(Outcome.IDENTITY_REJECTED);
    }

    public static RecordResultResult mutationRejected() {
        return rejected(Outcome.MUTATION_REJECTED);
    }

    public static RecordResultResult idempotencyConflict() {
        return rejected(Outcome.IDEMPOTENCY_CONFLICT);
    }

    public static RecordResultResult idempotencyInProgress() {
        return rejected(Outcome.IDEMPOTENCY_IN_PROGRESS);
    }

    private static RecordResultResult rejected(Outcome outcome) {
        return new RecordResultResult(
                outcome,
                Optional.empty(),
                Optional.empty(),
                false);
    }

    public enum Outcome {
        SUCCESS,
        QUIZ_LIMIT_REACHED,
        QUESTION_NOT_FOUND,
        SUBJECT_ACCESS_DENIED,
        IDENTITY_REJECTED,
        MUTATION_REJECTED,
        IDEMPOTENCY_CONFLICT,
        IDEMPOTENCY_IN_PROGRESS
    }
}
