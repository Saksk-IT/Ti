package io.saksk.ti.personalbank.api;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Immutable provider-owned question scope for a personal-bank facts read. */
public record PersonalBankQuestionSelection(
        int bankId,
        Optional<String> portableType,
        Optional<List<Integer>> candidateQuestionIds
) {

    public PersonalBankQuestionSelection {
        if (bankId <= 0) {
            throw new IllegalArgumentException("bankId must be positive");
        }
        portableType = Objects.requireNonNull(portableType, "portableType");
        candidateQuestionIds = Objects.requireNonNull(
                candidateQuestionIds, "candidateQuestionIds")
                .map(PersonalBankQuestionSelection::normalizedIds);
    }

    private static List<Integer> normalizedIds(List<Integer> questionIds) {
        Objects.requireNonNull(questionIds, "candidateQuestionIds value");
        if (questionIds.stream().anyMatch(Objects::isNull)) {
            throw new NullPointerException("candidateQuestionIds must not contain null");
        }
        if (questionIds.stream().anyMatch(questionId -> questionId <= 0)) {
            throw new IllegalArgumentException(
                    "candidateQuestionIds must contain only positive IDs");
        }
        return List.copyOf(questionIds.stream().distinct().sorted().toList());
    }
}
