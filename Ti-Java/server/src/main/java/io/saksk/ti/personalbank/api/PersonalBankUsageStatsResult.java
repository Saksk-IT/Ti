package io.saksk.ti.personalbank.api;

import java.util.Objects;

/** Tri-state HTTP-neutral result for the legacy personal-bank usage-statistics read. */
public record PersonalBankUsageStatsResult(
        Outcome outcome,
        PersonalBankUsageStatsView view
) {

    public PersonalBankUsageStatsResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        if ((outcome == Outcome.AVAILABLE) != (view != null)) {
            throw new IllegalArgumentException(
                    "Only an available result may contain a usage-statistics view");
        }
    }

    public static PersonalBankUsageStatsResult available(PersonalBankUsageStatsView view) {
        return new PersonalBankUsageStatsResult(
                Outcome.AVAILABLE,
                Objects.requireNonNull(view, "view"));
    }

    public static PersonalBankUsageStatsResult notFound() {
        return new PersonalBankUsageStatsResult(Outcome.NOT_FOUND, null);
    }

    public static PersonalBankUsageStatsResult forbidden() {
        return new PersonalBankUsageStatsResult(Outcome.FORBIDDEN, null);
    }

    public enum Outcome {
        AVAILABLE,
        NOT_FOUND,
        FORBIDDEN
    }
}
