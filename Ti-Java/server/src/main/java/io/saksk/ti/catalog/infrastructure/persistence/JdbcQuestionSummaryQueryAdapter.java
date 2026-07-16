package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import io.saksk.ti.catalog.application.port.QuestionSummaryQueryPort;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionSummaryQueryAdapter implements QuestionSummaryQueryPort {

    static final String SELECT_ALL_QUESTION_SUMMARIES = """
            SELECT q.id,
                   q.subject_id,
                   q.type,
                   q.content,
                   q.difficulty,
                   q.tags,
                   q.image_path,
                   q.created_by,
                   q.updated_at
            FROM questions q
            ORDER BY q.id DESC""";

    static final String SELECT_QUESTION_SUMMARIES_BY_SUBJECT = """
            SELECT q.id,
                   q.subject_id,
                   q.type,
                   q.content,
                   q.difficulty,
                   q.tags,
                   q.image_path,
                   q.created_by,
                   q.updated_at
            FROM questions q
            WHERE q.subject_id = :subject_id
            ORDER BY q.id DESC""";

    static final String SELECT_QUESTION_SUMMARIES_BY_TYPE = """
            SELECT q.id,
                   q.subject_id,
                   q.type,
                   q.content,
                   q.difficulty,
                   q.tags,
                   q.image_path,
                   q.created_by,
                   q.updated_at
            FROM questions q
            WHERE q.type = :question_type
            ORDER BY q.id DESC""";

    static final String SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE = """
            SELECT q.id,
                   q.subject_id,
                   q.type,
                   q.content,
                   q.difficulty,
                   q.tags,
                   q.image_path,
                   q.created_by,
                   q.updated_at
            FROM questions q
            WHERE q.subject_id = :subject_id
              AND q.type = :question_type
            ORDER BY q.id DESC""";

    private final JdbcClient jdbc;

    JdbcQuestionSummaryQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<QuestionCatalogSummaryView> listQuestionSummaries(QuestionCatalogListQuery query) {
        Objects.requireNonNull(query, "query");
        JdbcClient.StatementSpec statement = jdbc.sql(sqlFor(query));
        if (query.subjectId().isPresent()) {
            statement = statement.param("subject_id", query.subjectId().orElseThrow());
        }
        if (query.questionType().isPresent()) {
            statement = statement.param("question_type", query.questionType().orElseThrow());
        }
        return statement.query(JdbcQuestionSummaryQueryAdapter::mapSummary).list();
    }

    static String sqlFor(QuestionCatalogListQuery query) {
        Objects.requireNonNull(query, "query");
        if (query.subjectId().isPresent() && query.questionType().isPresent()) {
            return SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE;
        }
        if (query.subjectId().isPresent()) {
            return SELECT_QUESTION_SUMMARIES_BY_SUBJECT;
        }
        if (query.questionType().isPresent()) {
            return SELECT_QUESTION_SUMMARIES_BY_TYPE;
        }
        return SELECT_ALL_QUESTION_SUMMARIES;
    }

    private static QuestionCatalogSummaryView mapSummary(ResultSet row, int rowNumber)
            throws SQLException {
        return new QuestionCatalogSummaryView(
                row.getLong("id"),
                nullableLong(row, "subject_id"),
                row.getString("type"),
                row.getString("content"),
                row.getObject("difficulty", Integer.class),
                row.getString("tags"),
                row.getString("image_path"),
                nullableLong(row, "created_by"),
                row.getObject("updated_at", LocalDateTime.class));
    }

    private static Long nullableLong(ResultSet row, String column) throws SQLException {
        long value = row.getLong(column);
        return row.wasNull() ? null : value;
    }
}
