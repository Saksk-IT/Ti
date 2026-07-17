package io.saksk.ti.personalbank.api;

import java.util.Objects;

/** HTTP-neutral authorization result for one personal-bank question read. */
public record PersonalBankQuestionAccessResult(Outcome outcome) {

    public PersonalBankQuestionAccessResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
    }

    public static PersonalBankQuestionAccessResult available() {
        return new PersonalBankQuestionAccessResult(Outcome.AVAILABLE);
    }

    public static PersonalBankQuestionAccessResult denied() {
        return new PersonalBankQuestionAccessResult(Outcome.DENIED);
    }

    public enum Outcome {
        AVAILABLE,
        DENIED
    }
}
