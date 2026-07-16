package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;

class QuestionCountSqlContractTest {

    @Test
    void anonymousAndAuthenticatedScopesHaveExactFixedSql() {
        assertThat(JdbcQuestionCountQueryAdapter.sqlFor(query(
                        QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                        Set.of(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty())))
                .isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL)
                .doesNotContain("s.id IS NOT NULL", "excluded_subject_ids");

        assertThat(JdbcQuestionCountQueryAdapter.sqlFor(query(
                        QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                        Set.of(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty())))
                .isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL
                        + JdbcQuestionCountQueryAdapter.REQUIRE_EXISTING_SUBJECT_SQL)
                .contains("s.id IS NOT NULL")
                .doesNotContain("excluded_subject_ids");
    }

    @Test
    void authenticatedExclusionsUseOneIntegerArrayAndAllPredicate() {
        String sql = JdbcQuestionCountQueryAdapter.sqlFor(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(4, 2),
                Optional.empty(),
                Optional.empty(),
                Optional.empty()));

        assertThat(sql).isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL
                + JdbcQuestionCountQueryAdapter.REQUIRE_EXISTING_SUBJECT_SQL
                + JdbcQuestionCountQueryAdapter.EXCLUDE_SUBJECTS_SQL);
        assertThat(sql)
                .contains("s.id <> ALL(CAST(:excluded_subject_ids AS integer[]))")
                .containsOnlyOnce(":excluded_subject_ids")
                .doesNotContain(" IN (");
    }

    @Test
    void candidateIdsUseOneBigintArrayAndAnyPredicateWithNoDynamicInList() {
        String sql = JdbcQuestionCountQueryAdapter.sqlFor(query(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(List.of(1L, 2L, 3L))));

        assertThat(sql).isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL
                + JdbcQuestionCountQueryAdapter.CANDIDATE_QUESTION_IDS_SQL);
        assertThat(sql)
                .contains("q.id = ANY(CAST(:candidate_question_ids AS bigint[]))")
                .containsOnlyOnce(":candidate_question_ids")
                .doesNotContain(" IN (", ":candidate_question_ids_0");
    }

    @Test
    void optionalScalarFiltersRemainBoundParametersAndAreNeverInterpolated() {
        String subjectValue = "数学' OR true --";
        String typeValue = "single_choice/*value*/";
        String sql = JdbcQuestionCountQueryAdapter.sqlFor(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(2),
                Optional.of(subjectValue),
                Optional.of(typeValue),
                Optional.of(List.of(11L))));

        assertThat(sql).isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL
                + JdbcQuestionCountQueryAdapter.REQUIRE_EXISTING_SUBJECT_SQL
                + JdbcQuestionCountQueryAdapter.EXCLUDE_SUBJECTS_SQL
                + JdbcQuestionCountQueryAdapter.SUBJECT_NAME_SQL
                + JdbcQuestionCountQueryAdapter.QUESTION_TYPE_SQL
                + JdbcQuestionCountQueryAdapter.CANDIDATE_QUESTION_IDS_SQL);
        assertThat(sql)
                .contains("s.name = :subject_name", "q.type = :question_type")
                .doesNotContain(subjectValue, typeValue);
    }

    @Test
    void explicitEmptyCandidatesAddNoSqlBecauseTheServiceShortCircuitsBeforeJdbc() {
        String sql = JdbcQuestionCountQueryAdapter.sqlFor(query(
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(List.of())));

        assertThat(sql)
                .isEqualTo(JdbcQuestionCountQueryAdapter.BASE_COUNT_SQL)
                .doesNotContain("candidate_question_ids");
    }

    @Test
    void everyVariantIsReadOnlyAndReferencesOnlyCatalogOwnedTables() {
        String sql = JdbcQuestionCountQueryAdapter.sqlFor(query(
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(2),
                Optional.of("数学"),
                Optional.of("single_choice"),
                Optional.of(List.of(1L))));
        String normalized = sql.toLowerCase();

        assertThat(normalized)
                .contains("from questions q", "left join subjects s")
                .doesNotContain(
                        "favorites",
                        "mistakes",
                        "user_progress",
                        "user_question_tag_items",
                        "insert ",
                        "update ",
                        "delete ",
                        "alter ",
                        "create ",
                        "drop ",
                        "truncate ");
    }

    private static QuestionCatalogCountQuery query(
            QuestionSubjectAssignmentScope scope,
            Set<Integer> excludedSubjectIds,
            Optional<String> subjectName,
            Optional<String> questionType,
            Optional<List<Long>> candidateIds
    ) {
        return new QuestionCatalogCountQuery(
                subjectName,
                questionType,
                scope,
                excludedSubjectIds,
                candidateIds);
    }
}
