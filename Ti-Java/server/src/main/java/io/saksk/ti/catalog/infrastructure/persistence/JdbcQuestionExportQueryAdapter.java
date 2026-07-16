package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import io.saksk.ti.catalog.application.port.QuestionExportQueryPort;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Objects;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionExportQueryAdapter implements QuestionExportQueryPort {

    static final String SELECT_ALL_QUESTION_EXPORT_RECORDS = """
            SELECT q.id,
                   q.subject_id,
                   s.name AS subject_name,
                   q.type,
                   q.content,
                   q.options,
                   q.answer,
                   q.analysis,
                   q.difficulty,
                   q.tags
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            ORDER BY q.id ASC""";

    static final String SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT = """
            SELECT q.id,
                   q.subject_id,
                   s.name AS subject_name,
                   q.type,
                   q.content,
                   q.options,
                   q.answer,
                   q.analysis,
                   q.difficulty,
                   q.tags
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.subject_id = :subject_id
            ORDER BY q.id ASC""";

    private final JdbcClient jdbc;

    JdbcQuestionExportQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<QuestionExportRecordView> listQuestionExportRecords(QuestionExportQuery query) {
        Objects.requireNonNull(query, "query");
        JdbcClient.StatementSpec statement = jdbc.sql(sqlFor(query));
        if (query.subjectId().isPresent()) {
            statement = statement.param("subject_id", query.subjectId().orElseThrow());
        }
        return statement.query(JdbcQuestionExportQueryAdapter::mapRecord).list();
    }

    static String sqlFor(QuestionExportQuery query) {
        Objects.requireNonNull(query, "query");
        return query.subjectId().isPresent()
                ? SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT
                : SELECT_ALL_QUESTION_EXPORT_RECORDS;
    }

    private static QuestionExportRecordView mapRecord(ResultSet row, int rowNumber)
            throws SQLException {
        return new QuestionExportRecordView(
                row.getLong("id"),
                nullableLong(row, "subject_id"),
                row.getString("subject_name"),
                row.getString("type"),
                row.getString("content"),
                row.getString("options"),
                row.getString("answer"),
                row.getString("analysis"),
                row.getObject("difficulty", Integer.class),
                row.getString("tags"));
    }

    private static Long nullableLong(ResultSet row, String column) throws SQLException {
        long value = row.getLong(column);
        return row.wasNull() ? null : value;
    }
}
