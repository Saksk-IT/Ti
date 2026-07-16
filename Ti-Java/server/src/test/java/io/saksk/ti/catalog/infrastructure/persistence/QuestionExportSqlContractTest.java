package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import io.saksk.ti.catalog.api.QuestionExportQuery;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class QuestionExportSqlContractTest {

    private static final List<String> EXPECTED_PROJECTION = List.of(
            "q.id",
            "q.subject_id",
            "s.name AS subject_name",
            "q.type",
            "q.content",
            "q.options",
            "q.answer",
            "q.analysis",
            "q.difficulty",
            "q.tags");

    @Test
    void exposesExactlyTwoFixedSubjectFilterVariants() {
        assertThat(JdbcQuestionExportQueryAdapter.sqlFor(query(Optional.empty())))
                .isSameAs(JdbcQuestionExportQueryAdapter.SELECT_ALL_QUESTION_EXPORT_RECORDS);
        assertThat(JdbcQuestionExportQueryAdapter.sqlFor(query(Optional.of(-7))))
                .isSameAs(
                        JdbcQuestionExportQueryAdapter.SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT);
        assertThatNullPointerException()
                .isThrownBy(() -> JdbcQuestionExportQueryAdapter.sqlFor(null))
                .withMessage("query");
    }

    @Test
    void everyVariantUsesTheSameTenColumnLeftJoinAscendingProjection() {
        List<String> variants = variants();

        assertThat(variants).doesNotHaveDuplicates().hasSize(2);
        for (String sql : variants) {
            assertThat(projection(sql)).containsExactlyElementsOf(EXPECTED_PROJECTION);
            assertThat(sql)
                    .contains(
                            "FROM questions q",
                            "LEFT JOIN subjects s ON q.subject_id = s.id")
                    .endsWith("ORDER BY q.id ASC")
                    .doesNotContain(
                            "SELECT *",
                            "users",
                            "user_subjects",
                            "is_locked",
                            "restricted",
                            "visibility",
                            "favorites",
                            "mistakes",
                            "LIMIT ",
                            "OFFSET ");
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
    void onlyTheFilteredVariantBindsTheExactIntegerSubjectIdOnce() {
        assertThat(JdbcQuestionExportQueryAdapter.SELECT_ALL_QUESTION_EXPORT_RECORDS)
                .doesNotContain("WHERE", ":subject_id");
        assertThat(JdbcQuestionExportQueryAdapter.SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT)
                .contains("WHERE q.subject_id = :subject_id");
        assertThat(occurrences(
                JdbcQuestionExportQueryAdapter.SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT,
                ":subject_id"))
                .isOne();
    }

    private static QuestionExportQuery query(Optional<Integer> subjectId) {
        return new QuestionExportQuery(subjectId);
    }

    private static List<String> variants() {
        return List.of(
                JdbcQuestionExportQueryAdapter.SELECT_ALL_QUESTION_EXPORT_RECORDS,
                JdbcQuestionExportQueryAdapter.SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT);
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
