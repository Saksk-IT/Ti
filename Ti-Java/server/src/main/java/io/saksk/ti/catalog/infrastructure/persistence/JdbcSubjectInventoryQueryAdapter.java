package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSubjectInventoryQueryAdapter implements SubjectInventoryQueryPort {

    static final String SELECT_SUBJECT_INVENTORY_SUMMARIES = """
            SELECT s.id AS subject_id,
                   s.name AS subject_name,
                   s.is_locked AS subject_locked,
                   COUNT(q.id) AS question_count
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            GROUP BY s.id, s.name, s.is_locked
            ORDER BY s.id ASC""";

    private final JdbcClient jdbc;

    JdbcSubjectInventoryQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<SubjectInventorySummaryView> listSubjectInventorySummaries() {
        return jdbc.sql(SELECT_SUBJECT_INVENTORY_SUMMARIES)
                .query((row, rowNumber) -> new SubjectInventorySummaryView(
                        row.getInt("subject_id"),
                        row.getString("subject_name"),
                        row.getObject("subject_locked", Boolean.class),
                        row.getLong("question_count")))
                .list();
    }
}
