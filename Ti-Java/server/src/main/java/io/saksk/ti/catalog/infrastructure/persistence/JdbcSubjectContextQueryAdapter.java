package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.application.port.SubjectContextQueryPort;
import java.sql.Types;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSubjectContextQueryAdapter implements SubjectContextQueryPort {

    static final String SELECT_SUBJECT_CONTEXT_BY_ID = """
            SELECT s.id AS subject_id,
                   s.name AS subject_name
            FROM subjects s
            WHERE s.id = :subject_id""";
    static final String SELECT_SUBJECT_CONTEXT_BY_EXACT_NAME = """
            SELECT s.id AS subject_id,
                   s.name AS subject_name
            FROM subjects s
            WHERE s.name = :subject_name
            ORDER BY s.id ASC
            LIMIT 2""";

    private final JdbcClient jdbc;

    JdbcSubjectContextQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<SubjectContextView> findSubjectById(long subjectId) {
        return jdbc.sql(SELECT_SUBJECT_CONTEXT_BY_ID)
                .param("subject_id", subjectId, Types.BIGINT)
                .query(JdbcSubjectContextQueryAdapter::mapSubject)
                .optional();
    }

    @Override
    public Optional<SubjectContextView> findSubjectByExactName(String subjectName) {
        java.util.List<SubjectContextView> matches =
                jdbc.sql(SELECT_SUBJECT_CONTEXT_BY_EXACT_NAME)
                        .param("subject_name", subjectName, Types.VARCHAR)
                        .query(JdbcSubjectContextQueryAdapter::mapSubject)
                        .list();
        if (matches.size() > 1) {
            throw new IllegalStateException(
                    "Exact subject name resolved to more than one catalog row");
        }
        return matches.stream().findFirst();
    }

    private static SubjectContextView mapSubject(
            java.sql.ResultSet row,
            int rowNumber
    ) throws java.sql.SQLException {
        return new SubjectContextView(
                row.getInt("subject_id"),
                row.getString("subject_name"));
    }
}
