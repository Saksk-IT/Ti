package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.application.port.QuestionDetailQueryPort;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionDetailQueryAdapter implements QuestionDetailQueryPort {

    static final String SELECT_QUESTION_BY_ID = """
            SELECT q.id,
                   q.subject_id,
                   q.type,
                   q.content,
                   q.options,
                   q.answer,
                   q.analysis,
                   q.tags,
                   q.difficulty,
                   q.image_path,
                   q.source,
                   q.created_by,
                   q.updated_by,
                   q.created_at,
                   q.updated_at
            FROM questions q
            WHERE q.id = :question_id""";

    private final JdbcClient jdbc;

    JdbcQuestionDetailQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<QuestionCatalogRecordView> findQuestionById(long questionId) {
        return jdbc.sql(SELECT_QUESTION_BY_ID)
                .param("question_id", questionId)
                .query(JdbcQuestionDetailQueryAdapter::mapQuestion)
                .optional();
    }

    private static QuestionCatalogRecordView mapQuestion(ResultSet row, int rowNumber)
            throws SQLException {
        return new QuestionCatalogRecordView(
                row.getLong("id"),
                nullableLong(row, "subject_id"),
                row.getString("type"),
                row.getString("content"),
                row.getString("options"),
                row.getString("answer"),
                row.getString("analysis"),
                row.getString("tags"),
                row.getObject("difficulty", Integer.class),
                row.getString("image_path"),
                row.getString("source"),
                nullableLong(row, "created_by"),
                nullableLong(row, "updated_by"),
                row.getObject("created_at", LocalDateTime.class),
                row.getObject("updated_at", LocalDateTime.class));
    }

    private static Long nullableLong(ResultSet row, String column) throws SQLException {
        long value = row.getLong(column);
        return row.wasNull() ? null : value;
    }
}
