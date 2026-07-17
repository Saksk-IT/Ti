package io.saksk.ti.learning.api;

import java.util.Objects;

/** Raw HTTP-neutral filters for the legacy personal-bank user-counts read. */
public record PersonalBankUserCountsQuery(
        int bankId,
        String rawQuestionType,
        String rawSource,
        String rawTag
) {

    public PersonalBankUserCountsQuery {
        if (bankId <= 0) {
            throw new IllegalArgumentException("bankId must be positive");
        }
        rawQuestionType = Objects.requireNonNull(rawQuestionType, "rawQuestionType");
        rawSource = Objects.requireNonNull(rawSource, "rawSource");
        rawTag = Objects.requireNonNull(rawTag, "rawTag");
    }
}
