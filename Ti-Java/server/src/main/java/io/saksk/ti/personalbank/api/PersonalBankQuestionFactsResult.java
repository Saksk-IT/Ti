package io.saksk.ti.personalbank.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral authorization-aware result for personal-bank question facts. */
public record PersonalBankQuestionFactsResult(
        Outcome outcome,
        Optional<PersonalBankQuestionFactsView> data
) {

    public PersonalBankQuestionFactsResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        data = Objects.requireNonNull(data, "data");
        if ((outcome == Outcome.AVAILABLE) != data.isPresent()) {
            throw new IllegalArgumentException(
                    "Question facts data must be present exactly when available");
        }
    }

    public static PersonalBankQuestionFactsResult available(
            PersonalBankQuestionFactsView data
    ) {
        return new PersonalBankQuestionFactsResult(
                Outcome.AVAILABLE,
                Optional.of(Objects.requireNonNull(data, "data")));
    }

    public static PersonalBankQuestionFactsResult denied() {
        return new PersonalBankQuestionFactsResult(Outcome.DENIED, Optional.empty());
    }

    public enum Outcome {
        AVAILABLE,
        DENIED
    }
}
