package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionTypeQueryAdapter implements QuestionTypeQueryPort {

    static final String SELECT_DISTINCT_QUESTION_TYPES =
            "SELECT DISTINCT q.type AS question_type FROM questions q";

    private final JdbcClient jdbc;

    JdbcQuestionTypeQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<String> findDistinctQuestionTypes() {
        return jdbc.sql(SELECT_DISTINCT_QUESTION_TYPES)
                .query((resultSet, rowNumber) -> resultSet.getString("question_type"))
                .list();
    }
}
