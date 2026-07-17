package io.saksk.ti.learning.api;

import java.util.Objects;
import java.util.Optional;

/** HTTP-neutral authorization result for a personal-bank user-counts read. */
public record PersonalBankUserCountsResult(
        Outcome outcome,
        Optional<PersonalBankUserCountsView> data
) {

    public PersonalBankUserCountsResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        data = Objects.requireNonNull(data, "data");
        if ((outcome == Outcome.AVAILABLE) != data.isPresent()) {
            throw new IllegalArgumentException(
                    "Only an available result may contain user-counts data");
        }
    }

    public static PersonalBankUserCountsResult available(PersonalBankUserCountsView data) {
        return new PersonalBankUserCountsResult(
                Outcome.AVAILABLE,
                Optional.of(Objects.requireNonNull(data, "data")));
    }

    public static PersonalBankUserCountsResult denied() {
        return new PersonalBankUserCountsResult(Outcome.DENIED, Optional.empty());
    }

    public enum Outcome {
        AVAILABLE,
        DENIED
    }
}
