package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class QuestionDetailSqlContractTest {

    @Test
    void runtimeQueryIsOneExplicitPrimaryKeyProjectionOverOnlyQuestions() {
        String sql = JdbcQuestionDetailQueryAdapter.SELECT_QUESTION_BY_ID;

        assertThat(sql)
                .contains(
                        "q.id",
                        "q.subject_id",
                        "q.type",
                        "q.content",
                        "q.options",
                        "q.answer",
                        "q.analysis",
                        "q.tags",
                        "q.difficulty",
                        "q.image_path",
                        "q.source",
                        "q.created_by",
                        "q.updated_by",
                        "q.created_at",
                        "q.updated_at",
                        "FROM questions q",
                        "WHERE q.id = :question_id")
                .doesNotContain(
                        "SELECT *",
                        "JOIN ",
                        "users",
                        "subjects",
                        "favorites",
                        "mistakes",
                        "INSERT",
                        "UPDATE",
                        "DELETE",
                        "CREATE",
                        "TEMP");
        assertThat(sql.split(":question_id", -1)).hasSize(2);
    }
}
