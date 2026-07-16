package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;

class QuestionCatalogCountQueryTest {

    @Test
    void defensivelyCopiesScopesAndCanonicalizesCandidateIdsWithoutChangingStrings() {
        Set<Integer> excluded = new HashSet<>(Set.of(7, 3));
        List<Long> candidates = new ArrayList<>(List.of(9L, 2L, 9L, 4L));

        var query = new QuestionCatalogCountQuery(
                Optional.of("  "),
                Optional.of("single_choice"),
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                excluded,
                Optional.of(candidates));
        excluded.add(11);
        candidates.add(12L);

        assertThat(query.subjectName()).contains("  ");
        assertThat(query.questionType()).contains("single_choice");
        assertThat(query.excludedSubjectIds()).containsExactlyInAnyOrder(3, 7);
        assertThat(query.candidateQuestionIds()).contains(List.of(2L, 4L, 9L));
        assertThatThrownBy(() -> query.excludedSubjectIds().add(13))
                .isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> query.candidateQuestionIds().orElseThrow().add(13L))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void preservesAbsentEmptyAndNonemptyCandidateScopesAsDifferentStates() {
        assertThat(query(Optional.empty()).candidateQuestionIds()).isEmpty();
        assertThat(query(Optional.of(List.of())).candidateQuestionIds())
                .contains(List.of());
        assertThat(query(Optional.of(List.of(2L))).candidateQuestionIds())
                .contains(List.of(2L));
    }

    @Test
    void rejectsAnonymousScopeWithAuthenticatedExclusions() {
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        Optional.empty(),
                        QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                        Set.of(1),
                        Optional.empty()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("unassigned-inclusive");
    }

    @Test
    void rejectsNonpositiveOrNullIdsAndNullComponents() {
        for (long invalid : List.of(0L, -1L)) {
            assertThatThrownBy(() -> query(Optional.of(List.of(invalid))))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("candidate question IDs");
        }
        List<Long> candidatesWithNull = new ArrayList<>();
        candidatesWithNull.add(null);
        assertThatThrownBy(() -> query(Optional.of(candidatesWithNull)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("candidate question IDs");

        Set<Integer> excludedWithNull = new HashSet<>();
        excludedWithNull.add(null);
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        Optional.empty(),
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        excludedWithNull,
                        Optional.empty()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("excluded subject IDs");
        for (int invalid : List.of(0, -1)) {
            assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                            Optional.empty(),
                            Optional.empty(),
                            QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                            Set.of(invalid),
                            Optional.empty()))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("excluded subject IDs");
        }
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        null,
                        Optional.empty(),
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        Set.of(),
                        Optional.empty()))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("subjectName");
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        null,
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        Set.of(),
                        Optional.empty()))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("questionType");
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        Optional.empty(),
                        null,
                        Set.of(),
                        Optional.empty()))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("subjectAssignmentScope");
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        Optional.empty(),
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        null,
                        Optional.empty()))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("excludedSubjectIds");
        assertThatThrownBy(() -> new QuestionCatalogCountQuery(
                        Optional.empty(),
                        Optional.empty(),
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        Set.of(),
                        null))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("candidateQuestionIds");
    }

    private static QuestionCatalogCountQuery query(Optional<List<Long>> candidates) {
        return new QuestionCatalogCountQuery(
                Optional.empty(),
                Optional.empty(),
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                candidates);
    }
}
