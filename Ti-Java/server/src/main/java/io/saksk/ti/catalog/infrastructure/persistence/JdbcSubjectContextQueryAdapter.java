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

    private final JdbcClient jdbc;

    JdbcSubjectContextQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<SubjectContextView> findSubjectById(long subjectId) {
        return jdbc.sql(SELECT_SUBJECT_CONTEXT_BY_ID)
                .param("subject_id", subjectId, Types.BIGINT)
                .query((row, rowNumber) -> new SubjectContextView(
                        row.getInt("subject_id"),
                        row.getString("subject_name")))
                .optional();
    }
}

