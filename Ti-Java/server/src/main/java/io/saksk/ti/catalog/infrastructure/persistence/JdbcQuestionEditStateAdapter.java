package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcQuestionEditStateAdapter implements QuestionEditStatePort {

    static final String SELECT_FOR_UPDATE = """
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
                   q.updated_at,
                   COALESCE(s.name, '') AS subject_name
              FROM questions q
              LEFT JOIN subjects s ON s.id = q.subject_id
             WHERE q.id = :questionId
               FOR UPDATE OF q""";

    static final String UPDATE_QUESTION = """
            UPDATE questions
               SET type = :type,
                   content = :content,
                   options = :options,
                   answer = :answer,
                   analysis = :analysis,
                   tags = :tags,
                   difficulty = :difficulty,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :questionId""";

    private final JdbcClient jdbc;

    JdbcQuestionEditStateAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public Optional<QuestionEditSnapshot> findForUpdate(long questionId) {
        requireWritableTransaction();
        return jdbc.sql(SELECT_FOR_UPDATE)
                .param("questionId", questionId)
                .query(JdbcQuestionEditStateAdapter::mapSnapshot)
                .optional();
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public void update(QuestionEditMutation mutation) {
        requireWritableTransaction();
        int updated = jdbc.sql(UPDATE_QUESTION)
                .param("type", mutation.type())
                .param("content", mutation.content())
                .param("options", mutation.optionsJson())
                .param("answer", mutation.answerJson())
                .param("analysis", mutation.analysis())
                .param("tags", mutation.tagsJson())
                .param("difficulty", mutation.difficulty())
                .param("questionId", mutation.questionId())
                .update();
        if (updated != 1) {
            throw new IllegalStateException(
                    "Catalog question edit did not update exactly one locked row");
        }
    }

    private static QuestionEditSnapshot mapSnapshot(ResultSet row, int rowNumber)
            throws SQLException {
        QuestionCatalogRecordView question = new QuestionCatalogRecordView(
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
        return new QuestionEditSnapshot(question, row.getString("subject_name"));
    }

    private static Long nullableLong(ResultSet row, String column) throws SQLException {
        long value = row.getLong(column);
        return row.wasNull() ? null : value;
    }

    private static void requireWritableTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalStateException(
                    "Catalog question edits require an active writable transaction");
        }
    }
}
