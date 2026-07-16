package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class QuestionListSqlContractTest {

    private static final List<String> EXPECTED_PROJECTION = List.of(
            "q.id",
            "q.subject_id",
            "q.type",
            "q.content",
            "q.difficulty",
            "q.tags",
            "q.image_path",
            "q.created_by",
            "q.updated_at");

    @Test
    void exposesExactlyFourFixedFilterVariants() {
        assertThat(JdbcQuestionSummaryQueryAdapter.sqlFor(query(false, false)))
                .isSameAs(JdbcQuestionSummaryQueryAdapter.SELECT_ALL_QUESTION_SUMMARIES);
        assertThat(JdbcQuestionSummaryQueryAdapter.sqlFor(query(true, false)))
                .isSameAs(JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT);
        assertThat(JdbcQuestionSummaryQueryAdapter.sqlFor(query(false, true)))
                .isSameAs(JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_TYPE);
        assertThat(JdbcQuestionSummaryQueryAdapter.sqlFor(query(true, true)))
                .isSameAs(
                        JdbcQuestionSummaryQueryAdapter
                                .SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE);
        assertThatNullPointerException()
                .isThrownBy(() -> JdbcQuestionSummaryQueryAdapter.sqlFor(null))
                .withMessage("query");
    }

    @Test
    void everyVariantUsesTheSameNineColumnQuestionsOnlyDescendingProjection() {
        List<String> variants = variants();

        assertThat(variants).doesNotHaveDuplicates().hasSize(4);
        for (String sql : variants) {
            assertThat(projection(sql)).containsExactlyElementsOf(EXPECTED_PROJECTION);
            assertThat(sql)
                    .contains("FROM questions q")
                    .endsWith("ORDER BY q.id DESC")
                    .doesNotContain(
                            "SELECT *",
                            "JOIN ",
                            "users",
                            "subjects",
                            "favorites",
                            "mistakes");
            assertThat(sql.toUpperCase(Locale.ROOT)).doesNotContain(
                    "INSERT ",
                    "UPDATE ",
                    "DELETE ",
                    "CREATE ",
                    "ALTER ",
                    "DROP ",
                    "TEMP ");
        }
    }

    @Test
    void eachFilteredVariantBindsOnlyItsDeclaredLegacyColumn() {
        assertThat(JdbcQuestionSummaryQueryAdapter.SELECT_ALL_QUESTION_SUMMARIES)
                .doesNotContain("WHERE", ":subject_id", ":question_type");
        assertThat(JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT)
                .contains("WHERE q.subject_id = :subject_id")
                .doesNotContain(":question_type");
        assertThat(JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_TYPE)
                .contains("WHERE q.type = :question_type")
                .doesNotContain(":subject_id");
        assertThat(JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE)
                .contains(
                        "WHERE q.subject_id = :subject_id",
                        "AND q.type = :question_type");

        assertThat(occurrences(
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT,
                ":subject_id"))
                .isOne();
        assertThat(occurrences(
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_TYPE,
                ":question_type"))
                .isOne();
        assertThat(occurrences(
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE,
                ":subject_id"))
                .isOne();
        assertThat(occurrences(
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE,
                ":question_type"))
                .isOne();
    }

    private static QuestionCatalogListQuery query(boolean subject, boolean type) {
        return new QuestionCatalogListQuery(
                subject ? Optional.of(-7) : Optional.empty(),
                type ? Optional.of("") : Optional.empty());
    }

    private static List<String> variants() {
        return List.of(
                JdbcQuestionSummaryQueryAdapter.SELECT_ALL_QUESTION_SUMMARIES,
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT,
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_TYPE,
                JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE);
    }

    private static List<String> projection(String sql) {
        String columns = sql.substring("SELECT ".length(), sql.indexOf("\nFROM questions q"));
        return Arrays.stream(columns.split(",\\R"))
                .map(String::trim)
                .toList();
    }

    private static int occurrences(String text, String token) {
        return text.split(token, -1).length - 1;
    }
}
