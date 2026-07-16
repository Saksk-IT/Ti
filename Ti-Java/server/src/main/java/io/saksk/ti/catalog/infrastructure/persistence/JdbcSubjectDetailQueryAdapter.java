package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.SubjectCatalogRecordView;
import io.saksk.ti.catalog.application.port.SubjectDetailQueryPort;
import java.sql.Types;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSubjectDetailQueryAdapter implements SubjectDetailQueryPort {

    static final String SELECT_SUBJECT_BY_ID = """
            SELECT s.id,
                   s.name
            FROM subjects s
            WHERE s.id = :subject_id""";

    private final JdbcClient jdbc;

    JdbcSubjectDetailQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<SubjectCatalogRecordView> findSubjectById(long subjectId) {
        return jdbc.sql(SELECT_SUBJECT_BY_ID)
                .param("subject_id", subjectId, Types.BIGINT)
                .query((row, rowNumber) -> new SubjectCatalogRecordView(
                        row.getInt("id"),
                        row.getString("name")))
                .optional();
    }
}
