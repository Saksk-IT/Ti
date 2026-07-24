package io.saksk.ti.catalog.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral result for the catalog-owned question edit. */
public record QuestionEditResult(
        Outcome outcome,
        Optional<QuestionEditView> data,
        Optional<String> detail,
        boolean replayed
) {

    public QuestionEditResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        data = Objects.requireNonNull(data, "data");
        detail = Objects.requireNonNull(detail, "detail");
        if ((outcome == Outcome.SUCCESS) != data.isPresent()) {
            throw new IllegalArgumentException(
                    "Question edit data must be present exactly for success");
        }
        if ((outcome == Outcome.INVALID_MULTI_CHOICE_ANSWER) != detail.isPresent()) {
            throw new IllegalArgumentException(
                    "Only an invalid multi-choice result may carry detail");
        }
        if (replayed && outcome != Outcome.SUCCESS
                && outcome != Outcome.QUESTION_NOT_FOUND
                && outcome != Outcome.INVALID_MULTI_CHOICE_ANSWER) {
            throw new IllegalArgumentException(
                    "Only durable question-edit outcomes may be replayed");
        }
    }

    public static QuestionEditResult success(QuestionEditView data, boolean replayed) {
        return new QuestionEditResult(
                Outcome.SUCCESS,
                Optional.of(Objects.requireNonNull(data, "data")),
                Optional.empty(),
                replayed);
    }

    public static QuestionEditResult forbidden() {
        return rejected(Outcome.FORBIDDEN);
    }

    public static QuestionEditResult questionNotFound(boolean replayed) {
        return new QuestionEditResult(
                Outcome.QUESTION_NOT_FOUND,
                Optional.empty(),
                Optional.empty(),
                replayed);
    }

    public static QuestionEditResult invalidMultiChoice(String detail, boolean replayed) {
        return new QuestionEditResult(
                Outcome.INVALID_MULTI_CHOICE_ANSWER,
                Optional.empty(),
                Optional.of(Objects.requireNonNull(detail, "detail")),
                replayed);
    }

    public static QuestionEditResult mutationRejected() {
        return rejected(Outcome.MUTATION_REJECTED);
    }

    public static QuestionEditResult idempotencyConflict() {
        return rejected(Outcome.IDEMPOTENCY_CONFLICT);
    }

    public static QuestionEditResult idempotencyInProgress() {
        return rejected(Outcome.IDEMPOTENCY_IN_PROGRESS);
    }

    private static QuestionEditResult rejected(Outcome outcome) {
        return new QuestionEditResult(
                outcome,
                Optional.empty(),
                Optional.empty(),
                false);
    }

    public enum Outcome {
        SUCCESS,
        FORBIDDEN,
        QUESTION_NOT_FOUND,
        INVALID_MULTI_CHOICE_ANSWER,
        MUTATION_REJECTED,
        IDEMPOTENCY_CONFLICT,
        IDEMPOTENCY_IN_PROGRESS
    }
}
