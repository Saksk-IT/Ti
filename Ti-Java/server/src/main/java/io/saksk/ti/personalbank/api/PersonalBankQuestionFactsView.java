package io.saksk.ti.personalbank.api;

import java.util.List;
import java.util.Objects;

/** Immutable provider-owned count and raw-type buckets for a question scope. */
public record PersonalBankQuestionFactsView(
        long total,
        List<PersonalBankQuestionTypeCount> rawTypes
) {

    public PersonalBankQuestionFactsView {
        if (total < 0) {
            throw new IllegalArgumentException("total must not be negative");
        }
        rawTypes = List.copyOf(Objects.requireNonNull(rawTypes, "rawTypes"));
    }
}
