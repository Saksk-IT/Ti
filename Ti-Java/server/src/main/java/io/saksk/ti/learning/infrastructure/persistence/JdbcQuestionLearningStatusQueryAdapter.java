package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.QuestionLearningStatusQueryPort;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionLearningStatusQueryAdapter implements QuestionLearningStatusQueryPort {

    private final JdbcClient jdbc;

    JdbcQuestionLearningStatusQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Status find(long identityId, long questionId) {
        return jdbc.sql("""
                        SELECT
                            EXISTS (
                                SELECT 1
                                FROM favorites
                                WHERE user_id = :identityId
                                  AND question_id = :questionId
                            ) AS favorite,
                            EXISTS (
                                SELECT 1
                                FROM mistakes
                                WHERE user_id = :identityId
                                  AND question_id = :questionId
                            ) AS mistake
                        """)
                .param("identityId", identityId)
                .param("questionId", questionId)
                .query((resultSet, rowNumber) -> new Status(
                        resultSet.getBoolean("favorite"),
                        resultSet.getBoolean("mistake")))
                .single();
    }
}
