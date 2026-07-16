package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class QuestionTypeSqlContractTest {

    @Test
    void runtimeQueryIsTheExactSingleLegacyDistinctProjection() {
        assertThat(JdbcQuestionTypeQueryAdapter.SELECT_DISTINCT_QUESTION_TYPES)
                .isEqualTo("SELECT DISTINCT q.type AS question_type FROM questions q")
                .doesNotContain(
                        "TRIM",
                        "WHERE",
                        "ORDER BY",
                        "INSERT",
                        "UPDATE",
                        "DELETE");
    }
}
