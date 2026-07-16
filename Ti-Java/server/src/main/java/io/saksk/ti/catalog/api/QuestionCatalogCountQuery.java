package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/** HTTP-neutral catalog criteria for counting questions owned by the catalog module. */
public record QuestionCatalogCountQuery(
        Optional<String> subjectName,
        Optional<String> questionType,
        QuestionSubjectAssignmentScope subjectAssignmentScope,
        Set<Integer> excludedSubjectIds,
        Optional<List<Long>> candidateQuestionIds
) {

    public QuestionCatalogCountQuery {
        subjectName = Objects.requireNonNull(subjectName, "subjectName");
        questionType = Objects.requireNonNull(questionType, "questionType");
        subjectAssignmentScope = Objects.requireNonNull(
                subjectAssignmentScope, "subjectAssignmentScope");
        Objects.requireNonNull(excludedSubjectIds, "excludedSubjectIds");
        if (excludedSubjectIds.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new IllegalArgumentException("excluded subject IDs must be positive");
        }
        excludedSubjectIds = Set.copyOf(excludedSubjectIds);
        candidateQuestionIds = Objects.requireNonNull(
                candidateQuestionIds, "candidateQuestionIds")
                .map(QuestionCatalogCountQuery::immutableCandidateIds);

        if (subjectAssignmentScope == QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED
                && !excludedSubjectIds.isEmpty()) {
            throw new IllegalArgumentException(
                    "unassigned-inclusive counts cannot exclude authenticated subject IDs");
        }
    }

    private static List<Long> immutableCandidateIds(List<Long> candidateIds) {
        Objects.requireNonNull(candidateIds, "candidateQuestionIds value");
        if (candidateIds.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new IllegalArgumentException("candidate question IDs must be positive");
        }
        return candidateIds.stream().distinct().sorted().toList();
    }
}
