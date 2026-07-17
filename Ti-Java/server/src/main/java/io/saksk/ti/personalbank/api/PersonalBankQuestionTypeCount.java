package io.saksk.ti.personalbank.api;

import java.util.Objects;
import java.util.Optional;

/** One nullable raw personal-bank question type and its PostgreSQL bigint count. */
public record PersonalBankQuestionTypeCount(
        Optional<String> rawType,
        long count
) {

    public PersonalBankQuestionTypeCount {
        rawType = Objects.requireNonNull(rawType, "rawType");
        if (count < 0) {
            throw new IllegalArgumentException("count must not be negative");
        }
    }
}
