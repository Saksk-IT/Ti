package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectCatalogQueryPort;
import io.saksk.ti.catalog.domain.SubjectCatalogEntry;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSubjectCatalogQueryAdapter implements SubjectCatalogQueryPort {

    static final String SELECT_UNLOCKED_SUBJECTS_WITH_COUNTS = """
            SELECT s.id AS subject_id,
                   s.name AS subject_name,
                   COUNT(q.id) AS question_count
            FROM subjects s
            LEFT JOIN questions q ON q.subject_id = s.id
            WHERE s.is_locked = false OR s.is_locked IS NULL
            GROUP BY s.id, s.name
            ORDER BY s.id ASC
            """;

    private final JdbcClient jdbc;

    JdbcSubjectCatalogQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<SubjectCatalogEntry> findUnlockedWithQuestionCounts() {
        return jdbc.sql(SELECT_UNLOCKED_SUBJECTS_WITH_COUNTS)
                .query((resultSet, rowNumber) -> new SubjectCatalogEntry(
                        resultSet.getInt("subject_id"),
                        resultSet.getString("subject_name"),
                        resultSet.getLong("question_count")))
                .list();
    }
}
